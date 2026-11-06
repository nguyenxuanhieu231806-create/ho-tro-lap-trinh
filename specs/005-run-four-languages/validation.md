# Kết quả xác minh Chạy thử bốn ngôn ngữ

Ngày 05/11/2026. Phạm vi được triển khai theo yêu cầu trực tiếp thêm nút chạy của người dùng, sau khi lập đặc tả, kế hoạch và danh sách việc trong Spec Kit 005.

## Kết quả

| Nhóm | Kết quả | Bằng chứng |
| --- | --- | --- |
| Giao thức bộ chạy, giới hạn đầu ra, Docker flags, hủy tiến trình kiểm thử, tên lớp Java, tương thích verify_code | 36 kiểm tra đạt; dùng phản hồi kiểm soát, không chạy mã sinh viên trên host | validation/verify-runner.py; runner-results.json |
| API HTTP thật trên Uvicorn, xác thực với DB tạm, kiểm tra đầu vào, bận, độc lập AI, hủy kết nối và giữ suất qua dọn dẹp | 7 nhóm đạt; worker chạy mã được thay bằng fixture | validation/verify-api.py; api-results.json |
| Edge headless, Monaco thật, phản hồi API kiểm soát | 17 kiểm tra đạt, không có lỗi JavaScript | validation/verify-ui.cjs; ui-results.json; ảnh desktop/mobile |
| Biên dịch và thực thi Docker thật | 25/25 ca đạt: Hello World, stdin, lỗi biên dịch, runtime, timeout, output limit cho 4 ngôn ngữ; hủy và dọn container | validation/verify-live.py; live-results.json |
| API với Docker thật | 24/24 kiểm tra đạt, 12 container được quan sát và xóa; SQLite tạm và cổng tạm | validation/verify-api-live.py; api-live-results.json |
| Trình duyệt gọi API/Docker thật | 7/7 kiểm tra đạt: nhập 7 5 in 12, sửa thành nhân in 35, kết quả cũ, Undo; không lỗi JavaScript | validation/verify-ui-live.cjs; ui-live-results.json; 03-run-real-desktop.png |
| Hồi quy giao diện | 28/28 kiểm tra đạt: đăng nhập, 4 ngôn ngữ, chat có dữ liệu kiểm soát, áp dụng bản sửa, Undo, desktop/mobile và giảm chuyển động | validation/verify-regression.cjs; regression-results.json |
| Thiết lập Windows | WSL 3.0.3 và hai thành phần đã cài; sau khi máy khởi động lại Docker Linux và image compiler hoạt động | validation/wsl-setup.json; wsl-features.json; wsl-install.log; live-results.json |

Người dùng đã đồng ý bật WSL/Virtual Machine Platform. Script quản trị dùng NoRestart, không tự khởi động lại máy. Khi người dùng yêu cầu tiếp tục sau đó, Docker Linux đã hoạt động; image fit-tutor-grader:1 được dựng và nghiệm thu thật. Image cuối: sha256:46e04cc8ff476bb9eb067914b9a2035a0d63f0961eca8d2c3111f44ce6dbd377. Hai lỗi quyền thực thi đã được tái hiện và sửa: thư mục case dùng 0755 để bộ điều khiển có thể chdir trước hạ UID, và tmpfs /work có exec tường minh cho sản phẩm C/C++. Không thêm capability; /tmp và /capture vẫn noexec.

## Đối chiếu đặc tả

FR-001/002/003/007: UI và API truyền nguyên bản chụp cùng stdin cho bốn ngôn ngữ, phân biệt trạng thái, chặn yêu cầu không có phiên. Đã kiểm tra bằng compiler thật qua hàm, HTTP và trình duyệt. SC-001/SC-002 đạt với các ca đã cung cấp.

FR-004/005: đã cấu hình giới hạn 3 giây chạy, 15 giây biên dịch, 60.000 ký tự nguồn, stdin 16.384 ký tự, 64 KiB đầu ra mỗi luồng, container không mạng và không bind thư mục host. Vòng lặp vô hạn và đầu ra quá nhiều bị giới hạn trong các ca Docker thật. Thời gian hiển thị gồm cả khởi tạo container và biên dịch, không chỉ thời gian thực thi.

FR-006: API nhận ngắt kết nối và truyền Event hủy; ca HTTP thật xác minh không trả lại suất khi worker còn dọn. Ca Docker thật và HTTP thật xác nhận container đã xóa, worker kết thúc và lượt tiếp theo chạy thành công. SC-003 đạt trong các tình huống kiểm tra khi Docker daemon hoạt động.

FR-008/009/010: kết quả nằm dưới Editor, giữ bố cục 55/45 và tab điện thoại, cảnh báo bản mã cũ, đầu ra dùng textContent. Ảnh trình duyệt đã xem trực tiếp. Hồi quy 28 ca xác minh áp dụng bản sửa/Undo và luồng giao diện; kiểm tra thật xác minh nút Run lấy mã vừa sửa. SC-004/SC-005 đạt trong phạm vi liên quan; phản hồi AI trong hồi quy được kiểm soát, không đánh đồng với kiểm thử độ chính xác hoặc tốc độ Ollama. Không đổi hàm completion.

## Các file thay đổi và lý do

