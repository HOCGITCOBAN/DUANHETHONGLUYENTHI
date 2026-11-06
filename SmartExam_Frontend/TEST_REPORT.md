# Kiểm thử SmartExam FE — 04/11/2026

## Đã thực hiện

- `node --check dist/app.js` và `node --check dist/api.js`: không có lỗi cú pháp.
- `node tests/domain.mjs`: PASS. Kiểm tra đăng nhập sai, chặn student gọi quản trị, payload trước thi không chứa đáp án/lời giải, tiếp tục lượt đang làm, chặn hai lượt khác đề, lưu đáp án, chấm/nộp idempotent, riêng tư lịch sử, khóa câu/đề đã xuất bản, chặn xuất bản đề trống, hết giờ, giới hạn lượt, thống kê và ẩn đề.
- Chrome thực tế qua trình duyệt: đăng nhập Sinh viên; mở đề, chọn đáp án, đánh dấu câu; tải lại trang còn đáp án/đánh dấu và thời gian tiếp tục; nộp bài, kết quả đúng 1/6 = 16,67 điểm; xem lời giải.
- Chrome thực tế: đăng xuất/chuyển Admin; tạo đề nháp, gán câu, lưu thành công; xuất bản đổi trạng thái và khóa sửa; mở câu hỏi đã xuất bản hiển thị các trường disabled và cảnh báo đúng.
- Đã xem ảnh màn hình tổng quan desktop để kiểm tra bố cục, độ tương phản, khoảng cách và chữ tiếng Việt.

## Giới hạn

- Chưa có Backend thật. Chế độ API có adapter và DTO đề xuất, chưa thể xác nhận tích hợp đầu cuối với FastAPI/CSDL/JWT thật.
- Có media queries cho 360px, 400px, 760px và 1150px; chưa kiểm thử thiết bị di động thật hoặc Edge. Cần nhóm kiểm tra Chrome/Edge và kích thước 360px trước buổi bảo vệ.
- Demo dùng localStorage không bảo mật, không đồng bộ giữa máy/trình duyệt. Khi đóng tab, lượt hết giờ được chốt ở lần truy cập tiếp theo; Backend thật phải tự xử lý deadline độc lập client.
- Chưa có refresh-token endpoint. JWT thật chỉ ở bộ nhớ, F5 cần đăng nhập lại; dữ liệu lượt thi vẫn do BE lưu và lấy lại qua Lịch sử.
- Các bài/câu hỏi và kết quả mẫu chỉ phục vụ trình diễn luồng sản phẩm.
