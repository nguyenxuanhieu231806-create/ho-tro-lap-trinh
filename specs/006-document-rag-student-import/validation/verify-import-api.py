"""Actual HTTP auth/XLSX/SQLite integration with temporary data and transport fixtures."""
import http.cookiejar
import io
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TEMPORARY = tempfile.TemporaryDirectory(prefix="fit-import-http-")
os.environ["TUTOR_RAG_DIR"] = str(Path(TEMPORARY.name) / "rag")

import api
import uvicorn
from openpyxl import Workbook


class Tutor:
    async def warmup(self):
        return {}

    async def health(self):
        return {"ready": True}


class ScopeFixture:
    """Exercise trusted server transport checks, not fake real TLS negotiation."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            if headers.get(b"x-fixture-remote") == b"1":
                scope = {**scope, "client": ("192.0.2.25", 4242)}
            if headers.get(b"x-fixture-https") == b"1":
                scope = {**scope, "scheme": "https"}
        await self.app(scope, receive, send)


checks = []


def check(label, value):
    assert value, label
    checks.append(label)


def workbook_bytes():
    book = Workbook()
    sheet = book.active
    sheet.append(["Email", "MSSV", "Họ và tên", "Lớp", "Năm học", "Mật khẩu"])
    sheet.append(["api-student@example.test", "00701", "Sinh viên API kiểm thử", "CNTT3.K25", 3, "api_student_fixture_123"])
    sheet.append(["invalid-email", "00702", "Sinh viên email sai", "CNTT3.K25", 3, None])
    output = io.BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()


def main():
    api.DB = Path(TEMPORARY.name) / "accounts.sqlite3"
    api.OllamaTutor = Tutor
    api.create_admin(api.DB, "admin-api@example.test", "Quản trị API kiểm thử", "admin_api_fixture_123")
    app = api.create_app()
    server = uvicorn.Server(uvicorn.Config(ScopeFixture(app), host="127.0.0.1", port=0, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    port = server.servers[0].sockets[0].getsockname()[1]
    base = "http://127.0.0.1:" + str(port)
    admin = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    student = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(path, body=None, client=admin, file=None, headers=None):
        headers = dict(headers or {})
        if file is not None:
            boundary = "fit-test-" + uuid.uuid4().hex
            data = ("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="students.xlsx"\r\n'
                    "Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n").encode() + file + ("\r\n--" + boundary + "--\r\n").encode()
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        elif body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        else:
            data = None
        request = Request(base + path, data=data, headers=headers)
        try:
            with client.open(request, timeout=25) as response:
                raw = response.read()
                content = json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw
                return response.status, content, dict(response.headers)
        except HTTPError as error:
            return error.code, json.loads(error.read()), dict(error.headers)

    try:
        check("anonymous cannot download import template", call("/api/admin/students/template")[0] == 401)
        issued = api.ISSUED_ACCOUNTS[0]
        check("student login remains available", call("/api/auth/login", {"username": issued["username"], "password": api.INITIAL_PASSWORD}, client=student)[0] == 200)
        check("student cannot import or download admin template", call("/api/admin/students/template", client=student)[0] == 403)
        check("explicit administrator logs in", call("/api/auth/login", {"username": "admin-api@example.test", "password": "admin_api_fixture_123"})[0] == 200)
        code, template, _ = call("/api/admin/students/template")
        check("actual XLSX template returned", code == 200 and template.startswith(b"PK"))
        data = workbook_bytes()
        code, denied, _ = call("/api/admin/students/import/preview", file=data, headers={"X-Fixture-Remote": "1"})
        check("HTTP LAN transport cannot upload account credentials", code == 403)
        code, preview, headers = call("/api/admin/students/import/preview", file=data)
        check("localhost HTTP import preview succeeds", code == 200 and preview["counts"]["valid"] == 1 and preview["counts"]["invalid"] == 1)
        check("preview response redacts supplied password", "api_student_fixture_123" not in json.dumps(preview))
        check("sensitive responses disable browser caching", headers.get("cache-control", headers.get("Cache-Control")) == "no-store")
        batch = preview["batch_id"]
        code, _, _ = call("/api/admin/students/import/" + batch + "/confirm", {}, headers={"X-Fixture-Remote": "1"})
        check("HTTP LAN transport cannot confirm credentials", code == 403)
        code, result, _ = call("/api/admin/students/import/" + batch + "/confirm", {}, headers={"X-Fixture-Remote": "1", "X-Fixture-Https": "1"})
        check("trusted HTTPS scheme permits administrator confirmation", code == 200 and result["counts"]["success"] == 1)
        check("first confirm returns credentials only to authenticated admin", result["credentials"][0]["email"] == "api-student@example.test" and result["credentials"][0]["password"] == "api_student_fixture_123")
        check("repeated confirm is idempotent without credential replay", call("/api/admin/students/import/" + batch + "/confirm", {})[1]["credentials"] == [])
        report = call("/api/admin/students/import/" + batch + "/report")[1]
        check("stored report has no plaintext password", "api_student_fixture_123" not in json.dumps(report))
        api.initialize()
        check("imported student can login after reinitialization", call("/api/auth/login", {"username": "api-student@example.test", "password": "api_student_fixture_123"}, client=student)[0] == 200)
        check("imported account has student role", call("/api/auth/me", client=student)[1]["role"] == "student")
        check("Origin validation remains enabled", call("/api/admin/students/import/preview", file=data, headers={"Origin": "https://untrusted.example.test"})[0] == 403)
        check("credential staging removed after commit", not list((Path(TEMPORARY.name) / "account-imports").glob("*.xlsx")))
    finally:
        server.should_exit = True
        thread.join(timeout=15)
    check("temporary HTTP server stops cleanly", not thread.is_alive())
    result = {"mode": "actual HTTP/XLSX/auth/temp SQLite; remote-client and HTTPS scheme are controlled ASGI fixtures, not real TLS", "passed": len(checks), "checks": checks}
    Path(__file__).with_name("import-api-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


try:
    main()
finally:
    TEMPORARY.cleanup()
