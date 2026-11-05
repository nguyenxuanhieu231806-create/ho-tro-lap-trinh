"""Exercise real authenticated HTTP routes against the actual Docker runner.

Only Ollama warm-up/health are replaced: execution, compiler, auth and HTTP are real.
Accounts are created in a temporary SQLite database, never in project data.
"""
from __future__ import annotations

import http.client
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api
import code_verifier as runner
import uvicorn

CASES = {
    "python": (
        'print("Xin chào")',
        'a, b = map(int, input().split())\nprint(a + b)',
    ),
    "c": (
        '#include <stdio.h>\nint main(void) { puts("Xin chào"); return 0; }',
        '#include <stdio.h>\nint main(void) { int a,b; if(scanf("%d%d",&a,&b)!=2) return 2; printf("%d\\n",a+b); return 0; }',
    ),
    "cpp": (
        '#include <iostream>\nint main() { std::cout << "Xin chào\\n"; }',
        '#include <iostream>\nint main() { int a,b; std::cin >> a >> b; std::cout << a+b << "\\n"; }',
    ),
    "java": (
        'package edu.hpuni; public class Welcome { public static void main(String[] args) { System.out.println("Xin chào"); } }',
        'import java.util.Scanner; public class Sum { public static void main(String[] args) { Scanner s=new Scanner(System.in); System.out.println(s.nextInt()+s.nextInt()); } }',
    ),
}


class NoOllamaWarmup:
    async def warmup(self):
        return {}

    async def health(self):
        return {"ready": True, "model": "validation-no-ollama-call", "message": "Ollama is not part of this runner test"}


