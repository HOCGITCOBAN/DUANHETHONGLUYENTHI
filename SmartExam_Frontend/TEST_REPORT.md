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

## Cập nhật US-06 / T05F917

Kiểm tra ngày 11/11/2026 trên nhánh `feature/t05f917-question-crud`, dựa trên main `015e6d7`.

- Backend: 41 kiểm thử câu hỏi và 2 kiểm thử migration đạt trong lượt chạy toàn bộ suite.
  Bao gồm quyền 401/403, không tin role từ JWT, tạo 2/6 phương án, tự sinh/giữ ID,
  thứ tự phương án, sửa/thay/xóa phương án, ẩn/mở không xóa dữ liệu, bộ lọc kết hợp,
  dữ liệu rỗng/quá dài/null/trùng ID, số đáp án đúng và boolean sai kiểu.
- Đã giả lập lỗi CSDL khi thay phương án: cả nội dung câu hỏi lẫn các phương án cũ
  được hoàn tác. Khóa ngoại SQLite được bật và kiểm thử.
- Migration `0003`: upgrade/check/downgrade/upgrade đạt; nâng từ `0002` với tài khoản
  và môn học đã có giữ nguyên dữ liệu. CSDL phát triển đã nâng tới `0003 (head)`;
  `alembic check` không phát hiện chênh lệch metadata.
- Toàn bộ backend: **100 passed, 1 failed**. Lỗi duy nhất có sẵn trên main là
  `test_password_length_boundaries_are_accepted[128]`: kiểm thử yêu cầu 128 ký tự
  nhưng đăng ký hiện giới hạn 72 byte UTF-8 theo bcrypt. Không thay đổi xác thực trong US-06.
- Frontend: `node tests/questions.mjs` đạt **7 kiểm thử**; `registration.mjs` đạt 7;
  `domain.mjs` vẫn PASS. `node --check dist/app.js` và `node --check dist/api.js` đạt.
- Chromium với FastAPI/SQLite thật: đăng nhập admin vào thẳng Ngân hàng câu hỏi;
  tạo/sửa môn học; tạo/sửa/ẩn câu hỏi; giữ ID phương án; giới hạn thêm/xóa 2–6;
  bỏ đáp án đúng chặn gửi; chọn đáp án mới; lọc độ khó; reload giữ nội dung và trạng thái.
  Trang môn học/câu hỏi không gọi API đề thi chưa triển khai.
- Đã gửi danh sách không có đáp án đúng tới API qua trình duyệt: server trả 422,
  form hiển thị hướng dẫn tiếng Việt và cho phép thử lại. Không có lỗi JavaScript.
  Form được kiểm tra ở 390px không tràn ngang; danh sách được xem ở desktop 1440px.
- Ruff đạt cho model, schema, database, module câu hỏi, migration và kiểm thử liên quan.
  Ruff toàn repo còn **6 lỗi lint và 3 file cần format** có sẵn trên main
  (`admin.py`, `routes.py`, `test_registration.py`, `test_subjects.py`).

Các kiểm tra trình duyệt dùng CSDL và tài khoản admin tạm riêng, được dọn sau khi chạy.
Không thêm tài khoản mặc định, mật khẩu hoặc CSDL vào Git. API đề thi/xuất bản và quy tắc
khóa câu đã xuất bản ở backend chưa thuộc US-06; demo giữ quy tắc khóa có sẵn.

## Sửa lỗi tải trang và hướng dẫn admin cục bộ — T05F917

- Tái hiện nguyên nhân các ảnh lỗi trên Windows: một tài khoản tên `admin` được đăng ký
  với role `student`; frontend gọi cả đề thi/lịch sử trước khi dựng mọi trang sinh viên,
  nên các API chưa có gây `Not Found` cả ở hồ sơ và danh mục môn học.
- Đã tách collection cần tải theo route. Hồ sơ không tải collection khác; danh mục môn học
  dùng dữ liệu môn học thật. Trang đề thi/lịch sử/thống kê chưa có thông báo chưa sẵn sàng;
  tổng quan vẫn cho truy cập các chức năng hiện có, không trình bày số liệu thi giả.
- `node tests/page-data.mjs`: 15 kiểm thử đạt; adapter câu hỏi 8, đăng ký 7 và domain demo đạt.
  Kiểm tra cả backend đủ dữ liệu, collection chưa có, giữ lỗi mạng/401/403/500, và danh mục demo.
- `pytest tests/test_manage_admin.py tests/test_questions.py tests/test_migrations.py -q`:
  **51 kiểm thử đạt**. Lệnh cấp quyền chỉ chọn đúng email, giữ nguyên mật khẩu và tài khoản
  khác; hỗ trợ nhập tại terminal, chạy lại an toàn, xử lý email/CSDL sai và CSDL chưa migration.
- Chromium với FastAPI/SQLite thật: đăng ký tên `admin` vẫn là student; mở năm trang sinh viên
  không có lỗi `Not Found` toàn cục. Hồ sơ/môn học không gọi API đề thi/lịch sử. Giả lập 503
  vẫn hiển thị lỗi và thử lại được; 401 đưa về đăng nhập; student vẫn bị chặn trang/API quản trị.
- Chạy `app.manage_admin` qua stdin trên CSDL kiểm thử rồi đăng nhập lại: vào trang quản trị
  và tạo câu hỏi thật thành công (201). Tổng quan admin và thông báo các chức năng thi chưa có
  hiển thị được; không có lỗi JavaScript.
- Thêm `CAP_QUYEN_ADMIN.bat`; launcher backend dùng Python trong `.venv` để tránh phụ thuộc PATH.
  CLI được chạy thật trên Linux; các tệp `.bat` được kiểm tra nội dung, chưa chạy trên Windows
  trong môi trường tự động này.
