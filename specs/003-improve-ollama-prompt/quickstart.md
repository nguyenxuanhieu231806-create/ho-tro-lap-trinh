# Nghiệm thu prompt gia sư Ollama

## Kiểm tra đường đi trong hệ thống

1. Ở thư mục dự án, chạy `.\run.ps1 -CheckOnly` để kiểm tra model. Khởi động hệ thống bằng `.\run.ps1`, rồi mở [giao diện cục bộ](http://127.0.0.1:8000/).
2. Đăng nhập bằng tài khoản thử đã cấp. Bấm ô hỏi trống hoặc nút Câu lệnh mẫu. Kiểm tra ô có câu ngắn và con trỏ chọn đúng phần cần nhập. Thử gửi khi phần đó còn nguyên, rồi thay bằng câu hỏi thật. Kiểm tra gợi ý nhanh, nút Kiểm tra ngay, đổi ngôn ngữ và Kèm mã.
3. Quan sát câu trả lời xuất hiện dần. Với mã Python đúng, chờ kết quả rỗng về lỗi. Với `double(x)` trả `x+1` khi đề bài cần `2*x`, kiểm tra dòng lỗi và bản mã đầy đủ. Với yêu cầu thiếu dữ kiện và mã sai cú pháp, kiểm tra câu hỏi làm rõ và trường sửa có thể rỗng. Thử gợi ý khi gõ và áp dụng bản sửa vào đúng phiên bản mã.
4. Kiểm tra đăng nhập và đổi mật khẩu trên cơ sở dữ liệu tạm. Đối chiếu tải giao diện và logo, soạn thảo, hợp đồng chat JSON/NDJSON và cơ chế gợi ý.

## Phép so sánh trên Ollama

Cố định 24 đầu vào và đáp án theo ma trận dưới đây. Mỗi ô là một ca. Gắn mã đầu vào, dòng có lỗi và điều kiện mong đợi trước lúc chạy. Dùng đầu vào ngắn và giả lập. Năm hàng đầu dùng chung cho phép đo trung vị độ trễ. Hàng tối ưu chỉ tính vào phép đo chất lượng.

| Nhóm | C | C++ | Java | Python |
| --- | --- | --- | --- | --- |
| Hỏi lý thuyết có nhiễu | Kết thúc `main` và hàm thường kiểu `int` trong chương trình hosted | `vector::at` và `operator[]` khi chỉ số bằng kích thước | Hai `int` có cùng giá trị trong lịch sử từng hỏi về `String` | `b = a` và thay đổi list từ `b` |
| Giải thích đoạn được chọn | `-7 / 2` cho `-3` trong C11 | Vòng lặp theo tham chiếu thay đổi phần tử | `a.length` với mảng `int[]` | `range(3)` tạo các giá trị 0 đến 2 |
| Rà soát mã đúng | Nhân đôi số nguyên trong miền đầu vào đã chặn tràn | `v.at(1)` với vector có hai phần tử | Vòng lặp `i < a.length` | `double(x)` trả `2*x` |
| Sửa lỗi rõ ràng | `scanf("%d", x)` khi `x` là `int` | Comparator `<=` của `std::sort` | Vòng lặp `i <= a.length` có truy cập `a[i]` | `double(x)` trả `x+1` thay vì `2*x` |
| Thiếu dữ kiện sửa | Nhánh xử lý đầu vào âm thiếu biểu thức, đề bài chưa quy định kết quả | Nhánh xử lý vector rỗng chưa có giá trị trả | Nhánh xử lý `null` thiếu giá trị trả | Hàm có `return x +` với toán hạng và kết quả mong đợi chưa xác định |
| Tối ưu giữ hành vi | Duyệt chuỗi bất biến và gọi lại `strlen` | Duyệt chỉ đọc `vector<string>` bằng bản sao phần tử | Ghép chuỗi trong vòng lặp có số lượt lớn | Kiểm tra nhiều giá trị trong danh sách số nguyên bất biến |

Chạy các cặp tuần tự, cùng máy, cùng model đã nạp, cùng thông số và cùng dữ liệu. Đổi thứ tự cũ/mới xen kẽ theo ca. Tính thời gian từ khi bắt đầu yêu cầu tới khi nhận kết quả cuối qua kiểm tra. Ghi lại timeout và lỗi định dạng. Khi phép đo bị gián đoạn, tiếp tục từ cặp chưa hoàn tất và nạp model trước khi đo tiếp.

Chấm lời giải theo đáp án đã định, kiểm tra số dòng, loại lỗi, độ đầy đủ của bản sửa và lời nói về bằng chứng. Một phản hồi sai chuyên môn, trái cấu trúc hoặc thiếu kết quả được tính là ca không đạt. Ghi riêng số ca bịa lỗi và bỏ sót. Kiểm tra bản sửa bằng đối chiếu mã và kiểm tra cú pháp phù hợp. Mọi phép chạy mã thử cần dùng dữ liệu giả lập và môi trường thử.

| Tiêu chí | Cách kết luận |
| --- | --- |
| SC-001 | Số ca sai mới nhỏ hơn hoặc bằng 80% số ca sai cũ và số ca bịa lỗi không tăng. Nếu đường cơ sở có 0 ca sai, ghi nhận bộ ca chưa đo được cải thiện. |
| SC-002 | Mỗi ca thiếu bằng chứng chạy thử được kiểm tra phát biểu về việc chạy, biên dịch hoặc đúng với mọi đầu vào. |
| SC-003 | Bản sửa phải đầy đủ khi có căn cứ. Nếu cần thêm dữ kiện, kết quả nêu cụ thể lý do và câu hỏi làm rõ. |
| SC-004 | Trung vị thời gian trên cùng 20 ca đã định không vượt 110% đường cơ sở. Ghi rõ nếu timeout làm tiêu chí chưa thể kết luận. |
| SC-005 | Đăng nhập, đổi mật khẩu, soạn thảo, gợi ý mã và hiển thị chat đạt các bước kiểm tra hồi quy. |
