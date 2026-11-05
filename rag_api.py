"""Authenticated document RAG and administrator-only document/account imports."""
from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ai_core import AiError, sanitize_user_error
from document_ingest import parse_document
from rag_core import RagService
from rag_store import RagStore, RagStoreError
from student_import import ImportError as StudentImportError
from student_import import confirm_import, create_template, get_import_report, preview_import


class Question(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=5000)


class ConversationBody(BaseModel):
    title: str = Field(default="Hội thoại tài liệu", max_length=120)


class ImageReview(BaseModel):
    description: str = Field(default="", max_length=8000)
    decorative: bool = False


def make_rag_router(current_user: Callable, auth_db: Callable):
    router = APIRouter()
    store = RagStore()
    jobs = {}
    job_lock = asyncio.Lock()
    tasks = set()

    async def user(request, admin=False, secret=False):
        account = await run_in_threadpool(current_user, request)
        if not account:
            raise AiError("Vui lòng đăng nhập để sử dụng chức năng này.", 401)
        if admin and account.get("role") != "admin":
            raise AiError("Chỉ quản trị viên được nạp tài liệu hoặc nhập sinh viên.", 403)
        if secret and request.url.scheme != "https":
            host = request.client.host if request.client else ""
            if host not in {"127.0.0.1", "::1"}:
                raise AiError("Nhập và bàn giao mật khẩu chỉ qua localhost hoặc HTTPS.", 403)
        return account

    def response(data, status=200):
        return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})

    def failure(exc):
        if isinstance(exc, (RagStoreError, StudentImportError, AiError)):
            status = getattr(exc, "status", 400)
            message = str(exc)
        elif isinstance(exc, ValueError):
            status, message = 400, str(exc)[:500]
        else:
            status, message = 503, "Không hoàn tất được tác vụ tài liệu. Hãy kiểm tra dịch vụ và thử lại."
        return response({"error": message}, status if isinstance(status, int) else 400)

    async def upload(file, maximum):
        try:
            data = await file.read(maximum + 1)
            if len(data) > maximum:
                raise AiError("Tệp vượt giới hạn dung lượng cho phép.", 413)
            if not data:
                raise AiError("Tệp tải lên trống.", 400)
            return data
        finally:
            await file.close()

    @router.get("/api/rag/documents")
    async def documents(request: Request):
        try:
            await user(request)
            all_documents = await asyncio.to_thread(store.documents)
            return response({"documents": [
                {**d, "active_revision_id": d.get("active_revision")}
                for d in all_documents if d.get("active_revision") and d.get("revision_id") == d.get("active_revision")
            ]})
        except Exception as exc:
            return failure(exc)

    @router.get("/api/rag/conversations")
    async def conversations(request: Request):
        try:
            account = await user(request)
            await asyncio.to_thread(store.expire_history, 30)
            return response({"conversations": await asyncio.to_thread(store.conversations, account["username"])})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/rag/conversations")
    async def new_conversation(body: ConversationBody, request: Request):
        try:
            account = await user(request)
            return response(await asyncio.to_thread(store.create_conversation, account["username"], body.title))
        except Exception as exc:
            return failure(exc)

    @router.get("/api/rag/conversations/{conversation_id}/messages")
    async def messages(conversation_id: str, request: Request):
        try:
            account = await user(request)
            return response({"messages": await asyncio.to_thread(store.messages, account["username"], conversation_id)})
        except Exception as exc:
            return failure(exc)

    @router.delete("/api/rag/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: str, request: Request):
        try:
            account = await user(request)
            await asyncio.to_thread(store.delete_conversation, account["username"], conversation_id)
            return response({"message": "Đã xóa hội thoại."})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/rag/chat")
    async def chat(body: Question, request: Request):
        try:
            account = await user(request)
            if not body.question.strip():
                raise AiError("Hãy nhập câu hỏi.", 400)
            await asyncio.to_thread(store.messages, account["username"], body.conversation_id)
            slots = request.app.state.chat_slots
            if slots.locked():
                raise AiError("AI đang xử lý lượt trước. Vui lòng thử lại sau.", 503)
        except Exception as exc:
            return failure(exc)

        async def events():
            async with slots:
                try:
                    service = RagService(store, request.app.state.tutor)
                    async with asyncio.timeout(360):
                        async for event in service.stream(account["username"], body.conversation_id, body.question.strip()):
                            yield json.dumps(event, ensure_ascii=False) + "\n"
                except Exception as exc:
                    message = str(exc) if isinstance(exc, (AiError, RagStoreError)) else sanitize_user_error(exc)
                    yield json.dumps({"error": message}, ensure_ascii=False) + "\n"
        return StreamingResponse(events(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

    @router.get("/api/rag/sources/{chunk_id}")
    async def source(chunk_id: str, request: Request):
        try:
            await user(request)
            return response(await asyncio.to_thread(store.source, chunk_id))
        except Exception as exc:
            return failure(exc)

    @router.get("/api/admin/documents")
    async def admin_documents(request: Request):
        try:
            await user(request, admin=True)
            return response({"documents": await asyncio.to_thread(store.documents)})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/documents/preview")
    async def preview_document(request: Request, file: UploadFile = File(...), document_id: str | None = Form(None)):
        try:
            account = await user(request, admin=True)
            data = await upload(file, 20 * 1024 * 1024)
            parsed = await asyncio.to_thread(parse_document, file.filename or "", data)
            revision = await asyncio.to_thread(store.stage_document, file.filename or "", data, parsed, account["username"], document_id)
            return response(revision)
        except Exception as exc:
            return failure(exc)

    @router.get("/api/admin/documents/{revision_id}")
    async def revision(revision_id: str, request: Request):
        try:
            await user(request, admin=True)
            return response(await asyncio.to_thread(store.get_revision, revision_id))
        except Exception as exc:
            return failure(exc)

    @router.get("/api/admin/documents/{revision_id}/images/{image_id}")
    async def image(revision_id: str, image_id: str, request: Request):
        try:
            await user(request, admin=True)
            path, mime = await asyncio.to_thread(store.image_asset, revision_id, image_id, True)
            return FileResponse(path, media_type=mime, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/documents/{revision_id}/images/{image_id}/review")
    async def review_image(revision_id: str, image_id: str, body: ImageReview, request: Request):
        try:
            await user(request, admin=True)
            return response(await asyncio.to_thread(store.review_image, revision_id, image_id, body.description, body.decorative))
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/documents/{revision_id}/publish")
    async def publish(revision_id: str, request: Request):
        try:
            account = await user(request, admin=True)
            if revision_id != "_reindex":
                await asyncio.to_thread(store.get_revision, revision_id)
            if job_lock.locked() or any(j["status"] in {"pending", "running"} for j in jobs.values()):
                raise AiError("Đang có lượt nạp tài liệu. Hãy chờ hoặc hủy lượt trước.", 503)
            job_id = uuid.uuid4().hex
            cancel = threading.Event()
            job = {"id": job_id, "job_id": job_id, "owner": account["username"], "revision_id": revision_id,
                   "status": "pending", "message": "Đang chuẩn bị embedding…", "created": time.time(), "cancel": cancel}
            jobs[job_id] = job
            # Bounded in-memory reporting; document staging/revisions persist in SQLite.
            for old_id in list(jobs)[:-50]:
                if jobs[old_id]["status"] not in {"pending", "running"}:
                    jobs.pop(old_id, None)

            async def perform():
                async with job_lock:
                    job.update(status="running", message="Đang tạo embedding và kiểm tra chỉ mục…")
                    worker = None
                    try:
                        service = RagService(store, request.app.state.tutor)
                        profile = await asyncio.to_thread(service.embedding_profile_sync, cancel)
                        vector = (await asyncio.to_thread(service.embed_sync, ["Kiểm tra mô hình embedding."], cancel))[0]
                        profile["dimension"] = len(vector)

                        def embed(texts):
                            vectors = service.embed_sync(texts, cancel)
                            if cancel.is_set():
                                raise AiError("Đã hủy nạp tài liệu.", 499)
                            return vectors

                        operation = (store.reindex, profile, embed) if revision_id == "_reindex" else (store.publish_revision, revision_id, embed, profile)
                        worker = asyncio.create_task(asyncio.to_thread(*operation))
                        result = await asyncio.shield(worker)
                        job.update(status="completed", message="Đã nạp và công bố tài liệu.", result=result)
                    except BaseException as exc:
                        was_cancelled = cancel.is_set() or isinstance(exc, asyncio.CancelledError) or getattr(exc, "status", None) == 499
                        cancel.set()
                        if worker:
                            with suppress(Exception, asyncio.CancelledError):
                                await asyncio.shield(worker)
                        job.update(status="cancelled" if was_cancelled else "failed",
                                   message=str(exc) if isinstance(exc, (AiError, RagStoreError)) else "Không hoàn tất nạp tài liệu. Bản cũ được giữ nguyên.")
            task = asyncio.create_task(perform())
            tasks.add(task)
            task.add_done_callback(tasks.discard)
            return response({"job_id": job_id, "status": "pending"}, 202)
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/index/reindex")
    async def rebuild_index(request: Request):
        return await publish("_reindex", request)

    @router.get("/api/admin/jobs/{job_id}")
    async def job_status(job_id: str, request: Request):
        try:
            account = await user(request, admin=True)
            job = jobs.get(job_id)
            if not job or job["owner"] != account["username"]:
                raise AiError("Không tìm thấy tác vụ của bạn.", 404)
            return response({key: value for key, value in job.items() if key not in {"cancel", "owner"}})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str, request: Request):
        try:
            account = await user(request, admin=True)
            job = jobs.get(job_id)
            if not job or job["owner"] != account["username"]:
                raise AiError("Không tìm thấy tác vụ của bạn.", 404)
            job["cancel"].set()
            return response({"message": "Đã yêu cầu hủy. Đang kết thúc lượt xử lý hiện tại."})
        except Exception as exc:
            return failure(exc)

    @router.get("/api/admin/students/template")
    async def template(request: Request):
        try:
            await user(request, admin=True)
            data = await asyncio.to_thread(create_template)
            return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            headers={"Content-Disposition": 'attachment; filename="Danh-sach-sinh-vien.xlsx"', "Cache-Control": "no-store"})
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/students/import/preview")
    async def preview_students(request: Request, file: UploadFile = File(...)):
        try:
            account = await user(request, admin=True, secret=True)
            data = await upload(file, 10 * 1024 * 1024)
            return response(await asyncio.to_thread(preview_import, file.filename or "", data, account["username"], auth_db()))
        except Exception as exc:
            return failure(exc)

    @router.post("/api/admin/students/import/{batch_id}/confirm")
    async def confirm_students(batch_id: str, request: Request):
        try:
            account = await user(request, admin=True, secret=True)
            return response(await asyncio.to_thread(confirm_import, batch_id, account["username"], auth_db()))
        except Exception as exc:
            return failure(exc)

    @router.get("/api/admin/students/import/{batch_id}/report")
    async def import_report(batch_id: str, request: Request):
        try:
            account = await user(request, admin=True)
            return response(await asyncio.to_thread(get_import_report, batch_id, account["username"], auth_db()))
        except Exception as exc:
            return failure(exc)

    async def close():
        for job in jobs.values():
            if job["status"] in {"pending", "running"}:
                job["cancel"].set()
        if tasks:
            await asyncio.gather(*list(tasks), return_exceptions=True)

    return router, store, close
