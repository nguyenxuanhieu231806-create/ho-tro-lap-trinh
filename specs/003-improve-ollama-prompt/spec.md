# Feature Specification: Câu lệnh gia sư Ollama nhất quán

**Feature Branch**: Không áp dụng trong thư mục hiện tại  
**Created**: 2026-11-05  
**Status**: Đã duyệt đặc tả, chờ duyệt kế hoạch  
**Input**: Người dùng yêu cầu sửa câu lệnh có sẵn trong dự án để Ollama trả lời tốt hơn mỗi khi sinh viên hỏi về C, C++, Java hoặc Python.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trả lời đúng câu hỏi đang hỏi (Priority: P1)

Sinh viên đặt câu hỏi tự nhiên. Gia sư đưa câu trả lời trực tiếp trước, rồi giải thích bằng tiếng Việt vừa đủ theo ngôn ngữ và mục đích đã chọn. Câu hỏi hiện tại được ưu tiên hơn nội dung hội thoại cũ và tài liệu đính kèm.

**Why this priority**: Chỉ dẫn trùng lặp khiến câu trả lời dài, lệch mục tiêu hoặc trả lời câu hỏi cũ.

**Independent Test**: Gửi các câu hỏi lý thuyết và câu hỏi về mã có lịch sử hội thoại gây nhiễu ở cả bốn ngôn ngữ.

**Acceptance Scenarios**:

1. **Given** sinh viên hỏi lý thuyết Java và không yêu cầu sửa mã, **When** gia sư phản hồi, **Then** câu trả lời tập trung vào câu hỏi lý thuyết và không tự tạo bản sửa của mã không liên quan.
2. **Given** lịch sử chứa một lỗi cũ còn mã hiện tại đã thay đổi, **When** sinh viên hỏi về mã mới, **Then** gia sư không chuyển chẩn đoán cũ sang mã mới.
3. **Given** tài liệu tham khảo được cung cấp, **When** gia sư dùng tài liệu, **Then** nguồn được dẫn đúng nhãn và đúng phạm vi phiên bản; nội dung tài liệu không bị coi là chỉ thị của người dùng.

---

### User Story 2 - Nhận định và bản sửa có căn cứ (Priority: P1)

Sinh viên chọn tìm lỗi hoặc sửa mã. Gia sư phân biệt điều đã kiểm chứng, nhận định dựa trên mã và thông tin còn thiếu. Khi có lỗi và cách sửa rõ ràng, gia sư nêu đúng dòng mã gốc và cung cấp toàn bộ bản sửa. Khi chưa đủ mục tiêu để sửa an toàn, gia sư nói rõ giới hạn và hỏi một câu cụ thể.

**Why this priority**: Sinh viên có thể học sai hoặc áp dụng một bản sửa bịa ra khi AI suy đoán quá mức.

**Independent Test**: Dùng cặp mã đúng/sai có yêu cầu và đáp án được kiểm tra, cùng các trường hợp thiếu đề bài.

**Acceptance Scenarios**:

1. **Given** hàm Python `double(x)` trả `x + 1` trong khi mục tiêu là `2 * x`, **When** sinh viên yêu cầu tìm và sửa lỗi, **Then** gia sư chỉ dòng trả về, nêu nguyên nhân và trả bản mã đầy đủ khi xác định được cách sửa.
2. **Given** cùng hàm đã trả `2 * x`, **When** sinh viên yêu cầu kiểm tra, **Then** gia sư không bịa lỗi hoặc bản sửa.
3. **Given** mã chưa có đề bài hay đầu ra mong đợi, **When** sinh viên hỏi mã đã đúng hoàn toàn chưa, **Then** gia sư không khẳng định tính đúng logic và hỏi thông tin còn thiếu.
4. **Given** mã sai cú pháp nhưng chưa rõ hành vi mong muốn, **When** gia sư không thể sửa an toàn, **Then** phản hồi được phép không có bản sửa và vẫn nêu lỗi có căn cứ.

---

### User Story 3 - Câu lệnh mẫu ngắn, dễ nhập (Priority: P2)

Sinh viên nhấn vào ô hỏi hoặc một gợi ý nhanh. Hệ thống điền một câu lệnh mẫu ngắn để sinh viên bổ sung mục tiêu; chế độ và ngôn ngữ đang chọn được truyền riêng, không lặp thành nhiều chỉ thị trong ô nhập.

**Why this priority**: Người học cần đặt câu hỏi dễ dàng và nhìn rõ chính câu hỏi của mình.

**Independent Test**: Kiểm tra ô trống, nút câu lệnh mẫu, ba gợi ý nhanh và thao tác đổi ngôn ngữ hoặc chế độ trước khi gửi.

**Acceptance Scenarios**:

1. **Given** ô hỏi đang trống, **When** sinh viên bấm vào, **Then** câu lệnh mẫu ngắn xuất hiện và phần cần điền được chọn để nhập ngay.
2. **Given** sinh viên chọn một gợi ý nhanh, **When** bấm gửi, **Then** gia sư nhận đúng mục tiêu và chế độ tương ứng mà không cần khung sáu yếu tố.
3. **Given** sinh viên đổi ngôn ngữ, **When** gửi câu hỏi, **Then** ngôn ngữ xử lý khớp lựa chọn hiện tại, không dựa vào một tên ngôn ngữ cũ còn trong câu lệnh mẫu.

