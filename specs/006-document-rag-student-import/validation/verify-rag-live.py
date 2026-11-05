"""Synthetic corpus + actual Chroma + actual local Ollama, never the real corpus."""
import asyncio
import io
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from docx import Document
from ai_core import OllamaTutor
from document_ingest import parse_document
from rag_core import REFUSAL, RagService
from rag_store import RagStore


class TraceTutor(OllamaTutor):
    def __init__(self, traces):
        super().__init__()
        self.traces = traces

    async def _request(self, method, path, body=None, timeout=85):
        started = time.monotonic()
        result = await super()._request(method, path, body, timeout)
        if path == "/api/chat":
            self.traces.append({"schema": body["format"].get("title"),
                                "content": result.get("message", {}).get("content"),
                                "seconds": round(time.monotonic() - started, 2)})
        return result


async def main():
    report = {"mode": "synthetic corpus; actual local Chroma and Ollama; no real corpus/accounts changed",
              "checks": [], "traces": [], "results": []}
    try:
        with tempfile.TemporaryDirectory(prefix="fit-rag-live-") as temporary:
            store = RagStore(temporary)
            service = RagService(store, TraceTutor(report["traces"]))
            document = Document()
            document.add_heading("Quy định phòng thực hành Sao Biển", level=1)
            document.add_paragraph("Phòng thực hành Sao Biển mở cửa lúc 08:15 và đóng cửa lúc 17:30 từ thứ Hai đến thứ Sáu.")
            document.add_paragraph("Muốn đặt phòng, sinh viên gửi yêu cầu cho bộ phận quản lý trước ít nhất hai ngày làm việc.")
            table = document.add_table(rows=1, cols=2)
            table.cell(0, 0).text = "Loại hoạt động"
            table.cell(0, 1).text = "Số sinh viên tối đa"
            cells = table.add_row().cells
            cells[0].text, cells[1].text = "Dự án Hải Âu", "3"
            data = io.BytesIO()
            document.save(data)
            parsed = parse_document("Quy-dinh-Sao-Bien.docx", data.getvalue())
            staged = store.stage_document("Quy-dinh-Sao-Bien.docx", data.getvalue(), parsed, "admin@example.test")
            profile = await asyncio.to_thread(service.embedding_profile_sync)
            profile["dimension"] = len((await asyncio.to_thread(service.embed_sync, ["Đo kích thước embedding."]))[0])
            published = await asyncio.to_thread(store.publish_revision, staged["revision_id"], service.embed_sync, profile)
            report["profile"], report["published"] = profile, published
            report["checks"].append("actual embedding and Chroma publish")
            conversation = store.create_conversation("student@example.test", "Kiểm thử nguồn")
            cid = conversation.get("id", conversation.get("conversation_id"))
            question = "Phòng thực hành Sao Biển mở cửa và đóng cửa lúc mấy giờ?"
            events = []
            async for event in service.stream("student@example.test", cid, question):
                events.append(event)
            result = next(e["result"] for e in events if e.get("done"))
            report["results"].append({"case": "supported stream", **result})
            assert result["status"] == "supported" and "08:15" in result["reply"] and "17:30" in result["reply"], result
            assert result["citations"] and all(c["quote"] in store.source(c["id"])["text"] and "page" not in c for c in result["citations"])
            assert events[0].get("status") and not events[0].get("delta")
            report["checks"].extend(["supported answer contains actual facts", "citation quotes and locators resolve without invented pages", "status precedes approved content"])
            print("supported stream PASS", flush=True)
            cases = [
                ("outside", "Thủ đô của nước Pháp là gì?", "none"),
                ("keyword insufficient", "Lệ phí sử dụng phòng thực hành Sao Biển là bao nhiêu tiền?", "none"),
                ("partial", "Phòng thực hành Sao Biển mở cửa lúc mấy giờ và lệ phí sử dụng là bao nhiêu tiền?", "partial"),
                ("followup", "Giải thích tiếp phần đó về giờ đóng cửa.", "supported"),
            ]
            for label, query, expected in cases:
                history = store.messages("student@example.test", cid) if label == "followup" else []
                started = time.monotonic()
                result = await service.answer(query, history)
                report["results"].append({"case": label, "seconds": round(time.monotonic() - started, 2), **result})
                assert result["status"] == expected, (label, result)
                if expected == "none":
                    assert result["reply"] == REFUSAL and not result["citations"]
                else:
                    assert result["citations"] and all(c["quote"] in store.source(c["id"])["text"] for c in result["citations"])
                report["checks"].append(label)
                print(label, "PASS", flush=True)
            persisted = RagStore(temporary).messages("student@example.test", cid)
            assert persisted[-1]["status"] == "completed" and persisted[-1]["citations"]
            report["checks"].append("conversation restores from SQLite with citations")
            report["state"] = "passed"
    except Exception as exc:
        report["state"] = "failed"
        report["error"] = str(exc)
        raise
    finally:
        Path(__file__).with_name("rag-live-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"state": report.get("state"), "checks": len(report["checks"])}, ensure_ascii=False), flush=True)


asyncio.run(main())
