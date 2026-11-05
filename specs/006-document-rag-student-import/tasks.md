# Công việc 006 — đang triển khai

Người dùng đã thay yêu cầu chờ duyệt bằng “kh cần duyệt trước”. Tiến hành theo đặc tả; không tự cấp admin hoặc nạp corpus cá nhân chưa được chỉ định.

## P0 — Khảo sát và duyệt

- [x] T001 Kiểm tra .specify/workflows và khảo sát api.py, ai_core.py, static/index.html, schema SQLite chỉ đọc, requirements và model hiện có.
- [x] T002 Ghi survey.md, spec.md, research.md và các xác nhận về mode riêng/kho chung/citation/Excel.
- [x] T003 Soạn plan.md, data-model.md, contracts/proposed-apis.md và danh sách việc để người dùng xem trước; chưa coi gate plan/tasks đã duyệt.
- [ ] T004 Nhận Word/TXT/Excel mẫu; chốt định dạng/giới hạn, admin, cách xử lý cột Mật khẩu và bàn giao credentials, lịch sử/quy mô dùng.
- [x] T005 Người dùng cho phép tiếp tục không cần cổng duyệt riêng: “kh cần duyệt trước”.

## P1 — Nền tảng và migration được duyệt

- [ ] T006 Lập compatibility matrix và pin phụ thuộc Chroma/DOCX/Excel/upload sau duyệt; benchmark model embedding/sinh trên mẫu, không tự tải trước.
- [ ] T007 Thiết kế migration có backup/dry-run/rollback cho api.py/accounts.sqlite3; bỏ xóa/whitelist cố định, seed không phá tài khoản, phân quyền admin, MSSV uniqueness sau rà soát; test giữ bốn tài khoản/mật khẩu cũ qua restart.
- [ ] T008 Xây rag_store.py với registry/revision/job/history/ownership và Chroma adapter theo mode đã duyệt; storage ngoài static, mapping/profile rõ.

## US1 — Nạp tài liệu

- [ ] T009 Xây document_ingest.py theo mẫu: thứ tự paragraph/table/run/image/anchor/caption, cảnh báo vùng không hỗ trợ, private assets và locator.
- [ ] T010 Chốt và tích hợp OCR/ảnh phức tạp sau đối chiếu mẫu; có review trước dùng như bằng chứng.
- [ ] T011 Chunk theo cấu trúc, embed truncate=false theo profile, kiểm tra manifest; chống trùng, staging/publish và recovery/idempotency.
- [ ] T012 Thêm route admin/job/review trong rag_api.py và giao diện quản trị, có auth/role/limits/CSRF.

## US2/US3 — RAG và nguồn

- [ ] T013 Xây rag_core.py cho resolve query, Chroma retrieval, đủ bằng chứng từng ý, thiếu/một phần/mâu thuẫn; không fallback kiến thức nền/Internet.
- [ ] T014 Tách prompt/DTO RAG khỏi coder; tái dùng transport/điều phối Ollama có timeout và ngân sách tài nguyên.
- [ ] T015 Kiểm tra schema/citation IDs/supporting spans/support trước phát; stream status và answer đã duyệt, nguồn chỉ thực sự được dùng.
- [ ] T016 Giao diện chế độ tài liệu/citation/source viewer; giữ Chat code, ocean, Monaco, completion, Run và Apply/Undo.

## US4 — Hội thoại

- [ ] T017 Thêm create/list/load/delete theo owner, retention/quota, trạng thái canceled/failed và restore; câu tiếp nối truy xuất lại, không dùng AI trước làm evidence.

## US5 — Excel

- [ ] T018 Xây student_import.py với schema/map, đọc XLSX an toàn, phân loại thiếu/sai/trùng/conflict; preview không thay tài khoản và không lộ mật khẩu.
- [ ] T019 Confirm có batch/hash/TTL/idempotency/transaction, mật khẩu hash với salt; báo thành công/lỗi/bỏ qua, phương án credentials được duyệt và dọn file tạm.
- [ ] T020 UI admin nhập/xem trước/xác nhận/báo cáo; kiểm thử mới đăng nhập qua restart và các xung đột khi DB thay đổi sau preview.

## Nghiệm thu

- [ ] T021 Chạy AC-01–AC-22 với corpus/đáp án mẫu/Excel đã thống nhất; test tích hợp Chroma/Ollama/OCR thật, phân biệt fixture và kiểm tra thật.
- [ ] T022 Đo retrieval/answer/citation/abstention và tài nguyên/latency từng pha; không công bố chất lượng khi chỉ test similarity/JSON.
- [ ] T023 Hồi quy login/ocean/chat code/completion/diagnostics/Apply/Undo/Run bốn ngôn ngữ; cập nhật README/đóng gói theo lựa chọn đã duyệt.
- [ ] T024 Đối chiếu spec đã duyệt, liệt kê từng file thay đổi, phần chưa hoàn thành/chưa kiểm chứng và hỏi phản hồi sử dụng thực tế.
