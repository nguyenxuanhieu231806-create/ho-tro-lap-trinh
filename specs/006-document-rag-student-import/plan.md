# Kế hoạch kỹ thuật dự thảo 006

**Trạng thái:** ĐANG TRIỂN KHAI theo chỉ thị mới của người dùng “kh cần duyệt trước”. Giữ hồ sơ Spec Kit và kiểm thử; bỏ việc chờ xác nhận riêng trước mỗi bước. Không tự gán admin, nạp tài liệu cá nhân hay ghi đè tài khoản.

## Summary

Giữ ứng dụng Python/FastAPI/Monaco hiện tại. Bổ sung chế độ Hỏi đáp tài liệu và trang/khu vực quản trị nhỏ. Hai luồng riêng: ingestion có review/versioning và query có evidence gate/citation/streaming; dùng Chroma local và Ollama hiện có theo benchmark, không ép hai model sinh độc lập.

## Technical Context

- Runtime đã kiểm chứng: Python 3.12.14; Docker của hệ thống hiện dùng Python 3.11. Cần kiểm thử cả hai khi pin phụ thuộc mới.
- Cơ sở hiện tại: FastAPI/Uvicorn/Pydantic/python-dotenv, urllib cho Ollama; SQLite auth; không gian lập trình với Run Docker độc lập.
- Phụ thuộc đề xuất: chromadb, python-docx, openpyxl; python-multipart khi chọn upload chuẩn; Pillow/Tesseract và dữ liệu vie+eng chỉ nếu mẫu chứng minh cần OCR. Pin phiên bản tương thích sau duyệt, không thêm LangChain/cloud SDK mặc định.
- Storage đề xuất: accounts.sqlite3 giữ users/sessions/attempts và batch import; rag.sqlite3 mới cho registry/job/history; data/chroma và data/documents riêng, ngoài static.
- Triển khai ưu tiên local một tiến trình ứng dụng và Chroma persistent cùng máy. Phương án Chroma service Docker riêng còn là lựa chọn thay thế phải duyệt. Không công khai cổng Chroma/Ollama.
- Máy khoảng 15,7 GiB RAM, 8 logical CPU; chưa xác định GPU. Không đặt cam kết thời gian trả lời/khối lượng nạp trước benchmark corpus thực tế.

## Cổng phê duyệt

1. Duyệt spec và thông tin thiếu (mẫu tài liệu/Excel, admin, mật khẩu).
2. Duyệt plan, data-model, API và phạm vi auth migration/dependencies/model tải.
3. Chốt tasks; chỉ sau đó implement theo từng phần nhỏ có kiểm chứng và đối chiếu.

Không có thao tác bước 1 tự cho phép bước 2/3 khi chưa có chấp thuận rõ. Không sửa mã, DB, .env, requirements hoặc file .specify đang chọn ở lượt khảo sát.

## Thiết kế luồng nạp

Upload admin → kiểm tra loại/dung lượng/cấu trúc nén → hash và chống trùng → tạo staging revision → trích block theo thứ tự → liên kết bảng/ảnh/caption → OCR/mô tả được duyệt nếu cần → preview và cảnh báo → chunk theo cấu trúc → embed bằng profile cố định → Chroma staging → kiểm tra count/dimension/truy xuất thử → publish active revision trong registry.

Từ chối tệp không đọc được, không đoán encoding/numbering. Giới hạn file nén, số phần/ảnh/pixel, text và thời gian phải chốt theo mẫu trước khi mở upload. Mọi job có ID, tiến độ, retry/hủy, checkpoint; chỉ dùng tập revision active lấy từ registry khi truy vấn. Không thay bản active cũ tới khi toàn bộ bản mới đạt kiểm tra. Có xử lý job dở dang khi restart. Snapshot query gồm tập revision và index/embedding generation; kiểm tra ngay trước phát, đổi generation thì truy xuất lại có giới hạn, không trộn không gian vector.

