# Đặc tả 006 — Hỏi đáp tài liệu có bằng chứng và nhập sinh viên từ Excel

**Ngày:** 05/11/2026. **Trạng thái:** ĐANG TRIỂN KHAI — người dùng yêu cầu “kh cần duyệt trước”, thay thế cổng chờ duyệt riêng trước đó.

Triển khai theo phạm vi đã khảo sát, giữ các lựa chọn đã xác nhận. Mặc định khởi đầu: DOCX/TXT UTF-8/XLSX; giữ lịch sử 30 ngày; kho chung; mật khẩu trong Excel nếu có, trống thì tạo riêng; không tự gán admin. Cung cấp công cụ tạo admin cục bộ có nhập email/mật khẩu bởi chủ dự án. Mẫu kiểm thử tổng hợp không được nạp vào kho thật. OCR/ảnh không đọc chắc chắn phải review; không công bố nội dung ảnh suy đoán. Mẫu người dùng, admin thực và benchmark corpus thực vẫn cần trước khi kết luận chất lượng triển khai thực tế.

## Phạm vi và các quyết định đã được người dùng xác nhận

1. Thêm chế độ Hỏi đáp tài liệu riêng, giữ Chat/Sửa code và toàn bộ không gian lập trình hiện tại.
2. Kho tài liệu dùng chung cho mọi sinh viên đã đăng nhập trong phiên bản đầu.
3. Word không có phân trang xác thực thì dẫn tên tài liệu + mục/đoạn/vị trí. Chỉ hiện trang khi có metadata hợp lệ; không tự suy ra trang từ số đoạn hoặc page break cũ.
4. Excel chuẩn dùng Email, MSSV, Họ và tên, Lớp, Năm học; giữ email đăng nhập, MSSV duy nhất và mặc định chỉ thêm mới. Người dùng mô tả Excel có cả mật khẩu, đồng thời chọn tạo mật khẩu riêng. Dự thảo kết hợp để duyệt: thêm cột Mật khẩu tùy chọn; có giá trị thì dùng để cấp tài khoản mới sau băm, trống thì tạo riêng lúc commit. Không tự thay mật khẩu tài khoản cũ. Chưa chốt tài khoản quản trị và cách bàn giao thông tin đăng nhập cho từng sinh viên.

Hai bộ phận là hai trách nhiệm phần mềm: nạp tài liệu và hỏi đáp. Không yêu cầu hai mô hình sinh độc lập. ChromaDB là kho nội dung/embedding; không chứa tài khoản, mật khẩu, hash hoặc token. RAG mới không gọi Internet hoặc dùng kho language_reference.json làm nguồn thay thế.

## User Scenarios & Testing

### US1 — Quản trị viên nạp tài liệu có cấu trúc — P1

Quản trị viên tải tài liệu được hỗ trợ, xem kết quả trích xuất theo thứ tự đoạn/bảng/ảnh, xử lý cảnh báo rồi xác nhận công bố. Hệ thống ghi nhận tài liệu, phiên bản, block, liên kết ảnh/chú thích và chunk. Chỉ phiên bản công bố thành công mới được truy xuất.

**Kiểm tra độc lập:** tài liệu mẫu có đoạn trước ảnh, ảnh, chú thích, bảng có ô gộp và đoạn sau ảnh. So sánh bản trích với tài liệu gốc; mọi nội dung bị giới hạn/không hỗ trợ phải được báo, không được tự nhận nạp đầy đủ.

### US2 — Sinh viên hỏi theo dữ liệu đã nạp — P1

Sau xác thực, sinh viên đặt câu hỏi bất kỳ chủ đề nào trong kho chung. Backend truy xuất Chroma trước, xác định các phần có bằng chứng, sinh nháp và kiểm tra nguồn trước khi phát trả lời. Không đủ bằng chứng thì trả đúng: “Câu hỏi này vượt quá phạm vi dữ liệu đã được nạp vào hệ thống.” Đủ một phần thì chỉ trả phần được hỗ trợ và nói rõ phần còn lại vượt phạm vi.

