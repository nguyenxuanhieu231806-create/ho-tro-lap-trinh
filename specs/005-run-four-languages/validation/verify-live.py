"""Actual Docker compiler/runtime checks, ready to run once Docker Linux is available."""
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


CASES = {
    "python": {
        "hello": 'print("Xin chào")',
        "stdin": 'a, b = map(int, input().split())\nprint(a + b)',
        "compile_error": 'for i in range(2)\n    print(i)',
        "runtime_error": 'raise RuntimeError("loi kiem thu")',
        "timeout": 'while True:\n    pass',
        "output_limit": 'import sys\nsys.stdout.write("x" * 100000)',
    },
    "c": {
        "hello": '#include <stdio.h>\nint main(void) { puts("Xin chào"); return 0; }',
        "stdin": '#include <stdio.h>\nint main(void) { int a,b; if(scanf("%d%d",&a,&b)!=2) return 2; printf("%d\\n",a+b); return 0; }',
        "compile_error": 'int main(void) { int x = ; return 0; }',
        "runtime_error": 'int main(void) { return 7; }',
        "timeout": 'int main(void) { while(1) {} }',
        "output_limit": '#include <stdio.h>\nint main(void) { printf("%070000d", 0); return 0; }',
    },
    "cpp": {
        "hello": '#include <iostream>\nint main() { std::cout << "Xin chào\\n"; }',
        "stdin": '#include <iostream>\nint main() { int a,b; std::cin >> a >> b; std::cout << a+b << "\\n"; }',
        "compile_error": 'int main() { int x = ; return 0; }',
        "runtime_error": 'int main() { return 7; }',
        "timeout": 'int main() { while(true) {} }',
        "output_limit": '#include <iostream>\n#include <string>\nint main() { std::cout << std::string(100000, \'x\'); }',
    },
    "java": {
        "hello": 'package edu.hpuni; public class Welcome { public static void main(String[] args) { System.out.println("Xin chào"); } }',
        "stdin": 'import java.util.Scanner; public class Sum { public static void main(String[] args) { Scanner s=new Scanner(System.in); System.out.println(s.nextInt()+s.nextInt()); } }',
        "compile_error": 'public class CompileError { public static void main(String[] args) { int x = ; } }',
        "runtime_error": 'public class RuntimeErrorTest { public static void main(String[] args) { throw new RuntimeException("loi kiem thu"); } }',
        "timeout": 'public class Loop { public static void main(String[] args) { while(true) {} } }',
        "output_limit": 'public class Many { public static void main(String[] args) { System.out.print("x".repeat(100000)); } }',
    },
}


def save(report):
    Path(__file__).with_name("live-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    state = runner.runner_status()
    if not state["available"]:
        report = {"state": "blocked", "reason": state["reason"], "executed": 0, "passed": 0,
                  "note": "Actual Docker compiler tests have not run. Controlled protocol results are reported separately."}
        save(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    outcomes = []
    for language, cases in CASES.items():
        for kind, source in cases.items():
            result = runner.run_code(language, source, "7 5\n" if kind == "stdin" else "")
            wanted_status = "completed" if kind in {"hello", "stdin"} else kind
            passed = result["status"] == wanted_status
            if kind == "hello":
                passed = passed and result["stdout"].replace("\r\n", "\n") == "Xin chào\n"
            elif kind == "stdin":
                passed = passed and result["stdout"].replace("\r\n", "\n") == "12\n"
            elif kind == "runtime_error":
                passed = passed and isinstance(result["exit_code"], int) and result["exit_code"] != 0
            elif kind == "output_limit":
                passed = passed and len(result["stdout"].encode("utf-8")) <= runner.MAX_IO
            outcomes.append({
                "language": language, "case": kind, "expected_status": wanted_status,
                "status": result["status"], "passed": passed, "exit_code": result["exit_code"],
                "duration_ms": result["duration_ms"], "stdout_sample": result["stdout"][:200],
                "stderr_sample": result["stderr"][:400], "message": result["message"],
            })
            print(language, kind, result["status"], "PASS" if passed else "FAIL", flush=True)

    # This fixed Python test runs only in Docker and lets the caller inspect cleanup.
    cancellation = threading.Event()
    launch_seen = threading.Event()
    names = []
    results = []
    original_command = runner._bounded_command

    def trace_command(command, **kwargs):
        if len(command) > 1 and command[1] == "run":
            names.append(command[command.index("--name") + 1])
            launch_seen.set()
        return original_command(command, **kwargs)

    def cancel_target():
        results.append(runner.run_code("python", CASES["python"]["timeout"], cancelled=cancellation))

    with patch.object(runner, "_bounded_command", side_effect=trace_command):
        worker = threading.Thread(target=cancel_target)
        worker.start()
        if launch_seen.wait(timeout=20):
            time.sleep(0.3)
        cancellation.set()
        worker.join(timeout=15)
    cleanup_ok = bool(results) and results[0]["status"] == "cancelled" and not worker.is_alive()
    cli = runner._docker_cli()
    for name in names:
        state_after = original_command([cli, "inspect", "--format", "{{.State.Running}}", name], timeout=5, max_output=8192)
        cleanup_ok = cleanup_ok and state_after["returncode"] != 0
    outcomes.append({"case": "cancellation and named container cleanup", "passed": cleanup_ok,
                     "status": results[0]["status"] if results else "worker did not finish",
                     "containers_observed": len(names)})
    report = {
        "state": "passed" if all(item["passed"] for item in outcomes) else "failed",
        "executed": len(outcomes), "passed": sum(item["passed"] for item in outcomes),
        "image": state.get("image_id"), "results": outcomes,
    }
    save(report)
    print(json.dumps({"state": report["state"], "executed": report["executed"], "passed": report["passed"]}, ensure_ascii=False))
    return 0 if report["state"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
