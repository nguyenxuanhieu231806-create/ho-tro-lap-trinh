# Hợp đồng chạy mã

GET /api/tutor/runner và POST /api/tutor/run dùng phiên đăng nhập hiện hành. Dữ liệu sai trả 400; thiếu phiên trả 401; đang chạy hoặc môi trường chưa sẵn sàng trả 503 với thông báo tiếng Việt.

POST nhận language, current_code và stdin. Kết quả JSON có status, language, stdout, stderr, exit_code, duration_ms và message.

Nút Dừng hủy yêu cầu HTTP. Backend quan sát ngắt kết nối, báo hủy cho worker và dọn container. Kết quả không tự chèn vào Editor. Khi nguồn đổi, client ghi rõ kết quả thuộc bản trước.
