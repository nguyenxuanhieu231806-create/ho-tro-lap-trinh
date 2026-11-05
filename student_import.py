"""Preview and explicitly confirm XLSX account provisioning; never a RAG source."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import time
import unicodedata
import zipfile
from collections import defaultdict
from contextlib import closing
from pathlib import Path

MAX_FILE = 10 * 1024 * 1024
MAX_ROWS = 100
PREVIEW_TTL = 30 * 60
FIELDS = ("email", "student_id", "name", "class_name", "study_year", "password")
LABELS = ("Email", "MSSV", "Họ và tên", "Lớp", "Năm học", "Mật khẩu")
ALIASES = {
    "email": {"email", "gmail", "taikhoan", "username", "emaildangnhap"},
    "student_id": {"mssv", "masinhvien", "studentid"},
    "name": {"hovaten", "hoten", "fullname", "name"},
    "class_name": {"lop", "lophoc", "classname", "class"},
    "study_year": {"namhoc", "sinhviennam", "studyyear", "year", "nam"},
    "password": {"matkhau", "password", "pass", "matkhaukhoitao"},
}


class ImportError(Exception):
    """A public, credential-free import failure."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


ImportFailure = ImportError


def _canonical(value):
    text = unicodedata.normalize("NFKD", str(value)).lower().replace("đ", "d")
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in text if not unicodedata.combining(ch)))


def _check_archive(filename, data):
    if Path(filename).suffix.lower() != ".xlsx":
        raise ImportError("Chỉ hỗ trợ Excel .xlsx; không nhận .xls, macro hoặc tệp đổi đuôi.")
    if not isinstance(data, bytes) or not data or len(data) > MAX_FILE:
        raise ImportError("Tệp Excel trống hoặc vượt 10 MiB.", 413)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 10000 or sum(item.file_size for item in entries) > 100 * 1024 * 1024:
                raise ImportError("Cấu trúc nén Excel vượt giới hạn an toàn.", 413)
            names = {item.filename.lower() for item in entries}
            if "xl/workbook.xml" not in names or any("vbaproject" in name or name.startswith("xl/externallinks/") for name in names):
                raise ImportError("Không nhận Excel chứa macro, liên kết ngoài hoặc cấu trúc không hợp lệ.")
            if any(item.flag_bits & 1 for item in entries):
                raise ImportError("Không nhận Excel được mã hóa.")
    except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
        raise ImportError("Không đọc được cấu trúc Excel .xlsx.") from exc


