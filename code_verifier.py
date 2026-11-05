"""Bounded code checks; submitted programs run only in a local Docker sandbox.

Build the optional image: docker build -f Dockerfile.grader -t fit-tutor-grader:1 .
No compiler, interpreter, shell, or submitted program is invoked on the web host.
Python AST/compile() checks produce code objects only; they never execute them.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

MAX_SOURCE = 60000
MAX_TESTS = 10
MAX_IO = 65536
MAX_DOCKER_REPLY = 2 * 1024 * 1024
MAX_COMPILE_FILE = 16 * 1024 * 1024
RUN_TIMEOUT = 3
IMAGE = os.getenv("TUTOR_GRADER_IMAGE", "fit-tutor-grader:1")
LANGUAGES = {"python", "java", "c", "cpp"}


def _docker_cli():
    found = shutil.which("docker")
    if found:
        return found
    if os.name == "nt":
        candidate = Path(os.getenv("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe"
        if candidate.is_file():
            return str(candidate)
    return None


def _bounded_command(command, *, payload=None, timeout=8, max_output=MAX_DOCKER_REPLY, cancelled=None):
    """Drain both pipes with a strict memory bound, including hostile output."""
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    output, errors = bytearray(), bytearray()
    overflow = threading.Event()
    lock = threading.Lock()

    def drain(pipe, target):
        try:
            while True:
                chunk = pipe.read(4096)
                if not chunk:
                    break
                with lock:
                    room = max_output - len(output) - len(errors)
                    target.extend(chunk[:max(0, room)])
                    if len(chunk) > room:
                        overflow.set()
                if overflow.is_set():
                    process.kill()
        except (OSError, ValueError):
            pass
        finally:
            pipe.close()

    readers = [threading.Thread(target=drain, args=(process.stdout, output), daemon=True),
               threading.Thread(target=drain, args=(process.stderr, errors), daemon=True)]
    for reader in readers:
        reader.start()

    def feed():
        try:
            process.stdin.write(payload)
            process.stdin.close()
        except (OSError, ValueError):
            pass

    writer = None
    if payload is not None:
        writer = threading.Thread(target=feed, daemon=True)
        writer.start()
    timed_out = False
    was_cancelled = False
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        was_cancelled = cancelled is not None and cancelled.is_set()
        remaining = deadline - time.monotonic()
        if was_cancelled or remaining <= 0:
            timed_out = not was_cancelled
            process.kill()
            break
        try:
            process.wait(timeout=min(0.1, remaining))
        except subprocess.TimeoutExpired:
            continue
    if process.poll() is None:
        process.kill()
        process.wait(timeout=3)
    for reader in readers:
        reader.join(timeout=2)
    if writer:
        writer.join(timeout=1)
    if any(reader.is_alive() for reader in readers):
        timed_out = True
    return {
        "returncode": process.returncode, "stdout": bytes(output).decode("utf-8", "replace"),
        "stderr": bytes(errors).decode("utf-8", "replace"), "timeout": timed_out,
        "overflow": overflow.is_set(), "cancelled": was_cancelled,
    }


def sandbox_status(cancelled=None):
    """Read-only readiness check; never downloads an image or starts Docker."""
    result = {"available": False, "image": IMAGE, "reason": "Chưa cài Docker Desktop để chạy mã trong môi trường cách ly."}
    cli = _docker_cli()
    if not cli:
        return result
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/@:\-]{0,220}", IMAGE):
        result["reason"] = "Tên image kiểm chứng không hợp lệ."
        return result
    try:
        daemon = _bounded_command([cli, "version", "--format", "{{.Server.Os}}"], max_output=8192, cancelled=cancelled)
        if daemon["returncode"] != 0 or daemon["stdout"].strip() != "linux":
            result["reason"] = "Docker Linux chưa sẵn sàng. Hãy mở Docker Desktop trước khi kiểm chứng code."
            return result
        image = _bounded_command([cli, "image", "inspect", "--format", "{{.Id}}", IMAGE], max_output=8192, cancelled=cancelled)
        image_id = image["stdout"].strip()
        if image["returncode"] != 0 or not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
            result["reason"] = "Chưa có image kiểm chứng. Chạy: docker build -f Dockerfile.grader -t " + IMAGE + " ."
            return result
        result.update(available=True, image_id=image_id, reason="Môi trường Docker Linux và image kiểm chứng đã có.")
    except (OSError, subprocess.SubprocessError):
        result["reason"] = "Không kết nối được Docker trong thời gian cho phép."
    return result


def runner_status(cancelled=None):
    """Require the versioned output protocol before exposing console execution."""
    result = sandbox_status(cancelled)
    result.update(run_timeout_seconds=RUN_TIMEOUT, compile_timeout_seconds=15,
                  languages=sorted(LANGUAGES), max_source_chars=MAX_SOURCE, max_stdin_chars=16384)
    if not result["available"]:
        return result
    try:
        label = _bounded_command(
            [_docker_cli(), "image", "inspect", "--format",
             '{{ index .Config.Labels "fit-tutor.runner-protocol" }}', result["image_id"]],
            max_output=8192, cancelled=cancelled,
        )
        if label["returncode"] != 0 or label["stdout"].strip() != "1":
            result.update(available=False, reason="Image chạy mã cần được cập nhật. Chạy: docker build -f Dockerfile.grader -t " + IMAGE + " .")
        else:
            result["reason"] = "Môi trường chạy C, C++, Java và Python đã sẵn sàng."
    except (OSError, subprocess.SubprocessError):
        result.update(available=False, reason="Không kiểm tra được phiên bản môi trường chạy mã.")
    return result


def _sandbox_command(cli, name, image_id):
    return [
        cli, "run", "--pull=never", "--rm", "--interactive", "--name", name,
        "--network", "none", "--read-only", "--cpus", "1", "--memory", "512m",
        "--memory-swap", "512m", "--pids-limit", "96", "--cap-drop", "ALL",
        "--cap-add", "SETUID", "--cap-add", "SETGID", "--cap-add", "CHOWN", "--cap-add", "KILL",
        "--security-opt", "no-new-privileges",
        "--ulimit", "nofile=64:64", "--ulimit", "core=0:0",
        "--tmpfs", "/work:rw,exec,nosuid,nodev,size=64m,mode=1777",
        "--tmpfs", "/capture:rw,nosuid,nodev,noexec,size=4m,mode=700",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777",
        "--user", "0:0", image_id,
    ]


def _run_sandbox(language, source, inputs, status, cancelled=None):
    cli, name = _docker_cli(), "fit-grader-" + uuid.uuid4().hex
    payload = json.dumps({"language": language, "source": source, "inputs": inputs}, ensure_ascii=False).encode("utf-8")
    try:
        return _bounded_command(_sandbox_command(cli, name, status["image_id"]), payload=payload,
                                timeout=30 + len(inputs) * 5, cancelled=cancelled)
    finally:
        try:
            _bounded_command([cli, "rm", "--force", name], timeout=5, max_output=8192)
        except (OSError, subprocess.SubprocessError):
            pass


def run_code(language, source, stdin="", cancelled=None):
    """Run one console program in Docker and return observed output only."""
    if language not in LANGUAGES or not isinstance(source, str) or not source.strip() or len(source) > MAX_SOURCE:
        raise ValueError("Ngôn ngữ không hợp lệ, mã rỗng hoặc vượt 60.000 ký tự.")
    if not isinstance(stdin, str) or len(stdin) > 16384 or len(stdin.encode("utf-8")) > MAX_IO:
        raise ValueError("Dữ liệu nhập vượt giới hạn 16.384 ký tự hoặc 64 KiB.")
    started = time.monotonic()

    def finish(status, message, stdout="", stderr="", exit_code=None):
        return {"language": language, "status": status,
                "stdout": stdout.encode("utf-8")[:MAX_IO].decode("utf-8", "ignore"),
                "stderr": stderr.encode("utf-8")[:MAX_IO].decode("utf-8", "ignore"),
                "exit_code": exit_code, "duration_ms": round((time.monotonic() - started) * 1000),
                "message": message}

    if cancelled is not None and cancelled.is_set():
        return finish("cancelled", "Đã dừng yêu cầu chạy mã.")
    status = runner_status(cancelled)
    if cancelled is not None and cancelled.is_set():
        return finish("cancelled", "Đã dừng yêu cầu chạy mã.")
    if not status["available"]:
        return finish("unavailable", status["reason"])
    try:
        run = _run_sandbox(language, source, [stdin], status, cancelled)
        if run["cancelled"] or (cancelled is not None and cancelled.is_set()):
            return finish("cancelled", "Đã dừng chương trình và dọn môi trường chạy.")
        if run["timeout"] or run["overflow"] or run["returncode"] != 0:
            return finish("unavailable", "Môi trường chạy bị gián đoạn hoặc vượt giới hạn. Hãy thử lại.")
        reply = json.loads(run["stdout"])
        if not isinstance(reply, dict) or reply.get("protocol") != 1:
            raise ValueError("Invalid runner protocol")
        if reply.get("phase") == "compile" and reply.get("status") in {"timeout", "output_limit"}:
            if (not isinstance(reply.get("compile_output"), str)
                    or not isinstance(reply.get("compile_error"), str)
                    or not isinstance(reply.get("compile_exit_code"), int)):
                raise ValueError("Invalid compiler limit evidence")
            return finish(reply["status"], "Biên dịch vượt giới hạn thời gian hoặc đầu ra và đã bị dừng.",
                          reply.get("compile_output", ""), reply.get("compile_error", ""), reply.get("compile_exit_code"))
        if reply.get("infrastructure_error"):
            raise ValueError("Sandbox infrastructure error")
        compiled = reply.get("compile_ok")
        compile_output = reply.get("compile_output", "")
        compile_error = reply.get("compile_error", "")
        compile_exit = reply.get("compile_exit_code")
        if (not isinstance(compiled, bool) or not isinstance(compile_output, str)
                or not isinstance(compile_error, str) or not isinstance(compile_exit, int)):
            raise ValueError("Missing compiler evidence")
        if not compiled:
            return finish("compile_error", "Biên dịch hoặc kiểm tra cú pháp không thành công.",
                          compile_output[:MAX_IO], compile_error[:MAX_IO], compile_exit)
        cases = reply.get("cases")
        if not isinstance(cases, list) or len(cases) != 1 or not isinstance(cases[0], dict):
            raise ValueError("Missing execution evidence")
        case = cases[0]
        outcome = case.get("status")
        if outcome not in {"completed", "runtime_error", "timeout", "output_limit"}:
            raise ValueError("Invalid execution outcome")
        stdout, stderr, exit_code = case.get("output"), case.get("stderr"), case.get("exit_code")
        if not isinstance(stdout, str) or not isinstance(stderr, str) or not isinstance(exit_code, int):
            raise ValueError("Invalid output")
        if compile_error:
            stderr = compile_error.rstrip() + "\n" + stderr
        messages = {
            "completed": "Chương trình đã kết thúc. Hãy đối chiếu kết quả với yêu cầu bài toán.",
            "runtime_error": "Chương trình gặp lỗi khi thực thi. Xem thông báo lỗi bên dưới.",
            "timeout": "Chương trình vượt giới hạn chạy 3 giây và đã bị dừng.",
            "output_limit": "Chương trình xuất quá nhiều dữ liệu và đã bị dừng ở giới hạn 64 KiB.",
        }
        return finish(outcome, messages[outcome], stdout[:MAX_IO], stderr[:MAX_IO], exit_code)
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
        return finish("unavailable", "Không nhận được kết quả chạy hợp lệ. Kiểm tra Docker và thử lại.")


def _evidence(total):
    return {"available": False, "syntax_ok": None, "compile_ok": None, "passed": 0,
            "total": total, "cases": [], "errors": [], "reason": "Chưa kiểm chứng.",
            "verified": False, "tool": "docker"}


def _test_values(test):
    if hasattr(test, "model_dump"):
        test = test.model_dump()
    if not isinstance(test, dict):
        raise ValueError("Test case phải là dữ liệu có cấu trúc.")
    given = test.get("input", test.get("stdin", ""))
    wanted = test.get("expected_output", test.get("output", test.get("stdout")))
    if not isinstance(given, str) or not isinstance(wanted, str):
        raise ValueError("Input và output chuẩn phải là chuỗi.")
    if len(given.encode("utf-8")) > MAX_IO or len(wanted.encode("utf-8")) > MAX_IO:
        raise ValueError("Input/output vượt giới hạn 64 KiB cho mỗi test.")
    return given, wanted


def _normal_output(text):
    # Preserve spaces inside lines; tolerate OS newlines and final whitespace only.
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip()


def _diagnostics(stderr):
    items = []
    for line in stderr.splitlines():
        match = re.search(r"[^/\s:]+\.(?:c|cpp|py|java):(\d+)(?::\d+)?:\s*(.*)", line)
        if match and ("error" in line.lower() or "warning" in line.lower()):
            items.append({"line": int(match.group(1)), "message": match.group(2)[:1000]})
        if len(items) >= 15:
            break
    return items or [{"line": None, "message": stderr.strip()[:3000] or "Trình biên dịch không hoàn thành."}]


def verify_code(language, source, test_cases=()):
    """Compile and optionally test, failing closed when isolation is unavailable.

    `available=False` is infrastructure failure, never a zero mark. `verified`
    means every supplied test was executed/classified, not proof of all behavior.
    A compiler error has `compile_ok=False` even without executing any test.
    """
    if language not in LANGUAGES or not isinstance(source, str) or len(source) > MAX_SOURCE:
        raise ValueError("Ngôn ngữ không hợp lệ hoặc mã nguồn vượt 60.000 ký tự.")
    tests = list(test_cases)
    if len(tests) > MAX_TESTS:
        raise ValueError("Chỉ hỗ trợ tối đa 10 test case cho một lượt kiểm chứng.")
    values = [_test_values(test) for test in tests]
    evidence = _evidence(len(values))
    if language == "python":
        try:
            ast.parse(source, filename="main.py")
            compile(source, "main.py", "exec", dont_inherit=True)
        except SyntaxError as exc:
            evidence.update(available=True, syntax_ok=False, compile_ok=False, tool="python-parser",
                            reason="Mã Python có lỗi cú pháp; chương trình chưa được chạy.",
                            errors=[{"line": exc.lineno, "message": exc.msg[:1000]}])
            return evidence
        except (ValueError, RecursionError, MemoryError):
            evidence["reason"] = "Không phân tích được cấu trúc Python trong giới hạn cho phép."
            return evidence
        evidence["syntax_ok"] = True
        if not values:
            evidence.update(available=True, compile_ok=True, tool="python-parser",
                            reason="Cú pháp Python hợp lệ; chưa chạy test và chưa xác nhận logic.")
            return evidence
    status = sandbox_status()
    if not status["available"]:
        evidence["reason"] = status["reason"]
        return evidence
    try:
        # The sandbox receives inputs only; expected answers stay on the web host.
        run = _run_sandbox(language, source, [given for given, _ in values], status)
        if run["timeout"] or run["overflow"] or run["returncode"] != 0:
            evidence["reason"] = "Môi trường kiểm chứng bị ngắt hoặc vượt giới hạn; chưa thể kết luận Đúng/Sai."
            return evidence
        reply = json.loads(run["stdout"])
        if not isinstance(reply, dict) or reply.get("infrastructure_error"):
            evidence["reason"] = "Môi trường cách ly chưa hoàn thành kiểm chứng; không chấm điểm từ kết quả thiếu."
            return evidence
        compiled = reply.get("compile_ok")
        if not isinstance(compiled, bool):
            raise ValueError("Missing compiler evidence")
        evidence.update(available=True, compile_ok=compiled)
        if language == "python":
            evidence["syntax_ok"] = compiled
        if not compiled:
            stderr = reply.get("compile_error", "")
            evidence.update(errors=_diagnostics(str(stderr)), reason="Biên dịch không thành công; chưa chạy bài làm.")
            return evidence
        observed = reply.get("cases")
        if not isinstance(observed, list) or len(observed) != len(values):
            raise ValueError("Missing test evidence")
        for index, ((_, wanted), case) in enumerate(zip(values, observed), 1):
            if not isinstance(case, dict) or case.get("status") not in {"completed", "timeout", "runtime_error", "output_limit"}:
                raise ValueError("Invalid test evidence")
            output = case.get("output", "")
            stderr = case.get("stderr", "")
            if not isinstance(output, str) or not isinstance(stderr, str):
                raise ValueError("Invalid output")
            passed = case["status"] == "completed" and _normal_output(output) == _normal_output(wanted)
            evidence["cases"].append({"index": index, "passed": passed,
                                      "status": "passed" if passed else ("wrong_answer" if case["status"] == "completed" else case["status"]),
                                      "output": output[:MAX_IO], "stderr": stderr[:3000]})
        evidence["passed"] = sum(case["passed"] for case in evidence["cases"])
        evidence.update(verified=bool(values), reason=(f"Vượt qua {evidence['passed']}/{len(values)} test case đã cung cấp."
                                                      if values else "Biên dịch thành công; chưa chạy test và chưa xác nhận logic."))
        return evidence
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        evidence.update(available=False, compile_ok=None, cases=[], passed=0, verified=False,
                        reason="Không lấy được bằng chứng kiểm chứng hợp lệ; chưa thể kết luận Đúng/Sai.")
        return evidence


def _java_program(source):
    """Select a top-level Java source filename and its qualified entry class."""
    literals = r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    code = re.sub(literals, lambda match: re.sub(r"[^\n]", " ", match.group()), source)
    identifier = r"(?:[^\W\d]|[$_])(?:\w|[$])*"
    package = re.search(r"\bpackage\s+(" + identifier + r"(?:\s*\.\s*" + identifier + r")*)\s*;", code)
    package_name = re.sub(r"\s+", "", package.group(1)) if package else ""
    declaration = re.compile(
        r"\b(?P<modifiers>(?:(?:public|abstract|final|strictfp|sealed|non-sealed)\s+)*)"
        r"(?:class|record|enum|interface)\s+(?P<name>" + identifier + ")"
    )
    candidates, depth, previous = [], 0, 0
    for match in declaration.finditer(code):
        between = code[previous:match.start()]
        depth += between.count("{") - between.count("}")
        previous = match.end()
        if depth == 0:
            candidates.append(("public" in match.group("modifiers").split(), match.group("name")))
    name = next((name for public, name in candidates if public), None)
    if name is None:
        name = next((name for _, name in candidates if name == "Main"), candidates[0][1] if candidates else "Main")
    return name + ".java", (package_name + "." if package_name else "") + name


def _sandbox_main():
    """Trusted PID 1 in the optional Linux image; never call this on the host."""
    if sys.platform != "linux" or os.getpid() != 1 or os.geteuid() != 0 or not Path("/.dockerenv").is_file():
        raise SystemExit("Sandbox entry point requires an isolated Docker PID namespace.")
    import resource

    def drop_privileges(seconds, file_limit):
        os.setgroups([])
        os.setgid(65534)
        os.setuid(65534)
        resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def reap_students():
        # Freeze then kill every student UID in this private PID namespace,
        # including descendants that escaped the original process group.
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            victims = []
            for entry in Path("/proc").iterdir():
                if entry.name.isdigit():
                    try:
                        if entry.stat().st_uid == 65534:
                            victims.append(int(entry.name))
                    except OSError:
                        pass
            if not victims:
                return True
            for sig in (signal.SIGSTOP, signal.SIGKILL):
                for pid in victims:
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass
            while True:
                try:
                    if os.waitpid(-1, os.WNOHANG)[0] == 0:
                        break
                except ChildProcessError:
                    break
            # Allow the kernel to reap killed descendants; this is cleanup,
            # not an artificial delay in AI or student execution.
            threading.Event().wait(0.005)
        return False

    def invoke(command, cwd, given, seconds, *, file_limit=MAX_IO):
        started = time.monotonic()
        with tempfile.TemporaryFile(dir="/capture") as out, tempfile.TemporaryFile(dir="/capture") as err:
            child = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                     start_new_session=True, preexec_fn=lambda: drop_privileges(seconds, file_limit),
                                     env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(cwd),
                                          "TMPDIR": str(cwd), "LANG": "C.UTF-8", "PYTHONUTF8": "1",
                                          "PYTHONDONTWRITEBYTECODE": "1"})
            timed_out = False
            try:
                child.communicate(given.encode("utf-8"), timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait(timeout=2)
            clean = reap_students()
            out.seek(0); err.seek(0)
            stdout, stderr = out.read(MAX_IO), err.read(MAX_IO)
            limited = len(stdout) >= MAX_IO or len(stderr) >= MAX_IO or child.returncode == -signal.SIGXFSZ
            return {"returncode": child.returncode, "timeout": timed_out, "output_limit": limited,
                    "output": stdout.decode("utf-8", "replace"), "stderr": stderr.decode("utf-8", "replace"),
                    "clean": clean, "duration_ms": round((time.monotonic() - started) * 1000)}

    try:
        payload = json.loads(sys.stdin.buffer.read(4 * 1024 * 1024))
        language, source, inputs = payload["language"], payload["source"], payload["inputs"]
        if language not in LANGUAGES or not isinstance(source, str) or len(source) > MAX_SOURCE:
            raise ValueError("Invalid source")
        if not isinstance(inputs, list) or len(inputs) > MAX_TESTS or any(not isinstance(v, str) or len(v.encode()) > MAX_IO for v in inputs):
            raise ValueError("Invalid tests")
        work = Path("/work")
        filename = {"python": "main.py", "java": "Main.java", "c": "main.c", "cpp": "main.cpp"}[language]
        java_class = "Main"
        if language == "java":
            filename, java_class = _java_program(source)
        (work / filename).write_text(source, encoding="utf-8")
        (work / filename).chmod(0o444)
        javac_options = ["-J-Xmx128m", "-J-XX:MaxMetaspaceSize=128m", "-J-XX:ActiveProcessorCount=1"]
        commands = {
            "python": ["python3", "-I", "-c", "import pathlib; compile(pathlib.Path('main.py').read_text(encoding='utf-8'), 'main.py', 'exec')"],
            "c": ["gcc", "-std=c11", "-O0", "-Wall", "-Wextra", filename, "-o", "/work/program"],
            "cpp": ["g++", "-std=c++17", "-O0", "-Wall", "-Wextra", filename, "-o", "/work/program"],
            "java": ["javac", *javac_options, "-proc:none", "-encoding", "UTF-8", "-d", "/work/classes", filename],
        }
        compiled = invoke(commands[language], work, "", 15, file_limit=MAX_COMPILE_FILE)
        compile_fields = {"protocol": 1, "compile_exit_code": compiled["returncode"],
                          "compile_output": compiled["output"], "compile_error": compiled["stderr"]}
        if not compiled["clean"] or compiled["timeout"] or compiled["output_limit"]:
            status = "timeout" if compiled["timeout"] else "output_limit" if compiled["output_limit"] else "unavailable"
            print(json.dumps({**compile_fields, "infrastructure_error": True, "phase": "compile", "status": status}), flush=True)
            return
        if compiled["returncode"] != 0:
            infra_markers = ("could not create the java virtual machine", "insufficient memory",
                             "outofmemoryerror", "killed signal terminated program", "cannot allocate memory",
                             "no space left on device", "file size limit exceeded")
            if compiled["returncode"] < 0 or any(marker in compiled["stderr"].lower() for marker in infra_markers):
                print(json.dumps({"infrastructure_error": True}), flush=True)
                return
            print(json.dumps({**compile_fields, "compile_ok": False, "cases": []}), flush=True)
            return
        # Source and compiler artifacts are immutable to later student processes.
        for artifact in work.rglob("*"):
            if artifact.is_symlink():
                raise ValueError("Unexpected compiler artifact")
            os.chown(artifact, 0, 0)
            artifact.chmod(0o555 if artifact.is_dir() or artifact.name == "program" else 0o444)
        outcomes = []
        runtime = {"python": ["python3", "-I", "-B", "/work/main.py"],
                   "java": ["java", "-Xmx128m", "-Xss256k", "-XX:MaxMetaspaceSize=96m",
                            "-XX:CompressedClassSpaceSize=32m", "-XX:ReservedCodeCacheSize=32m",
                            "-XX:ActiveProcessorCount=1", "-cp", "/work/classes", java_class],
                   "c": ["/work/program"], "cpp": ["/work/program"]}[language]
        for index, given in enumerate(inputs):
            case_dir = work / ("case-" + str(index))
            # Popen enters cwd before preexec_fn drops UID. The controller has
            # no DAC_OVERRIDE; allow traversal while only the student can write.
            case_dir.mkdir(mode=0o755)
            os.chown(case_dir, 65534, 65534)
            observed = invoke(runtime, case_dir, given, RUN_TIMEOUT)
            if not observed["clean"]:
                raise ValueError("Unable to clean student processes")
            status = "timeout" if observed["timeout"] else "output_limit" if observed["output_limit"] else "runtime_error" if observed["returncode"] != 0 else "completed"
            outcomes.append({"status": status, "output": observed["output"], "stderr": observed["stderr"],
                             "exit_code": observed["returncode"], "duration_ms": observed["duration_ms"]})
        print(json.dumps({**compile_fields, "compile_ok": True, "cases": outcomes}, ensure_ascii=True), flush=True)
    except Exception:
        print(json.dumps({"infrastructure_error": True}), flush=True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--sandbox"]:
        _sandbox_main()
    else:
        raise SystemExit("Import verify_code() from the web server; do not run submitted code on the host.")
