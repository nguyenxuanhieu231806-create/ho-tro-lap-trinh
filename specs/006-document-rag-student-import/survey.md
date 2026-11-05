# Khảo sát nguồn chỉ đọc — 05/11/2026

## Đã kiểm chứng

Thư mục dự án: AI-Coding-Tutor-Multilang-Source. .specify tồn tại, workflow speckit có gate review-spec trước plan và review-plan trước tasks. Constitution hiện vẫn là mẫu chưa điền; áp dụng AGENTS do người dùng cung cấp. Feature 005 đang được chọn; chưa đổi lựa chọn.

| Phần | Hiện trạng | Bằng chứng |
| --- | --- | --- |
| Runtime | .venv Python 3.12.14; FastAPI 0.159.1, Uvicorn 0.54.0, Pydantic 2.14.1, python-dotenv 1.2.4 | importlib.metadata, không cài gói |
| Dependencies | requirements có đúng bốn phụ thuộc trực tiếp; chưa có chromadb, python-docx, openpyxl, Pillow, pytesseract hoặc onnxruntime trong .venv | requirements.txt và metadata |
| Ollama | API cục bộ có cntt-coder:latest và qwen2.5-coder:7b, cùng khoảng 4,68 GB; không thấy model embedding/vision chuyên dụng trong danh sách | GET /api/tags; không sinh nội dung/tải model |
| Tài nguyên | RAM khoảng 15,7 GiB và 8 logical processors | Win32_ComputerSystem; chưa xác định GPU từ kết quả khảo sát |
| Chat code | SYSTEM_ROLE giới hạn trợ giảng bốn ngôn ngữ; reference_context đếm từ khóa, lấy tối đa hai bản tóm lược | ai_core.py:23,81,101 |
| Streaming | Phát delta trước kiểm tra schema cuối; sources gắn tất cả reference truy xuất | ai_core.py:474–570 |
| History | Mảng RAM, giữ 20 message; gửi 4 message gần nhất x 1.500 ký tự; không conversation_id hoặc DB lịch sử | static/index.html:590,813,1271,1309; api.py:242–256 |
| API bảo vệ | /api/tutor/* có session; middleware chưa tự bảo vệ prefix quản trị mới | api.py:376–385 |
| DB | users, sessions, attempts; username PK, MSSV chưa unique; chưa role/admin hoặc bảng tài liệu/hội thoại | sqlite_master/PRAGMA chỉ đọc; api.py:69–90 |
| Seed | Bốn tài khoản cố định; khởi động xóa users/sessions ngoài whitelist; login/current_user cũng chặn email ngoài whitelist | api.py:31–39,55–66,117–118,129–138,195–200 |
| Hash/session | PBKDF2-HMAC-SHA256 600.000 vòng và salt; token session lưu hash, cookie HttpOnly/SameSite Strict, hạn 12 giờ | api.py:121–126,201–210 |
| Tệp mẫu | Không tìm thấy Excel trong workspace. Có Bao-cao-Word/Bao-cao-Ky-nghe-phan-mem-Web-ho-tro-lap-trinh.docx: 1.156 paragraph XML (bao gồm trong bảng), 24 table XML, 11 drawing/11 media | Kiểm kê ZIP/XML, chưa nạp hay xác nhận làm corpus |
| Hồi quy cần giữ | Chat code, completion 450 ms, chẩn đoán cú pháp, Apply/Undo, Run bốn ngôn ngữ, login và đại dương | api.py, ai_core.py, static/index.html, feature 005 |

Không đọc các giá trị hash mật khẩu, token phiên hoặc .env; không khởi động ứng dụng/initialize() trong khảo sát. Không gọi migration, viết DB, cài package hoặc nạp embedding. Không coi tài liệu báo cáo đã có là tài liệu người dùng muốn nạp khi chưa xác nhận.

## Đã được người dùng xác nhận trong lượt phân tích

- Chế độ Hỏi đáp tài liệu riêng; giữ Chat/Sửa code hiện tại.
- Kho chung cho sinh viên đã đăng nhập ở phiên bản đầu.
- Tên tài liệu + mục/đoạn/vị trí khi Word không có số trang xác thực.
- Excel chuẩn 5 cột Email, MSSV, Họ và tên, Lớp, Năm học; email đăng nhập/MSSV duy nhất, mặc định chỉ thêm mới. Người dùng mô tả Excel chứa thông tin đăng nhập và chọn mật khẩu riêng; phương án cột Mật khẩu tùy chọn và cách phân phối cần chốt trong phê duyệt cuối.

## Chưa kiểm chứng

Excel thực tế, các kiểu ảnh/tables phức tạp cần hỗ trợ, chất lượng OCR tiếng Việt, semantic retrieval trên corpus, độ đủ bằng chứng của model hiện có, tốc độ/RAM khi chạy RAG, GPU, quy mô dùng đồng thời. Không có benchmark nào được giả định đã đạt.
