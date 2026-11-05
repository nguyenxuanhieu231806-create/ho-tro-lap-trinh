"""Run: python -m uvicorn api:app --host 0.0.0.0 --port 8000."""
import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import asynccontextmanager, closing, contextmanager, suppress
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, SecretStr, StringConstraints, model_validator

from ai_core import SYSTEM_NAME, AiError, OllamaTutor, sanitize_user_error
from code_verifier import run_code, runner_status
from starlette.concurrency import run_in_threadpool

DB = Path(os.getenv("TUTOR_AUTH_DB", str(Path(__file__).parent / "data" / "accounts.sqlite3")))
COOKIE = "tutor_session"
LIFETIME = 60 * 60 * 12
router = APIRouter(prefix="/api/auth")
ISSUED_ACCOUNTS = [
    {"username": "levanduc12@gmail.com", "name": "Sinh viên Lê Văn Đức", "student_id": "243148201121", "class_name": "CNTT3.K25", "study_year": 3},
    {"username": "nguyenxuanhieu13@gmail.com", "name": "Sinh viên Nguyễn Xuân Hiếu", "student_id": "243148201146", "class_name": "CNTT3.K25", "study_year": 3},
    {"username": "buiquangvinh14@gmail.com", "name": "Sinh viên Bùi Quang Vinh", "student_id": "243148201101", "class_name": "CNTT3.K25", "study_year": 3},
    {"username": "nguyentienduy15@gmail.com", "name": "Sinh viên Nguyễn Tiến Duy", "student_id": "243148201135", "class_name": "CNTT3.K25", "study_year": 3},
]
ISSUED_EMAILS = {item["username"] for item in ISSUED_ACCOUNTS}
ISSUED_PLACEHOLDERS = ",".join("?" for _ in ISSUED_ACCOUNTS)
INITIAL_PASSWORD = "cntt3k25@hpuni"


@contextmanager
def connect():
    connection = sqlite3.connect(DB, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


AUTH_SCHEMA_VERSION = 3


def migrate_auth_database(db_path, *, seed=True):
    """Back up before schema upgrades; never reset, delete or replace accounts."""
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        version = db.execute("PRAGMA user_version").fetchone()[0]
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if version > AUTH_SCHEMA_VERSION:
            raise RuntimeError("CSDL tài khoản thuộc phiên bản mới hơn; không tự hạ cấp.")
        if "users" in tables and version < AUTH_SCHEMA_VERSION:
            columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
            if "student_id" in columns and db.execute(
                "SELECT 1 FROM users WHERE student_id<>'' GROUP BY student_id HAVING COUNT(*)>1 LIMIT 1"
            ).fetchone():
                raise RuntimeError("CSDL có MSSV trùng. Cần xử lý thủ công trước nâng cấp; chưa thay đổi tài khoản.")
            backup = path.with_name(path.stem + ".before-auth-v3-" + str(int(time.time())) + "-" + secrets.token_hex(3) + path.suffix)
            with closing(sqlite3.connect(backup)) as destination:
                db.backup(destination)
            try:
                backup.chmod(0o600)
            except OSError:
                pass
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires REAL NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (client TEXT PRIMARY KEY, count INTEGER NOT NULL, reset REAL NOT NULL)")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
            additions = {
                "study_year": "INTEGER",
                "class_name": "TEXT NOT NULL DEFAULT ''",
                "issued_version": "INTEGER NOT NULL DEFAULT 0",
                "student_id": "TEXT NOT NULL DEFAULT ''",
                "role": "TEXT NOT NULL DEFAULT 'student'",
            }
            for column, definition in additions.items():
                if column not in columns:
                    db.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            db.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_unique_student_id ON users(student_id) WHERE student_id<>''")
            db.execute("""CREATE TABLE IF NOT EXISTS account_import_batches (
                batch_id TEXT PRIMARY KEY, owner TEXT NOT NULL, file_hash TEXT NOT NULL,
                file_name TEXT NOT NULL, private_path TEXT NOT NULL, mapping_json TEXT NOT NULL,
                preview_json TEXT NOT NULL, db_fingerprint TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL, status TEXT NOT NULL DEFAULT 'preview',
                report_json TEXT
            )""")
            seeded = 0
            if seed:
                for account in ISSUED_ACCOUNTS:
                    if db.execute("SELECT 1 FROM users WHERE username=?", (account["username"],)).fetchone():
                        continue
                    salt = secrets.token_hex(16)
                    db.execute(
                        "INSERT INTO users(username,name,salt,password_hash,study_year,class_name,student_id,issued_version,role) VALUES(?,?,?,?,?,?,?,3,'student')",
                        (account["username"], account["name"], salt, digest(INITIAL_PASSWORD, salt),
                         account["study_year"], account["class_name"], account["student_id"]),
                    )
                    seeded += 1
            db.execute(f"PRAGMA user_version={AUTH_SCHEMA_VERSION}")
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"schema_version": AUTH_SCHEMA_VERSION, "backup": str(backup) if backup else None, "seeded": seeded}