Chỉ hiển thị số trang có căn cứ. Native DOCX dùng heading/block/paragraph/table/image locator. Với tài liệu cần page dùng bản render cố định và kiểm tra map; không tự tin vào cached page breaks. Lưu ảnh gốc, OCR và nguồn mô tả riêng; ảnh bị nhận diện sai chưa được phép trở thành bằng chứng chắc chắn.

## Thiết kế luồng hỏi đáp

Session → kiểm tra owner hội thoại → phân giải câu hỏi nối tiếp → tập tài liệu active được đọc → embedding query cùng profile → Chroma retrieval → kiểm tra độ đủ và ngữ cảnh nguồn → nếu đủ thì sinh nháp có claim/citation → kiểm tra schema/IDs/spans/support → stream nội dung đã duyệt + nguồn.

Không phát nháp. Trạng thái truy xuất/kiểm tra phát sớm; latency chữ đầu tiên có thể tăng. Không đủ trả đúng câu quy định. Đủ một phần chỉ giữ phần có nguồn. Dữ liệu mâu thuẫn phải trình bày hai phía có dẫn nguồn. Lỗi Chroma/model/JSON báo lỗi có thể thử lại, không giả thiếu dữ liệu hoặc gọi Internet.

Không dùng SYSTEM_ROLE coder, reference_context keyword hoặc resolve_model fallback hiện tại cho luật RAG. Có thể tái dùng transport urllib đã có bằng adapter với timeout/giới hạn/khóa, còn prompt/model/DTO RAG tách biệt. Model embedding pin riêng; không rơi sang coder model khi thiếu. Giữ cùng điều phối tài nguyên Ollama: lượt hỏi ưu tiên, ingestion batch có pause, không để các semaphore riêng tạo song song quá RAM. RAG đang xử lý thì giao diện tạm ngừng inline completion như chat hiện tại.

## Hội thoại

Lưu server theo owner username + UUID conversation; API kiểm tra owner từng lần. Client gửi question/conversation_id, không tự quyết lịch sử hoặc quyền. Lượt dở dang có status không coi là answer/evidence. Đề xuất giữ 30 ngày, lấy 4–6 lượt gần nhất trong ngân sách context và lưu tối đa theo quota sau benchmark; các con số phải duyệt. Không nhập lịch sử RAM cũ vào RAG tự động. Nguồn cũ pin revision; bị thu hồi thì hiển thị không còn khả dụng, không chuyển link sang revision khác.

## Excel, auth và migration phải được duyệt

Giữ username/email làm khóa như hiện tại. Sửa seed thành chỉ bổ sung tài khoản mẫu thiếu, không xóa tài khoản mới hoặc ghi đè hồ sơ/mật khẩu khi restart. Bỏ chặn email ngoài ISSUED_EMAILS ở login/current_user, thay bằng tài khoản trong DB đã được cấp; không mở đăng ký tự do.

Đề xuất role student/admin (mặc định student), chỉ cấp admin qua bootstrap cục bộ với email do chủ dự án chỉ định; chưa chỉ định email nên chưa thể tạo. MSSV là định danh nghiệp vụ duy nhất đã được đồng ý; cần kiểm kê trùng trong migration dry-run, chuẩn hóa dữ liệu và tạo ràng buộc thích hợp cho sinh viên, không tự xóa/gộp để hết trùng. Không làm giả MSSV cho admin. Backup trước, migration có phiên bản và rollback; giữ token/hash/PBKDF2 đã có.

Excel .xlsx với 5 cột đã chọn và Mật khẩu tùy chọn chờ duyệt. MSSV chuỗi giữ số 0; dữ liệu số bị mất thông tin báo lỗi. Công thức/links/macro không thực thi. Preview phân loại mới, thiếu/sai, trùng y hệt, cùng email khác MSSV, cùng MSSV khác email, trùng DB. Chỉ lưu batch metadata và bản tạm riêng có TTL; không thay users/sessions trước confirm. Không ghi password vào preview JSON hoặc log. Tệp tạm chứa dữ liệu đăng nhập phải ngoài static, quyền hạn chế, xóa sau xử lý/hết TTL; không tự đưa vào corpus RAG.