**Kiểm tra độc lập:** bộ câu hỏi có đáp án được xác nhận từ tài liệu, câu ngoài phạm vi, câu thiếu một phần, câu chỉ trùng từ khóa nhưng khác ý và tài liệu mâu thuẫn. Không coi khoảng cách vector là chứng minh đáp án.

### US3 — Trả lời streaming có trích dẫn thực sự sử dụng — P1

Giao diện phát các trạng thái đang truy xuất/đang kiểm tra, không phát nội dung nháp. Sau khi bản trả lời được kiểm tra, phát lần lượt các phần đã duyệt cùng citation. Trích dẫn có tên tài liệu, phiên bản, vị trí và trang khi xác thực được; bấm để xem đúng đoạn/bảng/ảnh đã dùng qua API có kiểm tra phiên.

**Kiểm tra độc lập:** ghi nhận sự kiện mạng, không có answer delta trước gate; citation ID phải tồn tại và trỏ đúng supporting span. Không liệt kê mọi đoạn tìm thấy thành nguồn đã dùng. Kiểm tra hủy, timeout và dữ liệu sai cấu trúc.

### US4 — Hội thoại theo người dùng và ngữ cảnh tiếp nối — P1

Sinh viên mở, tạo mới, tiếp tục và khôi phục hội thoại của mình. Lịch sử giúp xác định tham chiếu nhưng không thay thế bằng chứng: mọi câu hỏi kiến thức phải truy xuất lại Chroma. Câu trả lời AI trước đó không được dùng làm nguồn. Tham chiếu mơ hồ phải hỏi rõ.

**Kiểm tra độc lập:** tiếp nối “phần đó” sau reload; người B không đọc được hội thoại của A dù biết ID; đổi tài liệu/phiên bản không làm nguồn cũ tự trỏ sang nội dung mới.

### US5 — Quản trị viên nhập sinh viên có xem trước — P1

Quản trị viên tải Excel, ánh xạ cột, xem phân loại dòng mới/lỗi/trùng/xung đột; chưa xác nhận thì không có thay đổi tài khoản. Xác nhận chỉ nhập các dòng hợp lệ theo chính sách đã duyệt; transaction kiểm tra lại xung đột và chống gửi lặp. Báo thành công/thất bại/bỏ qua và lý do theo dòng.

**Kiểm tra độc lập:** tệp có thiếu cột, email sai, MSSV dạng số mất số 0, công thức, trùng trong tệp và trùng DB. Tài khoản nhập mới đăng nhập và tồn tại sau khởi động lại; bốn tài khoản cũ và mật khẩu cá nhân được giữ.

## Requirements

