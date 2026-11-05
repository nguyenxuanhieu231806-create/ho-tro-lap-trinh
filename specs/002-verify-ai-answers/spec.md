# Feature Specification: Kiểm chứng câu trả lời AI lập trình

**Feature Branch**: Không áp dụng trong thư mục hiện tại  
**Created**: 2026-11-05  
**Status**: Chờ duyệt đặc tả  
**Input**: Người dùng muốn trợ lý lập trình cục bộ trả lời chính xác hơn, tránh khẳng định mã đúng khi còn lỗi và cung cấp bản sửa có thể áp dụng khi đã xác định được lỗi.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kết luận dựa trên bằng chứng (Priority: P1)

Sinh viên hỏi mã hiện tại đúng hay sai. Hệ thống đối chiếu câu hỏi, mã và bằng chứng kiểm tra có sẵn, rồi phân biệt lỗi đã xác nhận, nghi vấn và điểm chưa đủ dữ kiện. Nếu đề bài hoặc đầu ra mong đợi chưa rõ, trợ lý hỏi lại thay vì khẳng định mã hoàn toàn đúng.

**Why this priority**: Kết luận sai làm sinh viên hiểu sai kiến thức và có thể áp dụng bản sửa không phù hợp.

**Independent Test**: Dùng bộ ca có yêu cầu và đáp án đã được kiểm tra, gồm mã đúng, mã sai cú pháp, mã đúng cú pháp nhưng sai kết quả, và câu hỏi thiếu đầu ra mong đợi.

**Acceptance Scenarios**:

1. **Given** mã Python của hàm `double(x)` trả về `x + 1` và yêu cầu trả `2 * x`, **When** sinh viên hỏi mã có đúng không, **Then** hệ thống chỉ rõ lỗi logic ở dòng trả về và không tuyên bố mã đúng chỉ vì cú pháp hợp lệ.
2. **Given** mã của hàm trả đúng `2 * x`, **When** sinh viên hỏi cùng yêu cầu, **Then** hệ thống không bịa ra lỗi hoặc bản sửa.
3. **Given** mã hợp lệ về cú pháp nhưng chưa có đề bài, dữ liệu mẫu hoặc kết quả mong đợi, **When** sinh viên hỏi mã đã đúng hoàn toàn chưa, **Then** hệ thống nêu rõ giới hạn bằng chứng và hỏi thông tin còn thiếu.
4. **Given** công cụ kiểm tra không sẵn sàng, **When** sinh viên yêu cầu kết luận, **Then** hệ thống thông báo phần chưa được kiểm chứng, không nói rằng đã chạy hoặc biên dịch mã.

---

### User Story 2 - Bản sửa đầy đủ và an toàn (Priority: P1)

Sinh viên muốn sửa mã sau khi AI chỉ ra lỗi. Hệ thống hiển thị đúng vị trí trong mã gốc, nguyên nhân, bản sửa đầy đủ khi có thể xác định, cùng trạng thái kiểm tra của bản sửa. Sinh viên chủ động chấp nhận hoặc giữ nguyên mã.

**Why this priority**: Bản sửa rỗng, sai cú pháp hoặc không còn khớp mã trong Editor có thể phá hỏng bài làm.

**Independent Test**: Thử bản sửa đúng, bản sửa chỉ có khoảng trắng, bản sửa sai cú pháp hoặc không biên dịch được, và mã đã thay đổi trong khi AI trả lời.

**Acceptance Scenarios**:

1. **Given** AI xác định lỗi có cách sửa rõ ràng, **When** kết quả được hiển thị, **Then** sinh viên thấy bản mã hoàn chỉnh và bằng chứng kiểm tra hoặc giới hạn kiểm tra trước khi chọn áp dụng.
2. **Given** bản sửa rỗng, không hợp lệ hoặc không khớp phiên bản mã gốc, **When** sinh viên xem kết quả, **Then** hệ thống không cho áp dụng bản sửa đó.
3. **Given** có cảnh báo nhưng chưa đủ thông tin để sửa an toàn, **When** AI phản hồi, **Then** hệ thống giải thích thông tin còn thiếu và không tạo bản sửa giả định.
4. **Given** mã C, C++, Java hoặc Python không qua kiểm tra khả dụng, **When** AI đề nghị sửa, **Then** trạng thái chưa kiểm chứng được thể hiện rõ, không trình bày như bản sửa đã được xác nhận.

---

### User Story 3 - Trả lời đúng trọng tâm với tốc độ đo được (Priority: P2)

