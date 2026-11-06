# Kế hoạch Chạy thử bốn ngôn ngữ

## Cơ sở triển khai

Đặc tả dựa trên yêu cầu trực tiếp thêm nút chạy của người dùng. Phạm vi bao gồm API, giao diện và bộ chạy cách ly cần thiết. Đã phân tích code_verifier.py, api.py, static/index.html và Dockerfile.grader.

## Thiết kế

Tái sử dụng chính sách Docker không mạng, RAM 512 MiB, CPU 1, giới hạn PID và các tmpfs hiện có. Bộ điều khiển container hạ UID/GID trước khi biên dịch và thực thi. Mở rộng kết quả với stdout/stderr, mã thoát và thời gian. Java nhận diện tên lớp công khai và package để dựng tên tệp/lệnh tương ứng.

GET /api/tutor/runner trả khả dụng và giới hạn. POST /api/tutor/run nhận current_code/language/stdin. Dùng một semaphore riêng với sự kiện hủy truyền xuống tiến trình Docker. Coroutine giữ suất tới khi worker dọn tác vụ xong.

Thêm RunRequest/RunResult và hai route trong api.py. Giao diện có Chạy thử/Dừng, stdin và khung kết quả dưới Editor; mã và ngôn ngữ trong kết quả đi cùng snapshot. Nút AI và gợi ý mã tiếp tục dùng luồng hiện hành.

## Tệp triển khai

code_verifier.py, api.py, static/index.html, Dockerfile.grader, .dockerignore, Dockerfile và README.md. Dockerfile của hệ thống đóng gói mô-đun chạy để nhập API được; máy chủ local gọi Docker CLI. Dùng Docker Linux cục bộ cho lần triển khai này.

## Xác minh

Bộ ca thật cho bốn ngôn ngữ gồm Hello World, cộng số từ stdin, lỗi biên dịch, lỗi runtime và vòng lặp vô hạn. Thử Java khác tên Main, tiếng Việt và giới hạn đầu ra. Kiểm tra hủy và tài nguyên Docker. API thử trên DB tạm và trình duyệt thử bố cục/kết quả với dữ liệu kiểm soát, cuối cùng kiểm tra endpoint thật khi môi trường sẵn sàng.

Hiến chương đang là mẫu. Áp dụng AGENTS.md và các tài liệu Spec Kit trong đặc tả, kế hoạch, danh sách việc. Đặc tả 003 về prompt tiếp tục theo phạm vi riêng.
