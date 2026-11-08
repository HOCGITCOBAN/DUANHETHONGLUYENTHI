# Kiểm thử SmartExam FE — 04/11/2026

## Đã thực hiện

- `node --check dist/app.js` và `node --check dist/api.js`: không có lỗi cú pháp.
- `node tests/domain.mjs`: PASS. Kiểm tra đăng nhập sai, chặn student gọi quản trị, payload trước thi không chứa đáp án/lời giải, tiếp tục lượt đang làm, chặn hai lượt khác đề, lưu đáp án, chấm/nộp idempotent, riêng tư lịch sử, khóa câu/đề đã xuất bản, chặn xuất bản đề trống, hết giờ, giới hạn lượt, thống kê và ẩn đề.
- Chrome thực tế qua trình duyệt: đăng nhập Sinh viên; mở đề, chọn đáp án, đánh dấu câu; tải lại trang còn đáp án/đánh dấu và thời gian tiếp tục; nộp bài, kết quả đúng 1/6 = 16,67 điểm; xem lời giải.
- Chrome thực tế: đăng xuất/chuyển Admin; tạo đề nháp, gán câu, lưu thành công; xuất bản đổi trạng thái và khóa sửa; mở câu hỏi đã xuất bản hiển thị các trường disabled và cảnh báo đúng.
- Đã xem ảnh màn hình tổng quan desktop để kiểm tra bố cục, độ tương phản, khoảng cách và chữ tiếng Việt.

## Giới hạn

- Các backend ngoài US-01 trong phần cập nhật bên dưới chưa được triển khai; chưa xác nhận tích hợp JWT và các nghiệp vụ thi với Backend thật.
- Có media queries cho 360px, 400px, 760px và 1150px; chưa kiểm thử thiết bị di động thật hoặc Edge. Cần nhóm kiểm tra Chrome/Edge và kích thước 360px trước buổi bảo vệ.
- Demo dùng localStorage không bảo mật, không đồng bộ giữa máy/trình duyệt. Khi đóng tab, lượt hết giờ được chốt ở lần truy cập tiếp theo; Backend thật phải tự xử lý deadline độc lập client.
- Chưa có refresh-token endpoint. JWT thật chỉ ở bộ nhớ, F5 cần đăng nhập lại; dữ liệu lượt thi vẫn do BE lưu và lấy lại qua Lịch sử.
- Các bài/câu hỏi và kết quả mẫu chỉ phục vụ trình diễn luồng sản phẩm.

## Cập nhật US-01 / T05F912 — 06/11/2026

- Backend: `python -m pytest -q` đạt **44 kiểm thử**, gồm lưu tài khoản thật, Argon2id,
  email trùng/đồng thời, quyền student, dữ liệu biên, alias tên, lỗi không lộ mật khẩu,
  migration và cấu hình frontend/CORS.
- Email Unicode tương đương được kiểm tra theo cả hai thứ tự gửi: lần đầu tạo tài khoản,
  lần sau trả 409 và giữ nguyên tài khoản ban đầu.
- Frontend: `node tests/registration.mjs` đạt **7 kiểm thử** cho HTTP adapter đăng ký;
  `node tests/domain.mjs` vẫn PASS. Kiểm tra cú pháp app.js/api.js và Ruff backend đều đạt.
- Chromium với FastAPI/CSDL thật: form gửi đăng ký trả 201 và hiển thị thành công;
  email trùng trả 409; email lỗi định dạng phía server trả 422 với thông báo tiếng Việt;
  mất kết nối hiển thị lỗi và mở lại form. Mật khẩu dài bị từ chối, không bị cắt ngắn.
- Form đăng ký được kiểm tra ở 360, 390, 768 và 1440px: không tràn ngang, không có lỗi JavaScript.
- Form đăng ký: hai lần gửi liên tiếp chỉ tạo một request; các trường được mở lại sau lỗi
  409/mất kết nối; mật khẩu và xác nhận được xóa sau thành công. Việc khóa form này chỉ áp dụng cho đăng ký.
- Chromium với Node demo: sinh viên có sẵn đăng nhập dashboard, đăng xuất, đăng ký mới,
  và sinh viên demo mới đăng nhập bằng demo123 đều hoạt động. Không có lỗi JavaScript.

Kiểm tra sử dụng CSDL/tài khoản tạm riêng; không đưa tệp CSDL hoặc thông tin đăng nhập thật vào repo.
Luồng đăng nhập/JWT của Backend chưa thuộc US-01. Các kiểm tra trình duyệt ở trên dùng Chromium,
không thay cho kiểm thử trên thiết bị thật hoặc Edge.
