# Đặc tả Chạy thử mã C, C++, Java và Python

**Ngày** 2026-11-05
**Cơ sở triển khai** Người dùng yêu cầu bổ sung trực tiếp nút chạy mã đang viết và mã sau khi AI sửa để xem chương trình chạy được hay chưa, hỗ trợ cả bốn ngôn ngữ. Áp dụng quy trình Spec Kit trước khi sửa mã.

## User Scenarios & Testing

### US1 — Chạy mã và xem kết quả — P1

Sinh viên chọn ngôn ngữ, viết mã, điền dữ liệu đầu vào nếu có và bấm Chạy thử. Kết quả hiện ngay trong khung mã, gồm đầu ra, lỗi, trạng thái kết thúc và thời gian. Sau khi áp dụng bản sửa AI, bấm Chạy thử sẽ lấy bản mã mới.

Ca chấp nhận gồm Hello World, chương trình đọc hai số và in tổng cho từng ngôn ngữ, lỗi cú pháp/biên dịch, lỗi khi chạy và chương trình không in gì.

### US2 — Chạy có giới hạn và dừng — P1

Sinh viên dừng tác vụ hoặc chương trình vượt thời gian. Hệ thống kết thúc tác vụ và dọn tài nguyên. Một tác vụ chạy mã tại một thời điểm, độc lập với suất xử lý Ollama.

Ca chấp nhận gồm vòng lặp vô hạn, đầu ra quá nhiều, tác vụ đồng thời, đóng kết nối và môi trường chạy chưa sẵn sàng.

### US3 — Kết quả gắn đúng bản mã — P2

Kết quả ghi rõ ngôn ngữ và thời điểm chạy. Nếu Editor thay đổi hoặc đổi ngôn ngữ, kết quả được đánh dấu thuộc bản chạy trước. Chạy xong không tự kết luận chương trình đúng mọi yêu cầu bài toán.

### Edge Cases

Không có dữ liệu nhập cho input/scanf/Scanner, nguồn rỗng/quá dài, stdin Unicode, Java dùng tên lớp công khai khác Main hoặc package, nguồn đổi trong khi đang chạy, sinh viên đang chat hoặc máy chủ bận, Docker chưa có image.

## Requirements

- FR-001 — Có nút Chạy thử cho C, C++, Java, Python và ô dữ liệu stdin.
- FR-002 — Chạy bản mã hiện tại đã chụp tại lúc bấm, trả stdout/stderr và mã thoát thực tế.
- FR-003 — Phân biệt completed, compile_error, runtime_error, timeout, output_limit, cancelled và unavailable.
- FR-004 — Giới hạn chạy chương trình 3 giây, biên dịch 15 giây, nguồn 60.000 ký tự, stdin 16.384 ký tự và đầu ra tối đa 64 KiB mỗi luồng.
- FR-005 — Mã sinh viên chạy trong Docker Linux cách ly mạng/tài nguyên với tệp tạm, không gắn thư mục dự án hoặc dữ liệu tài khoản vào tác vụ.
- FR-006 — Giữ giới hạn một tác vụ chạy; yêu cầu dừng hoặc mất kết nối phải dọn container trước khi trả lại suất.
- FR-007 — Endpoint chạy yêu cầu phiên đăng nhập và dữ liệu hợp lệ.
- FR-008 — Bố cục desktop 55/45 và tab điện thoại tiếp tục có vùng cuộn nội bộ; kết quả chạy có thể đóng/mở.
- FR-009 — Mã sau khi AI sửa chạy qua cùng nút, kèm nhãn khi kết quả thuộc bản mã cũ.
- FR-010 — Thông báo trạng thái tiếng Việt, hỗ trợ chạy chương trình console với dữ liệu nhập trước.

### Key Entities

Yêu cầu chạy gồm ngôn ngữ, mã nguồn và stdin. Kết quả gồm trạng thái, stdout, stderr, exit_code, duration_ms và thông báo. Bản chụp giao diện giữ model, version, mã và ngôn ngữ.

## Success Criteria

- SC-001 — Chạy thật Hello World và chương trình cộng hai số cho cả bốn ngôn ngữ.
- SC-002 — Lỗi biên dịch/cú pháp và lỗi khi chạy hiển thị riêng; chương trình vô hạn bị dừng.
- SC-003 — Dừng tác vụ/mất kết nối không để lại container chạy và suất được giải phóng sau dọn dẹp.
- SC-004 — Kết quả không ghi đè mã và có cảnh báo nếu mã đã đổi.
- SC-005 — Đăng nhập, chat, gợi ý mã, xem sửa và Undo tiếp tục qua kiểm tra liên quan.

## Assumptions

Dùng lại Dockerfile.grader và bộ cách ly đã có. Runtime mặc định Python 3.11, Java 17, C11 và C++17 theo image hiện có. Docker Desktop cục bộ cần chạy và image biên dịch cần được tạo một lần. Nếu có bước cài đặt hệ thống hoặc thỏa thuận Docker cần người dùng, ghi rõ trạng thái và hoàn thành phần mã độc lập.