def _read_rows(filename, data, mapping):
    _check_archive(filename, data)
    try:
        from openpyxl import load_workbook
    except ModuleNotFoundError as exc:
        raise ImportError("Chưa cài openpyxl. Hãy cài thư viện của dự án trước khi nhập Excel.", 503) from exc
    if mapping is None:
        mapping = {}
    if not isinstance(mapping, dict) or set(mapping) - set(FIELDS) - {"sheet"}:
        raise ImportError("Ánh xạ cột không hợp lệ.")
    workbook = None
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
        sheet_name = mapping.get("sheet")
        if sheet_name is not None and (not isinstance(sheet_name, str) or sheet_name not in workbook.sheetnames):
            raise ImportError("Không tìm thấy sheet đã chọn.")
        sheet = workbook[sheet_name] if sheet_name else workbook.worksheets[0]
        iterator = sheet.iter_rows()
        header = next(iterator, None)
        if header is None:
            raise ImportError("Sheet Excel không có hàng tiêu đề.")
        if any(cell.data_type == "f" for cell in header):
            raise ImportError("Hàng tiêu đề không được chứa công thức.")
        headers = [_canonical(cell.value or "") for cell in header]
        indexes = {}
        for field in FIELDS:
            explicit = mapping.get(field)
            if explicit is None:
                candidates = [index for index, name in enumerate(headers) if name in ALIASES[field]]
            elif isinstance(explicit, int) and not isinstance(explicit, bool):
                candidates = [explicit - 1] if 1 <= explicit <= len(headers) else []
            elif isinstance(explicit, str):
                candidates = [index for index, name in enumerate(headers) if name == _canonical(explicit)]
            else:
                candidates = []
            if len(candidates) > 1:
                raise ImportError("Có cột tiêu đề trùng. Hãy dùng ánh xạ theo số cột.")
            if not candidates:
                if field == "password" and explicit is None:
                    continue
                raise ImportError("Thiếu cột bắt buộc hoặc ánh xạ cột không đúng: " + LABELS[FIELDS.index(field)])
            indexes[field] = candidates[0]
        if len(set(indexes.values())) != len(indexes):
            raise ImportError("Mỗi trường phải dùng một cột Excel riêng.")
        parsed = []
        for row_number, cells in enumerate(iterator, 2):
            if row_number > MAX_ROWS + 1:
                raise ImportError(f"Chỉ nhận tối đa {MAX_ROWS} dòng dữ liệu cho một lượt nhập; hãy chia nhỏ tệp.", 413)
            if not any(cell.value is not None and str(cell.value).strip() for cell in cells):
                continue
            values = {}
            problems = []
            for field, index in indexes.items():
                cell = cells[index] if index < len(cells) else None
                value = None if cell is None else cell.value
                if cell is not None and cell.data_type == "f":
                    problems.append("Không nhận công thức ở cột " + LABELS[FIELDS.index(field)])
                    value = None
                if field != "study_year" and value is not None and not isinstance(value, str):
                    problems.append("Cột " + LABELS[FIELDS.index(field)] + " phải là văn bản để không mất ký tự/số 0 đầu")
                values[field] = value
            email = str(values.get("email") or "").strip().lower()
            sid = str(values.get("student_id") or "").strip()
            name = str(values.get("name") or "").strip()
            class_name = str(values.get("class_name") or "").strip()
            password = values.get("password")
            password = password if isinstance(password, str) and password else None
            year_value = values.get("study_year")
            year = None
            if isinstance(year_value, int) and not isinstance(year_value, bool):
                year = year_value
            elif isinstance(year_value, str) and re.fullmatch(r"(?:Năm\s*)?[1-8]", year_value.strip(), re.I):
                year = int(re.search(r"[1-8]", year_value).group())
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
                problems.append("Email không hợp lệ")
            if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", sid):
                problems.append("MSSV phải là chuỗi 1–40 chữ, số hoặc . _ -")
            if not 1 <= len(name) <= 160 or any(ord(ch) < 32 for ch in name):
                problems.append("Họ và tên phải có 1–160 ký tự hợp lệ")
            if not 1 <= len(class_name) <= 100 or any(ord(ch) < 32 for ch in class_name):
                problems.append("Lớp phải có 1–100 ký tự hợp lệ")
            if year is None or not 1 <= year <= 8:
                problems.append("Năm học phải là số nguyên từ 1 đến 8")
            if password is not None and not 4 <= len(password) <= 128:
                problems.append("Mật khẩu cung cấp cần 4–128 ký tự")
            parsed.append({"row": row_number, "sheet": sheet.title,
                           "profile": {"email": email, "student_id": sid, "name": name,
                                       "class_name": class_name, "study_year": year},
                           "password_supplied": password is not None, "_password": password,
                           "status": "invalid" if problems else "valid", "reason": "; ".join(problems)})
        if not parsed:
            raise ImportError("Sheet không có dòng sinh viên để nhập.")
        return parsed
    except ImportError:
        raise
    except Exception as exc:
        raise ImportError("Không đọc được dữ liệu Excel. Kiểm tra định dạng, sheet và tiêu đề.") from exc
    finally:
        if workbook is not None:
            workbook.close()


