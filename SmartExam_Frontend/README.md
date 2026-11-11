# SmartExam Frontend

## US-06 — Ngân hàng câu hỏi / T05F917

Đã kết nối API thật cho tạo, sửa, ẩn/mở câu hỏi, môn học, độ khó và 2–6 phương án
với đúng một đáp án đúng. Chạy migration và FastAPI theo `../SmartExam_Backend/README.md`,
rồi mở frontend do backend phục vụ và đăng nhập tài khoản admin. Admin được đưa tới
Ngân hàng câu hỏi; tạo môn học trước nếu danh mục trống. Trang này không phụ thuộc API đề thi.

Form hỗ trợ thêm/xóa phương án (giới hạn 2–6), chọn một đáp án bằng radio,
lời giải không bắt buộc, trạng thái hoạt động và lọc theo môn/độ khó/từ khóa.
Bỏ chọn “Câu hỏi đang hoạt động” để ẩn; dữ liệu vẫn tồn tại và có thể mở lại.
Lỗi API được hiển thị trong form để sửa và gửi lại.

`node server.mjs` vẫn dùng cấu hình `api-demo`: đăng nhập thật, nghiệp vụ câu hỏi/thi
mô phỏng trên trình duyệt. Dùng frontend cùng origin từ FastAPI để lưu câu hỏi thật.
Kiểm thử adapter: `node tests/questions.mjs`.

Các trang tải dữ liệu độc lập: hồ sơ dùng tài khoản đã đăng nhập, danh mục môn học
chỉ gọi danh mục; thiếu API đề thi/lịch sử không chặn các trang đó hoặc ngân hàng
câu hỏi. Tổng quan hiển thị các chức năng đang có; đề thi/lịch sử/thống kê thông báo
chưa sẵn sàng khi backend trả 404 cho collection tương ứng. Lỗi mạng, 401/403/5xx
vẫn được xử lý như lỗi, không chuyển sang dữ liệu demo. Kiểm thử: `node tests/page-data.mjs`.

Tài khoản có họ tên `admin` nhưng vai trò `student` vẫn là sinh viên. Chủ CSDL phát triển
có thể chạy `python -m app.manage_admin` trong backend hoặc mở `CAP_QUYEN_ADMIN.bat`,
nhập email đã đăng ký rồi đăng xuất/đăng nhập lại để vào Ngân hàng câu hỏi.

Toàn bộ FE1 + FE2 theo Product Backlog SmartExam: giao diện Sinh viên và Admin.
HTML, CSS, JavaScript ES modules thuần; không cần npm install, không dùng dịch vụ trả phí.

## Chạy trên máy

Cách nhanh trên Windows (đã cài Node.js 20+): giải nén rồi mở `CHAY_SMARTEXAM.bat`, truy cập http://localhost:5500 và giữ cửa sổ chạy mở. Hoặc chạy `node server.mjs`.

Cách dùng VS Code:

1. Giải nén vào một thư mục.
2. Mở thư mục bằng VS Code, cài extension Live Server nếu chưa có.
3. Nhấn chuột phải `dist/index.html` → Open with Live Server.
4. Hoặc nếu có Python: `python -m http.server 5500 --directory dist`, rồi mở http://localhost:5500.

Không mở file bằng double-click/file:// vì ES modules cần HTTP server.

`CHAY_SMARTEXAM.bat` starts the Backend (including database migrations) and the Frontend. The Frontend server may choose a free port from 5500 to 5510 if the default port is busy. `node server.mjs` starts only the Frontend; when using Live Server, start `SmartExam_Backend/CHAY_BACKEND.bat` in a separate window as well, because the default `api-demo` mode uses the Backend for login.

## Tài khoản demo

| Vai trò | Email | Mật khẩu demo |
|---|---|---|
| Sinh viên | student@smartexam.vn | demo123 |
| Admin | admin@smartexam.vn | admin123 |

Chế độ demo mô phỏng nghiệp vụ bằng localStorage. Tài khoản sinh viên mới đăng ký dùng chung mật khẩu demo123; mật khẩu nhập trên form chỉ được gửi trong chế độ API. Demo không phải hệ thống xác thực hay thi thật, không lưu mật khẩu người dùng.
Dữ liệu chỉ tồn tại trên trình duyệt/origin hiện tại. Muốn quay lại dữ liệu ban đầu, xóa dữ liệu trang trong DevTools → Application → Local storage. Không dùng thông tin cá nhân thật trong bản demo.

