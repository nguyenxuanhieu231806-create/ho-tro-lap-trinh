# Đặc tả bản mẫu Trạm nghiên cứu dưới biển

**Ngày** 2026-11-05
**Trạng thái** Đã triển khai và nghiệm thu bản mẫu ba màn hình.
**Cơ sở duyệt** Người dùng chọn bản mẫu cả ba màn hình và nhắn “bắt đầu làm nhớ là spec kit nhé”.

## User Scenarios & Testing

### US1 — Đăng nhập và khám phá trạm học tập — P1

Sinh viên thấy form trắng ở giữa cảnh trạm nghiên cứu dưới biển. Sau khi đăng nhập, màn chào mừng có bốn điểm sáng C, C++, Java và Python. Chọn điểm sáng mở giới thiệu ngắn. Bấm Bắt đầu học chuyển cảnh lặn xuống không gian học. Bỏ qua vào học ngay.

Các ca chấp nhận gồm đăng nhập hợp lệ và sai mật khẩu, đổi mật khẩu, màn chào mừng mỗi lần đăng nhập, chọn cả bốn ngôn ngữ và chọn trước khi Editor tải xong, bấm bỏ qua hoặc bắt đầu nhiều lần.

### US2 — Làm việc vừa khít màn hình — P1

Trên máy tính, Editor chiếm 55%, Chat chiếm 45%, các vùng nội dung tự cuộn trong khung. Trên điện thoại có hai tab Viết mã và Chat AI. Logo lớn ở đăng nhập và chào mừng, thu gọn trên thanh đầu trang. Hai khung học nền trắng, mã giữ màu cú pháp.

Các ca chấp nhận gồm ba màn hình tại 1366×768, 1920×1080 và điện thoại 390×844. Các nút cuối khung luôn truy cập được. Chuyển tab và đổi ngôn ngữ giữ đúng bản nháp hiện hành.

### US3 — Đọc lỗi và xem mã sửa — P1

Dấu đỏ cuối dòng mở mô tả ngắn khi rê chuột. Sinh viên bấm dòng lỗi trong chat để Editor cuộn tới và làm nổi dòng đó trong chốc lát. Bản sửa hiển thị thay đổi ngay từng dòng, xanh cho thêm và đỏ cho xóa, có thể xem mã đầy đủ và áp dụng theo bản chụp hiện hành.

Các ca chấp nhận gồm mã đã thay đổi khi AI xử lý, sửa dài, bấm lỗi trên điện thoại, áp dụng rồi Undo, xóa hội thoại sau khi xem bản so sánh.

### US4 — Hoạt ảnh và chế độ Tập trung — P2

Nền trạm nghiên cứu dùng navy, ngọc lam và điểm nhấn cam san hô. Trạm ở xa có cửa kính, đèn tín hiệu, cá bơi. Khi học có ánh sáng và bong bóng ngoài hai khung. Nút Tập trung dừng hoạt ảnh và cho phép tiếp tục. Ưu tiên gõ mã và cuộn mượt khi máy đang bận.

Các ca chấp nhận gồm bật/tắt Tập trung, hệ điều hành yêu cầu giảm chuyển động, chuyển sang tab trình duyệt khác, đang gõ hoặc cuộn và AI đang xử lý. Trạng thái chờ AI dùng dòng chữ với ba chấm, sau đó hiển thị nội dung stream thực tế.

### Edge Cases

Chuyển màn hình khi đăng nhập chậm, Monaco tải muộn, cảnh nền chưa tải, intro bị bỏ qua, bàn phím trên điện thoại, nội dung chat dài, model đang bận, bản sửa cùng mã gốc, thay đổi ngôn ngữ khi đang có kết quả cũ.

## Requirements

- FR-001 — Phong cách trạm nghiên cứu dưới biển với navy, ngọc lam và cam san hô.
- FR-002 — Form trắng giữa màn hình, logo lớn và tài khoản email được nhập bằng tay.
- FR-003 — Màn chào mừng có mỗi lần đăng nhập, nút Bỏ qua và Bắt đầu học với chuyển cảnh lặn.
- FR-004 — Bốn điểm chọn ngôn ngữ có giới thiệu ngắn và đồng bộ ngôn ngữ mở trong Editor.
- FR-005 — Máy tính dùng tỷ lệ cố định 55/45, vừa khít cửa sổ trình duyệt và cuộn trong từng khung.
- FR-006 — Điện thoại dùng tab Viết mã và Chat AI.
- FR-007 — Editor và Chat trắng, giữ logo khoa làm đại diện AI và màu cú pháp.
- FR-008 — Dấu cảnh báo cuối dòng mở mô tả khi rê chuột, bấm dòng trong chat cuộn và làm nổi dòng mã gốc.
- FR-009 — Xem sửa theo từng dòng thêm/xóa và áp dụng có Undo, tuân theo bản chụp mã.
- FR-010 — Nền chuyển động nhẹ khi học, có nút Tập trung, giảm chuyển động theo lựa chọn hệ điều hành và trạng thái hoạt động của trang.
- FR-011 — Dấu chờ AI ba chấm phản ánh chờ thật và nhường chỗ cho câu trả lời khi có nội dung.
- FR-012 — Dùng các luồng xác thực, AI và gợi ý mã hiện hành.

### Key Entities

Trạng thái màn hình, ngôn ngữ được chọn, tab di động hiện tại, lựa chọn Tập trung, bản chụp mã và bản mã sửa.

## Success Criteria

- SC-001 — Hoàn thành luồng đăng nhập → chào mừng → IDE và luồng bỏ qua trên bản Web.
- SC-002 — Tại các kích thước đã định, hai khung và nút gửi truy cập được, trang máy tính không tràn ngang.
- SC-003 — Bốn lựa chọn ở intro mở đúng ngôn ngữ và bản nháp.
- SC-004 — Chuyển tab di động giữ nội dung mã và chat. Nút dòng lỗi đưa về đúng vị trí.
- SC-005 — So sánh thêm/xóa chính xác với hai bản mã, áp dụng và Undo hoạt động, kết quả cũ bị vô hiệu hóa theo cơ chế hiện có.
- SC-006 — Hoạt ảnh dừng khi bật Tập trung, giảm chuyển động hoặc trang bị ẩn. Gõ, cuộn và chat stream có thể sử dụng khi cảnh nền hiển thị.
- SC-007 — Các đường xác thực và AI giữ hợp đồng hiện hành và vượt kiểm tra hồi quy liên quan.

## Assumptions

Bản đầu tiên dùng một cảnh nền tĩnh có các lớp ánh sáng và sinh vật chuyển động nhẹ để phù hợp máy chạy Ollama cục bộ. Hiệu ứng lặn kéo dài khoảng 0,8 giây và bỏ qua khi bật giảm chuyển động. Tạm giảm cảnh khi đang gõ, cuộn hoặc AI xử lý thay cho theo dõi CPU liên tục.
