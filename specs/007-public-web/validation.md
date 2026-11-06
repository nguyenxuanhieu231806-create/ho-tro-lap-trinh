# Xác minh link công khai — 06/11/2026

URL: https://slight-fitting-corps-tennis.trycloudflare.com

cloudflared 2026.10.7 tải từ release chính thức cloudflare/cloudflared; SHA-256
2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343 khớp digest asset chính thức.
Tunnel dùng HTTP/2 tới đúng Web http://127.0.0.1:8000 đã chạy; không khởi động lại/dừng máy chủ người dùng.

| Kiểm tra HTTP từ URL HTTPS ngoài | Kết quả |
| --- | --- |
| GET / | 200; có login-form |
| GET /LogoFITHPUni.png | 200 |
| GET /rag.js | 200 |
| GET /api/auth/me chưa đăng nhập | 401 |
| GET /api/rag/conversations chưa đăng nhập | 401 |
| POST /api/auth/login với Origin của tunnel và body rỗng | 400 validation, không bị lỗi Origin 403; không gửi credentials |

Không kiểm tra mật khẩu người dùng và không thay dữ liệu tài khoản. Không công khai cổng 11434.
Link này cần máy/Web/tunnel còn chạy; không phải uptime được bảo đảm hoặc hosting cố định.

Git local origin: https://github.com/nguyenxuanhieu231806-create/web-ho-tro-lap-trinh-cntt.git.
Commit ban đầu df2b9a2 đã có trong local. GitHub API công khai trả 404; không có GitHub credential
được lưu khả dụng khi kiểm tra noninteractive. Plugin GitHub không thực hiện được get_profile.
Đã yêu cầu người dùng hoàn tất Connect to GitHub; chưa tuyên bố repo đã push thành công.

Model cục bộ đã được nạp lại bằng warmup không sinh nội dung: ready=true, cntt-coder:latest.

Phát hiện đóng gói: Dockerfile cần data/language_reference.json nhưng Git trước đó bỏ toàn bộ data/.
Chỉ đưa bản tóm lược nguồn lập trình này vào Git; SQLite, tài khoản, tài liệu nạp, model và staging vẫn bị bỏ qua.

File thay đổi: .gitignore để loại .tools và dữ liệu riêng khỏi Git, cho phép đúng language_reference.json;
data/language_reference.json được thêm vào tập tracked để Dockerfile không thiếu đầu vào;
README.md thêm link demo và giới hạn;
specs/007-public-web/spec.md, plan.md, tasks.md ghi phạm vi/kế hoạch/trạng thái;
validation.md ghi bằng chứng. .tools/cloudflared.exe và log tunnel là công cụ vận hành local,
không đưa vào Git. Không sửa mã nguồn ứng dụng hoặc cấu hình model.