- FR-001: Không thay đổi hợp đồng API hoặc hành vi Chat lập trình, completion 450 ms, giải thích/sửa lỗi, Apply/Undo, Run bốn ngôn ngữ, đăng nhập và giao diện đại dương khi chưa được duyệt riêng.
- FR-002: Phiên bản đầu đề xuất .docx và .txt UTF-8; .doc/.docm, tệp mã hóa, OLE, đối tượng nhúng hoặc cấu trúc không hỗ trợ phải báo rõ. Danh sách định dạng cuối chờ tài liệu mẫu/xác nhận.
- FR-003: Trích xuất theo thứ tự cấu trúc, không gom hết chữ rồi mới gom bảng/ảnh. Theo dõi heading, paragraph/run, table/cell, ảnh inline/anchor, caption và quan hệ tới block lân cận. Liên kết không chắc chắn phải đánh dấu chờ duyệt.
- FR-004: Giữ ảnh gốc và nguồn gốc văn bản native/OCR/mô tả đã duyệt. OCR nhận chữ không chứng minh quan hệ, mũi tên hay ý nghĩa biểu đồ; ảnh phức tạp cần đối chiếu hoặc xử lý ảnh được duyệt trước công bố.
- FR-005: Mỗi chunk có document_id, revision_id, file_name, block range/section/paragraph hoặc table/image locator, nội dung, nguồn trích xuất, trạng thái duyệt và embedding profile. page chỉ tồn tại khi xác thực được kèm cơ sở xác định.
- FR-006: Chunk theo mục/đoạn, giữ code và hàng/cột bảng cùng tiêu đề/đơn vị cần thiết; không cắt im lặng mất điều kiện hoặc ngữ nghĩa. Giới hạn theo tokenizer/model được chọn và thử với truncate=false; không cố định số ký tự như số token.
- FR-007: ID tài liệu tách tên file. Hash byte để phát hiện nạp trùng; cập nhật tạo phiên bản mới theo lựa chọn có xác nhận. Cùng tên không được tự ghi đè, đổi tên không tạo bản trùng ngoài ý muốn.
- FR-008: Nạp theo staging, có kiểm tra số block/chunk/vector và truy xuất thử trước publish. Lỗi giữa chừng không làm mất phiên bản đang dùng. Commit active revision ở registry; truy vấn chỉ nhận ID/phiên bản đang công bố.
- FR-009: Embedding của tài liệu và truy vấn dùng cùng model/digest/dimension/preprocessing profile. Đổi profile phải dựng chỉ mục mới và kiểm tra trước chuyển; không tự fallback sang model embedding khác. Mỗi lượt ghim cả tập revision + embedding/index generation; trước phát kiểm tra còn hợp lệ, đã chuyển thì truy xuất lại có giới hạn, không trộn index/profile.
- FR-010: Tất cả câu hỏi kiến thức trong chế độ RAG phải đi qua retrieval Chroma trong phạm vi cho phép. Chroma hoặc embedding lỗi thì báo dịch vụ lỗi, không trả từ trí nhớ mô hình; phân biệt lỗi dịch vụ với thiếu dữ liệu.
- FR-011: Kiểm tra bằng chứng theo từng ý, đúng ngữ cảnh/điều kiện/phiên bản. Từ khóa gần giống, lịch sử AI, profile sinh viên, câu hỏi và mã do sinh viên nhập không phải bằng chứng tài liệu. Không đủ thì từ chối; đủ phần nào chỉ trả phần đó.
- FR-012: Không tự viết code, thêm số liệu hoặc suy ra quan hệ ảnh vượt tài liệu. Code chỉ được trích/diễn giải trong giới hạn có nguồn. Mâu thuẫn giữa nguồn phải nêu rõ thay vì tự chọn đáp án.
- FR-013: Tài liệu và lịch sử là dữ liệu không đáng tin về chỉ thị. Nội dung yêu cầu bỏ luật, lộ prompt, gọi Internet hoặc tài khoản không thay đổi chính sách.
- FR-014: Trước khi phát answer phải hoàn thành kiểm tra schema, citation IDs, supporting spans và mức hỗ trợ từng ý. Model không được tự tạo locator hoặc số trang; server kết xuất citation từ registry. Không phát nháp rồi mới thu hồi.
- FR-015: Mọi câu trích thông tin phải gắn citation tương ứng; sources cuối chỉ chứa các nguồn đã dùng. Truy xuất asset/source/history kiểm tra phiên và quyền; không phục vụ upload qua StaticFiles công khai.
- FR-016: Lịch sử quản lý phía server, gắn owner + conversation_id, lưu revision/citation. Giới hạn lịch sử/context và thời hạn lưu theo chính sách được duyệt. Không dùng localStorage khóa chung làm nguồn dữ liệu hội thoại.
- FR-017: Admin là quyền riêng, không tự nâng một trong bốn sinh viên. API nạp tài liệu và nhập Excel cần kiểm tra quyền phía server; cổng quản trị chưa được mở trước khi có cách cấp admin được duyệt.
- FR-018: Trước nhập Excel, sửa chính sách seed/whitelist theo phê duyệt: không xóa tài khoản ngoài bốn mẫu và không reset mật khẩu/hồ sơ quản lý khi khởi động lại.
- FR-019: Cột Excel đã được đồng ý gồm Email, MSSV, Họ và tên, Lớp, Năm học; email là login key, MSSV duy nhất, chỉ thêm mới mặc định. Cần xem file thật và duyệt chi tiết cột Mật khẩu tùy chọn trước implement. Không tự chuyển số thành MSSV nếu mất thông tin.
- FR-020: Tệp Excel chỉ vào luồng tài khoản; không đưa vào Chroma/Ollama hoặc lịch sử RAG. Không thực thi công thức/macro, không theo liên kết ngoài. Thông tin bí mật không xuất hiện trong preview thông thường, log hoặc vector store. Upload Excel có mật khẩu và bàn giao credentials chỉ qua localhost hoặc HTTPS, không qua HTTP mạng LAN/public; kiểm tra kênh phía server theo cấu hình proxy tin cậy đã duyệt.
- FR-021: Preview là bản chụp có hash, owner, TTL, ánh xạ và chính sách. Commit kiểm tra lại DB trong transaction, idempotency và chống preview cũ; mặc định không ghi đè hoặc đặt lại mật khẩu tài khoản đã có.
- FR-022: Ingestion có hàng chờ giới hạn, trạng thái, hủy/thử lại và timeout; ưu tiên lượt hỏi tương tác, không chặn event loop hoặc xếp hàng vô hạn. Không hứa tốc độ khi chưa đo trên máy và corpus.
- FR-023: Không thay dữ liệu/auth/API/kiến trúc, cài gói, tải model, chạy migration hoặc ingestion trước phê duyệt rõ ràng.

