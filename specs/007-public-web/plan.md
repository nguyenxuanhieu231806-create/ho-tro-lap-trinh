# Kế hoạch 007

1. Đọc cấu hình Git, .gitignore và trạng thái Web/Ollama; kiểm tra khả năng GitHub/hosting đã kết nối.
2. Chuẩn bị cloudflared chính thức, xác thực digest, đặt ngoài tập mã được push.
3. Dùng tunnel tới đúng cổng Web 8000 đã chạy; không dừng hoặc khởi động lại máy chủ của người dùng.
4. Kiểm tra URL HTTPS từ ngoài, trang/tài nguyên và auth boundary.
5. Hoàn tất upload Git khi người dùng đăng nhập GitHub. Không yêu cầu gửi token/mật khẩu trong chat.
6. Báo riêng link chạy và link mã nguồn, phần chưa hoàn tất và giới hạn của bản demo.
