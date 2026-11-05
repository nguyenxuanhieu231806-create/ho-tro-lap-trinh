# Quyết định triển khai giao diện 004

Bố cục cuối của trang hiện có đặt 55/45 nhưng các media query cũ gây chồng quy tắc. Gom lại CSS có cấu trúc và giữ các ID đang được JavaScript sử dụng. Logo nguồn tại static/LogoFITHPUni.png.

syncMotion() hiện dừng chuyển động ngoài intro. Bộ điều phối mới kết hợp màn hình, tùy chọn tập trung, yêu cầu giảm chuyển động, trang ẩn và thời gian tương tác. Giảm cảnh khi nhập liệu hoặc AI xử lý để ưu tiên việc học.

Dấu lỗi đã có hoverMessage. Nút dòng lỗi đã dùng matches(saved) trước khi cuộn. Mở rộng cách hiển thị và highlight trên các điểm này. Diff dùng createDiffEditor có renderSideBySide=false, chỉ tạo khi mở và hủy cùng hội thoại.

Bốn điểm sáng giới thiệu ngôn ngữ đồng bộ lựa chọn #language. Editor đọc lựa chọn hiện tại khi khởi tạo để xử lý việc sinh viên chọn trước lúc Monaco tải.

Ảnh mô phỏng tạo bằng ImageGen chỉ dẫn bố cục và ánh sáng. Cảnh nền triển khai là tài nguyên riêng, còn văn bản, logo, biểu mẫu, mã và các nút được dựng bằng HTML/Monaco.
