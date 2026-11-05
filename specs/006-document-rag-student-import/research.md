# Nghiên cứu và quyết định dự kiến — chưa duyệt triển khai

## 1. Một ứng dụng FastAPI, hai luồng chuyên trách

Tách ingestion/job và RAG query thành các module, không thay kiến trúc IDE đang chạy thành hệ microservice lớn. Một Ollama có thể phục vụ sinh đáp án và đối chiếu; dùng prompt/DTO riêng cho mọi chủ đề có trong kho. Model coder hiện có chỉ là ứng viên phải qua bộ câu hỏi tiếng Việt/phi lập trình. Thêm model sinh khác chỉ khi kiểm tra chứng minh cần và người dùng duyệt tải.

Embedding cần profile riêng. Đề xuất thử EmbeddingGemma nhỏ, có phạm vi đa ngôn ngữ/code theo trang model, sau đó so với nhu cầu corpus. Không mặc định model này đã đạt chất lượng tiếng Việt. Không dùng thông số embedding_length của model chat như chứng minh nó phù hợp embedding retrieval. Ollama /api/embed hỗ trợ input đơn/mảng và truncate=false; dùng để phát hiện chunk vượt context thay vì cắt lặng. [Ollama embed](https://docs.ollama.com/api/embed), [EmbeddingGemma](https://ollama.com/library/embeddinggemma).

## 2. Chroma và ranh giới dữ liệu

Đề xuất ban đầu: chromadb PersistentClient cục bộ, dữ liệu riêng data/chroma, không cổng công khai; lý do máy cá nhân và chưa biết tải lớn. Phương án thay thế là Chroma service trong Docker với volume riêng và client HTTP, chỉ mạng nội bộ; không dùng cổng 8000 của Web làm cổng mặc định thứ hai. Việc chọn mode phải được duyệt; chưa cài client/server.

Chroma nhận vector tính sẵn cùng documents và metadata, query theo query_embeddings và lọc allowed/active IDs từ backend. Không để default embedding function âm thầm tải hoặc thay model. Registry/ACL/quyền không giao cho LLM hoặc chỉ client filter. Cấu hình embedding collection gắn model/digest/dimension/parser/chunking profile; thay profile tạo chỉ mục mới. [Adding data](https://docs.trychroma.com/docs/collections/add-data), [Metadata filtering](https://docs.trychroma.com/docs/querying-collections/metadata-filtering), [Client/server](https://docs.trychroma.com/docs/run-chroma/client-server).

Chroma không chứa credentials hoặc danh sách sinh viên. data/rag.sqlite3 đề xuất lưu registry, revisions, jobs và hội thoại; accounts.sqlite3 giữ auth và thông tin nhập sinh viên. Không dựa vào transaction chung SQLite–Chroma: nạp staging, kiểm tra, rồi commit pointer phiên bản active ở registry; truy xuất dùng pointer này. Job idempotent và có cleanup/recovery khi tiến trình dừng.

## 3. Word, ảnh và vị trí

Ưu tiên .docx/.txt sau xác nhận mẫu. python-docx làm nền cho paragraph/table theo thứ tự, kết hợp OOXML relationships để giữ image rId/run/anchor, caption và các phần bổ sung. API pictures cấp cao chỉ hỗ trợ inline nên không đủ để tự khẳng định đọc toàn bộ floating shapes/text box. Kiểm kê phần chưa đọc được và chặn công bố như đầy đủ khi còn thiếu; không giả định tài liệu nào cũng đơn giản. [Document API](https://python-docx.readthedocs.io/en/latest/api/document.html), [Pictures/shapes](https://python-docx.readthedocs.io/en/latest/user/shapes.html).

Giữ raw block và bản chuẩn hóa riêng. Table lưu ô, hàng/cột và thông tin gộp; chunk bảng theo nhóm hàng kèm headers. Code giữ dòng/indentation. Ảnh lưu bytes, hash, vị trí, alt text, caption và liên kết. Văn bản OCR lưu engine/language/confidence/nguồn, không ghi đè native text. OCR đề xuất Tesseract vie+eng, chạy local trong job/worker có giới hạn, nhưng chưa chốt cài đặt trước xem mẫu. OCR không đọc đúng quan hệ UML chỉ bằng nhận chữ; với ảnh sơ đồ cần mô tả do quản trị duyệt hoặc benchmark VLM phù hợp. Chưa có model vision trên máy, không tự tải. [Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html).

Không coi lastRenderedPageBreak của Word là pagination hiện hành. Người dùng đã đồng ý locator theo mục/đoạn/vị trí. Nếu cần trang, yêu cầu bản PDF/render cố định có liên kết xác thực tới revision; phải phân biệt số trang vật lý và số in trên trang. PDF không tự trở thành định dạng ingest mới trong phạm vi đầu khi chưa được duyệt.

## 4. Retrieval, bằng chứng và streaming

Truy xuất ngữ nghĩa chỉ tạo ứng viên; bổ sung chính xác từ/định danh bằng tìm văn bản trong Chroma khi cần. Sau đó kiểm tra đúng câu hỏi, điều kiện, phủ định, bảng/code, phiên bản và từng ý trả lời. Mỗi claim gắn supporting chunk + đoạn nguồn; kiểm tra IDs, quote span và semantic support. Không suy ra sự thật chỉ từ threshold hoặc citation tồn tại. Chọn ngưỡng trên bộ validation, đo riêng retrieval và generation.

Phương án bảo thủ được đề xuất: sinh nháp nội bộ có schema claim/citation, kiểm tra toàn bộ trước khi phát answer theo NDJSON. Giao diện vẫn có status stream ngay từ đầu, nhưng có thời gian chờ trước chữ đầu tiên. Có thể nghiên cứu stream từng đoạn đã kiểm tra sau, không phải MVP mặc định. Nếu không chứng minh hỗ trợ được ý nào thì từ chối hoặc rút phần đó. Không hứa tuyệt đối không ảo giác trên câu hỏi chưa thấy; quy tắc kỹ thuật + tập đánh giá + đối chiếu người dùng là điều kiện phát hành.

## 5. Lịch sử và tài nguyên

Lưu owner/conversation/message ở server; không lấy history tùy ý từ client làm bằng chứng. Lượt gần nhất giúp resolve tham chiếu, sau đó retrieval mới. Pin revision dùng trong từng câu trả lời, không dẫn link sang bản mới khi nguồn bị sửa. Nếu source đã thu hồi, báo không còn khả dụng thay vì bịa vị trí. Chính sách giữ 30 ngày/giới hạn context chỉ là đề xuất cần duyệt.

Máy có khoảng 15,7 GiB RAM và 8 logical CPU; chưa xác định GPU. Nạp embedding và model 7B cùng lúc có thể tăng RAM/đổi model; cần đo. Ingestion chạy batch nhỏ/có pause, ưu tiên lượt hỏi, dùng chung điều phối tài nguyên Ollama, không mở nhiều worker vì tưởng sẽ nhanh hơn. Chroma lỗi không làm Chat code hoặc Run bị sập; RAG trả lỗi dịch vụ, không fallback tri thức nền.

## 6. Nhập Excel và quyền quản trị

openpyxl read-only là ứng viên .xlsx, đọc công thức dưới dạng dữ liệu để phát hiện và từ chối ở trường định danh, không thực thi công thức hoặc truy liên kết. Không dùng data_only để âm thầm tin cache công thức. Định dạng .xls/.xlsm chờ xác nhận, không tự nhận hỗ trợ. [Optimised modes](https://openpyxl.readthedocs.io/en/stable/optimized.html), [Excel reader](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html).

Đề xuất giữ email làm login key, MSSV làm định danh nghiệp vụ duy nhất sau rà soát dữ liệu. Chuyển seed sang chỉ bổ sung bốn mẫu còn thiếu, bỏ xóa ngoài whitelist, không ghi đè password/hồ sơ khi restart. Quyền admin riêng qua role trong users hoặc bảng role được duyệt; không tự chọn sinh viên làm admin. Thay đổi này cần migration backup/dry-run và chấp thuận rõ vì tác động auth hiện hữu.

Mặc định chỉ thêm mới; cùng email/MSSV là duplicate hoặc conflict báo riêng, không đổi email/mật khẩu hiện có. Preview không tạo account hoặc hash; commit kiểm tra lại trong transaction và idempotency. Cấp mật khẩu riêng vào thời điểm commit và bàn giao qua kênh riêng là khuyến nghị, không tự chuyển mật khẩu demo hiện tại sang chính sách khác. Import Excel không phải ingest RAG.

## 7. Phụ thuộc và phương án không chọn

Đề xuất thêm chromadb, python-docx, openpyxl vào phụ thuộc chỉ sau duyệt; OCR có thể cần Pillow/Tesseract binary+language data, package upload có thể cần python-multipart tùy API đã chốt. Chroma có phụ thuộc bắc cầu, không còn bảo đảm chỉ bốn gói/khởi động một giây. Không thêm LangChain, FAISS hay cloud SDK khi chưa có nhu cầu. Không truy cập Internet ở runtime RAG. Các URL trên chỉ dùng để thiết kế trong lượt khảo sát.
