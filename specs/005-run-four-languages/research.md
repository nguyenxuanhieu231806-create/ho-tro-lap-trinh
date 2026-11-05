# Nghiên cứu bộ chạy

code_verifier.py đã có cách ly Docker và kiểm chứng; ưu tiên chia sẻ chính sách container để các chức năng dùng cùng giới hạn. .dockerignore hiện loại code_verifier.py nên cần cho phép tệp này để Dockerfile.grader đóng gói được.

Docker Desktop CLI có thao tác start/status. Docker áp dụng giới hạn khi được truyền qua docker run; ghi rõ CPU/RAM thay cho cấu hình mặc định. Các tài liệu đối chiếu gồm [Docker run](https://docs.docker.com/reference/cli/docker/container/run/), [giới hạn tài nguyên](https://docs.docker.com/engine/containers/resource_constraints/) và [Desktop CLI](https://docs.docker.com/desktop/features/desktop-cli/).

Cancellation cần tới worker thật. Việc hủy await của asyncio.to_thread không tự dừng tiến trình Docker; dùng sự kiện hủy, dừng CLI, xóa container và giữ semaphore tới khi dọn xong.
# Phát hiện từ kiểm thử Docker thật sau khởi động lại

Ngày 05/11/2026, compiler đã chạy nhưng Popen của chương trình bị PermissionError khi chdir vào thư mục case mode 0700 thuộc UID 65534. Bộ điều khiển root đã bỏ DAC_OVERRIDE nên không thể đi vào thư mục này trước preexec_fn hạ UID. Phép tái hiện trong container: mode 0700 lỗi, mode 0755 chạy /bin/true thành công. Chuyển riêng thư mục case sang 0755, vẫn chỉ UID chủ sở hữu có quyền ghi; không mở thêm capability hay gắn thư mục host.

Sau đó Python/Java đạt nhưng C/C++ nhận PermissionError khi chạy /work/program. Phép thử với exec tường minh ở mount tmpfs /work chạy C thành công. Vì vậy /work cho phép exec để thực thi sản phẩm biên dịch, còn /tmp và /capture tiếp tục noexec. Đây chỉ là vùng tạm có giới hạn trong container, không phải thư mục host. Chạy lại các ca thật sau dựng image.