def main():
    report = {"mode": "real HTTP, temporary SQLite, actual Docker compiler/runtime", "checks": [], "results": []}
    destination = Path(__file__).with_name("api-live-results.json")
    ready = runner.runner_status()
    if not ready["available"]:
        report.update(state="blocked", reason=ready["reason"], passed=0)
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    names = []
    launches = []
    original_command = runner._bounded_command

    def trace_command(command, **kwargs):
        if len(command) > 1 and command[1] == "run":
            name = command[command.index("--name") + 1]
            names.append(name)
            launches.append((name, kwargs.get("cancelled")))
        return original_command(command, **kwargs)

    def container_missing(name):
        state = original_command([runner._docker_cli(), "inspect", "--format", "{{.State.Running}}", name], timeout=5, max_output=8192)
        return state["returncode"] != 0

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        report["checks"].append(label)

    try:
        with tempfile.TemporaryDirectory(prefix="fit-run-api-live-") as temporary:
            with patch.object(api, "DB", Path(temporary) / "accounts.sqlite3"), \
                    patch.object(api, "OllamaTutor", NoOllamaWarmup), \
                    patch.object(runner, "_bounded_command", side_effect=trace_command):
                server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=0, log_level="error"))
                thread = threading.Thread(target=server.run, daemon=True)
                thread.start()
                deadline = time.monotonic() + 10
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.02)
                check("HTTP server starts with temporary account database", server.started)
                port = server.servers[0].sockets[0].getsockname()[1]
                base = "http://127.0.0.1:" + str(port)
                jar = http.cookiejar.CookieJar()
                client = build_opener(HTTPCookieProcessor(jar))

                def request(route, body=None):
                    payload = json.dumps(body).encode("utf-8") if body is not None else None
                    req = Request(base + route, data=payload, headers={"Content-Type": "application/json"})
                    try:
                        with client.open(req, timeout=50) as reply:
                            return reply.status, json.loads(reply.read())
                    except HTTPError as exc:
                        return exc.code, json.loads(exc.read())

                try:
                    check("runner readiness requires login", request("/api/tutor/runner")[0] == 401)
                    check("run requires login", request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 401)
                    account = api.ISSUED_ACCOUNTS[0]
                    status, profile = request("/api/auth/login", {"username": account["username"], "password": api.INITIAL_PASSWORD})
                    check("seeded account login succeeds in isolated SQLite", status == 200 and profile.get("username") == account["username"])
                    status, readiness = request("/api/tutor/runner")
                    check("actual Docker image is ready through HTTP", status == 200 and readiness["available"] and readiness["runtime_limit_seconds"] == 3)
                    for language, examples in CASES.items():
                        for index, code in enumerate(examples):
                            kind = "hello" if index == 0 else "stdin"
                            status, result = request("/api/tutor/run", {"language": language, "current_code": code, "stdin": "7 5\n" if index else ""})
                            report["results"].append({"language": language, "case": kind, "http": status, "result": result})
                            wanted = "Xin chào\n" if index == 0 else "12\n"
                            check(language + " " + kind + " executes through HTTP", status == 200 and result.get("status") == "completed" and
                                  result.get("stdout", "").replace("\r\n", "\n") == wanted and result.get("exit_code") == 0)
                    invalid = ({"language": "sql", "current_code": "select 1"}, {"language": "python", "current_code": "  "},
                               {"language": "python", "current_code": "x" * 60001}, {"language": "python", "current_code": "print(1)", "stdin": "x" * 16385})
                    check("invalid language/blank/oversized inputs rejected", all(request("/api/tutor/run", body)[0] == 400 for body in invalid))
                    before = len(launches)
                    cookie = "; ".join(item.name + "=" + item.value for item in jar)
                    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                    connection.request("POST", "/api/tutor/run", json.dumps({"language": "python", "current_code": "while True:\n    pass"}),
                                       {"Content-Type": "application/json", "Cookie": cookie})
                    deadline = time.monotonic() + 10
                    while len(launches) == before and time.monotonic() < deadline:
                        time.sleep(0.01)
                    check("pending HTTP request starts a real container", len(launches) > before)
                    name, cancel_event = launches[-1]
                    deadline = time.monotonic() + 2
                    running = False
                    while not running and time.monotonic() < deadline:
                        state = original_command([runner._docker_cli(), "inspect", "--format", "{{.State.Running}}", name], timeout=2, max_output=8192)
                        running = state["returncode"] == 0 and state["stdout"].strip() == "true"
                        if not running:
                            time.sleep(0.02)
                    check("container is running before disconnect", running)
                    check("parallel request receives busy response", request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 503)
                    connection.sock.shutdown(socket.SHUT_RDWR)
                    connection.close()
                    deadline = time.monotonic() + 10
                    while not cancel_event.is_set() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    check("disconnect signals the actual Docker worker", cancel_event.is_set())
                    while api.app.state.run_slots.locked() and time.monotonic() < deadline:
                        time.sleep(0.02)
                    check("run slot released after cancelled worker finishes", not api.app.state.run_slots.locked())
                    check("cancelled named container removed", container_missing(name))
                    status, result = request("/api/tutor/run", {"language": "python", "current_code": "print(42)"})
                    check("next real run succeeds after cancellation", status == 200 and result.get("stdout") == "42\n")
                    browser_script = Path(__file__).with_name("verify-ui-live.cjs")
                    browser_env = dict(os.environ, FIT_RUN_TEST_BASE_URL=base, FIT_RUN_TEST_EMAIL=account["username"], FIT_RUN_TEST_PASSWORD=api.INITIAL_PASSWORD)
                    browser = subprocess.run(["node", str(browser_script)], env=browser_env, capture_output=True, text=True,
                                             encoding="utf-8", timeout=100)
                    if browser.returncode:
                        report["browser_error"] = browser.stderr[-3000:]
                    check("actual browser login and Run button use real runner", browser.returncode == 0)
                    check("all containers created by this test were removed", all(container_missing(name) for name in names))
                finally:
                    server.should_exit = True
                    thread.join(15)
                    check("temporary HTTP server stopped cleanly", not thread.is_alive())
        report.update(state="passed", passed=len(report["checks"]), containers_observed=len(names), image=ready.get("image_id"))
    except Exception as exc:
        report.update(state="failed", passed=len(report["checks"]), error=str(exc), containers_observed=len(names))
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, ensure_ascii=False, indent=2))
    return 0 if report["state"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
