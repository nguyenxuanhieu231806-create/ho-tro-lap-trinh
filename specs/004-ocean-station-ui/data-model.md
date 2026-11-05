# Trạng thái giao diện

| Trạng thái | Nơi sử dụng |
| --- | --- |
| Màn hình login/intro/ide | Luồng show() và xác thực hiện hành |
| Ngôn ngữ đã chọn | Bốn đèn intro, #language và model Monaco |
| Tab di động editor/chat | Hiển thị khung học và điều hướng từ kết quả lỗi |
| Tập trung | Lưu tùy chọn trên thiết bị, nút aria-pressed |
| Giảm chuyển động | matchMedia, trang ẩn và trạng thái bận/tương tác |
| Đang chuyển cảnh | Chặn thao tác lặp, có cách kết thúc khi hoạt ảnh tắt |
| Bản chụp mã và mã sửa | Đối chiếu diff và matches(saved) hiện có |
| Tài nguyên diff | Editor và model phụ được giải phóng cùng kết quả |

Dữ liệu tài khoản và nội dung giao tiếp tiếp tục đi qua các API và mô hình hiện hành.
