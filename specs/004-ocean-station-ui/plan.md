# Kế hoạch bản mẫu Trạm nghiên cứu dưới biển

**Ngày** 2026-11-05 · **Đặc tả** [004](spec.md)
**Phê duyệt phạm vi** 20 lựa chọn và yêu cầu bắt đầu triển khai theo Spec Kit của người dùng.

## Summary

Cập nhật giao diện trong static/index.html theo bảng quyết định. Dùng ảnh nền cảnh trạm và các lớp trang trí CSS/SVG, tái sử dụng show(), enterWorkspace(), các sự kiện Monaco và phản hồi chat. Bản mẫu đi xuyên ba màn hình với các chức năng thật hiện có.

## Technical Context

Python/FastAPI phục vụ HTML tĩnh. JavaScript dùng Monaco 0.50, marked và DOMPurify có sẵn. Cảnh nền là ảnh tĩnh, chuyển động dùng transform/opacity. Monaco diff editor chỉ tạo khi sinh viên mở xem sửa, hiển thị inline, chỉ đọc và giải phóng khi xóa chat.

Trạng thái UI dùng một bộ điều phối cho màn hình, chuyển cảnh, lựa chọn tập trung, tab di động và ngôn ngữ đã chọn trước lúc Editor tải. Dùng nhịp đang gõ/cuộn và đang xử lý AI để giảm cảnh nền, dừng khi trang ẩn hoặc yêu cầu giảm chuyển động.

## Constitution Check

.specify đã khởi tạo. Hiến chương hiện là mẫu. Áp dụng AGENTS.md người dùng cung cấp. Yêu cầu “bắt đầu làm nhớ là spec kit nhé” sau khi chốt bản mẫu được ghi nhận là phê duyệt triển khai phạm vi giao diện. Lập đặc tả, kế hoạch, danh sách việc trước khi sửa mã.

## Source Scope

- static/index.html — CSS, cảnh trang, markup và tương tác ba màn hình, hover lỗi, diff, tab, trạng thái chuyển động.
- static/ocean-station-bg.png — cảnh trạm nghiên cứu, dùng lại giữa các màn hình.
- .dockerignore — cho phép đóng gói ảnh nền mới cùng giao diện.
- specs/004-ocean-station-ui — thiết kế, công việc và kết quả nghiệm thu.

Backend, dữ liệu xác thực và prompt AI tiếp tục theo các hợp đồng hiện hành. Đặc tả 003 vẫn chờ duyệt kế hoạch riêng.

## Validation

Chụp lại bản HTML đường cơ sở ở thư mục tạm và băm api.py/ai_core.py trước khi sửa. Kiểm tra cú pháp JavaScript bằng Node. Kiểm tra giao diện trong trình duyệt ở 1366×768, 1920×1080 và 390×844. Dùng yêu cầu API được kiểm soát trong môi trường thử để kiểm tra chat stream, lỗi, diff, áp dụng và Undo. Kiểm tra các API xác thực bằng dữ liệu tạm nếu cần; tránh đổi mật khẩu tài khoản thực.

## Artifacts

Xem [nghiên cứu](research.md), [trạng thái UI](data-model.md), [hợp đồng giao diện](contracts/ui.md), [nghiệm thu](quickstart.md) và [các quyết định](design-decisions.md).
