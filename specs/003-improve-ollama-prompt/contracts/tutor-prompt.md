# Hợp đồng câu hỏi gia sư trên hệ thống

- `POST /api/tutor/chat` tiếp tục nhận `ChatRequest`. `Accept: application/x-ndjson` nhận các phần `delta`, sau đó là sự kiện hoàn tất chứa `result` hoặc sự kiện lỗi. Yêu cầu JSON thông thường nhận kết quả cuối theo đường hiện hành.
- `result` giữ `reply`, `issues`, `fixed_code` và thông tin nguồn hiện có. Dòng lỗi thuộc bản mã gửi trong yêu cầu. Giá trị `null` vẫn khác với thiếu khóa `fixed_code`.
- Yêu cầu giải thích hoặc không có mã gửi `fixed_code=null`. Rà soát Python sai cú pháp được phép trả `fixed_code=null` nếu đã báo lỗi có căn cứ và cần thêm thông tin. Bản sửa nếu có tiếp tục qua kiểm tra mã gốc, nội dung kết quả và cú pháp Python.
- Khi ô hỏi trống, thao tác lấy mẫu chọn sẵn phần `[Nhập yêu cầu của bạn]`. Gợi ý nhanh và Kiểm tra ngay tiếp tục đặt chế độ và bật Kèm mã. Lúc gửi, giao diện lấy ngôn ngữ và chế độ hiện tại.
- Các đường dẫn giải thích, sửa lỗi, xác thực và gợi ý mã tiếp tục dùng hợp đồng hiện hành.