## Chức năng

| Backlog | Giao diện đã có |
|---|---|
| US-01 đến US-04 | Đăng ký, đăng nhập, điều hướng theo vai trò, hồ sơ, đăng xuất |
| US-05 | Thêm, sửa, ẩn/mở môn học; tự tạo slug |
| US-06, US-07 | Ngân hàng câu hỏi, 2–6 phương án, đúng 1 đáp án đúng, lời giải, khóa sửa câu đã xuất bản |
| US-08 đến US-10 | Đề nháp, môn học, thời lượng, điểm đạt, lượt thi; chọn/sắp xếp câu, trọng số; xuất bản/ẩn |
| US-11 đến US-15 | Danh sách đề, tìm/lọc, bắt đầu, trả lời, tự lưu, đồng hồ, khôi phục sau F5, đánh dấu câu |
| US-16 đến US-20 | Xác nhận nộp, tự nộp khi hết giờ lúc trang đang mở, kết quả, lịch sử, xem đáp án/lời giải |
| US-21, US-22 | Thống kê tổng lượt/điểm/tỷ lệ đạt, tìm theo từ khóa/môn/độ khó |
| TK-04 | CSS responsive từ 360px, menu di động, bảng cuộn ngang, label và điều khiển bàn phím |

## Kết nối Backend

Sửa `dist/config.js`:

```js
window.SMARTEXAM_CONFIG = {
  mode: 'api',
  baseUrl: 'http://localhost:8000'
};
```

Cấu hình CORS trên Backend cho origin đang chạy FE. Khi FE chạy HTTPS, API cũng phải HTTPS.
Không có fallback ngầm sang demo nếu API lỗi. HTTP 401 yêu cầu đăng nhập lại; HTTP 403/lỗi nghiệp vụ hiển thị thông báo.
JWT ở bộ nhớ JavaScript, không lưu localStorage/sessionStorage trong chế độ API. F5 sẽ cần đăng nhập lại; sau đó vào Lịch sử để tiếp tục lượt thi. Muốn giữ phiên xuyên F5 cần Backend bổ sung refresh token bằng cookie HttpOnly và cập nhật adapter.

US-01 đã có Backend thật tại `../SmartExam_Backend` (task **T05F912**). Chạy theo README ở thư mục đó,
rồi mở **http://127.0.0.1:8000/#/register** để đăng ký vào CSDL. Backend phục vụ chính frontend này
và tự cấu hình API cùng origin; không cần sửa `dist/config.js` cho cách chạy đó.
Khi chạy riêng bằng `node server.mjs`, chế độ demo mặc định vẫn hoạt động như trước.

Đọc `API_CONTRACT.md` để xem endpoint/DTO. Các backend ngoài đăng ký sinh viên thuộc user story khác
và chưa được triển khai trong phần US-01 này; danh sách endpoint là hợp đồng phối hợp BE1/BE2.

## Cấu trúc

- `dist/index.html`: khung trang, cấu hình metadata.
- `dist/styles.css`: toàn bộ giao diện, responsive, focus/label.
- `dist/app.js`: router, giao diện Sinh viên/Admin, biểu mẫu, thi và kết quả.
- `dist/api.js`: HTTP adapter và service demo; mọi thao tác dữ liệu đi qua `api`.
- `dist/config.js`: cấu hình demo/API.
- `tests/domain.mjs`: kiểm thử nghiệp vụ demo, chạy `node tests/domain.mjs` (Node 20+).
- `API_CONTRACT.md`: hợp đồng dữ liệu và điểm nối API.
- `TEST_REPORT.md`: phạm vi kiểm thử đã thực hiện và giới hạn.

## Phần Backend phải đảm nhiệm khi dùng thật

Đăng ký/băm mật khẩu, JWT, phân quyền và bảo vệ dữ liệu; không trả đáp án đúng trước khi nộp; lưu đáp án trên CSDL, deadline theo giờ server; chấm điểm bằng transaction/idempotency, tự chốt bài khi đóng trình duyệt; bảo vệ cấu trúc đề/câu hỏi đã xuất bản. Kiểm tra phía FE chỉ phục vụ trải nghiệm và không thay thế các kiểm tra này.

Không có tính năng AI gọi model vì backlog hiện tại không có user story/API AI. Không tự thêm tính năng hoặc chi phí API ngoài phạm vi.
