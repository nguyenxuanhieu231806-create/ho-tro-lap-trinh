# Dữ liệu chạy mã

RunRequest gồm language thuộc c/cpp/java/python, current_code dài 1 tới 60.000 ký tự và stdin tối đa 16.384 ký tự. Mã trắng không được chạy.

RunResult gồm language, status, stdout, stderr, exit_code tùy chọn, duration_ms và message. Trạng thái completed chỉ thể hiện lần chạy kết thúc mã 0 với dữ liệu đã nhập. Chuỗi đầu ra được giới hạn theo byte và hiển thị textContent trên Web.

Bản chụp client gồm model, version, code và language để nhận diện kết quả của lần chạy trước khi nguồn đổi.
