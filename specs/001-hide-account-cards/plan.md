# Implementation Plan — Đăng nhập bằng email tự nhập

**Date**: 2026-11-04  
**Spec**: [Đặc tả](spec.md)

## Summary

Thay phần chọn tài khoản trong `static/index.html` bằng ô email giữ ID hiện tại. Gỡ markup, CSS và JavaScript của danh sách thẻ. Đặt nút Đổi mật khẩu dưới nút Đăng nhập. Bỏ route đọc danh sách công khai trong `api.py` vì form nhập email dùng các route xác thực hiện hành.

## Technical Context

FastAPI phục vụ HTML tĩnh. Đăng nhập nhận `username` và `password`, dùng SQLite và cookie phiên. Trình duyệt kiểm tra kiểu email. Backend chuẩn hóa email, xác thực rồi trả hồ sơ cá nhân cho màn hình chào mừng và Header.

## Constitution Check

Người dùng chỉ định trực tiếp form tự nhập email và cho phép sửa Backend khi cần. Phạm vi gồm giao diện đăng nhập, đường dẫn danh sách công khai và tài liệu liên quan. Thiết kế giữ mô hình dữ liệu, seed và các route xác thực.

## Project Structure

- `static/index.html` chứa form, nút đổi mật khẩu và trình xử lý.
- `api.py` gỡ route danh sách công khai.
- `README.md` cập nhật hướng dẫn nhập email.
- Tài liệu thiết kế và nghiệm thu nằm trong hồ sơ tính năng.

## Validation

Kiểm tra HTML và JavaScript, luồng form, bốn tài khoản trong SQLite bộ nhớ, đổi mật khẩu và route công khai. Đối chiếu nội dung seed trước và sau.
