# 007 — Link chạy công khai cho Web IDE hiện có

Ngày 06/11/2026. Người dùng yêu cầu đưa mã nguồn lên GitHub và gửi link bấm chạy, xác nhận phạm vi toàn bộ website hiện có. Người dùng trước đó bỏ bước chờ duyệt riêng.

GitHub Pages không chạy backend Python. Repo Git local có origin nhưng chưa xác thực GitHub; truy cập công khai trả 404 nên chưa thể tuyên bố mã đã tải lên. Cần hoàn tất xác thực GitHub để đẩy đúng repo. Không đưa .env, data/SQLite, credentials, .venv hay công cụ tải xuống vào Git.

Website và Ollama tại localhost hiện đang hoạt động. Khi chưa có tài khoản hosting, triển khai link demo HTTPS tới Web hiện có qua Cloudflare Quick Tunnel; không tự mua dịch vụ, không đổi model sang cloud và không sửa mã chạy của ứng dụng. Người dùng được báo link phụ thuộc máy còn bật. Nếu chọn link cố định, cần tài khoản máy chủ/hosting và cấu hình AI phù hợp; không coi demo là hosting 24/7.

Nghiệm thu: link công khai trả trang đăng nhập có logo/tài nguyên; API riêng tư vẫn 401 khi chưa đăng nhập; không mở riêng cổng Ollama/SQLite; ghi rõ lifetime và trạng thái GitHub. Không trả link repo chưa tồn tại như website chạy thật.

## Điều chỉnh phạm vi theo người dùng

Người dùng làm rõ: “đăng mã nguồn và chạy thử qua actions”. Bổ sung workflow GitHub Actions cho Python/API/Excel/Chroma, trình duyệt và compiler Docker bốn ngôn ngữ. Có push/pull_request/workflow_dispatch, chỉ contents:read, giới hạn thời gian và artifact kiểm thử. Không dùng Actions như hosting 24/7, không lưu secrets/data thực trong artifact, không coi các output AI kiểm soát là benchmark Ollama thật. Không tự thêm phí hosting hoặc mua dịch vụ.

## Sửa địa chỉ kho mã đã kiểm chứng

Trình duyệt GitHub của người dùng ngày 06/11/2026 đang mở kho thực tế
`nguyenxuanhieu231806-create/web-ho-tro-lap-trinh-`, có hai commit/workflow từ trước.
Origin cũ kết thúc `web-ho-tro-lap-trinh-cntt.git` không khớp kho này. Sửa origin
sang đúng kho đã có, fetch và đối chiếu trước khi đồng bộ; không force-push,
không xóa lịch sử hoặc ghi đè thay đổi remote chưa được phân tích.
