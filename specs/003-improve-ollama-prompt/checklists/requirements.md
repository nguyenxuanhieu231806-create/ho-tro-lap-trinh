# Specification Quality Checklist: Câu lệnh gia sư Ollama nhất quán

**Purpose**: Kiểm tra đặc tả trước khi lập kế hoạch  
**Created**: 2026-11-05  
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] Mô tả hành vi người học nhìn thấy, không ấn định thư viện cài đặt
- [x] Các câu lệnh được mô tả theo vai trò và kết quả mong muốn
- [x] Các mục bắt buộc của mẫu đặc tả đã hoàn thành

## Requirement Completeness

- [x] Không còn dấu cần làm rõ hoặc chỗ giữ mẫu
- [x] Có các luồng hỏi, tìm lỗi và dùng câu lệnh mẫu
- [x] Có trường hợp biên và giới hạn phạm vi
- [x] Có tiêu chí đo trên ca kiểm thử cố định

## Feature Readiness

- [x] Yêu cầu và kịch bản chấp nhận tương ứng
- [x] Không sửa mã ứng dụng trước bước duyệt đặc tả

## Notes

- Đã thử ca Python `double(x)` với prompt cũ: nhận diện đúng lỗi nhưng không cấp bản sửa. Bản prompt ngắn thử trong bộ nhớ đã trả mã sửa đầy đủ; ca đối chứng với mã đúng không bị bịa lỗi. Hai ca chưa chứng minh cải thiện tổng thể.
- Đặc tả này không thay thế đặc tả rộng hơn `002-verify-ai-answers` đang chờ duyệt.
