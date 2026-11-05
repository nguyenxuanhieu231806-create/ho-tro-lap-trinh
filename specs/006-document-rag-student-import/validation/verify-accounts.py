"""Real XLSX/SQLite/auth checks in temporary directories; no production records."""
import hashlib
import io
import json
import os
import secrets
import sqlite3
import sys
import tempfile
from pathlib import Path
from contextlib import closing, contextmanager
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
RAG_FIXTURE = tempfile.TemporaryDirectory(prefix="fit-account-rag-")
os.environ["TUTOR_RAG_DIR"] = RAG_FIXTURE.name

import api
import student_import as imports
from fastapi import Request
from openpyxl import Workbook


@contextmanager
def database(path):
    with closing(sqlite3.connect(path)) as connection:
        with connection:
            yield connection


def xlsx(rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(imports.LABELS)
    for row in rows:
        sheet.append(row)
    result = io.BytesIO()
    workbook.save(result)
    workbook.close()
    return result.getvalue()


checks = []


def check(label, result):
    assert result, label
    checks.append(label)


def denied(label, operation, status):
    try:
        operation()
    except imports.ImportError as error:
        check(label, error.status == status)
    else:
        raise AssertionError(label)


def request(cookie=None):
    headers = [(b"cookie", (api.COOKIE + "=" + cookie).encode())] if cookie else []
    return Request({"type": "http", "method": "POST", "scheme": "http", "path": "/api/auth/login",
                    "server": ("127.0.0.1", 8000), "client": ("127.0.0.1", 12345), "headers": headers})


with tempfile.TemporaryDirectory(prefix="fit-account-tests-") as directory:
    db_path = Path(directory) / "accounts.sqlite3"
    api.DB = db_path
    # Legacy fixture represents an existing extra account and personal password.
    salt = secrets.token_hex(16)
    personal_password = "personal_fixture_123"
    with database(db_path) as db:
        db.execute("CREATE TABLE users(username TEXT PRIMARY KEY,name TEXT NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL,student_id TEXT NOT NULL DEFAULT '')")
        db.execute("INSERT INTO users VALUES(?,?,?,?,?)", ("legacy@example.test", "Người học giữ hồ sơ", salt, api.digest(personal_password, salt), "00001"))
    result = api.initialize()
    check("versioned backup before auth schema migration", bool(result["backup"]) and Path(result["backup"]).is_file())
    check("four issued samples are inserted without deleting extra account", result["seeded"] == 4)
    with database(db_path) as db:
        old = db.execute("SELECT name,salt,password_hash FROM users WHERE username='legacy@example.test'").fetchone()
        check("legacy personal profile and password hash preserved", old == ("Người học giữ hồ sơ", salt, api.digest(personal_password, salt)))
        check("no administrator created automatically", db.execute("SELECT COUNT(*) FROM users WHERE role='admin'").fetchone()[0] == 0)
    api.create_admin(db_path, "admin@example.test", "Quản trị kiểm thử", "admin_fixture_1234")
    try:
        api.create_admin(db_path, "legacy@example.test", "Không nâng quyền", "admin_fixture_1234")
    except ValueError:
        check("bootstrap never promotes or resets existing account", True)
    else:
        raise AssertionError("existing account was promoted")
    api.initialize()
    with database(db_path) as db:
        check("restart is idempotent and retains extra/admin accounts", db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 6)
    login_response = api.login(api.Credentials(username="legacy@example.test", password=personal_password), request())
    check("non-hardcoded account authenticates", login_response.status_code == 200)
    token = login_response.headers["set-cookie"].split(";", 1)[0].split("=", 1)[1]
    check("session restores DB-authoritative account and role", api.current_user(request(token))["role"] == "student")

    rows = [
        ["one@example.test", "00101", "Sinh viên kiểm thử Một", "CNTT1", 2, "provided_fixture_123"],
        ["two@example.test", "00102", "Sinh viên kiểm thử Hai", "CNTT1", 2, None],
        ["not_an_email", "00103", "Tên không lỗi", "CNTT1", 2, None],
        ["number@example.test", 104, "MSSV số không hợp lệ", "CNTT1", 2, None],
        ["one@example.test", "00101", "Sinh viên kiểm thử Một", "CNTT1", 2, "provided_fixture_123"],
        ["legacy@example.test", "00001", "Không đổi tên", "CNTT1", 2, "new_not_applied"],
        ["levanduc12@gmail.com", "00105", "Email có MSSV khác", "CNTT1", 2, None],
        ["other@example.test", "243148201121", "MSSV thuộc email khác", "CNTT1", 2, None],
        ["=\"formula@example.test\"", "00106", "Không chạy công thức", "CNTT1", 2, None],
        ["conflict@example.test", "00107", "Xung đột Một", "CNTT1", 2, None],
        ["conflict@example.test", "00108", "Xung đột Hai", "CNTT1", 2, None],
    ]
    data = xlsx(rows)
    preview = imports.preview_import("students.xlsx", data, "admin@example.test", db_path)
    check("preview classifies all valid/error/duplicate/conflict rows", preview["counts"] == {"total": 11, "valid": 2, "invalid": 3, "duplicate": 2, "conflict": 4})
    check("preview contains no supplied password", "provided_fixture_123" not in json.dumps(preview))
    with database(db_path) as db:
        check("preview does not mutate users", db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 6)
    check("identical preview upload reuses batch", imports.preview_import("renamed.xlsx", data, "admin@example.test", db_path)["batch_id"] == preview["batch_id"])
    denied("other owner cannot read batch", lambda: imports.get_import_report(preview["batch_id"], "student@example.test", db_path), 404)
    denied("other owner cannot confirm batch", lambda: imports.confirm_import(preview["batch_id"], "student@example.test", db_path), 404)
    original_hash = imports.hashlib.pbkdf2_hmac
    lock_checks = []
    def hash_without_write_lock(*args, **kwargs):
        with database(db_path) as available:
            available.execute("BEGIN IMMEDIATE")
            available.rollback()
        lock_checks.append(True)
        return original_hash(*args, **kwargs)
    with patch.object(imports.hashlib, "pbkdf2_hmac", side_effect=hash_without_write_lock):
        confirmed = imports.confirm_import(preview["batch_id"], "admin@example.test", db_path)
    check("password hashing does not hold SQLite write lock", len(lock_checks) == 2)
    check("only valid new students inserted", confirmed["counts"] == {"total": 11, "success": 2, "failed": 7, "skipped": 2})
    credentials = {item["email"]: item["password"] for item in confirmed["credentials"]}
    check("provided password used and missing password generated separately", credentials["one@example.test"] == "provided_fixture_123" and len(credentials["two@example.test"]) >= 16)
    with database(db_path) as db:
        for email, password in credentials.items():
            stored_salt, stored_hash = db.execute("SELECT salt,password_hash FROM users WHERE username=?", (email,)).fetchone()
            check("PBKDF2 with salt for " + email, stored_hash == api.digest(password, stored_salt) and stored_hash != password)
        report = db.execute("SELECT report_json FROM account_import_batches WHERE batch_id=?", (preview["batch_id"],)).fetchone()[0]
        check("stored report contains no plaintext credentials", all(password not in report for password in credentials.values()))
    check("private Excel deleted after confirm", not list((Path(directory) / "account-imports").glob("*.xlsx")))
    replay = imports.confirm_import(preview["batch_id"], "admin@example.test", db_path)
    check("repeated confirmation is idempotent and credentials not replayed", replay["credentials"] == [] and replay["replayed"])
    api.initialize()
    response = api.login(api.Credentials(username="one@example.test", password=credentials["one@example.test"]), request())
    check("new student still authenticates after restart", response.status_code == 200)
    with database(db_path) as db:
        check("preexisting password not replaced by duplicate Excel row", db.execute("SELECT password_hash FROM users WHERE username='legacy@example.test'").fetchone()[0] == api.digest(personal_password, salt))
    stale = imports.preview_import("next.xlsx", xlsx([["three@example.test", "00110", "Sinh viên thứ Ba", "CNTT1", 2, None]]), "admin@example.test", db_path)
    api.create_admin(db_path, "admin2@example.test", "Quản trị mới", "admin_fixture_5678")
    denied("database changes require new preview", lambda: imports.confirm_import(stale["batch_id"], "admin@example.test", db_path), 409)
    with database(db_path) as db:
        db.execute("UPDATE account_import_batches SET expires=0 WHERE batch_id=?", (stale["batch_id"],))
    imports.cleanup_expired_imports(db_path)
    denied("expired preview cannot be committed", lambda: imports.confirm_import(stale["batch_id"], "admin@example.test", db_path), 409)
    check("expired credential upload removed", not list((Path(directory) / "account-imports").glob("*.xlsx")))
    denied("macro extension rejected", lambda: imports.preview_import("students.xlsm", data, "admin@example.test", db_path), 400)
    oversized = xlsx([["limit@example.test", "00999", "Sinh viên kiểm thử giới hạn", "CNTT1", 2, None]] * (imports.MAX_ROWS + 1))
    denied("more than 100 rows rejected without silent truncation", lambda: imports.preview_import("too-many.xlsx", oversized, "admin@example.test", db_path), 413)
    denied("empty rows rejected", lambda: imports.preview_import("missing.xlsx", xlsx([]), "admin@example.test", db_path), 400)
    check("empty XLSX template produced", imports.create_template().startswith(b"PK"))
    conflict_path = Path(directory) / "duplicate.sqlite3"
    with database(conflict_path) as db:
        db.execute("CREATE TABLE users(username TEXT PRIMARY KEY,name TEXT,salt TEXT,password_hash TEXT,student_id TEXT)")
        db.executemany("INSERT INTO users VALUES(?,?,?,?,?)", [("a", "A", "s", "h", "dup"), ("b", "B", "s", "h", "dup")])
    try:
        api.migrate_auth_database(conflict_path)
    except RuntimeError:
        with database(conflict_path) as db:
            check("duplicate MSSV stops migration without deleting or merging", db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2 and db.execute("PRAGMA user_version").fetchone()[0] == 0)
    else:
        raise AssertionError("duplicate MSSV not blocked")

result = {"mode": "real XLSX parsing and temporary SQLite/auth; production database untouched", "passed": len(checks), "checks": checks}
Path(__file__).with_name("accounts-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
RAG_FIXTURE.cleanup()