| File | Lý do |
| --- | --- |
| code_verifier.py | Thêm runner_status/run_code, kết quả đầy đủ, hủy có giới hạn, tái sử dụng cách ly với verify_code và hỗ trợ Java; sửa quyền case_dir và mount exec sau tái hiện thật |
| api.py | Hai API đăng nhập bắt buộc /runner và /run, DTO, suất chạy riêng và theo dõi ngắt kết nối |
| static/index.html | Nút Chạy thử/Dừng, stdin, stdout/stderr, metadata và kết quả cũ; vùng cuộn nội bộ |
| Dockerfile.grader | Nhãn phiên bản giao thức của image compiler |
| Dockerfile | Đóng gói code_verifier.py để API nhập mô-đun được |
| .dockerignore | Cho hai file bộ chạy vào build context được chọn lọc |
| README.md | Hướng dẫn dựng image, chạy console, giới hạn, kiểm tra và ranh giới triển khai Docker của hệ thống |
| .specify/feature.json | Chọn feature 005 đang thực hiện |
| specs/005-run-four-languages/spec.md | Đặc tả tính năng và tiêu chí nghiệm thu |
| specs/005-run-four-languages/plan.md | Kế hoạch kỹ thuật trước khi triển khai |
| specs/005-run-four-languages/research.md | Quyết định dùng bộ chạy Docker sẵn có |
| specs/005-run-four-languages/data-model.md | Mô tả dữ liệu yêu cầu/kết quả; không thay SQLite |
| specs/005-run-four-languages/contracts/runner.md | Hợp đồng hai route mới |
| specs/005-run-four-languages/quickstart.md | Luồng sử dụng và nghiệm thu |
| specs/005-run-four-languages/checklists/requirements.md | Checklist đặc tả |
| specs/005-run-four-languages/tasks.md | Theo dõi đầy đủ công việc, cập nhật hoàn thành sau nghiệm thu Docker thật |
| specs/005-run-four-languages/validation.md | Báo cáo này |
| specs/005-run-four-languages/validation/verify-api.py | Kiểm tra HTTP và DB tạm |
| specs/005-run-four-languages/validation/api-results.json | Kết quả 7 nhóm API |
| specs/005-run-four-languages/validation/verify-runner.py | Kiểm tra giao thức, hủy và cấu hình cách ly |
| specs/005-run-four-languages/validation/runner-results.json | Kết quả 36 phép thử có kiểm soát |
| specs/005-run-four-languages/validation/verify-ui.cjs | Kiểm tra trình duyệt cho nút và vùng chạy |
| specs/005-run-four-languages/validation/ui-results.json | Kết quả 17 phép thử giao diện |
| specs/005-run-four-languages/validation/01-run-desktop.png | Ảnh đối chiếu khung desktop |
| specs/005-run-four-languages/validation/02-run-mobile.png | Ảnh đối chiếu khung điện thoại |
| specs/005-run-four-languages/validation/verify-live.py | 25 ca compiler/runtime thật, chỉ chạy trong Docker |
| specs/005-run-four-languages/validation/live-results.json | Kết quả 25/25 ca thật, đầu ra và mã thoát |
| specs/005-run-four-languages/validation/verify-api-live.py | Nghiệm thu HTTP/SQLite tạm với Docker thật và dọn tài nguyên |
| specs/005-run-four-languages/validation/api-live-results.json | Kết quả 24 phép thử HTTP/Docker thật |
| specs/005-run-four-languages/validation/verify-ui-live.cjs | Nghiệm thu Run qua trình duyệt không thay API chạy bằng fixture |
| specs/005-run-four-languages/validation/ui-live-results.json | Kết quả 7 phép thử trình duyệt thật |
| specs/005-run-four-languages/validation/03-run-real-desktop.png | Ảnh chương trình Python thật nhận 7 5 và in 12 |
| specs/005-run-four-languages/validation/verify-regression.cjs | Tái sử dụng bộ hồi quy giao diện 004, giữ kết quả trong feature 005 |
| specs/005-run-four-languages/validation/regression-results.json | Kết quả 28 phép thử hồi quy |
| specs/005-run-four-languages/validation/01-login.png | Ảnh đăng nhập sau hồi quy |
| specs/005-run-four-languages/validation/02-welcome.png | Ảnh chào mừng sau hồi quy |
| specs/005-run-four-languages/validation/03-workspace.png | Ảnh xem diff và cảnh báo dòng lỗi |
| specs/005-run-four-languages/validation/04-mobile-chat.png | Ảnh tab Chat trên điện thoại |
| specs/005-run-four-languages/validation/05-mobile-editor.png | Ảnh tab Editor trên điện thoại |
| specs/005-run-four-languages/validation/06-desktop-large.png | Ảnh kiểm tra khung desktop lớn |
| specs/005-run-four-languages/validation/wsl-setup.json | Kết quả cài WSL và yêu cầu khởi động lại |
| specs/005-run-four-languages/validation/wsl-features.json | Trạng thái hai thành phần Windows sau khi bật |
| specs/005-run-four-languages/validation/wsl-install.log | Bằng chứng cài WSL thành công |

Không đổi requirements.txt, ai_core.py, dữ liệu tài khoản hay hàm seed. Không chỉnh cơ chế sinh nội dung Ollama.

## Cách sử dụng sau nghiệm thu

1. Giữ Docker Desktop chạy. Image compiler đã được dựng trên máy, không cần dựng lại mỗi lần mở hệ thống.
2. Tại thư mục dự án, khởi động hệ thống bằng run.ps1; đăng nhập rồi chọn ngôn ngữ, nhập nguồn/stdin và bấm Chạy thử. Sau khi áp dụng bản sửa AI, chạy lại bằng cùng nút.
3. Khi thay bộ chạy/image, dựng lại bằng docker build -f Dockerfile.grader -t fit-tutor-grader:1 . rồi chạy verify-live.py để nghiệm thu lại.

Toàn bộ T001–T011 hoàn thành. Chạy thành công với một bộ dữ liệu không chứng minh thuật toán đúng cho mọi trường hợp. Chương trình console nhận stdin trước khi chạy; không có terminal tương tác hay giao diện đồ họa. Các máy chủ/SQLite của kiểm thử là tạm và đã dọn; không để lại máy chủ nền chiếm cổng 8000 của người dùng.
