"""Synthetic documents and real temporary Chroma; no production corpus is loaded."""
import base64
import io
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from docx import Document
from docx.shared import Inches
from document_ingest import chunk_blocks, parse_document
from rag_store import RagStore, RagStoreError

report = {"mode": "synthetic fixtures, real temporary Chroma, controlled vectors (not model benchmark)", "checks": []}


def check(name, condition):
    assert condition, name
    report["checks"].append(name)


def denied(name, callback, status=None):
    try:
        callback()
    except (ValueError, RagStoreError) as exc:
        check(name, status is None or getattr(exc, "status", None) == status)
        return
    raise AssertionError(name)


def embed(texts):
    return [[1.0, 0.2, 0.1] for _ in texts]


with tempfile.TemporaryDirectory() as temporary:
    store = RagStore(Path(temporary) / "rag")
    text = "Chính sách học tập\n\nSinh viên phải lưu bài trước khi thoát.\n"
    parsed = parse_document("guide.txt", text.encode())
    check("TXT locators use lines and never invented pages", parsed["blocks"][1]["locator"] == "Dòng 3" and all("page" not in b for b in parsed["blocks"]))
    denied("invalid encoding rejected", lambda: parse_document("bad.txt", b"\xff\xfe\x00"))
    denied("legacy Word rejected explicitly", lambda: parse_document("bad.doc", b"word"))
    staged = store.stage_document("guide.txt", text.encode(), parsed, "admin@example.test")
    check("staging stays out of the published index", store.active_profile() is None)
    check("duplicate bytes do not create another revision", store.stage_document("renamed.txt", text.encode(), parsed, "admin@example.test")["duplicate"])
    profile = {"model": "controlled-test", "digest": "fixture1", "dimension": 3}
    published = store.publish_revision(staged["id"], embed, profile)
    check("actual Chroma publish stores all chunks", published["chunk_count"] == 2)
    active = store.active_profile()
    found = store.query([1.0, 0.2, 0.1], active["generation"])
    check("actual Chroma retrieval returns source-backed chunks", len(found["chunks"]) == 2 and all(c["file_name"] == "guide.txt" and "distance" in c for c in found["chunks"]))
    original_chunk = found["chunks"][0]["id"]
    updated = store.stage_document("guide.txt", b"Updated policy.", parse_document("guide.txt", b"Updated policy."), "admin@example.test", staged["document_id"])
    store.publish_revision(updated["id"], embed, profile)
    denied("stale generation rejected", lambda: store.query([1.0, 0.2, 0.1], active["generation"]), 409)
    found = store.query([1.0, 0.2, 0.1], store.active_profile()["generation"])
    check("retrieval excludes replaced revisions", all(c["revision_id"] == updated["id"] for c in found["chunks"]))
    check("historical citation stays on original immutable source", store.source(original_chunk)["revision_id"] == staged["id"])
    another = store.stage_document("new.txt", b"Unpublished policy.", parse_document("new.txt", b"Unpublished policy."), "admin@example.test")
    denied("embedding profile cannot silently change on publish", lambda: store.publish_revision(another["id"], embed, {**profile, "digest": "fixture2"}), 409)
    before = store.active_profile()["generation"]
    store.reindex({**profile, "digest": "fixture2"}, embed)
    check("reindex switches profile and generation only on completion", store.active_profile()["digest"] == "fixture2" and store.active_profile()["generation"] > before)
    before = store.active_profile()["generation"]
    def failure(values):
        raise RuntimeError("controlled transport failure")
    denied("failed publish does not damage the old active version", lambda: store.publish_revision(another["id"], failure, {**profile, "digest": "fixture2"}), 503)
    check("failed publish retains active generation", store.active_profile()["generation"] == before)
    with store._db() as database:
        database.execute("UPDATE revisions SET status='publishing' WHERE id=?", (another["id"],))
    reopened = RagStore(store.root)
    check("constructing another service cannot mark a live publish failed", reopened.get_revision(another["id"])["status"] == "publishing")
    with store._db() as database:
        database.execute("UPDATE revisions SET status='failed' WHERE id=?", (another["id"],))

    document = Document()
    document.add_heading("Mục thử nghiệm", level=1)
    document.add_paragraph("Trước bảng và ảnh.")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Tên"
    table.cell(0, 1).text = "Giá trị"
    table.cell(1, 0).text = "A"
    table.cell(1, 1).text = "10"
    pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
    document.add_picture(io.BytesIO(pixel), width=Inches(1))
    document.add_paragraph("Hình 1: Ảnh kiểm thử", style="Caption")
    document.add_paragraph("Sau ảnh.")
    buffer = io.BytesIO()
    document.save(buffer)
    parsed = parse_document("mixed.docx", buffer.getvalue())
    kinds = [b["kind"] for b in parsed["blocks"]]
    check("DOCX preserves table before subsequent image", kinds.index("table") < kinds.index("image"))
    check("DOCX stores structured cells", next(b for b in parsed["blocks"] if b["kind"] == "table")["rows"][1][1]["text"] == "10")
    check("image caption is explicitly linked", parsed["images"][0]["caption"] == "Hình 1: Ảnh kiểm thử")
    check("DOCX locators do not invent pagination", all("page" not in b for b in parsed["blocks"]))
    mixed = store.stage_document("mixed.docx", buffer.getvalue(), parsed, "admin@example.test")
    denied("unreviewed image cannot become evidence", lambda: store.publish_revision(mixed["id"], embed, {**profile, "digest": "fixture2"}), 409)
    store.review_image(mixed["id"], parsed["images"][0]["id"], "Ảnh kiểm thử đơn sắc, không có dữ liệu nghiệp vụ.")
    store.publish_revision(mixed["id"], embed, {**profile, "digest": "fixture2"})
    check("reviewed image description is available as indexed evidence", any(c["kind"] == "image" for c in store.query([1.0, 0.2, 0.1], store.active_profile()["generation"], 12)["chunks"]))
    asset, mime = store.image_asset(mixed["id"], parsed["images"][0]["id"])
    check("private image resolves by IDs and real MIME", asset.read_bytes() == pixel and mime == "image/png")
    denied("asset path traversal rejected", lambda: store.image_asset(mixed["id"], "../../secret"))

    conversation = store.create_conversation("a@example.test")
    pending = store.add_message("a@example.test", conversation["id"], "user", "Phần đó là gì?", status="pending")
    store.update_message_status("a@example.test", conversation["id"], pending["id"], "completed")
    store.add_message("a@example.test", conversation["id"], "assistant", "Nội dung có nguồn.", [{"id": original_chunk}])
    check("history persists and message lifecycle updates", len(store.messages("a@example.test", conversation["id"])) == 2 and store.messages("a@example.test", conversation["id"])[0]["status"] == "completed")
    denied("another owner cannot read history", lambda: store.messages("b@example.test", conversation["id"]), 404)
    denied("another owner cannot append history", lambda: store.add_message("b@example.test", conversation["id"], "user", "x"), 404)
    denied("another owner cannot delete history", lambda: store.delete_conversation("b@example.test", conversation["id"]), 404)
    store.delete_conversation("a@example.test", conversation["id"])
    check("owner can delete history", not store.conversations("a@example.test"))
    long = [{"id": "b", "kind": "paragraph", "locator": "Đoạn 1", "text": " " * 2 + "abc " * 2000}]
    chunks = chunk_blocks(long)
    check("long text is fully covered without exceeding chunk budget", all(len(c["text"]) <= 1000 for c in chunks) and "".join(c["text"] for c in chunks) == long[0]["text"])
    code_text = '```python\ndef example():\n    text = "a"\n\n    return text\n```\n'
    code = parse_document('code.txt', code_text.encode())
    check("fenced code preserves indentation and blank lines", len(code['blocks']) == 1 and code['blocks'][0]['text'] == code_text)
    denied("code lines are not split into invalid fragments", lambda: chunk_blocks([{'id':'x','kind':'code','locator':'Dòng 1','text':'x' * 1200}]))
    shared = RagStore(store.root)
    current = shared.active_profile()
    shared.query([1.0, 0.2, 0.1], current['generation'])
    other = RagStore(Path(temporary) / 'separate-rag')
    other_draft = other.stage_document('other.txt', b'Independent data.', parse_document('other.txt', b'Independent data.'), 'admin@example.test')
    other.publish_revision(other_draft['id'], embed, profile)
    store.close()
    store.close()
    check('close is idempotent and keeps another client for the same path alive', bool(shared.query([1.0, 0.2, 0.1], current['generation'])['chunks']))
    check('closing one store cannot stop a different persistent path', bool(other.query([1.0, 0.2, 0.1], other.active_profile()['generation'])['chunks']))
    denied('closed store cannot silently reopen a Chroma client', lambda: store.query([1.0, 0.2, 0.1], current['generation']), 503)
    shared.close()
    reopened.close()
    other.close()
    files = list((Path(temporary) / 'rag').rglob('data_level0.bin'))
    for file in files:
        assert (Path(temporary) / 'rag').resolve() in file.resolve().parents
        file.unlink()
    check('public close releases Windows mapped index files', bool(files) and all(not p.exists() for p in files))

check('temporary Chroma directory removed without ignoring cleanup failures', not Path(temporary).exists())

report.update(state="passed", passed=len(report["checks"]))
Path(__file__).with_name("storage-results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