Commit ràng buộc batch với admin, hash file/mapping/policy, TTL và idempotency. Kiểm tra lại trong transaction; có thay đổi xung đột thì yêu cầu preview lại, không ghi đè. Nếu cột Mật khẩu có thì băm PBKDF2 với salt riêng cho account mới; trống thì tạo riêng tại commit. Cách bàn giao credentials cho từng sinh viên chờ duyệt; không tạo API sinh viên xem toàn bộ file hoặc xem mật khẩu của nhau. Mật khẩu trong DB chỉ là hash, không phải dữ liệu có thể lấy lại ở giao diện. Upload Excel chứa mật khẩu và bàn giao credentials chỉ cho localhost/HTTPS, không HTTP LAN/public; đây là kiểm tra phía server, không chỉ thông báo giao diện.

## Phạm vi file dự kiến — chưa tạo mã

| File | Thay đổi dự kiến |
| --- | --- |
| api.py | Đăng ký router mới, kiểm tra admin/session, migration/seed theo duyệt; giữ route cũ |
| ai_core.py | Chỉ điều chỉnh nhỏ nếu cần giao diện transport/điều phối tài nguyên chung; không đổi prompt code hoặc completion |
| rag_api.py (mới) | Router RAG, source/history và admin document/import |
| rag_core.py (mới) | Retrieval, resolve ngữ cảnh, evidence gate, nháp có cấu trúc, stream đã duyệt |
| rag_store.py (mới) | Chroma adapter, registry/revisions/jobs/history có ownership |
| document_ingest.py (mới) | DOCX/TXT, block/table/image/caption, chunk và job nạp |
| student_import.py (mới) | Excel preview/validation/confirm/idempotency và báo cáo |
| static/index.html | Nút/chế độ tài liệu, danh sách hội thoại và citation; giữ IDE/ocean; admin UI chỉ cho role admin |
| requirements.txt | Phụ thuộc mới đã được duyệt, pin sau compatibility test |
| .env.example (mới nếu cần), README.md | Biến RAG/model/storage/limits, vận hành và import; không viết bí mật |
| Dockerfile, .dockerignore, docker-compose.yml, run.ps1 | Chỉ thay phần đóng gói/volume/kiểm tra dịch vụ cần thiết theo mode Chroma đã duyệt |
| data/accounts.sqlite3 | Chỉ migration auth/import sau backup và duyệt, không thay DB ở lượt đầu |
| data/rag.sqlite3, data/chroma, data/documents | Kho riêng chỉ tạo khi triển khai được duyệt |
| specs/006-document-rag-student-import/ | Hồ sơ Spec Kit và nghiệm thu |

Không tự sửa assessment_core.py, code_verifier.py, Dockerfile.grader, tài nguyên đồ họa hoặc nguồn báo cáo/UML. Không nạp DB tài khoản vào Chroma. Không tự chuyển toàn hệ thống sang cloud/model vision.

## Kiểm thử sau triển khai

Corpus và Excel mẫu do người dùng chốt trước. Unit/contract cho parser thứ tự, metadata, idempotency, citation và account validation; integration dùng Chroma thật cùng model embedding/generation đã chọn; test lỗi/hủy/khôi phục và auth theo owner/admin. Bộ QA được gán nhãn gồm AC-01–AC-22, có trường hợp gần nghĩa nhưng sai và ảnh có quan hệ hình học.

Đo phase latency: upload/extract/OCR/embed/query/generate/verify/first-approved-token; RAM/CPU và tải đồng thời. Không chỉ kiểm tra similarity hoặc JSON hợp lệ rồi báo AI chính xác. Chạy lại hồi quy login, ocean/Monaco, Chat code, completion, Apply/Undo, Run 4 ngôn ngữ. Mỗi bước có báo cáo thực hiện/chưa kiểm chứng và so với spec đã duyệt.