def initialize(db_path=None):
    return migrate_auth_database(DB if db_path is None else db_path)


def create_admin(db_path, email, name, password):
    """Explicit local provisioning; never promote an existing student implicitly."""
    email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
        raise ValueError("Email quản trị không hợp lệ.")
    if not name.strip() or len(name.strip()) > 160 or not 12 <= len(password) <= 128:
        raise ValueError("Họ tên không được trống; mật khẩu quản trị cần 12–128 ký tự.")
    migrate_auth_database(db_path)
    with closing(sqlite3.connect(db_path, timeout=10)) as db:
        with db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM users WHERE username=?", (email,)).fetchone():
                raise ValueError("Email đã tồn tại. Không tự đổi mật khẩu hoặc nâng quyền tài khoản hiện có.")
            salt = secrets.token_hex(16)
            db.execute(
                "INSERT INTO users(username,name,salt,password_hash,study_year,class_name,student_id,issued_version,role) VALUES(?,?,?,?,NULL,'','',3,'admin')",
                (email, name.strip(), salt, digest(password, salt)),
            )
    return {"username": email, "name": name.strip(), "role": "admin"}


def digest(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request):
    token = request.cookies.get(COOKIE, "")
    if not token or len(token) > 128:
        return None
    with connect() as db:
        row = db.execute(
            "SELECT u.username,u.name,u.student_id,u.study_year,u.class_name,u.role FROM sessions s JOIN users u ON u.username=s.username "
            "WHERE s.token_hash=? AND s.expires>?", (token_hash(token), time.time())
        ).fetchone()
    return dict(row) if row else None


def error(message, status=400):
    return JSONResponse({"error": message}, status_code=status)


def limited(request):
    """Bound password work and account creation per client, including unknown users."""
    client = request.client.host if request.client else "local"
    now = time.time()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM attempts WHERE reset < ?", (now,))
        row = db.execute("SELECT count FROM attempts WHERE client=?", (client,)).fetchone()
        if row and row["count"] >= 30:
            return True
        db.execute("INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(client) "
                   "DO UPDATE SET count=count+1", (client, now + 300))
    return False


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=4, max_length=128)


class PasswordChange(BaseModel):
    current_password: SecretStr = Field(min_length=4, max_length=128)
    new_password: SecretStr = Field(min_length=4, max_length=128)


@router.post("/change-password")
def change_password(body: PasswordChange, request: Request):
    if limited(request):
        return error("Bạn thao tác quá nhiều. Vui lòng thử lại sau 5 phút.", 429)
    user = current_user(request)
    if not user:
        return error("Vui lòng đăng nhập trước khi đổi mật khẩu.", 401)
    new_password = body.new_password.get_secret_value()
    if new_password == body.current_password.get_secret_value():
        return error("Mật khẩu mới phải khác mật khẩu hiện tại.")
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT salt,password_hash FROM users WHERE username=?", (user["username"],)).fetchone()
        if not row or not hmac.compare_digest(digest(body.current_password.get_secret_value(), row["salt"]), row["password_hash"]):
            return error("Mật khẩu hiện tại không đúng.", 401)
        salt = secrets.token_hex(16)
        db.execute("UPDATE users SET salt=?,password_hash=? WHERE username=?", (salt, digest(new_password, salt), user["username"]))
        db.execute("DELETE FROM sessions WHERE username=? AND token_hash<>?", (user["username"], token_hash(request.cookies.get(COOKIE, ""))))
    return JSONResponse({"message": "Đã đổi mật khẩu. Các phiên đăng nhập khác đã kết thúc."}, headers={"Cache-Control":"no-store"})


