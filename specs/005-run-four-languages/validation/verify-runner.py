"""Regression checks for the runner protocol; compilers are simulated here."""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import code_verifier as runner

READY = {"available": True, "image_id": "sha256:" + "0" * 64, "reason": "test"}
SOURCES = {
    "python": 'a, b = map(int, input().split())\nprint(a + b)\n',
    "c": '#include <stdio.h>\nint main(void) { int a,b; scanf("%d%d",&a,&b); printf("%d\\n",a+b); return 0; }\n',
    "cpp": '#include <iostream>\nint main() { int a,b; std::cin >> a >> b; std::cout << a+b << "\\n"; }\n',
    "java": 'package edu.hpuni; public class Demo { public static void main(String[] args) { System.out.println("Xin chào"); } }\n',
}
FIELDS = {"language", "status", "stdout", "stderr", "exit_code", "duration_ms", "message"}


def transport(reply):
    return {
        "stdout": json.dumps(reply, ensure_ascii=False), "stderr": "", "returncode": 0,
        "timeout": False, "overflow": False, "cancelled": False,
    }


def reply(status="completed", output="12\n", stderr="", exit_code=0):
    return {
        "protocol": 1, "compile_ok": True, "compile_exit_code": 0,
        "compile_output": "", "compile_error": "",
        "cases": [{"status": status, "output": output, "stderr": stderr, "exit_code": exit_code}],
    }


