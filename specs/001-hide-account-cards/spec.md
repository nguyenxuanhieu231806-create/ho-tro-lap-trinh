# Feature Specification — Đăng nhập bằng email tự nhập

**Feature Branch**: Không áp dụng trong thư mục hiện tại  
**Created**: 2026-11-04  
**Status**: Đã triển khai và kiểm tra mã nguồn  

## User Scenarios & Testing

### User Story 1 — Nhập email cá nhân (Priority: P1)

Sinh viên mở form gọn, tự nhập email đã cấp và mật khẩu. Hồ sơ xuất hiện ở màn hình chào mừng và Header sau xác thực.

**Independent Test**: Dùng dữ liệu thử nghiệm để đăng nhập lần lượt với bốn tài khoản cấp sẵn.

1. Khách mở trang và thấy logo, tiêu đề, ô email, ô mật khẩu, nút Đăng nhập và Đổi mật khẩu.
2. Trang không hiển thị dòng đếm, thẻ, danh sách chọn hoặc chi tiết hồ sơ trước xác thực.
3. Đăng nhập thành công hiển thị đúng họ tên, MSSV, lớp và năm học. Nhập sai thông tin hiển thị thông báo chung.

### User Story 2 — Đổi mật khẩu và tiếp tục phiên (Priority: P2)

Sinh viên có thể đổi mật khẩu ngay từ form hoặc qua Header. Khi có phiên hợp lệ, form có nút tiếp tục phiên với nhãn chung.

**Independent Test**: Mở và đóng phần đổi mật khẩu, kiểm tra xác nhận mật khẩu mới, rồi xác thực và cập nhật mật khẩu trên dữ liệu thử nghiệm.

### Edge Cases

- Email nhập có chữ hoa vẫn được chuẩn hóa khi xác thực.
- Khi mật khẩu mới nhập lại khác nhau, form báo lỗi trước khi gửi.
- Khách không thể lấy danh sách hồ sơ bằng đường dẫn từng dùng để tải danh sách chọn.

## Requirements

- **FR-001**: Gỡ dòng đếm, thẻ và danh sách chọn. Cung cấp ô nhập email trống.
- **FR-002**: Giữ bốn tài khoản cấp sẵn, dữ liệu, thông tin hồ sơ và cơ chế cấp thêm tài khoản.
- **FR-003**: Hồ sơ được cung cấp cho chủ tài khoản sau xác thực. Đóng đường dẫn công khai trả danh sách.
- **FR-004**: Giữ luồng đổi mật khẩu ở form và Header, màn hình chào mừng, tiếp tục phiên và đăng xuất.

## Success Criteria

- **SC-001**: Có 0 thẻ và 0 danh sách email công khai trên màn hình.
- **SC-002**: Bốn tài khoản thử nghiệm đều đăng nhập và nhận đúng hồ sơ.
- **SC-003**: Yêu cầu ẩn danh không lấy được danh sách hồ sơ. Đổi mật khẩu thành công trong dữ liệu thử nghiệm.

## Assumptions

- Nút Đổi mật khẩu nhỏ dưới nút Đăng nhập là cách bố trí hiện tại của bản sửa, chờ lựa chọn vị trí cuối của người dùng.
- Các ca thử dùng SQLite trong bộ nhớ để tách khỏi tài khoản đang sử dụng.
