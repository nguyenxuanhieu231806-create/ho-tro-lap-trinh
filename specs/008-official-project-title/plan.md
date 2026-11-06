# Kế hoạch kỹ thuật 008 — Đã duyệt

## Nguyên tắc thực hiện

Thay chuỗi theo từng vị trí đã khảo sát; giữ toàn bộ logic, định danh và hợp đồng.
Không cài thư viện, không đổi DB/API, không tạo lại model hoặc khởi động lại tiến
trình của người dùng ngoài phạm vi yêu cầu. Giữ bốn tệp 007 đang có thay đổi từ
lượt đổi tên GitHub; không khôi phục hoặc ghi đè các thay đổi đó.

## Tệp và lý do dự kiến

| Tệp/nhóm | Thay đổi |
| --- | --- |
| static/index.html | Title, heading đăng nhập, lời chào tĩnh/động, Header/tooltip |
| static/admin.html, static/admin.js | Liên kết trở về và hướng dẫn đăng nhập |
| ai_core.py | SYSTEM_NAME đầy đủ; hai cách gọi giao diện trong SYSTEM_ROLE |
| Modelfile | Cùng hai thay đổi câu chữ trong chỉ dẫn, không đổi model/tham số |
| manage_accounts.py | Mô tả CLI không mang tên đề tài cũ |
| run.ps1 | Thông báo dừng hệ thống, giữ nguyên kiểm tra health/service |
| README.md | Tên đề tài và các câu hướng dẫn, giữ thuật ngữ Web Worker/lệnh nguyên dạng |
| .github/workflows/verify-web-ide.yml | Tên hiển thị và nhãn/log; giữ đường dẫn và các lệnh |
| Mô tả/chú thích do dự án viết | Bỏ cách gọi cũ nếu có, không sửa thư viện bên thứ ba |
| specs/001–007 | Chỉ lời văn hướng dẫn/tên gọi; giữ URL, đường dẫn, số liệu, kết quả lịch sử |
| specs/008-official-project-title | Ghi đặc tả, tiến độ và bằng chứng đối chiếu |

## Trình tự sau phê duyệt

1. Ghi nhận phê duyệt; thực hiện từng thay thế có kiểm soát, xem diff để bảo đảm
   không đụng thông tin tài khoản/dữ liệu riêng hay các định danh kỹ thuật.
2. Rà lại từ web/website không phân biệt hoa thường; phân loại từng chỗ còn lại.
3. Kiểm tra cú pháp Python/JavaScript và YAML; đối chiếu các mã service, endpoint,
   schema và lệnh Docker không thay đổi. Không viết thêm bài test chỉ so chuỗi.
4. Chạy các kiểm thử giao diện sẵn có bằng dữ liệu tạm và kiểm tra thủ công qua
   Playwright cho tên mới, các viewport và nhãn trang quản trị. Không chạy AI thật
   hoặc nạp tài liệu/tài khoản thật cho một thay đổi tên hiển thị.
5. Lưu bằng chứng mới ở thư mục kiểm chứng 008 hoặc vùng kết quả tạm; giữ nguyên
   ảnh/báo cáo lịch sử. Chỉ chạy thêm kiểm thử nếu có lỗi hoặc thay đổi mới.
6. Đối chiếu tiêu chí, báo từng tệp đã sửa và phần chưa kiểm chứng. Nếu đồng bộ
   GitHub, chỉ gửi thay đổi liên quan, không gửi .env/SQLite hay môi trường ảo.

## Rủi ro cụ thể

Tên đầy đủ dài hơn ở lời chào. Kiểm tra lại bố cục; ưu tiên dùng CSS co giãn hiện
có và tên rút gọn tại Header, không thay thiết kế đại dương. Modelfile chỉ là cấu
hình nguồn; không tuyên bố trọng số mô hình được huấn luyện hay đã tạo lại model.
