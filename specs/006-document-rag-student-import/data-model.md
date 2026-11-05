# Mô hình dữ liệu đề xuất — chưa tạo hoặc thay đổi CSDL

## Auth và import: accounts.sqlite3 hiện tại

Giữ users.username (email) và quan hệ sessions.username đang dùng. Thêm quyền admin/student cần duyệt; giữ PBKDF2/salt/token hash. Student_id duy nhất cho sinh viên sau khi kiểm tra dữ liệu; không dùng UNIQUE ràng buộc admin có MSSV rỗng vào một MSSV giả. Lựa chọn cụ thể partial index/role table chốt ở migration design, không tự chạy ALTER/CREATE INDEX.

ImportBatch dự kiến gồm batch_id, admin_owner, file_hash, mapping/policy fingerprint, created/expires, status, tổng đếm và idempotency_key; ImportRow gồm sheet/row, normalized profile, action/status và reason. Preview không sửa users/sessions; metadata batch không chứa password, salt, password_hash hoặc token. Tệp nguồn riêng có TTL có thể chứa mật khẩu theo yêu cầu người dùng, phải bảo vệ và xóa; không lưu bản sao credentials vào RAG.

## Registry/hội thoại: data/rag.sqlite3 đề xuất mới

| Thực thể | Trường chính và quy tắc |
| --- | --- |
| Document | document_id UUID, tên hiển thị, scope shared, active_revision_id; tên không phải ID |
| DocumentRevision | revision_id, document_id, file hash, normalized content hash, parser profile, private asset path, status và thời gian; immutable khi công bố |
| ContentBlock | block_id, revision_id, order_index, kind, section path, paragraph/run hoặc table/cell/image locator, raw/normalized text, extraction source, review state |
| ImageAsset | image_id, revision_id, hash, mime, private path, anchor/caption block IDs; OCR/mô tả riêng và trạng thái duyệt |
| ChunkManifest | chunk_id, revision_id, block range, content hash, embedding_profile_id, Chroma record ID; mapping tới block để dẫn nguồn |
| EmbeddingProfile | model name + digest, dimension, preprocessing/chunking/tokenizer version, distance metric, collection name; không đổi âm thầm |
| IndexState | index generation đang công bố + embedding profile/collection và phiên bản registry; query ghim cùng tập active revisions, kiểm tra trước phát để không trộn profile khi chuyển index |
| IngestionJob | job_id, owner, revision_id, phase, counters, warnings, error code, retry/idempotency và thời gian; không log nội dung credentials |
| Conversation | conversation_id, owner_username, title, created/updated/expires, status; service kiểm tra owner qua auth DB |
| Message | message_id, conversation_id, role, content, status pending/completed/failed/cancelled, parent/turn ID, timestamps |
| Citation | message/claim ID, document/revision/chunk/block IDs, supporting offsets, locator và page provenance; chỉ nguồn được dùng |

Hai SQLite riêng không có foreign key xuyên DB. owner_username tham chiếu logic tới tài khoản qua service, không tuyên bố SQL FK đảm bảo điều này. Xóa/thu hồi tài liệu và chính sách lịch sử cần xử lý ở service; citation không đổi sang revision mới.

## Chroma collections

Lưu chunk ID, embedding đã tính, chunk text được công bố và metadata phẳng: document_id/revision_id, file_name, section/locator, block start/end, extraction_source, embedding profile và scope. Chi tiết quan hệ/asset nằm trong registry, không nhồi tùy ý cấu trúc lồng vào metadata. Trang chưa xác định thì bỏ key ở Chroma, giữ NULL ở registry; không dùng 0 hay giá trị đoán.

Query_embeddings theo profile, lọc tập revision active/được phép do backend tính; luôn kiểm tra lại registry trước khi làm evidence hoặc đọc asset. Không có mật khẩu, danh sách sinh viên, token hoặc lịch sử hội thoại trong Chroma. Không coi metadata trong collection tự nó là hệ thống phân quyền.

## Publish và cập nhật

Revision staging được trích/chunk/embed trước, kiểm tra đủ record và retrieval probes, sau đó cập nhật active_revision_id và generation trong transaction registry phù hợp. Truy vấn ghim tập active cùng embedding/index generation tại đầu lượt và kiểm tra tính khả dụng trước phát; generation đã đổi thì truy xuất lại có giới hạn. Chroma và SQLite không có distributed transaction, có thể còn staging mồ côi tạm thời nhưng chúng không bao giờ được đưa vào truy xuất; job reconciliation/cleanup idempotent theo ID xử lý sau recovery. Bản active cũ không bị xóa trước khi bản mới đạt kiểm tra. Cùng nội dung/hash nạp lại là noop/reuse có xác nhận; tên file trùng không tự upsert cùng document ID.
