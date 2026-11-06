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

## Xác minh workflow Actions tại máy

Ngày 06/11/2026, ba nhóm trong `scripts/ci_checks.py` đều kết thúc exit 0:

| Nhóm | Kiểm tra đạt | Phạm vi |
| --- | --- | --- |
| backend | 130 | accounts 32, import API 19, storage 36, runner protocol 36, API runner 7 |
| browser | 66 | giao diện kế thừa 28, RAG/admin 21, Run Code 17; Edge headless desktop/mobile |
| compiler | 25 | Docker thực thi thật: stdout/stdin, lỗi cú pháp/runtime, timeout, giới hạn output |

Windows chặn quyền thư mục tạm ở lần chạy giới hạn đầu tiên; chạy lại với quyền
truy cập thư mục tạm bình thường đạt cả ba nhóm. Dữ liệu kiểm thử độc lập, không
thay cơ sở dữ liệu thật. Các báo cáo mới/ảnh được sao chép vào `ci-results/`;
báo cáo lịch sử tracked được khôi phục, không ghi đè bằng bằng chứng của lần khác.
YAML có đủ push/pull_request/workflow_dispatch và 3 job, cú pháp Python hợp lệ.
Một lượt rà soát chỉ đọc độc lập chưa phát hiện lỗi đường dẫn/dependency Linux.
Đã kiểm tra 155 tệp văn bản tracked không thấy mẫu khóa Gemini/GitHub/private key;
`.env`, SQLite và `.tools` không nằm trong danh sách tracked.

Giới hạn: kiểm thử AI dùng dữ liệu kiểm soát; không xác nhận chất lượng sinh nội dung
của Ollama hoặc end-to-end RAG trên mô hình thật. Trình duyệt cần tải Monaco từ CDN.
Kết quả local không thay thế kết quả GitHub Actions; chưa có URL run khi chưa push.

`docker build -t fit-tutor-web:ci .` đã đạt với Python 3.11 Linux và các thư viện
trong requirements. Chạy image ở user không đặc quyền, filesystem chỉ đọc,
không mạng, hai vùng tmpfs riêng: import api thành công và ba tệp giao diện,
logo, tham chiếu tồn tại. Không truy cập DB, Ollama hay volume thật của máy.

Tệp bổ sung/thay đổi cho Actions:

- `.github/workflows/verify-web-ide.yml`: ba job, quyền contents:read, action pin SHA,
  timeout và artifact giới hạn thời gian lưu.
- `scripts/ci_checks.py`: chạy các bài kiểm thử có sẵn, chỉ thu báo cáo vừa tạo.
- `.gitignore`: bỏ node_modules và ci-results khỏi Git.
- `specs/004-ocean-station-ui/validation/verify-ui.cjs`: cho phép chọn Playwright/channel
  qua môi trường; giữ mặc định Edge local.
- `specs/005-run-four-languages/validation/verify-ui.cjs`: cùng điều chỉnh đường dẫn browser.
- `specs/006-document-rag-student-import/validation/verify-ui-rag.cjs`: cùng điều chỉnh browser.
- `specs/006-document-rag-student-import/validation/verify-ui-api.cjs`: cùng điều chỉnh browser
  để có thể dùng lại; bài này không nằm trong workflow hiện tại.
- `README.md`: cách chạy Actions, đọc artifact và giới hạn kiểm thử/hosting.
- `specs/007-public-web/spec.md`, `plan.md`, `tasks.md`, `validation.md`: cập nhật phạm vi,
  kế hoạch, danh sách việc và bằng chứng theo yêu cầu chạy thử qua Actions.