Sinh viên hỏi lý thuyết, giải thích một đoạn được chọn hoặc nhờ tìm lỗi. Hệ thống ưu tiên câu hỏi và phần mã được chọn, không kéo các câu trả lời cũ không liên quan vào kết luận; phần trả lời hiện ra dần khi có nội dung.

**Why this priority**: Ngữ cảnh thừa làm phản hồi chậm và khiến AI trả lời lệch câu hỏi.

**Independent Test**: Đo thời gian trả lời cho cùng ca trước và sau thay đổi; thử mã dài, vùng chọn lặp lại, câu hỏi lý thuyết khi tắt đính kèm mã và yêu cầu bị hủy.

**Acceptance Scenarios**:

1. **Given** sinh viên chỉ chọn một đoạn mã, **When** yêu cầu giải thích đoạn đó, **Then** vị trí dòng và nội dung được giải thích khớp đúng vùng đã chọn, kể cả khi đoạn mã giống hệt xuất hiện nhiều lần.
2. **Given** sinh viên tắt đính kèm mã, **When** hỏi lý thuyết trong lúc Editor chứa file dài, **Then** câu hỏi vẫn được gửi và mã trong Editor không làm vượt giới hạn yêu cầu.
3. **Given** yêu cầu AI đang xử lý, **When** có nội dung đầu tiên, **Then** giao diện hiển thị dần và không đưa kết luận cuối cùng chưa qua kiểm tra thành bản sửa có thể áp dụng.

---

### User Story 4 - Đánh giá câu trả lời của sinh viên có đáp án gốc (Priority: P3)

Sinh viên sử dụng nút câu hỏi kiểm tra đã có trên giao diện. Câu hỏi, đáp án và tiêu chí được giữ ở máy chủ; kết quả chấm nêu rõ cơ sở đối chiếu, phần đúng, phần sai và giới hạn của các ca kiểm thử. Nếu chức năng chưa sẵn sàng, giao diện không mời sinh viên nộp bài vào một đường dẫn không hoạt động.

**Why this priority**: Tính năng hiện có trên giao diện cần có kết quả đáng tin cậy, không thể để AI tự đổi đáp án sau khi sinh viên nộp.

**Independent Test**: Chọn câu trắc nghiệm đúng/sai, nộp câu tự luận đủ/thiếu ý và nộp mã vượt/không vượt các ca kiểm thử đã xác định trước.

**Acceptance Scenarios**:

1. **Given** câu trắc nghiệm có đáp án cố định, **When** sinh viên chọn đáp án, **Then** kết quả được đối chiếu với đáp án đã lưu trước khi nộp.
2. **Given** câu lập trình có ca kiểm thử xác định trước, **When** sinh viên nộp mã, **Then** kết quả phân biệt ca đạt, ca không đạt và ca chưa thể kiểm tra; không khẳng định mã đúng với mọi đầu vào.
3. **Given** chức năng chấm chưa khả dụng, **When** giao diện được mở, **Then** sinh viên được thông báo rõ thay vì gặp lỗi sau khi hoàn thành câu trả lời.

### Edge Cases