@router.post("/login")
def login(body: Credentials, request: Request):
    if limited(request):
        return error("Bạn thao tác quá nhiều. Vui lòng thử lại sau 5 phút.", 429)
    username = body.username.strip().lower()
    with connect() as db:
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        candidate = digest(body.password.get_secret_value(), row["salt"] if row else "00" * 16)
        if not row or not hmac.compare_digest(candidate, row["password_hash"]):
            return error("Gmail hoặc mật khẩu không đúng.", 401)
        token = secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires <= ?", (time.time(),))
        old = request.cookies.get(COOKIE, "")
        if old:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(old),))
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (token_hash(token), username, time.time()+LIFETIME))
    response = JSONResponse({"username": username, "name": row["name"], "student_id": row["student_id"],
                             "study_year": row["study_year"], "class_name": row["class_name"], "role": row["role"]})
    response.set_cookie(COOKIE, token, max_age=LIFETIME, httponly=True,
                        secure=request.url.scheme == "https" or PUBLIC_ORIGIN.startswith("https://"), samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/me")
def me(request: Request):
    user = current_user(request)
    response = JSONResponse(user if user else {"error": "Vui lòng đăng nhập."}, status_code=200 if user else 401)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/logout")
def logout(request: Request):
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash(request.cookies.get(COOKIE, "")),))
    response = JSONResponse({"message": "Đã đăng xuất."})
    response.delete_cookie(COOKIE, path="/", samesite="strict")
    return response


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
LOGO_PATH = next((STATIC_DIR / name for name in
                  ("LogoFITHPUni.png", "LogoFITHPUni.jpg", "LogoFITHPUni.PNG", "LogoFITHPUni.JPG")
                  if (STATIC_DIR / name).is_file()), STATIC_DIR / "LogoFITHPUni.png")
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "").strip().rstrip("/")
Language = Literal["python", "java", "cpp", "c"]
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: NonBlank = Field(max_length=8000)


class LanguageRequest(BaseModel):
    language: Language


