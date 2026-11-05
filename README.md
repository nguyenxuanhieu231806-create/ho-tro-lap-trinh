# Web hỗ trợ lập trình cho sinh viên Khoa Công nghệ Thông tin

Python/FastAPI + Ollama cục bộ, hỗ trợ C, C++, Java và Python.

## Ba file mã nguồn chính

- `ai_core.py`: urllib, Ollama, FIM và kiểm tra nội dung AI.
- `api.py`: FastAPI, xác thực Gmail, SQLite, hợp đồng dữ liệu và phục vụ giao diện.
- `static/index.html`: toàn bộ HTML/CSS/JavaScript, Monaco và ba màn hình.

Giữ `static/LogoFITHPUni.png`, `.env`, `requirements.txt`, `run.ps1`, cấu hình PyCharm,
`.venv` và `data/accounts.sqlite3`. Không xóa data nếu cần giữ tài khoản.

## Chạy trong PyCharm

Chọn interpreter `.venv/Scripts/python.exe`, mở Terminal tại thư mục dự án:

```powershell
.\run.ps1
```

Mở http://127.0.0.1:8000. Dừng bằng Ctrl+C trước khi chạy lại. Đổi cổng:
`.\run.ps1 -Port 8001`. Nếu cổng đang bận, dừng phiên cũ hoặc chọn cổng khác.

Cài mới:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu môi trường hiện có không có pip, dùng `uv pip install --python .venv/Scripts/python.exe -r requirements.txt`.
Bốn phụ thuộc trực tiếp: fastapi, uvicorn, pydantic, python-dotenv.
Các phụ thuộc bắc cầu như Starlette, AnyIO, pydantic-core vẫn cần thiết.

## Ollama

`.env` cạnh ai_core.py:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=cntt-coder
```

Model chuyên dụng được tạo từ `qwen2.5-coder:7b` đã có trên máy:

```powershell
ollama create cntt-coder -f .\Modelfile
ollama show cntt-coder
ollama run cntt-coder
```

`Modelfile` và `SYSTEM_ROLE` trong `ai_core.py` dùng cùng bộ chỉ thị cho C99/C11,
C++17/20, Java 17+ và Python 3.10+. Đây là đóng gói chỉ thị và tham số suy luận,
không cập nhật trọng số. Web chọn tối đa hai bản tóm lược phù hợp từ `data/language_reference.json`;
không chèn ví dụ có bug vào mọi câu hỏi. Kho hiện có 41 bản tóm lược có nguồn:
11 mục Python, 10 Java, 10 C và 10 C++; đây không phải toàn văn giáo trình/tiêu chuẩn.
Tài liệu được chọn theo ngôn ngữ và câu hỏi trước, rồi mới dùng mã đính kèm khi câu hỏi
không khớp chủ đề nào. Mỗi lần chỉ gửi tối đa hai đoạn để giữ ngữ cảnh gọn.
Phạm vi phiên bản và loại nguồn được gửi cùng nội dung, giúp phân biệt quy tắc ngôn ngữ
với khuyến nghị phong cách hoặc chi tiết riêng của nhà cung cấp.

Nguồn nền tảng (đã đối chiếu ngày 02/11/2026):

| Ngôn ngữ | Nguồn | Phạm vi |
| --- | --- | --- |
| Python | [Tài liệu Python 3.14](https://docs.python.org/3.14/), [PEP 8](https://peps.python.org/pep-0008/) | Hàm, phạm vi, kiểu dựng sẵn, ngoại lệ, phong cách |
| Java | [JLS Java 17](https://docs.oracle.com/javase/specs/jls/se17/html/index.html), [API Java 17](https://docs.oracle.com/en/java/javase/17/docs/api/index.html) | Kiểu, return, khởi tạo biến, Scanner, Collections |
| C | [WG14 N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf), [Microsoft CRT](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/crt-alphabetical-function-reference?view=msvc-170) | Bản thảo C11, I/O, chuỗi, cấp phát và vòng đời |
| C++ | [WG21 N4659](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/n4659.pdf), [Microsoft STL](https://learn.microsoft.com/en-us/cpp/standard-library/cpp-standard-library-reference?view=msvc-170), [Core Guidelines](https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines) | Bản thảo C++17, STL, con trỏ sở hữu và RAII |

N1570/N4659 là bản thảo, không phải bản ISO thương mại đã xuất bản. Core Guidelines/PEP 8
là hướng dẫn; vi phạm phong cách không tự chứng minh chương trình sai. Chi tiết Microsoft
được giới hạn rõ trong từng mục. Chỉ các quy tắc đã tóm lược mới được đưa vào câu hỏi;
Web không tự đọc toàn bộ URL và không tìm Internet trong lúc sinh câu trả lời.
Thay đổi này bổ sung tài liệu truy xuất, không huấn luyện trọng số mô hình. Mô hình vẫn có thể
diễn giải sai; cần đối chiếu đề bài, chạy/biên dịch và kiểm thử khi đánh giá bản sửa.
Khi sửa bộ chỉ thị, cần đồng bộ cả hai rồi tạo lại model.
Khởi động lại Web sau khi đổi `.env`; biến OLLAMA_MODEL của tiến trình nếu có sẽ ưu tiên hơn file.
Chat/phân tích và completion dùng temperature 0.1; num_ctx 8192 và repeat_penalty 1.1.
Tham số không bảo đảm mọi câu trả lời đúng, và ngữ cảnh lớn có thể tăng độ trễ trên CPU.
Không cần API key, không tự tải model hoặc chọn model cloud.
Nếu model cấu hình chưa được tải, ưu tiên model lập trình cục bộ có sẵn.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -c "import asyncio; from ai_core import OllamaTutor; print(asyncio.run(OllamaTutor().health()))"
```

