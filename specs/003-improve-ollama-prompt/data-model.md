# Dữ liệu của câu hỏi và kết quả gia sư

| Dữ liệu | Thành phần | Quy tắc |
| --- | --- | --- |
| `ChatRequest` | `language`, `mode`, `question`, `current_code`, `selected_code`, `history` | Câu hỏi phản ánh mục tiêu người học nhập. Ngôn ngữ và chế độ lấy từ lựa chọn hiện tại. Vùng chọn phải thuộc mã đính kèm. |
| Ngữ cảnh gửi Ollama | Chỉ dẫn hệ thống, lịch sử, câu hỏi, mã đánh số, thông tin kiểm tra cú pháp và bản tóm lược nguồn có nhãn | Ưu tiên câu hỏi hiện tại. Giữ số dòng để đối chiếu mã gốc và nhãn nguồn để kiểm tra lời dẫn. |
| `UnifiedResult` | `reply`, `issues`, `fixed_code` | `fixed_code` là khóa bắt buộc. Dùng `null` khi bản sửa chưa xác định được hoặc không cần thiết. Mỗi mục lỗi mang dòng gốc và mức độ hiện hành. |
| Ca đánh giá | Đầu vào giả lập, câu trả lời mong đợi, dòng lỗi và điều kiện áp dụng bản sửa | Cùng dữ liệu cho hai prompt. Giữ bản ghi đo ngoài dữ liệu tài khoản và tránh đưa lịch sử sinh viên thật vào phép đo. |

Dữ liệu câu hỏi và kết quả tiếp tục đi qua mô hình yêu cầu và phản hồi hiện có. Tài khoản và phiên sử dụng SQLite theo hợp đồng hiện hành.
