"""Exercise real FastAPI routes with a temporary account database and controlled AI."""
import asyncio
import hashlib
import http.cookiejar
import json
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


class TestTutor:
    async def warmup(self):
        return await self.health()

    async def health(self):
        return {"ready": True, "ollama_connected": True, "model": "ui-fixture", "message": "Kiểm thử giao diện"}

    async def chat_stream(self, body, schema, student):
        yield {"delta": "Phản hồi kiểm thử"}
        yield {"done": True, "model": "ui-fixture", "result": {"reply": "Phản hồi kiểm thử", "issues": [], "fixed_code": None}}

    async def complete(self, body):
        return {"completion": ""}


def main():
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in ("api.py", "ai_core.py", "Modelfile")}
    checks = []
    with tempfile.TemporaryDirectory(prefix="fit-ocean-auth-") as temp:
        api.DB = Path(temp) / "accounts.sqlite3"
        api.OllamaTutor = TestTutor
        server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=0, log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Không khởi động được máy chủ kiểm thử.")
                time.sleep(0.05)
            port = server.servers[0].sockets[0].getsockname()[1]
            base = "http://127.0.0.1:" + str(port)
            client = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

            def request(route, body=None):
                data = json.dumps(body).encode() if body is not None else None
                req = Request(base + route, data=data, headers={"Content-Type": "application/json"})
                try:
                    with client.open(req, timeout=10) as response:
                        return response.status, response.read()
                except HTTPError as exc:
                    return exc.code, exc.read()

            assert b"ocean-station-bg.png" in request("/")[1]
            assert request("/ocean-station-bg.png")[0] == 200
            assert request("/LogoFITHPUni.png")[0] == 200
            checks.append("FastAPI serves updated HTML, background and original logo")
            assert request("/api/tutor/chat", {"question": "Xin chào", "language": "python"})[0] == 401
            checks.append("Unauthenticated tutor request rejected")
            for account in api.ISSUED_ACCOUNTS:
                status, raw = request("/api/auth/login", {"username": account["username"], "password": api.INITIAL_PASSWORD})
                assert status == 200
                profile = json.loads(raw)
                assert profile["student_id"] == account["student_id"]
                assert request("/api/auth/me")[0] == 200
                assert request("/api/auth/logout", {})[0] == 200
            checks.append("All four provisioned test accounts authenticate and retain profiles")
            account = api.ISSUED_ACCOUNTS[0]
            assert request("/api/auth/login", {"username": account["username"], "password": api.INITIAL_PASSWORD})[0] == 200
            assert request("/api/auth/change-password", {"current_password": api.INITIAL_PASSWORD, "new_password": "test-only-new-password"})[0] == 200
            assert request("/api/auth/logout", {})[0] == 200
            assert request("/api/auth/login", {"username": account["username"], "password": "test-only-new-password"})[0] == 200
            checks.append("Password change works on isolated test data")
            status, raw = request("/api/tutor/chat", {"question": "Xin chào", "language": "python"})
            assert status == 200 and json.loads(raw)["fixed_code"] is None
            assert request("/api/tutor/complete", {"language": "python", "prefix": "print", "suffix": ""})[0] == 200
            checks.append("Authenticated chat and completion contracts work with controlled AI")
            assert json.loads(request("/api/health")[1])["static_ready"]
            checks.append("Static readiness includes original logo and HTML")
        finally:
            server.should_exit = True
            thread.join(timeout=5)
    assert hashes == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in hashes}
    checks.append("Backend and model configuration digests stable during verification")
    output = {"checks": checks, "backend_sha256": hashes, "database": "temporary isolated test database", "ai": "controlled fixture"}
    Path(__file__).with_name("api-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