## Key Entities

Document, DocumentRevision, ContentBlock, ImageAsset, Chunk, EmbeddingProfile, IngestionJob; Conversation, Message, Citation; ImportBatch, ImportRow. Đây là các thực thể thiết kế đề xuất, chưa tồn tại trong dự án. Users/sessions/attempts hiện có vẫn là nguồn xác thực.

## Tiêu chí nghiệm thu

| Mã | Tình huống | Kết quả phải đạt |
| --- | --- | --- |
| AC-01 | Có dữ liệu hỗ trợ | Đáp án đúng theo bộ đáp án mẫu; mỗi ý có nguồn hợp lệ, đúng vị trí |
| AC-02 | Không có dữ liệu | Trả đúng câu từ chối, không thêm kiến thức ngoài kho |
| AC-03 | Chỉ có một phần | Trả phần có nguồn, chỉ rõ phần thiếu, không lấp bằng kiến thức model |
| AC-04 | Chỉ trùng từ khóa/điều kiện khác | Không kết luận từ similarity; từ chối hoặc hỏi rõ |
| AC-05 | Câu hỏi tiếp nối | Dùng đúng hội thoại để hiểu câu, truy xuất lại; AI cũ không là evidence |
| AC-06 | Tham chiếu mơ hồ | Hỏi rõ, không suy đoán đoạn đang nói tới |
| AC-07 | Word có chữ, bảng, ảnh | Thứ tự và quan hệ đối chiếu đúng bản gốc; cảnh báo đầy đủ phần chưa đọc được |
| AC-08 | Ảnh UML/biểu đồ, OCR sai | Không biến chữ OCR hoặc mô tả chưa duyệt thành kết luận đáng tin |
| AC-09 | Trang có/không xác thực | Chỉ hiện trang thật; còn lại dùng mục/đoạn/vị trí đã được người dùng đồng ý |
| AC-10 | Citation không dùng/sai ID/sai đoạn | Không phát câu trả lời sai nguồn; từ chối kết quả không qua kiểm tra |
| AC-11 | Streaming | Không answer delta trước gate; có tiến độ; stream sau kiểm tra mang citation |
| AC-12 | Reload/đăng nhập tài khoản khác | Khôi phục đúng owner; chặn đọc/sửa hội thoại, nguồn chưa công bố của người khác |
| AC-13 | Nạp lặp/đổi tên/cùng tên/cập nhật | Không trùng/ghi đè ngoài ý muốn; chỉ bản công bố được truy xuất |
| AC-14 | Nạp lỗi giữa chừng | Bản đang công bố vẫn dùng được; staging dở dang không được truy xuất và được reconciliation/cleanup idempotent sau recovery, không nhân đôi bản công bố |
| AC-15 | Đổi embedding profile | Không trộn vector; chỉ chuyển sau reindex và kiểm tra |
| AC-16 | Tài liệu mâu thuẫn/chỉ thị độc hại | Nêu mâu thuẫn có nguồn; bỏ chỉ thị tài liệu và không lộ dữ liệu bí mật |
| AC-17 | Excel lỗi/trùng | Preview không sửa tài khoản/phiên; chỉ lưu metadata batch quản trị nếu được duyệt; phân loại rõ từng dòng và lý do, báo đếm khớp tổng |
| AC-18 | Commit lặp/DB thay đổi sau preview | Không nhân đôi hoặc ghi đè âm thầm; yêu cầu preview lại khi cần |
| AC-19 | Sinh viên mới sau restart | Đăng nhập được, không bị seed xóa; bốn sinh viên cũ/mật khẩu đã đổi còn nguyên |
| AC-20 | Phân quyền admin và dữ liệu bí mật | Sinh viên bị chặn import/upload; không có credentials trong Chroma/chat/log |
| AC-21 | Dịch vụ lỗi/hủy/quá tải | Lỗi tiếng Việt, không fallback ngoài kho, không treo API; message dở dang không được coi hoàn tất |
| AC-22 | Hồi quy không gian lập trình | Login, Chat code, completion, giải thích/sửa lỗi, Apply/Undo và Run C/C++/Java/Python qua lại các ca liên quan |

