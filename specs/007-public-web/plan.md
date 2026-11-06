# Kế hoạch 007

1. Đọc cấu hình Git, .gitignore và trạng thái hệ thống/Ollama; kiểm tra khả năng GitHub/hosting đã kết nối.
2. Chuẩn bị cloudflared chính thức, xác thực digest, đặt ngoài tập mã được push.
3. Dùng tunnel tới đúng cổng hệ thống 8000 đã chạy; không dừng hoặc khởi động lại máy chủ của người dùng.
4. Kiểm tra URL HTTPS từ ngoài, trang/tài nguyên và auth boundary.
5. Hoàn tất upload Git khi người dùng đăng nhập GitHub. Không yêu cầu gửi token/mật khẩu trong chat.
6. Báo riêng link chạy và link mã nguồn, phần chưa hoàn tất và giới hạn của bản demo.
7. Theo yêu cầu mới, thêm workflow kiểm thử Actions gồm backend, trình duyệt và Docker compiler. Dùng actions chính thức được pin SHA; test dữ liệu tạm, không chạy model 7B/Cloud cần secret và không upload DB/mật khẩu. Làm kiểm thử browser portable bằng cấu hình module/channel từ env, giữ Edge mặc định khi chạy local.
8. Sửa origin theo kho GitHub thực tế đã quan sát, fetch và kiểm tra lịch sử/tệp từ xa;
   hợp nhất lịch sử nếu cần, giữ thay đổi hợp lệ của người dùng và không force-push.
9. Theo yêu cầu đổi tên, kiểm tra tên `ho-tro-lap-trinh`, đổi tên kho đã có trên
   GitHub, xác minh URL và commit không đổi, rồi cập nhật origin và ghi nhận kết quả.
