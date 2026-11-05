# Hợp đồng hiển thị đăng nhập

- `#student-account` là ô email trống, có nhãn Tài khoản (Email).
- Form gửi `username` và `password` tới `POST /api/auth/login`. Hồ sơ trả về dùng cho màn hình chào mừng và Header.
- `GET /api/auth/accounts` bị gỡ. `GET /api/auth/me` yêu cầu phiên hợp lệ để trả hồ sơ chủ phiên.
- Nút Đổi mật khẩu điều khiển nhóm nhập mật khẩu mới. Luồng đổi mật khẩu hiện dùng phiên đã xác thực.