## Đăng nhập và giao diện

Tự nhập Gmail đã được cấp và mật khẩu vào form đăng nhập. Hồ sơ xuất hiện sau khi xác thực.
Đây là danh sách giả định phục vụ demo, không phải xác nhận tài khoản do trường thực tế cấp.

| Sinh viên | MSSV | Gmail đăng nhập |
| --- | --- | --- |
| Lê Văn Đức | 243148201121 | levanduc12@gmail.com |
| Nguyễn Xuân Hiếu | 243148201146 | nguyenxuanhieu13@gmail.com |
| Bùi Quang Vinh | 243148201101 | buiquangvinh14@gmail.com |
| Nguyễn Tiến Duy | 243148201135 | nguyentienduy15@gmail.com |

Cả bốn thuộc lớp CNTT3.K25, năm 3. Mật khẩu khởi tạo: `cntt3k25@hpuni`.
Lần nâng cấp này đổi mật khẩu khởi tạo cũ `1234` sang mật khẩu mới; giữ mật khẩu cá nhân đã đổi.
Không tự điền mật khẩu lên giao diện và không trả mật khẩu/giá trị băm qua danh sách tài khoản.
Không mở đăng ký tự do. Có thể đổi mật khẩu sau khi xác thực mật khẩu hiện tại.
Mật khẩu đã đổi không bị đặt lại khi khởi động Web. Gmail là định danh nội bộ, chưa xác minh bằng Google OAuth.
Mật khẩu được băm PBKDF2; cookie phiên HttpOnly/SameSite Strict.

Giữ màn hình đăng nhập trắng tối đa 440px, giới thiệu đáy đại dương và Web IDE nền trắng.
Hoạt ảnh dùng transform/opacity; tạm dừng khi rời màn hình giới thiệu hoặc ẩn tab.
Chế độ giảm chuyển động của hệ điều hành được tôn trọng.
Monaco, Markdown và highlight vẫn dùng CDN: trình duyệt cần Internet khi chưa có cache.

## Cảnh báo lỗi khi gõ

