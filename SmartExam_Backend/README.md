# SmartExam Backend — US-01 / T05F912

## Login and JWT

`POST /auth/login` accepts `{ "email": "student@example.com", "password": "..." }` and
returns `{ "access_token": "...", "token_type": "bearer" }`. Send the token as
`Authorization: Bearer <access_token>` to `GET /auth/me` to retrieve the current user's
public profile. Access tokens use HS256 and expire after 30 minutes. Invalid credentials,
expired tokens, and invalid tokens return HTTP 401.

Set `JWT_SECRET_KEY` to a stable, randomly generated secret of at least 32 bytes for any
deployment. If omitted, the app creates a process-local random key for local development;
tokens then stop working after a server restart. For example in PowerShell:

```powershell
$env:JWT_SECRET_KEY = "replace-with-a-long-random-secret-value"
```

`POST /auth/register` tạo tài khoản sinh viên từ họ tên, email và mật khẩu.
Backend băm mật khẩu bằng Argon2id, từ chối email đã tồn tại và gán quyền `student`.
Tài khoản được lưu bằng SQLAlchemy trong SQLite; Alembic quản lý migration bảng `users`.

## Chạy trên máy

Cần Python 3.11 trở lên và đầy đủ hai thư mục `SmartExam_Backend`, `SmartExam_Frontend`
trong repo. Từ thư mục repo:

```bash
cd SmartExam_Backend
python -m venv .venv
```

Kích hoạt môi trường bằng một lệnh phù hợp:

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- macOS/Linux: `source .venv/bin/activate`

Cài thư viện, tạo bảng và chạy server:

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Form đăng ký kết nối API thật: <http://127.0.0.1:8000/#/register>.
- Tài liệu API tương tác: <http://127.0.0.1:8000/docs>.
- CSDL mặc định: `smartexam.db` trong thư mục chạy lệnh.

Chạy migration trước lần đăng ký đầu tiên. Ứng dụng không tự tạo bảng khi khởi động.
`requirements.txt` khóa các phiên bản thư viện được dùng cho dự án.

Backend phục vụ giao diện hiện có trong `../SmartExam_Frontend/dist` và trả cấu hình
API cùng origin qua `/config.js`. Mở URL backend ở trên để kiểm tra tài khoản trong CSDL.
Chạy `node server.mjs` trong thư mục frontend vẫn dùng cấu hình demo ban đầu.

Phạm vi backend hiện tại là US-01. Đăng nhập, JWT, phân quyền truy cập API thi và
các nghiệp vụ làm bài thuộc những user story khác.

## Hợp đồng API

**`POST /auth/register`**, với header `Content-Type: application/json`:

```json
{
  "name": "Nguyễn Minh Anh",
  "email": "student@example.com",
  "password": "MatKhauCuaToi123!"
}
```

`name` khớp với form và hợp đồng frontend hiện có. Có thể dùng `full_name` thay cho
`name` để tương thích; chỉ gửi một trong hai tên trường.

Thành công trả **201 Created**:

```json
{
  "id": "ae8509a9-453c-4b0a-82cd-ec9891ff50b4",
  "name": "Nguyễn Minh Anh",
  "email": "student@example.com",
  "role": "student"
}
```

Email đã tồn tại trả **409 Conflict**:

```json
{"detail": "Email đã được đăng ký."}
```

Dữ liệu không hợp lệ, thiếu trường hoặc chứa trường ngoài hợp đồng trả **422**.
`detail` là mảng lỗi gồm `loc`, `msg`, `type`; phản hồi không chứa giá trị đầu vào
hoặc context có thể làm lộ mật khẩu.

Thử bằng curl:

```bash
curl -i http://127.0.0.1:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"name":"Nguyễn Minh Anh","email":"student@example.com","password":"MatKhauCuaToi123!"}'
```

## Quy tắc dữ liệu

Các giới hạn độ dài dưới đây là quyết định triển khai cho những điểm backlog chưa quy định:

- Họ tên: bỏ khoảng trắng đầu/cuối, từ 1 đến 120 ký tự, không rỗng sau khi xử lý.
- Email: bỏ khoảng trắng đầu/cuối, chuẩn hóa Unicode NFC rồi xử lý không phân biệt
  hoa/thường bằng `casefold()`, sau đó kiểm tra định dạng và giới hạn 254 ký tự.
  `Student@EXAMPLE.COM` và `student@example.com` được xem là cùng một tài khoản.
- Mật khẩu: từ 8 đến 128 ký tự, không chỉ gồm khoảng trắng. Giữ nguyên mật khẩu,
  kể cả khoảng trắng đầu/cuối; không tự cắt ngắn.
- Request chỉ nhận họ tên, email, mật khẩu. Gửi `role`, `is_admin`, `password_hash`
  hoặc trường khác bị từ chối. Server luôn gán `student`, CSDL cũng có mặc định này.
- Argon2id dùng 64 MiB bộ nhớ, 3 vòng, parallelism 4; thư viện sinh salt ngẫu nhiên
  16 byte cho từng mật khẩu. CSDL chỉ lưu hash, response chỉ trả thông tin công khai.
- CSDL có ràng buộc `UNIQUE(email)`. Yêu cầu đăng ký trùng đồng thời chỉ tạo được
  một tài khoản; transaction bị từ chối được rollback.

Cột lưu họ tên trong CSDL là `full_name`; tên trường công khai trong response là `name`.

## Cấu hình

### CSDL

Đặt cùng biến môi trường `DATABASE_URL` khi chạy Alembic và server.
Ví dụ với một tệp SQLite khác:

```bash
# macOS/Linux
export DATABASE_URL="sqlite:///./another-database.db"
```

```powershell
# Windows PowerShell
$env:DATABASE_URL = "sqlite:///./another-database.db"
```

Sau đó chạy lại `python -m alembic upgrade head` và lệnh uvicorn như phần khởi động.
Ứng dụng đọc biến môi trường của tiến trình; không tự nạp tệp `.env`.

### Frontend chạy riêng

Luồng tại cổng 8000 dùng cùng origin. Nếu chạy frontend riêng bằng Node tại cổng 5500,
đổi `SmartExam_Frontend/dist/config.js` thành:

```js
window.SMARTEXAM_CONFIG = { mode: 'api', baseUrl: 'http://127.0.0.1:8000' };
```

CORS mặc định cho phép `http://localhost:5500` và `http://127.0.0.1:5500`.
Để dùng origin khác, đặt `CORS_ORIGINS` trên tiến trình backend, ngăn cách bằng dấu phẩy:

```bash
export CORS_ORIGINS="http://localhost:5500,http://127.0.0.1:5500"
```

## Kiểm thử

Tại thư mục backend, với môi trường Python đã kích hoạt:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Kiểm thử dùng CSDL tạm riêng: tạo tài khoản và kiểm tra dữ liệu lưu, xác minh hash
và salt Argon2id, email trùng kể cả yêu cầu đồng thời, quyền `student`, kiểm tra
dữ liệu biên, bảo toàn mật khẩu Unicode/khoảng trắng, che dữ liệu nhạy cảm khỏi lỗi,
và migration lên/xuống.

Kiểm thử frontend tại thư mục `SmartExam_Frontend`:

```bash
node tests/domain.mjs
node tests/registration.mjs
```

## Cấu trúc

```text
app/
  main.py              # App factory, frontend, cấu hình, xử lý lỗi
  database.py          # Engine và session
  models.py            # Bảng users
  schemas.py           # Request/response công khai
  routes.py            # POST /auth/register
  security.py          # Argon2id
migrations/            # Alembic migration tạo bảng users
tests/                 # Kiểm thử API và migration
```
