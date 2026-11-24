# SmartExam

Triển khai **US-01 — Đăng ký tài khoản Sinh viên**, mã task **T05F912**:
nhập họ tên, email, mật khẩu; băm mật khẩu bằng Argon2id; chặn email trùng;
server gán quyền `student` qua `POST /auth/register`.

- `SmartExam_Backend/`: FastAPI, SQLAlchemy, Alembic, SQLite và kiểm thử API.
- `SmartExam_Frontend/`: giao diện JavaScript hiện có, hỗ trợ API thật và chế độ demo.

## US-06 — CRUD Câu hỏi & Phương án (T05F917)

Admin có thể tạo, sửa, ẩn/mở câu hỏi theo môn học và độ khó. Backend lưu câu hỏi,
lời giải và các phương án theo thứ tự; kiểm tra **2–6 phương án và đúng một đáp án đúng**.
API: `GET/POST /admin/questions`, `PATCH /admin/questions/{id}`.

Chạy migration và backend theo hướng dẫn bên dưới, sau đó đăng nhập bằng tài khoản
admin. Trong chế độ API cùng origin, admin được đưa tới **Ngân hàng câu hỏi**;
tạo môn học trước nếu danh mục còn trống. Đăng ký công khai chỉ tạo tài khoản student;
cách cấp quyền admin có trong [README backend](SmartExam_Backend/README.md#phân-quyền-admin-admin).

Xem [hợp đồng US-06](SmartExam_Frontend/API_CONTRACT.md#us-06-đã-triển-khai--t05f917)
và [báo cáo kiểm thử](SmartExam_Frontend/TEST_REPORT.md#cập-nhật-us-06--t05f917).

## Chạy đăng ký với CSDL thật

Cần Python 3.11 trở lên. Từ thư mục repo:

```bash
cd SmartExam_Backend
python -m venv .venv
```

Kích hoạt môi trường:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Sau đó chạy:

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở **<http://127.0.0.1:8000/#/register>** để đăng ký.
Backend phục vụ luôn giao diện từ `SmartExam_Frontend/dist` và cấu hình gọi API cùng origin.
Tài khoản được lưu trong `SmartExam_Backend/smartexam.db`; Swagger tại
<http://127.0.0.1:8000/docs>.

Backend trong phần việc này thực hiện US-01. API đăng nhập/JWT và các nghiệp vụ thi
thuộc các user story tiếp theo. Xem [hướng dẫn backend](SmartExam_Backend/README.md)
để biết hợp đồng API, cấu hình và kiểm thử.

## Chạy demo giao diện

Cần Node.js 20 trở lên. Từ thư mục repo:

```bash
cd SmartExam_Frontend
node server.mjs
```

Mở <http://localhost:5500>. Chế độ demo dùng dữ liệu mô phỏng trong trình duyệt;
đăng ký tại đây không tạo tài khoản trong CSDL backend.
Xem [hướng dẫn frontend](SmartExam_Frontend/README.md) để thử các giao diện Sinh viên/Admin.

## Kiểm thử

```bash
# Trong SmartExam_Backend, với môi trường Python đã kích hoạt:
python -m pytest -q
python -m ruff check .
python -m ruff format --check .

# Trong SmartExam_Frontend:
node tests/domain.mjs
node tests/registration.mjs
node tests/questions.mjs
```
