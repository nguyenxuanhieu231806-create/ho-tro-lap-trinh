# Danh sách việc bản mẫu Trạm nghiên cứu dưới biển

**Input** [Đặc tả](spec.md), [kế hoạch](plan.md), [nghiên cứu](research.md)
**Phê duyệt** Người dùng đã yêu cầu bắt đầu theo 20 lựa chọn.

## Chuẩn bị

- [x] T001 Kiểm tra mã nguồn và .specify, ghi đặc tả và kế hoạch trong specs/004-ocean-station-ui.
- [x] T002 Lưu HTML đường cơ sở và băm các tệp backend ở thư mục tạm.
- [x] T003 [P] Tạo static/ocean-station-bg.png theo bảng màu và cảnh trạm đã duyệt.

## US1 — Ba màn hình và chọn ngôn ngữ

- [x] T004 [US1] Sửa CSS/markup đăng nhập và intro trong static/index.html.
- [x] T005 [US1] Thêm bốn đèn chọn ngôn ngữ, nội dung giới thiệu, Bỏ qua và chuyển cảnh lặn trong static/index.html.
- [x] T006 [US1] Đồng bộ ngôn ngữ chọn trước khi Monaco tải và các bản nháp hiện có.

## US2 — Bố cục và tab di động

- [x] T007 [US2] Gom quy tắc khung nhìn 55/45, header và vùng cuộn trong static/index.html.
- [x] T008 [US2] Thêm hai tab điện thoại và gọi lại bố trí Monaco khi hiện Editor.

## US3 — Phản hồi mã và chat

- [x] T009 [US3] Thêm avatar khoa, trạng thái chờ ba chấm và highlight khi bấm dòng lỗi.
- [x] T010 [US3] Thay phần xem sửa bằng Monaco inline diff, giữ áp dụng/Undo và giải phóng tài nguyên.

## US4 — Hoạt ảnh và tập trung

- [x] T011 [US4] Thêm bộ điều phối chuyển động, nút Tập trung và giảm cảnh khi trang bận hoặc ẩn.
- [x] T012 [US4] Kiểm tra chế độ giảm chuyển động và thao tác chuyển cảnh lặp.

## Nghiệm thu

- [x] T013 Kiểm tra cú pháp, ID DOM và hành vi API bằng dữ liệu kiểm soát.
- [x] T014 Kiểm tra và chụp ba màn hình trên desktop/mobile trong trình duyệt.
- [x] T015 Đối chiếu SC-001 tới SC-007, băm backend sau thay đổi và ghi kết quả trong specs/004-ocean-station-ui/validation.md.

## Phụ thuộc và phối hợp

T001–T002 trước các sửa mã. T003 và thiết kế cảnh có thể chạy song song. Phần CSS/markup và JavaScript dùng các vùng chỉnh riêng, tích hợp trước T013. US1–US4 hoàn tất trước nghiệm thu toàn luồng.