def _fingerprint(db):
    rows = db.execute("SELECT username,name,student_id,class_name,study_year,role FROM users ORDER BY username").fetchall()
    return hashlib.sha256(json.dumps([list(row) for row in rows], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _classify(parsed, db):
    candidates = [row for row in parsed if row["status"] == "valid"]
    for field in ("email", "student_id"):
        groups = defaultdict(list)
        for row in candidates:
            groups[row["profile"][field]].append(row)
        for group in groups.values():
            if len(group) < 2:
                continue
            signatures = {json.dumps([row["profile"], row["_password"]], ensure_ascii=False, sort_keys=True) for row in group}
            if len(signatures) > 1:
                for row in group:
                    row.update(status="conflict", reason="Email hoặc MSSV lặp trong tệp với thông tin khác nhau")
            else:
                for row in group[1:]:
                    if row["status"] == "valid":
                        row.update(status="duplicate", reason="Dòng lặp y hệt trong Excel; chỉ giữ một dòng")
    current = {row["username"]: row["student_id"] for row in db.execute("SELECT username,student_id FROM users")}
    by_sid = {sid: email for email, sid in current.items() if sid}
    for row in parsed:
        if row["status"] != "valid":
            continue
        email, sid = row["profile"]["email"], row["profile"]["student_id"]
        if email in current:
            if current[email] == sid:
                row.update(status="duplicate", reason="Email và MSSV đã tồn tại; không đổi hồ sơ hoặc mật khẩu")
            else:
                row.update(status="conflict", reason="Email đã thuộc MSSV khác")
        elif sid in by_sid:
            row.update(status="conflict", reason="MSSV đã thuộc email khác")
    public = [{key: value for key, value in row.items() if not key.startswith("_")} for row in parsed]
    counts = {"total": len(public)}
    counts.update({status: sum(row["status"] == status for row in public) for status in ("valid", "invalid", "duplicate", "conflict")})
    return public, counts


def _connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def _directory(auth_db):
    folder = Path(auth_db).resolve().parent / "account-imports"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    return folder


def _remove_private(path, folder):
    if not path:
        return
    candidate = Path(path).resolve()
    if candidate.parent == folder.resolve() and candidate.name.endswith(".xlsx"):
        candidate.unlink(missing_ok=True)


def cleanup_expired_imports(auth_db):
    folder = _directory(auth_db)
    with closing(_connect(auth_db)) as db:
        expired = db.execute("SELECT batch_id,private_path FROM account_import_batches WHERE private_path<>'' AND (expires<? OR status IN ('committed','expired'))", (time.time(),)).fetchall()
        for row in expired:
            try:
                _remove_private(row["private_path"], folder)
            except OSError:
                # Retain the tracked private path so maintenance can retry.
                continue
            with db:
                db.execute("UPDATE account_import_batches SET private_path='',status=CASE WHEN status='preview' THEN 'expired' ELSE status END WHERE batch_id=?", (row["batch_id"],))


def preview_import(filename, data, owner, auth_db, mapping=None):
    """Create a redacted preview. Users/sessions remain untouched."""
    if not isinstance(owner, str) or not owner:
        raise ImportError("Thiếu quản trị viên xác nhận lượt nhập.", 403)
    rows = _read_rows(filename, data, mapping)
    cleanup_expired_imports(auth_db)
    mapping_json = json.dumps(mapping or {}, sort_keys=True, ensure_ascii=False)
    file_hash = hashlib.sha256(data).hexdigest()
    folder = _directory(auth_db)
    with closing(_connect(auth_db)) as db:
        administrator = db.execute("SELECT role FROM users WHERE username=?", (owner,)).fetchone()
        if administrator is None or administrator["role"] != "admin":
            raise ImportError("Cần quyền quản trị để xem trước danh sách sinh viên.", 403)
        fingerprint = _fingerprint(db)
        existing = db.execute(
            "SELECT batch_id,expires,preview_json FROM account_import_batches WHERE owner=? AND file_hash=? AND mapping_json=? AND db_fingerprint=? AND status='preview' AND expires>? ORDER BY created DESC LIMIT 1",
            (owner, file_hash, mapping_json, fingerprint, time.time()),
        ).fetchone()
        if existing:
            return json.loads(existing["preview_json"])
        public, counts = _classify(rows, db)
        batch_id = secrets.token_urlsafe(24)
        now = time.time()
        preview = {"batch_id": batch_id, "file_name": Path(filename.replace("\\", "/")).name[:200],
                   "expires": now + PREVIEW_TTL, "rows": public, "counts": counts,
                   "message": "Chưa thay đổi tài khoản. Xác nhận để chỉ thêm các dòng hợp lệ; không ghi đè tài khoản cũ."}
        private = folder / (secrets.token_hex(24) + ".xlsx")
        descriptor = os.open(private, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            with db:
                db.execute(
                    "INSERT INTO account_import_batches(batch_id,owner,file_hash,file_name,private_path,mapping_json,preview_json,db_fingerprint,created,expires) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (batch_id, owner, file_hash, preview["file_name"], str(private), mapping_json,
                     json.dumps(preview, ensure_ascii=False), fingerprint, now, now + PREVIEW_TTL),
                )
        except Exception:
            _remove_private(private, folder)
            raise
    return preview


def get_import_report(batch_id, owner, auth_db):
    with closing(_connect(auth_db)) as db:
        batch = db.execute("SELECT owner,status,preview_json,report_json FROM account_import_batches WHERE batch_id=?", (batch_id,)).fetchone()
    if batch is None or batch["owner"] != owner:
        raise ImportError("Không tìm thấy lượt nhập của bạn.", 404)
    if batch["status"] == "committed":
        return json.loads(batch["report_json"])
    return {**json.loads(batch["preview_json"]), "status": batch["status"]}


def confirm_import(batch_id, owner, auth_db):
    """Idempotently insert valid accounts, returning initial credentials once."""
    folder = _directory(auth_db)
    private = None
    try:
        with closing(_connect(auth_db)) as db:
            batch = db.execute("SELECT * FROM account_import_batches WHERE batch_id=?", (batch_id,)).fetchone()
            if batch is None or batch["owner"] != owner:
                raise ImportError("Không tìm thấy lượt nhập của bạn.", 404)
            if batch["status"] == "committed":
                db.rollback()
                return {**json.loads(batch["report_json"]), "credentials": [], "replayed": True}
            if batch["status"] != "preview" or batch["expires"] <= time.time():
                raise ImportError("Bản xem trước đã hết hạn. Hãy tải lại Excel.", 409)
            if _fingerprint(db) != batch["db_fingerprint"]:
                raise ImportError("Danh sách tài khoản đã thay đổi sau khi xem trước. Hãy xem trước lại.", 409)
            private = Path(batch["private_path"]).resolve()
            if private.parent != folder.resolve():
                raise ImportError("Tệp tạm không hợp lệ; hãy tạo bản xem trước mới.", 409)
            try:
                data = private.read_bytes()
            except OSError as exc:
                raise ImportError("Tệp xem trước không còn. Hãy tải lại Excel.", 409) from exc
            if hashlib.sha256(data).hexdigest() != batch["file_hash"]:
                raise ImportError("Tệp tạm đã thay đổi. Hãy tải lại Excel.", 409)
            parsed = _read_rows(batch["file_name"], data, json.loads(batch["mapping_json"]))
            public, _ = _classify(parsed, db)
            before = json.loads(batch["preview_json"])["rows"]
            if public != before:
                raise ImportError("Kết quả kiểm tra đã thay đổi; cần xem trước lại.", 409)
            credentials = []
            prepared = []
            for row in parsed:
                if row["status"] != "valid":
                    continue
                profile = row["profile"]
                password = row["_password"] or secrets.token_urlsafe(14)
                salt = secrets.token_hex(16)
                hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()
                prepared.append((profile["email"], profile["name"], salt, hashed,
                                 profile["study_year"], profile["class_name"], profile["student_id"]))
                credentials.append({"email": profile["email"], "password": password})
            # PBKDF2 is deliberately outside the SQLite write transaction: a
            # large import must not block login rate-limit/session writes.
            db.execute("BEGIN IMMEDIATE")
            latest = db.execute("SELECT * FROM account_import_batches WHERE batch_id=?", (batch_id,)).fetchone()
            if latest is None or latest["owner"] != owner:
                raise ImportError("Không tìm thấy lượt nhập của bạn.", 404)
            if latest["status"] == "committed":
                db.rollback()
                return {**json.loads(latest["report_json"]), "credentials": [], "replayed": True}
            if latest["status"] != "preview" or latest["expires"] <= time.time() or _fingerprint(db) != batch["db_fingerprint"]:
                raise ImportError("Bản xem trước hoặc danh sách tài khoản đã thay đổi. Hãy xem trước lại.", 409)
            admin = db.execute("SELECT role FROM users WHERE username=?", (owner,)).fetchone()
            if admin is None or admin["role"] != "admin":
                raise ImportError("Cần quyền quản trị để xác nhận nhập sinh viên.", 403)
            db.executemany(
                "INSERT INTO users(username,name,salt,password_hash,study_year,class_name,student_id,issued_version,role) VALUES(?,?,?,?,?,?,?,3,'student')",
                prepared,
            )
            report_rows = [{**row, "status": "success" if row["status"] == "valid" else row["status"],
                            "reason": "Đã cấp tài khoản" if row["status"] == "valid" else row["reason"]} for row in public]
            success = len(credentials)
            failed = sum(row["status"] in {"invalid", "conflict"} for row in public)
            report = {"batch_id": batch_id, "status": "committed", "rows": report_rows,
                      "counts": {"total": len(public), "success": success, "failed": failed,
                                 "skipped": len(public) - success - failed},
                      "message": "Đã nhập các dòng hợp lệ. Thông tin đăng nhập chỉ được bàn giao một lần ở phản hồi xác nhận; không nằm trong báo cáo."}
            db.execute("UPDATE account_import_batches SET status='committed',report_json=? WHERE batch_id=?",
                       (json.dumps(report, ensure_ascii=False), batch_id))
            db.commit()
        cleanup_expired_imports(auth_db)
        with closing(_connect(auth_db)) as db:
            pending = bool(db.execute("SELECT private_path FROM account_import_batches WHERE batch_id=?", (batch_id,)).fetchone()[0])
        return {**report, "credentials": credentials, "replayed": False, "cleanup_pending": pending}
    except sqlite3.IntegrityError as exc:
        raise ImportError("Email hoặc MSSV vừa được cấp ở lượt khác. Hãy xem trước lại; chưa nhập lượt này.", 409) from exc


def create_template():
    """Return an empty XLSX template, without account examples or passwords."""
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:
        raise ImportError("Chưa cài openpyxl.", 503) from exc
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sinh viên"
    sheet.append(LABELS)
    sheet.freeze_panes = "A2"
    for column, width in zip("ABCDEF", (34, 24, 34, 22, 16, 28)):
        sheet.column_dimensions[column].width = width
    for row in sheet.iter_rows(min_row=2, max_row=MAX_ROWS + 1, min_col=1, max_col=2):
        for cell in row:
            cell.number_format = "@"
    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()