- Mã đúng cú pháp nhưng sai logic; bản sửa đúng cú pháp nhưng sai đầu ra mong đợi.
- Mã có nhiều đoạn giống nhau, vùng chọn thay đổi trong lúc AI đang trả lời.
- Không có mã, thiếu đề bài, không có dữ liệu kiểm thử hoặc công cụ kiểm tra tạm thời không khả dụng.
- AI trả kết quả sai cấu trúc, nội dung quá dài, vị trí lỗi ngoài file, bản sửa rỗng hoặc lời giải mâu thuẫn với danh sách lỗi.
- Mã của sinh viên có đầu vào nguy hiểm; việc kiểm thử không được phép gây tác động lên máy chủ hoặc dữ liệu tài khoản.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Hệ thống MUST phân biệt kết quả đã được công cụ xác nhận, nhận định của AI và trường hợp chưa đủ dữ kiện để kết luận.
- **FR-002**: Hệ thống MUST tránh thông báo mã đúng hoàn toàn khi mới chỉ xác nhận cú pháp hoặc khi chưa có mục tiêu và đầu ra mong đợi.
- **FR-003**: Hệ thống MUST kiểm tra vị trí lỗi, tính đầy đủ và tính hợp lệ của bản sửa trước khi cho sinh viên áp dụng.
- **FR-004**: Hệ thống MUST từ chối bản sửa rỗng, bản sửa không còn khớp phiên bản mã đang mở và bản sửa thất bại ở bước kiểm tra bắt buộc có sẵn.
- **FR-005**: Hệ thống MUST nêu rõ khi không thể xác minh hoặc sửa an toàn và MUST không tự nhận đã chạy hay biên dịch mã nếu chưa thực hiện.
- **FR-006**: Hệ thống MUST ưu tiên câu hỏi và vùng mã được chọn; khi không đính kèm mã, nội dung Editor không được ảnh hưởng đến giới hạn yêu cầu.
- **FR-007**: Hệ thống MUST giữ khả năng hiển thị câu trả lời từng phần và hủy yêu cầu cũ khi người học dừng tác vụ.
- **FR-008**: Chức năng câu hỏi kiểm tra đang hiển thị MUST có luồng nộp và đánh giá hoạt động, hoặc hiển thị trạng thái chưa khả dụng trước khi người học bắt đầu.
- **FR-009**: Đáp án và tiêu chí của câu hỏi kiểm tra MUST được cố định trước khi nộp và không tiết lộ cho người học trước khi gửi câu trả lời.
- **FR-010**: Hoạt động kiểm tra mã của người học MUST được cô lập khỏi dữ liệu tài khoản và giới hạn thời gian, tài nguyên.
- **FR-011**: Hệ thống MUST giữ nguyên đăng nhập, đổi mật khẩu, bốn tài khoản hiện có, bốn ngôn ngữ và bố cục chính khi cải thiện AI.
- **FR-012**: Hệ thống MUST lưu lại các phép đo chất lượng và độ trễ trên bộ ca chuẩn để có thể so sánh trước và sau thay đổi mà không lưu mật khẩu hoặc dữ liệu cá nhân trong báo cáo.

### Key Entities *(include if feature involves data)*

- **Ca đánh giá**: Câu hỏi, ngôn ngữ, mã gốc, yêu cầu mong đợi và kết luận chuẩn được người kiểm tra xác nhận.
- **Bằng chứng kiểm tra**: Kết quả kiểm tra cú pháp, biên dịch hoặc ca chạy thử; trạng thái khả dụng và giới hạn áp dụng.
- **Kết quả phân tích**: Lời giải, các vấn đề theo dòng, bản sửa tùy chọn và bằng chứng đi kèm.
- **Câu hỏi kiểm tra**: Nội dung hiển thị và đáp án, tiêu chí cố định ở phía máy chủ.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên bộ ít nhất 80 ca độc lập, cân bằng giữa bốn ngôn ngữ và gồm cả mã đúng, mã sai, ít nhất 90% kết luận đúng/sai hoặc “chưa đủ dữ kiện” khớp đáp án đã duyệt; báo cáo riêng tỷ lệ bỏ sót và báo sai.
- **SC-002**: Trong toàn bộ ca kiểm thử về bản sửa rỗng, sai cú pháp hoặc sai phiên bản, không có bản sửa nào được đưa vào Editor.
- **SC-003**: Trong toàn bộ ca không có bằng chứng chạy thử, giao diện không tuyên bố mã đã được chạy hay đúng với mọi đầu vào.
- **SC-004**: Đối với 20 ca phản hồi ngắn trên cùng máy, có số liệu thời gian đến nội dung đầu tiên và thời gian hoàn tất; trung vị thời gian hoàn tất khi model đã nạp không tăng quá 10% so với đường cơ sở nếu chất lượng đạt SC-001.
- **SC-005**: Đăng nhập, hồ sơ, đổi mật khẩu, soạn thảo và gợi ý mã hiện có vẫn vượt qua các ca kiểm tra hồi quy liên quan.

## Assumptions

- Model cục bộ hiện tại được giữ làm đường cơ sở; thay model hoặc tinh chỉnh trọng số chỉ được cân nhắc sau khi có số liệu so sánh và đánh giá tài nguyên máy.
- Khi thiếu yêu cầu chức năng hoặc ca kiểm thử, hệ thống chỉ có thể đánh giá phần cú pháp, cấu trúc và vấn đề có chứng cứ; không cam kết xác định đúng sai mọi thuật toán.
- Việc chạy mã của sinh viên chỉ được triển khai khi có môi trường cô lập phù hợp; nếu chưa có, hệ thống báo giới hạn kiểm chứng.
- Luồng đăng nhập và dữ liệu tài khoản hiện có nằm ngoài phạm vi thay đổi. Chức năng câu hỏi kiểm tra đã xuất hiện trên giao diện được đưa vào phạm vi vì đang thiếu luồng phản hồi hoạt động.