Bộ phân tích Tree-sitter chạy trong Web Worker riêng, sau 550 ms ngừng gõ, hỗ trợ
C, C++, Java và Python. Dấu cảnh báo đỏ nằm cuối dòng; rê chuột để xem mô tả.
Kết quả cũ bị bỏ nếu sửa mã hoặc đổi ngôn ngữ. Không gọi Ollama, không chạy mã người dùng.
Các lỗi AI xác định trong Chat cũng dùng dấu cảnh báo này và được xóa khi mã thay đổi.
Đây là kiểm tra cú pháp, không xác minh tên biến, kiểu dữ liệu, thiếu thư viện hay tính đúng thuật toán.
Không thấy dấu đỏ không đồng nghĩa chương trình chắc chắn đúng.

Tài nguyên phân tích được lưu cục bộ trong `static/syntax/` (khoảng 7,3 MB),
tải ngữ pháp theo ngôn ngữ đang chọn; không thêm thư viện Python. Phiên bản, nguồn,
mã kiểm tra và giấy phép nằm trong `static/syntax/NOTICE.json` và các tệp `LICENSE-*.txt`.

## Hiệu năng và giới hạn

- Completion debounce 450ms, hủy fetch cũ ngay khi gõ tiếp; tối đa 40 dòng và 12.000 ký tự quanh con trỏ.
- Backend giới hạn lại ngữ cảnh; temperature 0.1, num_predict 128, dừng ở cuối dòng; Tab nhận, Esc bỏ.
- urllib chạy trong luồng nền, không chặn event loop. Chỉ một lời gọi sinh nội dung mỗi lúc.
- Hủy trình duyệt không thể ngắt ngay socket urllib đang chờ. Luồng cũ giữ khóa đến khi trả về/hết timeout,
  nên yêu cầu tiếp theo có thể nhận 503; không xếp hàng vô hạn các lượt sinh code.
- Timeout mạng completion 10 giây, tổng completion 12 giây; chat 165 giây/lần gọi, tổng 180 giây.
- Giới hạn phản hồi HTTP 2 MB; JSON phải qua kiểm tra Pydantic, không sửa đoán dữ liệu sai cấu trúc.
- Chat hợp nhất trả JSON gồm reply, issues và fixed_code trong một lần gọi Ollama. Phân tích là tĩnh, chưa chạy mã.
- Tốc độ model phụ thuộc RAM/CPU/GPU và trạng thái nạp; không bảo đảm dưới 1 giây, 60 FPS hoặc CPU 0%.

API hỗ trợ `/api/tutor/chat`, `/api/tutor/complete`, `/api/tutor/explain`, `/api/tutor/fix` và `/api/health`.
Trường language nhận `c`, `cpp`, `java`, `python`. C dùng trình tô màu C của Monaco.

## Chạy thử mã trong Editor

Chọn **C / C++ / Java / Python**, mở **Đầu vào & Kết quả chạy**, điền dữ liệu chương trình
cần đọc vào ô **Dữ liệu đầu vào (stdin)**, rồi bấm **Chạy thử** trên thanh công cụ Editor.
Ví dụ chương trình đọc hai số thì nhập `3 5`. Đây là chương trình console với dữ liệu nhập trước,
không phải terminal tương tác từng phím hay môi trường chạy ứng dụng đồ họa.

Kết quả gồm đầu ra chuẩn, thông báo lỗi/cảnh báo, mã thoát và thời gian cả lượt xử lý.
Nút **Dừng** hủy yêu cầu; máy chủ dọn tác vụ trước khi nhận lượt mới. Sau khi áp dụng bản sửa AI,
bấm **Chạy thử** để kiểm tra bản mã mới. Nếu sửa mã, đổi ngôn ngữ hoặc dữ liệu đầu vào,
kết quả trước đó được đánh dấu đã cũ. Chạy thành công chỉ xác nhận lần chạy với đầu vào đã cung cấp;
cần thử thêm dữ liệu để đánh giá yêu cầu bài toán.

