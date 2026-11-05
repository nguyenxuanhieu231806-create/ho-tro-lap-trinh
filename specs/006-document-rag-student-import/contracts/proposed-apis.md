# API đề xuất — chưa thêm endpoint hoặc đổi hợp đồng hiện có

Giữ nguyên /api/auth/* hiện hữu và /api/tutor/chat, complete, explain, fix, run, runner, /api/health. Không mở đăng ký tự do. Các tên route dưới đây phục vụ duyệt phạm vi, chưa là hợp đồng triển khai cuối.

| Route dự kiến | Người dùng/quyền | Trách nhiệm |
| --- | --- | --- |
| POST /api/rag/conversations | Đã đăng nhập | Tạo hội thoại owner từ session |
| GET /api/rag/conversations | Đã đăng nhập | Liệt kê của chính mình có phân trang |
| GET /api/rag/conversations/{id}/messages | Owner | Khôi phục nội dung và citation của hội thoại |
| DELETE /api/rag/conversations/{id} | Owner | Xóa/đóng theo chính sách đã duyệt |
| POST /api/rag/chat | Owner | conversation_id, question; không bắt buộc language, không nhận arbitrary history làm evidence |
| GET /api/rag/sources/{citation_id} | Đã đăng nhập và được đọc nguồn | Đúng revision/block/image/table đã sử dụng; không đường dẫn tệp tùy ý |
| POST /api/admin/documents/preview | Admin | Upload và trích staging, trả job/progress/warnings để review |
| GET /api/admin/jobs/{id} | Admin owner | Trạng thái/trích xuất/chunk counts/warnings |
| POST /api/admin/documents/{revision_id}/publish | Admin | Xác nhận review, embed/verify và publish theo job |
| POST /api/admin/jobs/{id}/cancel | Admin owner | Hủy job có kiểm soát |
| POST /api/admin/students/import/preview | Admin | XLSX + sheet/mapping/policy, trả batch/dòng lỗi/trùng; không sửa tài khoản |
| POST /api/admin/students/import/{batch_id}/confirm | Admin owner | Confirm hash/idempotency/TTL; transaction kiểm tra lại và chỉ thêm hợp lệ |
| GET /api/admin/students/import/{batch_id}/report | Admin owner | Báo đếm/dòng/lý do, không mật khẩu rõ |

Không tự bổ sung API xem tất cả mật khẩu, xem credentials của sinh viên khác hoặc public account enumeration. Giao diện quản trị cần role server; ẩn nút không đủ. HTTP 401 chưa đăng nhập, 403 thiếu quyền, 409 batch/revision xung đột, 400 dữ liệu không hợp lệ, 413 vượt giới hạn, 503 dịch vụ/bận; chi tiết validation thống nhất với chuẩn lỗi hiện tại khi chốt hợp đồng.

## Stream RAG dự kiến

NDJSON phù hợp transport hiện có: các sự kiện status trước answer, sau đó chỉ có các đoạn nội dung đã vượt kiểm tra kèm citation IDs do server cấp; cuối lượt có done và message ID. Nếu refuse thì status rõ và đúng câu quy định. Service errors có code/message tiếng Việt, không thay bằng câu refuse. Không phát raw model JSON/nháp/analysis nội bộ. Không hứa stream token trực tiếp của model trước kiểm chứng.

## Quyền và secret

User identity/owner/admin lấy từ cookie session, không từ body hoặc email admin client gửi. Origin/CSRF kiểm tra cho các route thay đổi như cơ chế hiện có, bổ sung kiểm tra role. Assets/documents/staging ngoài StaticFiles; tên file dùng để hiển thị, đường dẫn thực do server sinh. Import secret chỉ được xử lý trong kênh admin đã duyệt, không trong report thông thường/citation/Chroma. Upload Excel chứa mật khẩu và bàn giao credentials chỉ localhost hoặc HTTPS theo cấu hình proxy tin cậy; server chặn HTTP mạng LAN/public cho những thao tác này.
