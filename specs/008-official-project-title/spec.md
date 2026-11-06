# 008 — Chuẩn hóa tên đề tài chính thức

Ngày: 06/11/2026. Trạng thái: đã triển khai và kiểm chứng tại máy.

## Yêu cầu và thông tin đã kiểm chứng

Người dùng yêu cầu bỏ chữ “web” trong dự án vì tên đề tài là:

**Hệ thống hỗ trợ lập trình cho sinh viên Khoa Công nghệ Thông tin – Trường Đại học Hải Phòng**.

Đã kiểm tra `.specify` tồn tại và khảo sát mã hiện hành. Tên có “Web” đang xuất
hiện trong title trình duyệt, form đăng nhập, lời chào tĩnh/cá nhân hóa, tiêu đề
và tooltip Header, liên kết/thông báo trang quản trị, mô tả công cụ tài khoản,
chỉ dẫn AI, README, nhãn Actions và một số lời hướng dẫn/đặc tả cũ.
`SYSTEM_NAME` trong ai_core.py được FastAPI dùng làm tên ứng dụng; hiện còn thiếu
tên trường. Không có kiểm thử hiện hành phụ thuộc vào chuỗi tiêu đề cũ.

## Phạm vi

- Chuẩn hóa tên đầy đủ ở vị trí giới thiệu/tên ứng dụng. Lời chào giữ tên sinh viên,
  lớp và bổ sung đúng tên trường. Header có thể hiển thị rút gọn “Hệ thống hỗ trợ
  lập trình · Khoa CNTT” để vừa màn hình, tooltip mang đầy đủ tên chính thức.
- Bỏ “Web/Web IDE/website” trong các câu giới thiệu, nhãn, thông báo, mô tả và lời
  hướng dẫn do dự án quản lý; dùng “hệ thống”, “ứng dụng”, “giao diện” hoặc “không
  gian lập trình” tùy nghĩa. Không thay thế mù toàn bộ chuỗi ký tự.
- Đồng bộ hai câu nhắc tới giao diện trong SYSTEM_ROLE và Modelfile; chỉ đổi cách
  gọi, không thay quy tắc sư phạm, schema, model hoặc tham số suy luận.
- Đồng bộ README, tên hiển thị Actions và lời văn trong tài liệu đặc tả 001–007
  có thể chỉnh sửa. Giữ nguyên số liệu, kết quả và đường dẫn bằng chứng lịch sử.
- Chỉ thay tên/mô tả hiển thị; không thay đổi cấu trúc API hoặc dữ liệu.

## Ranh giới kỹ thuật cần giữ để bảo toàn chức năng

Không đổi: service health `fit-hpuni-programming-web`, tên dịch vụ Docker `web`,
image `fit-tutor-web:ci`, tên tệp workflow/nhóm concurrency, thuật ngữ chuẩn
`Web Worker`, `websocket`, URL/đường dẫn cũ có vai trò dẫn chứng, thư mục
`007-public-web`, thư viện/binary do bên thứ ba, ví dụ hạ tầng Spec Kit, .git,
.venv, .env, SQLite, tài liệu người dùng đã nạp và ảnh kiểm thử lịch sử.
Không đổi thư mục local hoặc tên kho GitHub `ho-tro-lap-trinh` vừa được duyệt.

## Tiêu chí nghiệm thu

1. Title, đăng nhập, lời chào và Header dùng tên mới phù hợp vị trí; tên trường
   đầy đủ đúng “Trường Đại học Hải Phòng”.
2. Người dùng không thấy “Web/Web IDE” trong các nhãn/thông báo của giao diện chính
   và quản trị. Thông tin cá nhân hóa và các nút hiện có vẫn hoạt động.
3. Các chỗ còn từ web được phân loại là định danh/thuật ngữ/đường dẫn kỹ thuật hoặc
   tài nguyên ngoài phạm vi, không phải tên đề tài hay lời giới thiệu còn sót.
4. README, mô tả CLI, chỉ dẫn AI và nhãn Actions thống nhất cách gọi mới.
5. Đăng nhập → chào mừng → IDE trên 1366×768, 1920×1080 và 390×844 không tràn khung;
   logo, chuyển cảnh, hai khung code/chat và các thao tác hiện hành giữ nguyên.
6. Xác thực, API, service health, JSON, lưu trữ và lệnh Docker giữ hợp đồng hiện hành.

## Phê duyệt

Người dùng xác nhận “Duyệt toàn bộ phạm vi đổi tên” qua câu hỏi duyệt ngày
06/11/2026, bao gồm đặc tả, kế hoạch và danh sách việc. Cơ sở: mục 7 trong AGENTS.md
người dùng cung cấp: “Require explicit user approval before implementing changes.”