Bộ chạy độc lập với Ollama và dùng image compiler Docker riêng. Không cần thêm thư viện Python.
Trên Windows cần Docker Desktop chạy Linux containers với WSL 2. Nếu chưa có WSL, mở PowerShell
**Run as administrator**, chạy `wsl --install --no-distribution`, và khởi động lại khi Windows yêu cầu.
Xem [hướng dẫn Microsoft WSL](https://learn.microsoft.com/en-us/windows/wsl/install).
Sau khi Docker Desktop báo engine đang chạy, mở Terminal tại thư mục dự án:

```powershell
docker build -f Dockerfile.grader -t fit-tutor-grader:1 .
.\run.ps1
```

Nếu `docker` chưa có trong PATH, dùng đường dẫn CLI mà Docker Desktop cài đặt:

```powershell
& "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe" build -f Dockerfile.grader -t fit-tutor-grader:1 .
```

Dựng lại image khi cập nhật `code_verifier.py` hoặc `Dockerfile.grader`; image cũ thiếu nhãn giao thức
sẽ được báo rõ trên giao diện. `TUTOR_GRADER_IMAGE` cho phép đổi tên image. Mặc định dùng Python 3.11,
Java 17, C11 và C++17, không cài thêm thư viện vào mỗi lượt chạy.

Các giới hạn: biên dịch 15 giây, thực thi 3 giây, 1 CPU, RAM 512 MiB, 96 PID,
mã nguồn 60.000 ký tự, stdin 16.384 ký tự và stdout/stderr tối đa 64 KiB mỗi luồng.
Chỉ một tác vụ chạy mã mỗi lúc; suất xử lý này tách riêng với Chat/Gợi ý AI.
Mỗi tác vụ dùng container không mạng, hệ thống tệp gốc chỉ đọc và các vùng tạm có giới hạn;
không gắn thư mục dự án hoặc cơ sở dữ liệu tài khoản vào container.

Hai API yêu cầu đăng nhập: `GET /api/tutor/runner` kiểm tra môi trường và `POST /api/tutor/run`
nhận `language`, `current_code`, `stdin`. Khi Docker chưa chạy hoặc chưa có image, API trả thông báo
tiếng Việt; hệ thống không chuyển sang chạy mã sinh viên trực tiếp trên Windows.
Phương án này dành cho Web chạy bằng `.\run.ps1` trên máy có Docker CLI. Image Web trong Docker Compose
vẫn phục vụ Chat/Editor; chưa được cấu hình kết nối bộ chạy Docker và không gắn Docker socket tự động.

Kiểm tra thật sau khi dựng image:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 specs\005-run-four-languages\validation\verify-live.py
```


## Triển khai Windows / LAN / public / Docker

### Windows một lần bấm

Bấm đúp `deploy.bat`. File này chạy PowerShell với ExecutionPolicy Bypass chỉ trong tiến trình đó,
không đổi chính sách hệ thống. Nếu chính sách do tổ chức quản lý vẫn chặn script, cần quản trị viên hỗ trợ.
Yêu cầu máy có Python 3.11+ và Ollama; script tạo .venv/cài 4 thư viện nếu thiếu,
khởi động Ollama nền nếu cần, kiểm tra và nạp model đã tải, rồi chạy web một worker trên 0.0.0.0:8000.
Không tự tải model nhiều GB. Lần đầu chạy `ollama pull qwen2.5-coder:7b` nếu chưa có model.

```powershell
.\deploy.bat
.\deploy.bat -Port 8001
.\deploy.bat -CheckOnly -NoBrowser
```

Giữ cửa sổ chạy web mở; Ctrl+C dừng web. Ollama vẫn hoạt động để ứng dụng khác sử dụng.
Chỉ mở trình duyệt sau khi `/api/health` báo ready. Cổng bận được báo rõ, không tự tắt chương trình khác.
Script in localhost và các IP LAN; chọn IP Wi-Fi/Ethernet trong `ipconfig`, tránh IP adapter ảo Docker/VPN.
Các thiết bị phải cùng mạng, không bật client isolation. Nếu Windows Firewall hỏi, cho phép Python trên
mạng Private phù hợp; không tắt firewall. Không cần mở cổng 11434 cho phương án chạy Windows.

### Health và đường dẫn

`GET /api/health`: HTTP 200 khi có index/logo, kết nối Ollama được và model đã nằm trong bộ nhớ;
HTTP 503 kèm message tiếng Việt khi chưa sẵn sàng. Không sinh token trong mỗi health probe.
Model tự nạp một lần lúc khởi động; sau 10 phút nhàn rỗi Ollama có thể giải phóng nó,
health chuyển 503 cho đến khi một yêu cầu AI nạp lại hoặc chạy preflight lần nữa.
Đây là readiness, không phải bằng chứng mọi bài toán AI sẽ trả lời đúng hoặc luôn nhanh.

Static lấy từ Path(__file__).resolve(), không phụ thuộc thư mục Terminal.
Logo .png/.jpg (kể cả đuôi viết hoa) được phục vụ qua cả hai URL.
Chế độ debug tắt, lỗi API không trả stack trace cho người dùng.
Biến môi trường của hệ điều hành/container được ưu tiên hơn .env.

### Link public bằng Cloudflare Tunnel

Cài cloudflared theo https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/.
Sau khi web chạy và health ready, mở Terminal thứ hai:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Chia sẻ URL HTTPS trycloudflare.com in trong Terminal. Link demo thay đổi khi chạy lại,
hết hiệu lực khi dừng tunnel. Khách vẫn đăng ký/đăng nhập Gmail của hệ thống.
Không tunnel cổng Ollama 11434. Quick Tunnel dành cho demo, không phải hosting lâu dài.
Có thể dùng chức năng tạo mã QR cho trang trong trình duyệt để chia sẻ URL vừa nhận.

Phương án ngrok: cài từ https://ngrok.com/download, lấy token trong tài khoản ngrok:

```powershell
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN
ngrok http http://127.0.0.1:8000
```

Thay placeholder bằng token của bạn tại Terminal, không đưa vào repository hay gửi qua chat.
Với web chạy trực tiếp bằng run.ps1, proxy localhost được tin cậy để nhận đúng HTTPS
và cookie Secure. Không dùng --forwarded-allow-ips '*' trên cổng LAN công khai.

### Docker Desktop

Bật Docker Desktop Linux containers. Ollama vẫn chạy trên máy chủ, model không được đóng gói vào image.
Docker Desktop dùng host.docker.internal để gọi máy chủ. Nếu Ollama chỉ nghe loopback và container không
kết nối được, thoát Ollama ở system tray rồi chạy trong Terminal riêng:

```powershell
$env:OLLAMA_HOST = '0.0.0.0:11434'
ollama serve
```

Chỉ cho phép mạng nội bộ Docker truy cập 11434 bằng firewall phù hợp; không mở Ollama ra Internet
hay chuyển tiếp cổng router. Biến trên chỉ áp dụng cho Terminal hiện tại; cách Windows trực tiếp
không cần đổi OLLAMA_HOST. Khi hết thử Docker, dừng lệnh serve đó và mở lại Ollama bình thường.

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose logs --tail 50 web
docker compose down
```

Không chạy đồng thời run.ps1 và container cùng cổng 8000. Docker chạy user không phải root,
không copy .env/.venv/data/.git vào image. Named volume tutor_data giữ tài khoản qua các lần thay container;
`docker compose down -v` xóa dữ liệu này. Volume Docker bắt đầu rỗng, không tự nhập tài khoản Windows.

Với tunnel từ host vào Docker, đặt PUBLIC_ORIGIN bằng URL HTTPS chính xác được tunnel in ra
(trong .env hoặc môi trường Terminal), rồi tạo lại container:

```powershell
$env:PUBLIC_ORIGIN = 'https://YOUR-DEMO-HOST.trycloudflare.com'
docker compose up -d
```

Cấu hình này giữ kiểm tra Origin và cookie HTTPS, không tin tất cả proxy. Không sửa Host header
trong tunnel. Nếu thay link public, cập nhật PUBLIC_ORIGIN tương ứng.
Khi PUBLIC_ORIGIN là HTTPS, đăng nhập qua URL HTTPS đó; bỏ cấu hình này và khởi động lại
nếu quay về demo chỉ qua localhost/LAN HTTP (cookie Secure không gửi qua LAN HTTP).

Mọi người dùng chung model trên laptop: web phục vụ nhiều phiên, nhưng chỉ một lượt sinh AI đồng thời;
lượt khác nhận thông báo bận. Không tăng worker để nhân bản tải model. Demo cần laptop bật,
Ollama chạy và mạng ổn định; 60 FPS là thuộc tính render của trình duyệt, không được bảo đảm bởi uvicorn.


## Nguồn kiến thức và kiểm tra độ tin cậy

Kho `data/language_reference.json` lưu bản tóm lược tiếng Việt, đường dẫn gốc,
phạm vi phiên bản và từ khóa. Nguồn gồm Python 3.14 Language Reference/Tutorial,
Oracle Java 17 API và JLS, bản thảo C11 WG14 N1570, Microsoft C Runtime/STL,
và bản thảo C++17 WG21 N4659. Các tóm lược bao phủ
41 chủ đề; không khẳng định mô hình đã học toàn bộ bốn ngôn ngữ.

- Python: https://docs.python.org/3.14/reference/expressions.html
- Java: https://docs.oracle.com/en/java/javase/17/docs/api/index.html
- C11: https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf
- C++ STL: https://learn.microsoft.com/en-us/cpp/standard-library/cpp-standard-library-reference?view=msvc-170

Khi chat, hệ thống tra theo ngôn ngữ và chủ đề, đưa tối đa hai đoạn vào ngữ cảnh.
Không tải Internet trong mỗi câu hỏi. Khung chat hiển thị tài liệu đã cung cấp cho AI;
điều đó không đồng nghĩa mọi câu trả lời đã được chứng minh đúng bằng tài liệu.
Để cập nhật kho, cần kiểm tra nguồn gốc, phiên bản, điều kiện áp dụng của từng bản ghi
rồi khởi động lại Web. Đây là truy xuất tài liệu, không phải fine-tuning trọng số.

Chế độ Hỏi đáp mặc định không đính kèm code; bật Kèm mã khi cần.
Các nút Giải thích/Tìm lỗi/Tối ưu chọn đúng mục đích, dùng chung một khung chat.
Ô nhập trống tự điền một câu lệnh ngắn theo ngôn ngữ và mục đích đang chọn.
Phần [Nhập yêu cầu của bạn] được bôi chọn để gõ thay; cần điền yêu cầu cụ thể trước khi gửi.
Nút Câu lệnh mẫu giữ nguyên yêu cầu đang viết. Người học có thể nhập câu hỏi tự do.
Mã/câu hỏi quá ngân sách ngữ cảnh sẽ bị từ chối rõ ràng; lịch sử cũ được bỏ trước,
không tự cắt file rồi đưa ra một bản sửa được coi là toàn bộ file.

Bản sửa Python được kiểm tra bằng ast.parse (không chạy mã). Kiểm tra này phát hiện
lỗi cú pháp, không xác nhận thuật toán hay đầu ra. C/C++/Java hiện chưa được compiler
kiểm chứng tự động trong Web. Nếu dòng bị xóa vẫn để lại chương trình hợp lệ,
cần đề bài/đầu ra mong đợi để phát hiện thiếu logic. Không dùng thông báo
chưa phát hiện lỗi như bảo đảm chương trình đúng.