def main():
    checks = []

    def record(name):
        checks.append(name)

    with patch.object(runner, "runner_status", return_value=READY):
        for language, source in SOURCES.items():
            for status, exit_code in (("completed", 0), ("runtime_error", 7), ("timeout", -9), ("output_limit", -25)):
                expected = reply(status, "Xin chào\n", "diagnostic", exit_code)
                with patch.object(runner, "_run_sandbox", return_value=transport(expected)) as send:
                    result = runner.run_code(language, source, "7 5\n")
                    assert set(result) == FIELDS
                    assert result["language"] == language and result["status"] == status
                    assert result["stdout"] == "Xin chào\n" and result["exit_code"] == exit_code
                    assert result["duration_ms"] >= 0
                    assert send.call_args.args[:3] == (language, source, ["7 5\n"])
                record(language + " " + status + " protocol and exact source/stdin")
            failed_compile = {
                "protocol": 1, "compile_ok": False, "compile_exit_code": 1,
                "compile_output": "", "compile_error": "source:2: compiler error", "cases": [],
            }
            with patch.object(runner, "_run_sandbox", return_value=transport(failed_compile)):
                result = runner.run_code(language, source)
                assert result["status"] == "compile_error" and result["exit_code"] == 1
                assert result["stderr"] == failed_compile["compile_error"]
            record(language + " compile_error")
        for language, source in SOURCES.items():
            with patch.object(runner, "_run_sandbox", return_value=transport({"protocol": 0})):
                assert runner.run_code(language, source)["status"] == "unavailable"
            cancelled = threading.Event()
            cancelled.set()
            with patch.object(runner, "_run_sandbox") as send:
                assert runner.run_code(language, source, cancelled=cancelled)["status"] == "cancelled"
                send.assert_not_called()
            record(language + " malformed protocol and cancellation")

        data = reply(output="é" * 65536, stderr="ề" * 65536)
        data["compile_error"] = "warning: a reviewed compiler warning"
        with patch.object(runner, "_run_sandbox", return_value=transport(data)):
            result = runner.run_code("python", SOURCES["python"])
            assert len(result["stdout"].encode("utf-8")) <= runner.MAX_IO
            assert len(result["stderr"].encode("utf-8")) <= runner.MAX_IO
            assert result["stderr"].startswith("warning:")
        record("UTF-8 output bounds and retained compiler warnings")

        for malformed in (
            {"protocol": 1, "compile_ok": True, "compile_exit_code": 0, "compile_output": "", "compile_error": "", "cases": []},
            {"protocol": 1, "compile_ok": True, "compile_exit_code": 0, "compile_output": "", "compile_error": "", "cases": [None]},
            {"protocol": 1, "phase": "compile", "status": "timeout", "compile_output": None},
        ):
            with patch.object(runner, "_run_sandbox", return_value=transport(malformed)):
                assert runner.run_code("python", SOURCES["python"])["status"] == "unavailable"
        record("Malformed protocol fails closed")
        compile_timeout = {
            "protocol": 1, "phase": "compile", "status": "timeout", "infrastructure_error": True,
            "compile_output": "", "compile_error": "compiler interrupted", "compile_exit_code": -9,
        }
        with patch.object(runner, "_run_sandbox", return_value=transport(compile_timeout)):
            assert runner.run_code("java", SOURCES["java"])["status"] == "timeout"
        record("Compiler timeout classified")

    calls = []

    def fake_command(command, **kwargs):
        calls.append((command, kwargs))
        return transport(reply())

    for language, source in SOURCES.items():
        calls.clear()
        with patch.object(runner, "_docker_cli", return_value="docker-test"), patch.object(runner, "_bounded_command", side_effect=fake_command):
            runner._run_sandbox(language, source, ["Xin chào\n7 5\n"], READY)
        command, arguments = calls[0]
        data = json.loads(arguments["payload"].decode("utf-8"))
        assert data == {"language": language, "source": source, "inputs": ["Xin chào\n7 5\n"]}
        assert command[command.index("--network") + 1] == "none"
        assert command[command.index("--memory") + 1] == "512m"
        assert command[command.index("--memory-swap") + 1] == "512m"
        assert command[command.index("--cpus") + 1] == "1"
        assert command[command.index("--pids-limit") + 1] == "96"
        assert command[command.index("--cap-drop") + 1] == "ALL"
        assert "--read-only" in command and "no-new-privileges" in command
        assert "--mount" not in command and "--volume" not in command and "-v" not in command
        assert not any(str(ROOT) in str(part) for part in command)
        name = command[command.index("--name") + 1]
        assert calls[-1][0] == ["docker-test", "rm", "--force", name]
        record(language + " Docker isolation, input-only payload and exact cleanup")

    with patch.object(runner, "sandbox_status", return_value=dict(READY)), patch.object(runner, "_docker_cli", return_value="docker-test"):
        with patch.object(runner, "_bounded_command", return_value={"returncode": 0, "stdout": "1\n"}):
            assert runner.runner_status()["available"]
        with patch.object(runner, "_bounded_command", return_value={"returncode": 0, "stdout": "<no value>\n"}):
            state = runner.runner_status()
            assert not state["available"] and "docker build" in state["reason"]
    record("Versioned runner image readiness")

    with patch.object(runner, "sandbox_status", return_value=READY), patch.object(runner, "_run_sandbox", return_value=transport(reply(output="12\n"))):
        evidence = runner.verify_code("c", SOURCES["c"], [{"input": "7 5\n", "expected_output": "12"}])
        assert evidence["passed"] == 1 and evidence["verified"] and evidence["compile_ok"]
    assert runner.verify_code("python", "return 4")["syntax_ok"] is False
    assert runner.verify_code("python", "def double(x):\n    return 2*x\n")["verified"] is False
    record("Existing verify_code contract preserved")

    java_cases = [
        ('package edu.hpuni; public class Demo {}', ("Demo.java", "edu.hpuni.Demo")),
        ('/* public class Fake {} */ class Main { String s="class FalseName"; }', ("Main.java", "Main")),
        ('class Outer { public class Inner {} }', ("Outer.java", "Outer")),
        ('package thử; public final class Chào {}', ("Chào.java", "thử.Chào")),
        ('package sample; public record Data(int x) {}', ("Data.java", "sample.Data")),
    ]
    for source, expected in java_cases:
        assert runner._java_program(source) == expected
    record("Java public type, package, comments, nested types and Unicode")

    event = threading.Event()
    timer = threading.Timer(0.15, event.set)
    timer.start()
    started = time.monotonic()
    # This fixed test helper sleeps only. No submitted program executes on the host.
    result = runner._bounded_command([sys.executable, "-c", "import time; time.sleep(10)"], timeout=6, cancelled=event)
    timer.join()
    cancellation_ms = round((time.monotonic() - started) * 1000)
    assert result["cancelled"] and not result["timeout"] and cancellation_ms < 5000
    record("Trusted helper process cancellation")

    result = runner._bounded_command(
        [sys.executable, "-c", 'import sys; sys.stdout.write("x" * 100000)'],
        max_output=1024,
    )
    assert result["overflow"] and len(result["stdout"].encode()) <= 1024
    record("Trusted helper output overflow is bounded")

    report = {
        "mode": "controlled protocol and trusted helper checks",
        "submitted_code_executed_on_host": False,
        "live_docker_compiler_tests": "not executed by this script",
        "passed": len(checks), "checks": checks, "cancellation_ms": cancellation_ms,
    }
    Path(__file__).with_name("runner-results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
