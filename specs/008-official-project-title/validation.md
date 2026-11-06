# Kiểm chứng 008 — Tên đề tài chính thức

Ngày 06/11/2026. Người dùng duyệt toàn bộ phạm vi trước triển khai.

Tên đầy đủ: **Hệ thống hỗ trợ lập trình cho sinh viên Khoa Công nghệ Thông tin – Trường Đại học Hải Phòng**.
Header rút gọn có tooltip đầy đủ; lời chào giữ họ tên và lớp.

## Kết quả đối chiếu

| Tiêu chí | Kết quả |
| --- | --- |
| Tên chính thức trên giao diện chính | Đã đổi title, đăng nhập, chào mừng, Header và tooltip |
| Trang quản trị | Nhãn trở về và thông báo không còn Web IDE |
| Chỉ dẫn AI và tên API hiển thị | SYSTEM_NAME đầy đủ; SYSTEM_ROLE và Modelfile đồng nhất |
| README/CLI/Actions/tài liệu | Đã đồng bộ lời văn và tên hiển thị |
| Hợp đồng/logic | 9 kiểm tra AST/cấu hình đạt; thay đổi chỉ là các chuỗi đã duyệt và chú thích |
| Cú pháp | Toàn bộ Python gốc; hai script inline; admin.js/rag.js; PowerShell và YAML hợp lệ |
| Giao diện hiện hành | 28 kiểm tra ba màn hình/Editor/Chat +21 RAG/quản trị +17 Chạy thử =66 đạt |
| Bố cục với tiêu đề dài | 1366×768,1920×1080,390×844: đăng nhập, lời chào cá nhân hóa, không tràn ngang, Bỏ qua truy cập được |
| Ảnh kiểm tra | Đã xem màn chào mừng desktop và đăng nhập/chào mừng mobile; tên mới và nút nằm trong khung |

Một lần chạy bộ 004 timeout khi đăng nhập lại sau đăng xuất, sau khi đã đạt25 kiểm tra.
Chạy lại cùng bài kiểm thử đạt đủ28, không có lỗi JavaScript và không sửa logic xác thực.
Rà soát chỉ ra bài kiểm thử cũ chỉ đợi form hiện mà không đợi location.reload hoàn tất;
đây là khả năng đua thời điểm tải trang, không coi lượt timeout là kết quả đạt.
Các nhóm RAG/Chạy thử hoàn tất riêng, không chạy lại khi đã đạt.

Kiểm thử dùng phiên/tài khoản/phản hồi AI được kiểm soát; không đọc hoặc thay SQLite
thật, không gọi mô hình thật và không đánh giá lại chất lượng AI/hiệu năng compiler.
Không tạo tệp mã test mới. Chạy các bài kiểm thử sẵn có bằng bộ nạp trong bộ nhớ và
lưu báo cáo/ảnh mới vào `ci-results/008-official-project-title/` (bỏ khỏi Git);
ảnh/JSON bằng chứng lịch sử không bị ghi đè.

## Các trường hợp còn từ web theo phạm vi đã duyệt

- `fit-hpuni-programming-web`: định danh health, đồng bộ với bộ khởi chạy.
- `web` trong Docker Compose và `fit-tutor-web:ci`: định danh/lệnh hiện hành.
- `verify-web-ide.yml`, nhóm concurrency và thư mục `007-public-web`: đường dẫn kỹ thuật.
- `Web Worker`: thuật ngữ API trình duyệt chính thức.
- URL/tên tệp cũ trong nhật ký chẩn đoán, ví dụ tên báo cáo .docx; ví dụ/libraries
  do bên thứ ba cung cấp, .git/.venv/.env/dữ liệu/ảnh lịch sử: giữ nguyên.
- Đặc tả008 dùng từ cần loại bỏ khi giải thích phạm vi, không dùng làm tên sản phẩm.

Các tệp Markdown đã chỉnh giữ nguyên toàn bộ khối lệnh có hàng rào và URL gốc.
Màu sắc, hoạt ảnh, logic giao diện, endpoint, schema, DB, quyền và cấu hình model
không bị thay đổi. Modelfile là cấu hình nguồn; chưa tạo lại model đang lưu trên Ollama.

## Danh mục tệp

| Tệp | Lý do |
| --- | --- |
| `.github/workflows/verify-web-ide.yml` | Đổi tên hiển thị workflow, nhãn bước và thông báo; giữ nguyên job/lệnh/quyền. |
| `Dockerfile.grader` | Đổi cách gọi trong chú thích, không đổi bước dựng image. |
| `Modelfile` | Đồng bộ hai câu chỉ dẫn dùng từ giao diện, không đổi model/tham số. |
| `README.md` | Tên đề tài đầy đủ, tên Actions và lời hướng dẫn thống nhất. |
| `ai_core.py` | Tên ứng dụng đầy đủ và hai câu chỉ dẫn AI; sửa mô tả mô-đun. |
| `api.py` | Đổi từ trong chú thích, giữ API và service health. |
| `code_verifier.py` | Đổi chú thích/thông báo CLI, giữ bộ kiểm chứng và sandbox. |
| `manage_accounts.py` | Đổi mô tả CLI quản lý tài khoản. |
| `rag_store.py` | Đổi chú thích, không đổi lưu trữ/dữ liệu. |
| `run.ps1` | Đổi một thông báo dừng hệ thống, giữ toàn bộ lệnh và health. |
| `specs/001-hide-account-cards/quickstart.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/003-improve-ollama-prompt/contracts/tutor-prompt.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/003-improve-ollama-prompt/plan.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/003-improve-ollama-prompt/quickstart.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/003-improve-ollama-prompt/research.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/003-improve-ollama-prompt/spec.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/004-ocean-station-ui/design-decisions.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/004-ocean-station-ui/quickstart.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/004-ocean-station-ui/spec.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/005-run-four-languages/data-model.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/005-run-four-languages/plan.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/005-run-four-languages/validation.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/006-document-rag-student-import/plan.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/006-document-rag-student-import/research.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/006-document-rag-student-import/spec.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. |
| `specs/007-public-web/plan.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. Giữ các cập nhật đổi tên GitHub có sẵn trước lượt này. |
| `specs/007-public-web/spec.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. Giữ các cập nhật đổi tên GitHub có sẵn trước lượt này. |
| `specs/007-public-web/tasks.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. Giữ các cập nhật đổi tên GitHub có sẵn trước lượt này. |
| `specs/007-public-web/validation.md` | Đồng bộ lời văn dùng tên hệ thống; giữ URL, đường dẫn, lệnh và bằng chứng cũ. Giữ các cập nhật đổi tên GitHub có sẵn trước lượt này. |
| `specs/008-official-project-title/plan.md` | Kế hoạch triển khai và cách kiểm chứng. |
| `specs/008-official-project-title/spec.md` | Đặc tả tên chính thức, phạm vi và phê duyệt. |
| `specs/008-official-project-title/tasks.md` | Theo dõi các việc đã hoàn thành. |
| `specs/008-official-project-title/validation.md` | Ghi kết quả, giới hạn và danh mục tệp sửa. |
| `static/admin.html` | Đổi nhãn quay về hệ thống. |
| `static/admin.js` | Đổi hướng dẫn đăng nhập trên trang quản trị. |
| `static/index.html` | Tên trang/đăng nhập/lời chào cá nhân hóa/Header/tooltip. |