class ChatRequest(LanguageRequest):
    mode: Literal["ask", "review", "explain", "optimize"] = "ask"
    question: NonBlank = Field(max_length=5000)
    current_code: str = Field(default="", max_length=60000)
    selected_code: str = Field(default="", max_length=20000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class CompletionRequest(LanguageRequest):
    prefix: str = Field(max_length=60000)
    suffix: str = Field(max_length=60000)


class CodeRequest(LanguageRequest):
    current_code: str = Field(min_length=1, max_length=60000)


class RunRequest(CodeRequest):
    stdin: str = Field(default="", max_length=16384)

    @model_validator(mode="after")
    def require_source(self):
        if not self.current_code.strip():
            raise ValueError("Mã nguồn trống")
        return self


class RunResult(BaseModel):
    language: Language
    status: Literal["completed", "compile_error", "runtime_error", "timeout", "output_limit", "cancelled", "unavailable"]
    stdout: str = Field(max_length=65536)
    stderr: str = Field(max_length=65536)
    exit_code: int | None
    duration_ms: int = Field(ge=0)
    message: str


class ExplainRequest(CodeRequest):
    start_line: int | None = Field(default=None, ge=1)
    end_line: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def check_range(self):
        total = len(self.current_code.split("\n"))
        if not 1 <= (self.start_line or 1) <= (self.end_line or total) <= total:
            raise ValueError("Invalid line range")
        return self


class ExplanationItem(BaseModel):
    line_range: list[int] = Field(min_length=2, max_length=2)
    code_snippet: str = Field(max_length=60000)
    explanation: NonBlank = Field(max_length=8000)
    concept_note: str = Field(max_length=4000)


class ExplanationResult(BaseModel):
    items: list[ExplanationItem] = Field(min_length=1, max_length=300)


class Issue(BaseModel):
    line: int = Field(ge=1)
    severity: Literal["error", "warning", "optimization"]
    message: NonBlank = Field(max_length=4000)
    suggestion: str = Field(max_length=4000)


class UnifiedResult(BaseModel):
    reply: NonBlank = Field(max_length=40000)
    issues: list[Issue] = Field(
        max_length=300,
        description="Các lỗi phát hiện trong CURRENT_CODE; [] khi không phát hiện lỗi.",
    )
    fixed_code: str | None = Field(
        max_length=60000,
        description="Toàn bộ mã đã sửa, giữ phần không đổi; null khi không cần sửa.",
    )


class FixResult(BaseModel):
    summary: NonBlank = Field(max_length=8000)
    fixed_full_code: str = Field(min_length=1, max_length=60000)
    issues: list[Issue] = Field(max_length=300)


async def cancel_on_disconnect(request, operation):
    """Cancel the coroutine when the browser aborts; the urllib worker stays bounded."""
    task = asyncio.create_task(operation)
    try:
        while not task.done():
            if await request.is_disconnected():
                raise asyncio.CancelledError()
            await asyncio.wait({task}, timeout=0.1)
        return await task
    finally:
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task


def create_app():
    from rag_api import make_rag_router
    from student_import import cleanup_expired_imports
    rag_router, rag_store, close_rag = make_rag_router(current_user, lambda: DB)

    @asynccontextmanager
    async def lifespan(app):
        await run_in_threadpool(initialize)
        app.state.tutor = OllamaTutor()
        app.state.chat_slots = asyncio.Semaphore(1)
        app.state.completion_slots = app.state.chat_slots
        app.state.run_slots = asyncio.Semaphore(1)
        async def maintenance():
            while True:
                try:
                    await asyncio.to_thread(cleanup_expired_imports, DB)
                    await asyncio.to_thread(rag_store.expire_history, 30)
                except Exception:
                    pass  # Keep existing IDE available; import/history routes report their own errors.
                await asyncio.sleep(300)
        maintenance_task = asyncio.create_task(maintenance())
        async def preload():
            try:
                await app.state.tutor.warmup()
            except Exception:
                pass  # /api/health reports a friendly diagnosis; the web stays usable.
        warmup = asyncio.create_task(preload())
        try:
            yield
        finally:
            maintenance_task.cancel()
            with suppress(asyncio.CancelledError):
                await maintenance_task
            warmup.cancel()
            with suppress(asyncio.CancelledError):
                await warmup
            await close_rag()

    app = FastAPI(title=SYSTEM_NAME, lifespan=lifespan, debug=False)
    app.include_router(router)
    app.include_router(rag_router)
    app.state.rag_store = rag_store

    @app.middleware("http")
    async def account_session(request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and origin not in {str(request.base_url).rstrip("/"), PUBLIC_ORIGIN}:
                return JSONResponse({"error": "Nguồn yêu cầu không hợp lệ."}, status_code=403)
        protected = request.url.path.startswith(("/api/tutor/", "/api/rag/", "/api/admin/"))
        if protected:
            request.state.student = await run_in_threadpool(current_user, request)
            if not request.state.student:
                return JSONResponse({"error": "Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại."}, status_code=401)
        if request.url.path.startswith("/api/admin/"):
            if request.state.student.get("role") != "admin":
                return JSONResponse({"error": "Chỉ quản trị viên được sử dụng chức năng này."}, status_code=403)
            import_path = request.url.path.startswith("/api/admin/students/import/")
            if import_path and request.method == "POST" and request.url.scheme != "https":
                if not request.client or request.client.host not in {"127.0.0.1", "::1"}:
                    return JSONResponse({"error": "Nhập mật khẩu chỉ qua localhost hoặc HTTPS."}, status_code=403)
            uploads = {"/api/admin/documents/preview": 22 * 1024 * 1024,
                       "/api/admin/students/import/preview": 12 * 1024 * 1024}
            if request.method == "POST" and request.url.path in uploads:
                length = request.headers.get("content-length", "")
                if not length.isdecimal():
                    return JSONResponse({"error": "Tệp tải lên phải có độ dài xác định."}, status_code=411)
                if int(length) > uploads[request.url.path]:
                    return JSONResponse({"error": "Tệp tải lên vượt giới hạn dung lượng."}, status_code=413)
        return await call_next(request)
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        message = "Không tìm thấy tài nguyên yêu cầu." if exc.status_code == 404 else "Yêu cầu không thể thực hiện."
        return JSONResponse({"error": message}, status_code=exc.status_code, headers=exc.headers)

    @app.get("/api/health")
    async def health(request: Request):
        result = await request.app.state.tutor.health()
        result["service"] = "fit-hpuni-programming-web"
        result["static_ready"] = (STATIC_DIR / "index.html").is_file() and LOGO_PATH.is_file()
        if not result["static_ready"]:
            result.update(ready=False, status="unavailable", message="Thiếu giao diện hoặc logo trong thư mục static.")
        return JSONResponse(result, status_code=200 if result["ready"] else 503,
                            headers={"Cache-Control": "no-store"})

    @app.get("/LogoFITHPUni.png", include_in_schema=False)
    @app.get("/LogoFITHPUni.jpg", include_in_schema=False)
    async def logo():
        if not LOGO_PATH.is_file():
            return JSONResponse({"error": "Thiếu ảnh Logo Khoa CNTT."}, status_code=404)
        return FileResponse(LOGO_PATH)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not return Pydantic input values: the body may contain a password.
        return JSONResponse({"error": "Dữ liệu không hợp lệ hoặc vượt giới hạn ký tự."}, status_code=400)

    @app.exception_handler(Exception)
    async def error(request, exc):
        status = exc.status if isinstance(exc, AiError) else 502
        if not isinstance(status, int) or not 400 <= status <= 599:
            status = 502
        if isinstance(exc, TimeoutError):
            status = 504
        return JSONResponse({"error": sanitize_user_error(exc)}, status_code=status)

    async def perform(request, body, kind, schema=None):
        slots = request.app.state.completion_slots if kind == "completion" else request.app.state.chat_slots
        if slots.locked():
            return JSONResponse({"error": "Máy chủ đang bận. Vui lòng thử lại."}, status_code=503)
        async with slots:
            method = getattr(request.app.state.tutor, "complete" if kind == "completion" else kind)
            try:
                operation = method(body, schema) if schema else method(body)
                return await cancel_on_disconnect(request, operation)
            except Exception as exc:
                # Handle here so ASGI does not log raw upstream exceptions.
                return await error(request, exc)

    @app.post("/api/tutor/chat")
    async def chat(body: ChatRequest, request: Request):
        if "application/x-ndjson" in request.headers.get("accept", ""):
            slots = request.app.state.chat_slots
            if slots.locked():
                return JSONResponse({"error": "Máy chủ đang bận. Vui lòng thử lại."}, status_code=503)
            async def stream():
                async with slots:
                    try:
                        async for event in request.app.state.tutor.chat_stream(body, UnifiedResult, request.state.student):
                            yield json.dumps(event, ensure_ascii=False) + "\n"
                    except Exception as exc:
                        yield json.dumps({"error": sanitize_user_error(exc)}, ensure_ascii=False) + "\n"
            return StreamingResponse(stream(), media_type="application/x-ndjson",
                                     headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
        slots = request.app.state.chat_slots
        if slots.locked():
            return JSONResponse({"error": "Máy chủ đang bận. Vui lòng thử lại."}, status_code=503)
        async with slots:
            async def collect():
                async for event in request.app.state.tutor.chat_stream(body, UnifiedResult, request.state.student):
                    if event.get("done"):
                        return event["result"]
            return await cancel_on_disconnect(request, collect())

    @app.get("/api/tutor/runner")
    async def runner(request: Request):
        state = dict(await run_in_threadpool(runner_status))
        state.update(languages=["c", "cpp", "java", "python"], runtime_limit_seconds=3,
                     running=request.app.state.run_slots.locked())
        return JSONResponse(state, headers={"Cache-Control": "no-store"})

    @app.post("/api/tutor/run", response_model=RunResult)
    async def run_program(body: RunRequest, request: Request):
        slots = request.app.state.run_slots
        if slots.locked():
            return JSONResponse({"error": "Đang có chương trình chạy thử. Vui lòng chờ hoặc dừng lượt trước."}, status_code=503)
        async with slots:
            cancelled = threading.Event()
            worker = asyncio.create_task(asyncio.to_thread(
                run_code, body.language, body.current_code, body.stdin, cancelled))

            async def watch_disconnect():
                while True:
                    event = await request.receive()
                    if event["type"] == "http.disconnect":
                        return

            disconnected = asyncio.create_task(watch_disconnect())

            try:
                done, _ = await asyncio.wait({worker, disconnected}, return_when=asyncio.FIRST_COMPLETED)
                if worker not in done:
                    cancelled.set()
                    return JSONResponse({"error": "Đã dừng chạy chương trình."}, status_code=499)
                result = RunResult.model_validate(worker.result())
                if result.status == "unavailable":
                    return JSONResponse({"error": result.message}, status_code=503)
                return result
            except ValueError:
                return JSONResponse({"error": "Dữ liệu chạy mã không hợp lệ hoặc kết quả chưa đầy đủ."}, status_code=400)
            except Exception:
                return JSONResponse({"error": "Không thể hoàn tất lần chạy. Hãy kiểm tra môi trường chạy và thử lại."}, status_code=503)
            finally:
                disconnected.cancel()
                with suppress(asyncio.CancelledError):
                    await disconnected
                cancelled.set()
                # Keep the run slot until the worker has removed its container.
                with suppress(asyncio.CancelledError, Exception):
                    await asyncio.shield(worker)

    @app.post("/api/tutor/complete")
    async def complete(body: CompletionRequest, request: Request):
        return await perform(request, body, "completion")

    @app.post("/api/tutor/explain", response_model=ExplanationResult)
    async def explain(body: ExplainRequest, request: Request):
        return await perform(request, body, "explain", ExplanationResult)

    @app.post("/api/tutor/fix", response_model=FixResult)
    async def fix(body: CodeRequest, request: Request):
        return await perform(request, body, "fix", FixResult)


    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


app = create_app()
