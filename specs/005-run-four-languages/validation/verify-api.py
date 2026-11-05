"""Validate runner routes with isolated auth data and controlled workers."""
import http.client
import http.cookiejar
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import api
import uvicorn

checks = []
entered = threading.Event()
release = threading.Event()
cancelled_seen = threading.Event()
cleanup = threading.Event()
received = []


class Tutor:
    async def warmup(self):
        return {}

    async def health(self):
        return {"ready": True}

    async def chat_stream(self, body, schema, student):
        yield {"done": True, "result": {"reply": "AI vẫn phục vụ", "issues": [], "fixed_code": None}}


def fake_run(language, source, stdin, cancelled):
    received.append((language, source, stdin))
    status = source if source in {"compile_error", "runtime_error", "timeout", "output_limit", "unavailable"} else "completed"
    if source in {"WAIT", "CANCEL"}:
        entered.set()
        deadline = time.monotonic() + 8
        while not release.is_set() and not cancelled.is_set() and time.monotonic() < deadline:
            release.wait(0.01)
        if cancelled.is_set():
            cancelled_seen.set()
            cleanup.set()
            time.sleep(0.4)
            cleanup.clear()
            status = "cancelled"
    return {"language": language, "status": status, "stdout": stdin or "Hello\n", "stderr": "<error>" if status != "completed" else "",
            "exit_code": 0 if status == "completed" else 1, "duration_ms": 8, "message": "Kết quả kiểm thử"}


def main():
    with tempfile.TemporaryDirectory(prefix="fit-run-api-") as temporary:
        api.DB = Path(temporary) / "accounts.sqlite3"
        api.OllamaTutor = Tutor
        api.runner_status = lambda: {"available": True, "reason": "Sẵn sàng"}
        api.run_code = fake_run
        server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=0, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        port = server.servers[0].sockets[0].getsockname()[1]
        base = "http://127.0.0.1:" + str(port)
        jar = http.cookiejar.CookieJar()
        client = build_opener(HTTPCookieProcessor(jar))

        def request(route, body=None, opener=client):
            data = json.dumps(body).encode() if body is not None else None
            req = Request(base + route, data=data, headers={"Content-Type": "application/json"})
            try:
                with opener.open(req, timeout=12) as reply:
                    return reply.status, json.loads(reply.read())
            except HTTPError as exc:
                return exc.code, json.loads(exc.read())

        try:
            assert request("/api/tutor/runner")[0] == 401
            assert request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 401
            checks.append("run and readiness require authenticated session")
            account = api.ISSUED_ACCOUNTS[0]
            assert request("/api/auth/login", {"username": account["username"], "password": api.INITIAL_PASSWORD})[0] == 200
            status, ready = request("/api/tutor/runner")
            assert status == 200 and ready["available"] and ready["runtime_limit_seconds"] == 3
            checks.append("runner readiness contract")
            for language in ("c", "cpp", "java", "python"):
                body = {"language": language, "current_code": "sample-" + language, "stdin": "2 3\n"}
                status, output = request("/api/tutor/run", body)
                assert status == 200 and output["stdout"] == body["stdin"] and output["language"] == language
                assert received[-1] == (language, body["current_code"], body["stdin"])
            checks.append("four languages forward exact code and stdin")
            for body in ({"language": "sql", "current_code": "x"},
                         {"language": "python", "current_code": "  "},
                         {"language": "python", "current_code": "x" * 60001},
                         {"language": "python", "current_code": "x", "stdin": "x" * 16385}):
                assert request("/api/tutor/run", body)[0] == 400
            checks.append("invalid language, blank source and oversized inputs rejected")
            for state in ("compile_error", "runtime_error", "timeout", "output_limit"):
                status, output = request("/api/tutor/run", {"language": "python", "current_code": state})
                assert status == 200 and output["status"] == state and output["stderr"] == "<error>"
            assert request("/api/tutor/run", {"language": "python", "current_code": "unavailable"})[0] == 503
            checks.append("execution and infrastructure states remain distinct")
            entered.clear(); release.clear()
            result = []
            job = threading.Thread(target=lambda: result.append(request("/api/tutor/run", {"language": "python", "current_code": "WAIT"})))
            job.start()
            assert entered.wait(3)
            assert request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 503
            assert request("/api/tutor/chat", {"language": "python", "question": "Xin chào"})[0] == 200
            release.set(); job.join(3)
            assert result[0][0] == 200
            checks.append("single run slot independent from AI chat")
            entered.clear(); release.clear(); cancelled_seen.clear()
            cookie = "; ".join(item.name + "=" + item.value for item in jar)
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            connection.request("POST", "/api/tutor/run", json.dumps({"language": "python", "current_code": "CANCEL"}),
                               {"Content-Type": "application/json", "Cookie": cookie})
            assert entered.wait(3)
            connection.sock.shutdown(socket.SHUT_RDWR)
            connection.close()
            assert cancelled_seen.wait(3)
            assert request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 503
            deadline = time.monotonic() + 3
            while cleanup.is_set() and time.monotonic() < deadline:
                time.sleep(0.02)
            time.sleep(0.05)
            assert request("/api/tutor/run", {"language": "python", "current_code": "print(1)"})[0] == 200
            checks.append("disconnect cancels worker and holds slot through cleanup")
        finally:
            release.set()
            server.should_exit = True
            thread.join(5)
    Path(__file__).with_name("api-results.json").write_text(json.dumps({"checks": checks}, indent=2), encoding="utf-8")
    print(json.dumps({"checks": checks}, indent=2))


if __name__ == "__main__":
    main()

