# Kế hoạch chỉnh prompt gia sư Ollama

**Ngày** 2026-11-05 · **Tính năng** 003 · **Đặc tả** [Câu lệnh gia sư Ollama](spec.md) · **Trạng thái** Chờ duyệt kế hoạch

## Tóm tắt

Tập trung chỉ dẫn sư phạm trong thông điệp hệ thống của hệ thống. Đặt câu hỏi hiện tại trước phần mã và tài liệu. Dùng một câu mẫu ngắn trên giao diện và lấy mục đích, ngôn ngữ từ lựa chọn tại lúc gửi. Cho phép kết quả tìm lỗi Python báo rõ lỗi cú pháp và hỏi thêm khi chưa thể đưa bản sửa có căn cứ.

## Bối cảnh kỹ thuật

- Windows, Python 3.12 trong môi trường dự án, FastAPI, Pydantic 2 và Ollama cục bộ. Trình duyệt chạy HTML, JavaScript và Monaco.
- Hệ thống dùng thông điệp hệ thống trong `/api/chat`. Trình đọc phản hồi hệ thống nhận NDJSON. Gợi ý khi gõ dùng luồng hoàn thành mã riêng.
- Dùng cùng model và cấu hình sinh nội dung cho hai lượt đo. So sánh chất lượng trên 24 ca và trung vị thời gian trên 20 ca ngắn trong cùng bộ.
- Dùng Python và Node có sẵn để kiểm tra đường đi của dữ liệu. Thử giao diện và xác thực qua ứng dụng, dùng dữ liệu SQLite tạm cho phép thử đăng nhập và đổi mật khẩu.

## Đối chiếu quy tắc dự án

Hiến chương trong `.specify/memory/constitution.md` đang là mẫu. Kế hoạch áp dụng các yêu cầu AGENTS.md do người dùng cung cấp và cổng duyệt trong quy trình Spec Kit của dự án. Người dùng đã duyệt đặc tả 003. Sau khi duyệt kế hoạch, tạo danh sách việc và thực hiện theo thứ tự kiểm tra đường cơ sở, sửa, kiểm tra hồi quy và đối chiếu đặc tả.

Ranh giới triển khai gồm các phần dưới đây. Các kiểm tra cuối sẽ đối chiếu đường dẫn và cấu trúc kết quả của API, đăng nhập, lưu tài khoản, bốn ngôn ngữ, Monaco và giao diện hiện có.

## Thay đổi đề xuất

| Tệp | Thay đổi |
| --- | --- |
| `ai_core.py` | Thay `SYSTEM_ROLE` bằng bản đã thử trong phần nghiên cứu. Giữ chỉ dẫn từng chế độ và gắn ngôn ngữ theo yêu cầu hiện tại. Đưa mục `[QUESTION]` lên trước mã nguồn trong `chat_messages()`. Trong `chat_stream()`, bỏ nhánh bắt buộc `fixed_code` phải là chuỗi khi rà soát Python sai cú pháp. Giữ kiểm tra kết quả và số dòng hiện hành. |
| `static/index.html` | Dùng mẫu `Hãy giúp tôi [Nhập yêu cầu của bạn].`. Ba gợi ý nhanh điền trực tiếp yêu cầu tương ứng. Giữ chọn phần cần điền, chặn gửi mẫu chưa điền, nút Kiểm tra ngay và cách lấy ngôn ngữ, chế độ, mã tại lúc gửi. |
| `README.md` | Cập nhật hai đoạn mô tả nơi đặt chỉ dẫn của hệ thống và cách áp dụng khi chạy lại ứng dụng. |

Giữ `api.py` và `Modelfile` làm nguồn cho hợp đồng API và cấu hình model hiện tại. Chi tiết trường dữ liệu và các trạng thái giao diện nằm trong [mô hình dữ liệu](data-model.md) và [hợp đồng](contracts/tutor-prompt.md).

## Xác minh

1. Cố định đầu vào và đáp án trước khi đo. Lưu bản đọc của `ai_core.py` cũ ngoài cây mã nguồn để đối chiếu trong cùng môi trường.
2. Kiểm tra yêu cầu gửi tới Ollama và sự kiện trả về bằng luồng giả lập. Kiểm tra `fixed_code=null` kèm lỗi cú pháp có căn cứ, các đường từ chối bản sửa không hợp lệ và đường gợi ý mã.
3. Kiểm tra bộ soạn câu hỏi, gợi ý nhanh, đính kèm mã, đổi ngôn ngữ và hiển thị kết quả trong hệ thống. Dùng phiên và dữ liệu thử nghiệm cho các bước xác thực.
4. Chạy cặp cũ/mới theo [hướng dẫn nghiệm thu](quickstart.md). Chấm dựa trên đáp án và vị trí dòng đã định. Ghi kết quả từng tiêu chí SC-001 đến SC-005 trước khi báo hoàn tất.

## Hồ sơ thiết kế

- [Nghiên cứu và bản prompt đã thử](research.md)
- [Mô hình dữ liệu](data-model.md)
- [Hợp đồng hệ thống và Ollama](contracts/tutor-prompt.md)
- [Hướng dẫn nghiệm thu](quickstart.md)
