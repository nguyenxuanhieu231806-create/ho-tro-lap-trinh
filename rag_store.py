"""Private document registry, versioned Chroma index and per-account conversations."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from document_ingest import chunk_blocks


class RagStoreError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", value):
        raise RagStoreError("Mã tài nguyên không hợp lệ.")
    return value


class RagStore:
    def __init__(self, root=None):
        self.root = Path(root or os.getenv("TUTOR_RAG_DIR", Path(__file__).parent / "data" / "rag")).resolve()
        static_dir = (Path(__file__).parent / "static").resolve()
        if self.root == static_dir or static_dir in self.root.parents:
            raise RagStoreError("Kho tài liệu phải nằm ngoài thư mục static công khai.")
        self.root.mkdir(parents=True, exist_ok=True)
        self.files_dir = self.root / "documents"
        self.files_dir.mkdir(exist_ok=True)
        self.chroma_dir = self.root / "chroma"
        self.db_path = self.root / "rag.sqlite3"
        self._client = None
        self._closed = False
        self._lock = threading.RLock()
        self._publish_lock = threading.Lock()
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS documents(
                  id TEXT PRIMARY KEY,name TEXT NOT NULL,active_revision TEXT,created REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions(
                  id TEXT PRIMARY KEY,document_id TEXT NOT NULL,file_name TEXT NOT NULL,
                  file_hash TEXT NOT NULL,owner TEXT NOT NULL,status TEXT NOT NULL,
                  created REAL NOT NULL,parsed TEXT NOT NULL,collection_name TEXT);
                CREATE INDEX IF NOT EXISTS revision_hash ON revisions(file_hash);
                CREATE TABLE IF NOT EXISTS images(
                  revision_id TEXT NOT NULL,id TEXT NOT NULL,path TEXT NOT NULL,mime TEXT NOT NULL,
                  metadata TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',reviewed INTEGER NOT NULL DEFAULT 0,
                  decorative INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(revision_id,id));
                CREATE TABLE IF NOT EXISTS chunks(
                  id TEXT PRIMARY KEY,revision_id TEXT NOT NULL,document_id TEXT NOT NULL,
                  text TEXT NOT NULL,metadata TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS chunk_revision ON chunks(revision_id);
                CREATE TABLE IF NOT EXISTS index_state(
                  singleton INTEGER PRIMARY KEY CHECK(singleton=1),generation INTEGER NOT NULL,
                  profile TEXT,collection_name TEXT);
                INSERT OR IGNORE INTO index_state VALUES(1,0,NULL,NULL);
                CREATE TABLE IF NOT EXISTS conversations(
                  id TEXT PRIMARY KEY,owner TEXT NOT NULL,title TEXT NOT NULL,
                  created REAL NOT NULL,updated REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS conversation_owner ON conversations(owner,updated);
                CREATE TABLE IF NOT EXISTS messages(
                  id TEXT PRIMARY KEY,conversation_id TEXT NOT NULL,role TEXT NOT NULL,
                  content TEXT NOT NULL,citations TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
                CREATE INDEX IF NOT EXISTS message_conversation ON messages(conversation_id,created);
            """)

    @contextmanager
    def _db(self):
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _chroma(self):
        with self._lock:
            if self._closed:
                raise RagStoreError("Kho tài liệu đã đóng. Hãy mở lại dịch vụ trước khi truy xuất.", 503)
            if self._client is None:
                try:
                    import chromadb
                    from chromadb.config import Settings
                    self._client = chromadb.PersistentClient(
                        path=str(self.chroma_dir), settings=Settings(anonymized_telemetry=False))
                except Exception as exc:
                    raise RagStoreError("Chưa mở được ChromaDB. Kiểm tra thư viện và thư mục dữ liệu.", 503) from exc
            return self._client

    def close(self):
        """Release this client's reference using Chroma's public, refcounted API.

        Waits for this instance's publisher to finish. App shutdown should cancel
        and await jobs first. Other clients, including ones for the same path,
        keep their own references; no global cache/system is stopped manually.
        """
        with self._publish_lock, self._lock:
            if self._closed:
                return
            if self._client is not None:
                self._client.close()
                self._client = None
            self._closed = True

    def __enter__(self):
        if self._closed:
            raise RagStoreError("Kho tài liệu đã đóng.", 503)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _collection(self, name, create=False):
        try:
            client = self._chroma()
            if create:
                return client.get_or_create_collection(
                    name=name, embedding_function=None, metadata={"hnsw:space": "cosine"})
            return client.get_collection(name, embedding_function=None)
        except RagStoreError:
            raise
        except Exception as exc:
            raise RagStoreError("Không truy cập được chỉ mục tài liệu trong ChromaDB.", 503) from exc

    @staticmethod
    def _profile(profile):
        if not isinstance(profile, dict):
            raise RagStoreError("Cấu hình embedding không hợp lệ.")
        model, digest, dimension = profile.get("model"), profile.get("digest"), profile.get("dimension")
        if not isinstance(model, str) or not model or not isinstance(digest, str) or not digest:
            raise RagStoreError("Cần cố định tên và phiên bản model embedding.")
        if not isinstance(dimension, int) or isinstance(dimension, bool) or not 1 <= dimension <= 65536:
            raise RagStoreError("Số chiều embedding không hợp lệ.")
        return {"model": model, "digest": digest, "dimension": dimension}

    @staticmethod
    def _vectors(values, count, dimension):
        if not isinstance(values, list) or len(values) != count:
            raise RagStoreError("Số embedding không khớp số đoạn tài liệu.", 502)
        result = []
        for vector in values:
            if not isinstance(vector, (list, tuple)) or len(vector) != dimension:
                raise RagStoreError("Embedding không đúng số chiều đã cấu hình.", 502)
            if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector):
                raise RagStoreError("Embedding có giá trị không hợp lệ.", 502)
            norm = math.sqrt(sum(x * x for x in vector))
            if norm <= 0:
                raise RagStoreError("Embedding rỗng không thể đưa vào chỉ mục.", 502)
            result.append([float(x) / norm for x in vector])
        return result

    def stage_document(self, filename, data, parsed, owner, document_id=None):
        name = Path(str(filename).replace("\\", "/")).name[:200]
        if not name or not isinstance(data, bytes) or not isinstance(parsed, dict):
            raise RagStoreError("Dữ liệu tài liệu không hợp lệ.")
        fingerprint = hashlib.sha256(data).hexdigest()
        with self._lock, self._db() as db:
            duplicate = db.execute("SELECT id,document_id,status FROM revisions WHERE file_hash=? ORDER BY created LIMIT 1",
                                   (fingerprint,)).fetchone()
            if duplicate:
                return {"id": duplicate["id"], "revision_id": duplicate["id"],
                        "document_id": duplicate["document_id"], "status": duplicate["status"],
                        "duplicate": True, "message": "Nội dung này đã được nạp; không tạo bản trùng."}
            if document_id:
                _id(document_id)
                if not db.execute("SELECT 1 FROM documents WHERE id=?", (document_id,)).fetchone():
                    raise RagStoreError("Không tìm thấy tài liệu cần cập nhật.", 404)
            else:
                document_id = uuid.uuid4().hex
                db.execute("INSERT INTO documents VALUES(?,?,NULL,?)", (document_id, name, time.time()))
            revision_id = uuid.uuid4().hex
            folder = self.files_dir / revision_id
            folder.mkdir(mode=0o700)
            original = folder / "original"
            original.write_bytes(data)
            original.chmod(0o600)
            clean = {key: value for key, value in parsed.items() if key != "images"}
            clean["images"] = []
            for image in parsed.get("images", []):
                image_id = _id(image["id"])
                path = folder / (image_id + ".asset")
                path.write_bytes(image["data"])
                path.chmod(0o600)
                metadata = {k: v for k, v in image.items() if k not in {"data", "path"}}
                db.execute("INSERT INTO images(revision_id,id,path,mime,metadata) VALUES(?,?,?,?,?)",
                           (revision_id, image_id, str(path), image.get("mime", "application/octet-stream"), _json(metadata)))
                clean["images"].append(metadata)
            db.execute("INSERT INTO revisions VALUES(?,?,?,?,?,?,?,?,NULL)",
                       (revision_id, document_id, name, fingerprint, owner, "draft", time.time(), _json(clean)))
            return {"id": revision_id, "revision_id": revision_id, "job_id": revision_id,
                    "document_id": document_id, "status": "draft", "duplicate": False,
                    "warnings": clean.get("warnings", []), "unsupported": clean.get("unsupported", []),
                    "block_count": len(clean.get("blocks", [])), "image_count": len(clean["images"])}

    def documents(self):
        with self._db() as db:
            return [dict(row) for row in db.execute("""SELECT d.id,d.name,d.active_revision,d.created,
                r.id AS revision_id,r.status,r.file_name,r.created AS revision_created,
                (SELECT COUNT(*) FROM chunks c WHERE c.revision_id=r.id) AS chunk_count
                FROM documents d JOIN revisions r ON r.document_id=d.id ORDER BY r.created DESC LIMIT 500""")]

    def get_revision(self, revision_id):
        _id(revision_id)
        with self._db() as db:
            row = db.execute("SELECT * FROM revisions WHERE id=?", (revision_id,)).fetchone()
            if not row:
                raise RagStoreError("Không tìm thấy phiên bản tài liệu.", 404)
            result = {**dict(row), **json.loads(row["parsed"])}
            result.pop("parsed", None)
            result["revision_id"] = result["id"] = revision_id
            result["images"] = []
            for image in db.execute("SELECT * FROM images WHERE revision_id=? ORDER BY id", (revision_id,)):
                result["images"].append({**json.loads(image["metadata"]), "id": image["id"],
                                         "description": image["description"], "reviewed": bool(image["reviewed"]),
                                         "decorative": bool(image["decorative"])})
            return result

    def review_image(self, revision_id, image_id, description, decorative=False):
        if not isinstance(description, str) or len(description) > 12000 or (not decorative and len(description.strip()) < 10):
            raise RagStoreError("Hãy mô tả ảnh ít nhất 10 ký tự hoặc đánh dấu ảnh trang trí.")
        with self._lock, self._db() as db:
            revision = db.execute("SELECT status FROM revisions WHERE id=?", (_id(revision_id),)).fetchone()
            if not revision or revision["status"] not in {"draft", "failed"}:
                raise RagStoreError("Chỉ có thể duyệt ảnh trong bản nháp chưa công bố.", 409)
            changed = db.execute("UPDATE images SET description=?,reviewed=1,decorative=? WHERE revision_id=? AND id=?",
                                 (description.strip(), int(bool(decorative)), revision_id, _id(image_id))).rowcount
            if not changed:
                raise RagStoreError("Không tìm thấy ảnh.", 404)
        return {"id": image_id, "image_id": image_id, "revision_id": revision_id,
                "reviewed": True, "description": description.strip(), "decorative": bool(decorative)}

    def image_asset(self, revision_id, image_id, allow_draft=False):
        with self._db() as db:
            row = db.execute("SELECT i.path,i.mime,r.status FROM images i JOIN revisions r ON r.id=i.revision_id "
                             "WHERE i.revision_id=? AND i.id=?", (_id(revision_id), _id(image_id))).fetchone()
        if not row or (row["status"] != "published" and not allow_draft):
            raise RagStoreError("Không tìm thấy ảnh được phép đọc.", 404)
        path = Path(row["path"]).resolve()
        if self.files_dir not in path.parents or not path.is_file():
            raise RagStoreError("Tệp ảnh không còn khả dụng.", 404)
        return path, row["mime"]

    def _revision_chunks(self, revision):
        if revision.get("unsupported"):
            raise RagStoreError("Tài liệu còn cấu trúc chưa đọc được: " + "; ".join(revision["unsupported"][:4]), 409)
        pending = [image for image in revision["images"] if not image["reviewed"]]
        if pending:
            raise RagStoreError("Hãy duyệt mô tả hoặc đánh dấu trang trí cho tất cả ảnh trước khi công bố.", 409)
        blocks = [dict(block) for block in revision.get("blocks", [])]
        by_id = {block["id"]: block for block in blocks}
        for image in revision["images"]:
            block = by_id.get(image["block_id"])
            if block is not None:
                block["decorative"] = image["decorative"]
                block["text"] = "Mô tả ảnh đã được quản trị duyệt: " + image["description"] if not image["decorative"] else ""
        try:
            values = chunk_blocks(blocks)
        except ValueError as exc:
            raise RagStoreError(str(exc), 409) from exc
        if not values:
            raise RagStoreError("Không có nội dung văn bản hoặc mô tả ảnh được duyệt để lập chỉ mục.")
        result = []
        for item in values:
            chunk_id = hashlib.sha256((revision["id"] + ":" + item["block_id"] + ":" + str(item["offset_start"])).encode()).hexdigest()
            result.append({**item, "id": chunk_id, "revision_id": revision["id"],
                           "document_id": revision["document_id"], "file_name": revision["file_name"]})
        return result

    @staticmethod
    def _collection_name(profile):
        return "fit-rag-" + hashlib.sha256(_json(profile).encode()).hexdigest()[:24]

    def _insert_vectors(self, collection, chunks, embedder, profile):
        for index in range(0, len(chunks), 8):
            batch = chunks[index:index + 8]
            vectors = self._vectors(embedder([value["text"] for value in batch]), len(batch), profile["dimension"])
            metadata = [{key: value[key] for key in ("revision_id", "document_id", "file_name", "locator", "block_id", "kind")}
                        for value in batch]
            collection.upsert(ids=[value["id"] for value in batch], embeddings=vectors,
                              documents=[value["text"] for value in batch], metadatas=metadata)
        loaded_ids = set()
        for index in range(0, len(chunks), 128):
            loaded = collection.get(ids=[value["id"] for value in chunks[index:index + 128]], include=[])
            loaded_ids.update(loaded["ids"])
        if loaded_ids != {value["id"] for value in chunks}:
            raise RagStoreError("ChromaDB chưa lưu đủ các đoạn tài liệu.", 503)

    def publish_revision(self, revision_id, embedder_callable, profile):
        profile = self._profile(profile)
        with self._publish_lock:
            revision = self.get_revision(revision_id)
            if revision["status"] == "published":
                return {"id": revision_id, "revision_id": revision_id, "status": "published", "duplicate": True}
            values = self._revision_chunks(revision)
            current = self.active_profile()
            if current and {key: current[key] for key in profile} != profile:
                raise RagStoreError("Model embedding đã thay đổi. Cần tái lập chỉ mục trước khi công bố phiên bản mới.", 409)
            name = self._collection_name(profile)
            with self._db() as db:
                db.execute("UPDATE revisions SET status='publishing',collection_name=? WHERE id=?", (name, revision_id))
            collection = None
            try:
                collection = self._collection(name, create=True)
                self._insert_vectors(collection, values, embedder_callable, profile)
                with self._lock, self._db() as db:
                    for value in values:
                        db.execute("INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?)",
                                   (value["id"], revision_id, revision["document_id"], value["text"], _json(value)))
                    db.execute("UPDATE revisions SET status='published',collection_name=? WHERE id=?", (name, revision_id))
                    db.execute("UPDATE documents SET active_revision=? WHERE id=?", (revision_id, revision["document_id"]))
                    db.execute("UPDATE index_state SET generation=generation+1,profile=?,collection_name=? WHERE singleton=1",
                               (_json(profile), name))
            except Exception as exc:
                try:
                    if collection is not None:
                        collection.delete(ids=[value["id"] for value in values])
                except Exception:
                    pass  # Never active: recovery cleanup can safely retry by revision ID.
                with self._db() as db:
                    db.execute("UPDATE revisions SET status='failed' WHERE id=?", (revision_id,))
                if isinstance(exc, RagStoreError):
                    raise
                raise RagStoreError("Chưa hoàn tất lập chỉ mục; phiên bản đang dùng vẫn được giữ.", 503) from exc
            return {"id": revision_id, "revision_id": revision_id, "status": "published",
                    "chunk_count": len(values), "generation": self.active_profile()["generation"]}

    def active_profile(self):
        with self._db() as db:
            row = db.execute("SELECT * FROM index_state WHERE singleton=1").fetchone()
            if not row["profile"]:
                return None
            return {**json.loads(row["profile"]), "generation": row["generation"], "collection_name": row["collection_name"]}

    def generation_valid(self, generation):
        with self._db() as db:
            return db.execute("SELECT generation FROM index_state WHERE singleton=1").fetchone()[0] == generation

    def query(self, vector, expected_generation, limit=6):
        with self._lock:
            profile = self.active_profile()
            if not profile:
                return {"generation": 0, "profile": None, "chunks": []}
            if profile["generation"] != expected_generation:
                raise RagStoreError("Kho tài liệu vừa thay đổi. Hãy truy xuất lại câu hỏi.", 409)
            embedding = self._vectors([vector], 1, profile["dimension"])[0]
            with self._db() as db:
                revisions = [row[0] for row in db.execute("SELECT active_revision FROM documents WHERE active_revision IS NOT NULL")]
            if not revisions:
                return {"generation": profile["generation"], "profile": profile, "chunks": []}
            collection = self._collection(profile["collection_name"])
            try:
                count = collection.count()
                if count == 0:
                    return {"generation": profile["generation"], "profile": profile, "chunks": []}
                result = collection.query(query_embeddings=[embedding], n_results=min(max(int(limit), 1), 12, count),
                                          where={"revision_id": {"$in": revisions}}, include=["distances"])
                ids = result["ids"][0]
                distances = result.get("distances", [[]])[0]
                chunks = []
                for index, chunk_id in enumerate(ids):
                    value = self.source(chunk_id)
                    if value["revision_id"] in revisions:
                        value["distance"] = float(distances[index]) if index < len(distances) else None
                        chunks.append(value)
            except RagStoreError:
                raise
            except Exception as exc:
                raise RagStoreError("Không truy xuất được ChromaDB trong lượt hỏi này.", 503) from exc
            return {"generation": profile["generation"], "profile": profile, "chunks": chunks}

    def source(self, chunk_id):
        with self._db() as db:
            row = db.execute("SELECT c.*,r.status FROM chunks c JOIN revisions r ON r.id=c.revision_id WHERE c.id=?",
                             (_id(chunk_id),)).fetchone()
        if not row or row["status"] != "published":
            raise RagStoreError("Nguồn tài liệu chưa được công bố hoặc không còn khả dụng.", 404)
        result = json.loads(row["metadata"])
        result.update(id=row["id"], text=row["text"], quote=row["text"])
        return result

    def reindex(self, profile, embedder_callable):
        """Build a new profile separately and switch only after every active chunk exists."""
        profile = self._profile(profile)
        with self._publish_lock:
            current = self.active_profile()
            if current and {key: current[key] for key in profile} == profile:
                return {"status": "unchanged", "generation": current["generation"]}
            with self._db() as db:
                rows = db.execute("SELECT c.metadata FROM chunks c JOIN documents d ON d.active_revision=c.revision_id").fetchall()
            chunks = [json.loads(row[0]) for row in rows]
            if not chunks:
                raise RagStoreError("Chưa có tài liệu công bố để tái lập chỉ mục.")
            name = self._collection_name(profile)
            collection = self._collection(name, create=True)
            try:
                self._insert_vectors(collection, chunks, embedder_callable, profile)
            except Exception as exc:
                if isinstance(exc, RagStoreError):
                    raise
                raise RagStoreError("Tái lập chỉ mục chưa hoàn tất; chỉ mục cũ vẫn dùng được.", 503) from exc
            with self._lock, self._db() as db:
                db.execute("UPDATE index_state SET generation=generation+1,profile=?,collection_name=? WHERE singleton=1",
                           (_json(profile), name))
            return {"status": "completed", "chunk_count": len(chunks), "generation": self.active_profile()["generation"]}

    def recover_staging(self, mark_interrupted=False):
        """Delete only failed/nonactive chunks, never an active revision or another profile."""
        removed = 0
        # mark_interrupted is an explicit OFFLINE repair option. The caller must
        # stop every web worker before using it; constructors never mark live jobs.
        with self._publish_lock, self._lock, self._db() as db:
            if mark_interrupted:
                db.execute("UPDATE revisions SET status='failed' WHERE status='publishing'")
            rows = db.execute("SELECT r.id,r.collection_name FROM revisions r LEFT JOIN documents d "
                              "ON d.active_revision=r.id WHERE r.status IN ('failed','draft') AND d.id IS NULL").fetchall()
            for row in rows:
                name = row["collection_name"]
                if name:
                    try:
                        self._collection(name).delete(where={"revision_id": row["id"]})
                    except RagStoreError:
                        continue
                removed += db.execute("DELETE FROM chunks WHERE revision_id=?", (row["id"],)).rowcount
        return {"removed_chunks": removed}

    def _conversation(self, db, owner, conversation_id):
        row = db.execute("SELECT * FROM conversations WHERE id=? AND owner=?", (_id(conversation_id), owner)).fetchone()
        if not row:
            raise RagStoreError("Không tìm thấy hội thoại của tài khoản này.", 404)
        return row

    def create_conversation(self, owner, title=""):
        now = time.time()
        conversation_id = uuid.uuid4().hex
        title = str(title).strip()[:120] or "Hội thoại tài liệu mới"
        with self._db() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?,?,?)", (conversation_id, owner, title, now, now))
        return {"id": conversation_id, "conversation_id": conversation_id, "title": title, "created": now, "updated": now}

    def conversations(self, owner):
        self.expire_history()
        with self._db() as db:
            return [dict(row) for row in db.execute("SELECT id,title,created,updated FROM conversations WHERE owner=? ORDER BY updated DESC LIMIT 100", (owner,))]

    def messages(self, owner, conversation_id):
        self.expire_history()
        with self._db() as db:
            self._conversation(db, owner, conversation_id)
            values = []
            for row in db.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY created,id LIMIT 500", (conversation_id,)):
                item = dict(row)
                item["citations"] = json.loads(item["citations"])
                values.append(item)
            return values

    def add_message(self, owner, conversation_id, role, content, citations=None, status="completed"):
        if role not in {"user", "assistant"} or status not in {"pending", "completed", "failed", "cancelled"}:
            raise RagStoreError("Trạng thái tin nhắn không hợp lệ.")
        if not isinstance(content, str) or len(content) > 40000 or len(_json(citations or [])) > 100000:
            raise RagStoreError("Tin nhắn vượt giới hạn lưu trữ.")
        now, message_id = time.time(), uuid.uuid4().hex
        with self._db() as db:
            conversation = self._conversation(db, owner, conversation_id)
            count = db.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (conversation_id,)).fetchone()[0]
            if count >= 500:
                raise RagStoreError("Hội thoại đã đủ 500 tin nhắn. Hãy tạo hội thoại mới.", 409)
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (message_id, conversation_id, role, content,
                       _json(citations or []), status, now))
            title = content.strip()[:100] if role == "user" and conversation["title"] == "Hội thoại tài liệu mới" else conversation["title"]
            db.execute("UPDATE conversations SET updated=?,title=? WHERE id=?", (now, title, conversation_id))
        return {"id": message_id, "conversation_id": conversation_id, "role": role, "content": content,
                "citations": citations or [], "status": status, "created": now}

    def update_message_status(self, owner, conversation_id, message_id, status):
        if status not in {"pending", "completed", "failed", "cancelled"}:
            raise RagStoreError("Trạng thái tin nhắn không hợp lệ.")
        with self._db() as db:
            self._conversation(db, owner, conversation_id)
            if not db.execute("UPDATE messages SET status=? WHERE id=? AND conversation_id=?",
                              (status, _id(message_id), conversation_id)).rowcount:
                raise RagStoreError("Không tìm thấy tin nhắn.", 404)
        return {"id": message_id, "status": status}

    def delete_conversation(self, owner, conversation_id):
        with self._db() as db:
            self._conversation(db, owner, conversation_id)
            db.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
            db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        return {"deleted": True}

    def expire_history(self, days=30):
        cutoff = time.time() - max(1, int(days)) * 86400
        with self._db() as db:
            db.execute("DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE updated<?)", (cutoff,))
            return db.execute("DELETE FROM conversations WHERE updated<?", (cutoff,)).rowcount
