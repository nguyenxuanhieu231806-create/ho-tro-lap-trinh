"""Actual HTTP/browser/auth/SQLite/Chroma/XLSX; model outputs use controlled fixtures."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
REPORT = Path(__file__).with_name("ui-api-harness-results.json")


def main():
    report = {"mode": "actual HTTP/auth/SQLite/Chroma/XLSX/browser; controlled embedding and answer fixtures", "checks": []}
    with tempfile.TemporaryDirectory(prefix="fit-rag-ui-api-") as temporary:
        folder = Path(temporary)
        os.environ["TUTOR_AUTH_DB"] = str(folder / "accounts.sqlite3")
        os.environ["TUTOR_RAG_DIR"] = str(folder / "rag")
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        import api
        import uvicorn
        from openpyxl import Workbook
        from rag_core import RagService

        class NoWarmup:
            preferred_model = "controlled-answer-fixture"

            async def warmup(self):
                return None

            async def health(self):
                return {"ready": True, "status": "ready", "ollama_connected": True,
                        "model": "controlled-model-fixture", "message": "Embedding/answer fixtures in integration test only"}

            async def complete(self, body):
                return {"completion": ""}

        def profile(self, cancelled=None):
            return {"model": "controlled-embedding:latest", "digest": "ui-api-fixture-profile"}

        def embed(self, texts, cancelled=None):
            return [[1.0, 0.0, 0.0] for _ in texts]

        async def answer(self, question, history):
            current = await asyncio.to_thread(self.store.active_profile)
            if not current:
                return {"reply": "Câu hỏi này vượt quá phạm vi dữ liệu đã được nạp vào hệ thống.", "citations": []}
            found = await asyncio.to_thread(self.store.query, [1.0, 0.0, 0.0], current["generation"], 2)
            source = found["chunks"][0]
            citation = {key: source[key] for key in ("id", "file_name", "locator", "document_id", "revision_id")}
            return {"reply": source["text"] + " [1]", "citations": [citation], "status": "supported"}

        admin_email, admin_password = "integration-admin@example.test", "Admin-Fixture-Only-2026"
        student_email, student_password = "integration-student@example.test", "Student-Fixture-Only-2026"
        api.create_admin(api.DB, admin_email, "Quản trị tích hợp kiểm thử", admin_password)
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Email", "MSSV", "Họ và tên", "Lớp", "Năm học", "Mật khẩu"])
        sheet.append([student_email, "00012345", "Sinh viên tích hợp kiểm thử", "TEST.K25", 3, student_password])
        sheet.append(["email-sai", "00012346", "Dòng dữ liệu cần sửa", "TEST.K25", 3, None])
        xlsx = folder / "Danh-sach-kiem-thu.xlsx"
        workbook.save(xlsx)
        workbook.close()
        with patch.object(api, "OllamaTutor", NoWarmup), \
                patch.object(RagService, "embedding_profile_sync", profile), \
                patch.object(RagService, "embed_sync", embed), \
                patch.object(RagService, "answer", answer):
            server = uvicorn.Server(uvicorn.Config(api.app, host="127.0.0.1", port=0, log_level="error"))
            thread = threading.Thread(target=server.run, daemon=True)
            thread.start()
            deadline = time.monotonic() + 20
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.025)
            if not server.started:
                raise AssertionError("Temporary HTTP server did not start")
            report["checks"].append("temporary HTTP server and isolated SQLite/RAG storage started")
            try:
                port = server.servers[0].sockets[0].getsockname()[1]
                env = dict(os.environ, TUTOR_UI_BASE=f"http://127.0.0.1:{port}",
                           TUTOR_UI_ADMIN_EMAIL=admin_email, TUTOR_UI_ADMIN_PASSWORD=admin_password,
                           TUTOR_UI_STUDENT_EMAIL=student_email, TUTOR_UI_STUDENT_PASSWORD=student_password,
                           TUTOR_UI_XLSX_FILE=str(xlsx))
                result = subprocess.run(["node", str(Path(__file__).with_name("verify-ui-api.cjs"))],
                                        cwd=ROOT, env=env, timeout=180, capture_output=True, text=True, encoding="utf-8")
                print(result.stdout, end="")
                if result.returncode:
                    print(result.stderr, end="", file=sys.stderr)
                    raise AssertionError("Actual browser/API integration failed")
                report["checks"].append("actual browser account/document/import/history/source integration passed")
            finally:
                server.should_exit = True
                thread.join(timeout=15)
                if thread.is_alive():
                    raise AssertionError("Temporary HTTP server did not stop")
                report["checks"].append("temporary HTTP server stopped")
        report["state"] = "passed"
    report["checks"].append("temporary account database, spreadsheet and RAG corpus removed")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