**Thước đo đề xuất:** trên bộ câu hỏi gán nhãn được hai bên chốt, mọi citation phải trỏ đúng và mọi ca ngoài kho trong bộ kiểm thử phải từ chối; không có câu trả lời phát trước gate. Báo riêng retrieval recall, đúng đáp án, hỗ trợ từng ý, độ chính xác trích dẫn, tỷ lệ từ chối sai và latency/RAM. Quy mô corpus, số câu hỏi và ngưỡng hiệu năng chưa chốt. Không tuyên bố 100% chính xác trên mọi câu hỏi thực tế chỉ nhờ prompt hoặc RAG.

## Những điểm còn cần xác nhận trước triển khai phụ thuộc

- Tài liệu Word/văn bản mẫu để kiểm tra chữ, bảng, ảnh; có chấp nhận .docx/.txt trước và có tệp .doc cũ không? Báo cáo Word hiện có chỉ là ứng viên khảo sát, chưa được chọn làm dữ liệu nạp.
- Excel mẫu và sheet/cột thật; xác nhận cách nhập mật khẩu có sẵn khi cột Mật khẩu được điền. Chính sách email/MSSV duy nhất và chỉ thêm mới đã được đồng ý; phạm vi domain email và quy tắc chi tiết cần mẫu.
- Tài khoản admin nào và cách tạo lần đầu; không tự phân vai.
- Cách bàn giao riêng tài khoản/mật khẩu cho sinh viên; đã chọn mật khẩu khởi tạo riêng. Dự kiến dùng mật khẩu trong Excel nếu có, còn trống thì tạo riêng; không công khai danh sách mật khẩu hoặc trả mật khẩu đang lưu từ hash. Đổi mật khẩu dùng luồng hiện có; ép đổi lần đầu chỉ là tùy chọn ngoài mặc định nếu được duyệt riêng.
- Số tài liệu, dung lượng/số trang/ảnh, số sinh viên đồng thời; thời gian lưu hội thoại. Đề xuất ban đầu 30 ngày, 20 message cho giải tham chiếu, 4–6 lượt gần nhất trong context; chờ duyệt và đo.
- Phương án Chroma trong process hay dịch vụ Docker riêng; cài thêm thư viện/model/OCR và thay DB/API phải duyệt theo plan.

## Cổng phê duyệt

Chỉ tạo tài liệu phân tích trong feature 006. plan/tasks là dự thảo phục vụ đánh giá ở lượt đầu theo yêu cầu người dùng, không phải bước đã duyệt trong workflow. Không đổi feature đang chọn của .specify, không sửa mã chạy hoặc DB. Sau khi chốt thông tin thiếu: duyệt spec → duyệt plan/phạm vi migration/API → chốt tasks → cho phép implement.
