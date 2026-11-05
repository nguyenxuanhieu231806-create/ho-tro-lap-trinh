# Tasks — Đăng nhập bằng email tự nhập

- [x] T001 Rà soát phạm vi, đặc tả và thiết kế.
- [x] T002 [US1] Đổi form, gỡ phần dựng thẻ và dữ liệu gợi ý trong `static/index.html`.
- [x] T003 [US1] Gỡ route danh sách công khai trong `api.py`.
- [x] T004 [US2] Cập nhật nút Đổi mật khẩu và tiếp tục phiên trong `static/index.html`.
- [x] T005 Cập nhật hướng dẫn đăng nhập trong `README.md`.
- [x] T006 Kiểm tra form và luồng xác thực thử nghiệm, đối chiếu FR-001 đến FR-004.

T001 đi trước các sửa đổi. T006 thực hiện sau khi hoàn tất form, đường dẫn và hướng dẫn.

## Kết quả

Kiểm tra HTML và JavaScript xác nhận form nhập email, nút đổi mật khẩu, kiểm tra nhập lại và gắn hồ sơ Header. Bốn tài khoản đều xác thực thành công trong SQLite bộ nhớ. Kiểm tra mã nguồn xác nhận thay đổi Backend giới hạn ở route danh sách.

Máy chủ cổng 8000 đã phục vụ HTML mới. Tiến trình Backend đang chạy cần khởi động lại để nạp thay đổi route.