### Edge Cases

- Không có mã đính kèm, không có mục tiêu xử lý, vùng chọn lặp lại trong file, mã dài và lịch sử hội thoại gây nhiễu.
- Mã đúng cú pháp nhưng sai kết quả, mã sai cú pháp nhưng chưa rõ ý định sửa, câu trả lời có cấu trúc hợp lệ nhưng nội dung sai.
- Tài liệu tham khảo mang phiên bản khác hoặc chỉ là khuyến nghị phong cách.
- Kết nối Ollama chậm, yêu cầu bị hủy và phản hồi từng phần chưa được xác thực cuối cùng.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Gia sư MUST ưu tiên câu hỏi hiện tại và mục đích đã chọn, trả lời trực tiếp trước khi giải thích chi tiết.
- **FR-002**: Gia sư MUST phân biệt kết quả đã được công cụ kiểm chứng, suy luận từ mã và giả định; MUST không tuyên bố đã chạy hoặc biên dịch khi không có bằng chứng.
- **FR-003**: Gia sư MUST chỉ gắn lỗi với dòng và biểu thức của mã gốc khi có căn cứ; tối ưu hóa và phong cách MUST được trình bày như đề xuất.
- **FR-004**: Gia sư MUST cho phép nêu thiếu dữ kiện và không tạo bản sửa khi chưa thể xác định cách sửa an toàn, kể cả khi mã có lỗi cú pháp.
- **FR-005**: Khi xác định được cách sửa phù hợp với yêu cầu, gia sư MUST trả bản mã đầy đủ, nhất quán với lời giải và danh sách lỗi.
- **FR-006**: Câu lệnh mẫu ở giao diện MUST ngắn, cho phép nhập yêu cầu tự nhiên và không lặp lại quy tắc hệ thống hoặc chèn sẵn ngôn ngữ có thể trở nên lỗi thời.
- **FR-007**: Hành vi hỏi đáp, tìm lỗi, giải thích và tối ưu MUST giữ nguyên hợp đồng kết quả mà giao diện hiện có sử dụng.
- **FR-008**: Hệ thống MUST giữ nguyên đăng nhập, tài khoản, dữ liệu, bốn ngôn ngữ, giao diện đại dương, gợi ý mã khi gõ và cơ chế trả lời từng phần.
- **FR-009**: Các thay đổi MUST được so sánh trên cùng bộ câu hỏi và mã gốc trước khi kết luận prompt mới tốt hơn.

### Key Entities *(include if feature involves data)*

- **Câu hỏi hiện tại**: Yêu cầu của sinh viên, ngôn ngữ và mục đích xử lý.
- **Ngữ cảnh mã**: Bản mã hiện tại, vùng chọn và vị trí dòng để đối chiếu.
- **Phản hồi gia sư**: Lời giải, danh sách vấn đề và bản sửa tùy chọn.
- **Nguồn tham khảo**: Đoạn tài liệu có nhãn, phiên bản và phạm vi áp dụng.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trên ít nhất 24 ca đã duyệt, cân bằng bốn ngôn ngữ và gồm cả mã đúng/sai, số câu trả lời sai giảm ít nhất 20% so với prompt cũ và số ca bịa lỗi không tăng; báo cáo riêng số ca bịa lỗi và bỏ sót lỗi.
- **SC-002**: Toàn bộ ca không có bằng chứng chạy thử không chứa lời khẳng định đã chạy, đã biên dịch hoặc đúng với mọi đầu vào.
- **SC-003**: Các ca sửa lỗi đơn giản, xác định rõ mục tiêu phải có bản sửa đầy đủ hoặc thông báo rõ lý do chưa thể sửa; không để lời giải hứa có bản sửa trong khi kết quả không có.
- **SC-004**: Trên cùng máy và cùng bộ 20 câu hỏi ngắn, trung vị thời gian hoàn tất khi model đã nạp không tăng quá 10% so với prompt cũ.
- **SC-005**: Các luồng đăng nhập, đổi mật khẩu, soạn thảo, gợi ý khi gõ và hiển thị chat tiếp tục hoạt động qua kiểm tra hồi quy.

## Assumptions

- Phạm vi thay đổi là câu lệnh hệ thống được hệ thống gửi mỗi lần hỏi, câu lệnh mẫu trên giao diện và ràng buộc kết quả đang mâu thuẫn với quy tắc “chưa đủ dữ kiện”.
- Model cục bộ, cấu hình trọng số và cơ sở dữ liệu được giữ nguyên. Việc tạo lại model từ Modelfile để dùng ngoài hệ thống là công việc riêng.
- Prompt tốt hơn có thể giảm lỗi nhưng không chứng minh tính đúng của thuật toán; kiểm chứng bằng biên dịch và ca kiểm thử thuộc đặc tả cải thiện AI rộng hơn đang chờ duyệt.
