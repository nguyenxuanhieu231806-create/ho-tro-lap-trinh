# 007 — Link chạy công khai cho Web IDE hiện có

Ngày 06/11/2026. Người dùng yêu cầu đưa mã nguồn lên GitHub và gửi link bấm chạy, xác nhận phạm vi toàn bộ website hiện có. Người dùng trước đó bỏ bước chờ duyệt riêng.

GitHub Pages không chạy backend Python. Repo Git local có origin nhưng chưa xác thực GitHub; truy cập công khai trả 404 nên chưa thể tuyên bố mã đã tải lên. Cần hoàn tất xác thực GitHub để đẩy đúng repo. Không đưa .env, data/SQLite, credentials, .venv hay công cụ tải xuống vào Git.

Website và Ollama tại localhost hiện đang hoạt động. Khi chưa có tài khoản hosting, triển khai link demo HTTPS tới Web hiện có qua Cloudflare Quick Tunnel; không tự mua dịch vụ, không đổi model sang cloud và không sửa mã chạy của ứng dụng. Người dùng được báo link phụ thuộc máy còn bật. Nếu chọn link cố định, cần tài khoản máy chủ/hosting và cấu hình AI phù hợp; không coi demo là hosting 24/7.

Nghiệm thu: link công khai trả trang đăng nhập có logo/tài nguyên; API riêng tư vẫn 401 khi chưa đăng nhập; không mở riêng cổng Ollama/SQLite; ghi rõ lifetime và trạng thái GitHub. Không trả link repo chưa tồn tại như website chạy thật.
