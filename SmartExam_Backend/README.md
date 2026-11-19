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

## Phân quyền admin (`/admin/*`)

Mọi route thêm vào `admin_router` (`app/admin.py`) tự động yêu cầu quyền admin:

- Không có token, token sai hoặc hết hạn: **401** (từ `current_user`).
- Token hợp lệ nhưng tài khoản là `student`: **403**
  `{"detail": "Bạn không có quyền thực hiện thao tác này."}`.
- Tài khoản `admin`: được xử lý bình thường.

Role được đọc từ bảng `users` ở mỗi request, không dựa vào claim `role` trong token, nên thăng
hoặc hạ quyền có hiệu lực ngay. Route quản trị mới chỉ cần:

```python
from app.admin import admin_router


@admin_router.get("/subjects")
def list_subjects(): ...
```

Đăng ký luôn tạo `student`; tài khoản admin phải tạo tay trong CSDL, ví dụ
`UPDATE users SET role = 'admin' WHERE email = '...';`. Kiểm thử: `tests/test_admin_guard.py`.

`POST /auth/register` tạo tài khoản sinh viên từ họ tên, email và mật khẩu.
Backend băm mật khẩu bằng Argon2id, từ chối email đã tồn tại và gán quyền `student`.
Tài khoản được lưu bằng SQLAlchemy trong SQLite; Alembic quản lý migration bảng `users`.

## Câu hỏi, gán câu hỏi vào đề và bảo vệ đề đã xuất bản (US-07, US-09)

**Ngân hàng câu hỏi** (`/admin/questions`, chỉ admin): `GET` liệt kê, `POST` tạo, `PATCH /{id}`
sửa, `DELETE /{id}` xóa. Một câu có 2 đến 6 phương án và đúng một phương án đúng; `subject_id`
phải tồn tại; `difficulty` là `easy`, `medium` hoặc `hard`. Phương án chỉ được sửa cùng câu hỏi.

**Gán câu hỏi vào đề** (`PUT /admin/exams/{id}/questions`): body
`{"questions": [{"question_id": "...", "points": 2}, ...]}`. Mỗi lần gọi là **thay toàn bộ** danh sách
của đề.

- Thứ tự của mảng chính là thứ tự câu trong đề; muốn đổi thứ tự thì gửi lại mảng đã sắp xếp.
- `points` là số lớn hơn 0 và không quá 100, đặt riêng cho từng câu. Không nhận trường nào khác.
- Một câu hỏi chỉ được chọn một lần: trùng thì **422** `Câu hỏi trong đề không được trùng.`
- Câu hỏi phải có trong ngân hàng: không tồn tại thì **422** `Câu hỏi không tồn tại: <id>.`
- Chỉ đề `draft` mới sửa được danh sách, đề `published` hoặc `archived` trả **409**.
- Khi bị từ chối (422, 409), danh sách cũ của đề giữ nguyên.

**Bảo vệ câu hỏi đã xuất bản**: quy tắc dựa trên trạng thái đề chứa câu hỏi.

| Câu hỏi nằm trong | `PATCH` (kể cả đổi `is_active`) | `DELETE` |
|---|---|---|
| Không đề nào | Cho phép | Cho phép (204) |
| Chỉ đề `draft` hoặc `archived` | Cho phép | **409** (hãy ẩn bằng `is_active=false`) |
| Có ít nhất một đề `published` | **409** | **409** |

- 409 trả `{"detail": "Câu hỏi đang nằm trong đề thi đã xuất bản nên không thể sửa hoặc xóa. Hãy lưu trữ đề thi trước."}`.
- Muốn sửa câu đang ở đề đã xuất bản: lưu trữ đề (`archived`) rồi sửa. Đề xuất bản lại thì câu bị khóa lại.
- Logic nằm ở `app/question_lock.py` (đọc danh sách câu hỏi JSON của các đề `published`). Route nào
  sửa/xóa câu hỏi hoặc phương án cũng phải gọi `ensure_not_in_published_exam(db, question_id)`.
- Kiểm tra ở tầng ứng dụng: endpoint `publish` nên kiểm tra trong cùng transaction với việc đổi trạng thái.

## Lưu đáp án và tự chấm khi hết giờ (US-14, US-17)

**`PUT /attempts/{attempt_id}/answers/{question_id}`** (cần đăng nhập, chỉ chủ lượt thi) với body
`{"option_id": "..."}` lưu ngay đáp án vào CSDL và trả `{"question_id", "option_id"}`. Gọi lại với
phương án khác thì **đổi đáp án** (mỗi câu chỉ có một bản ghi trong `attempt_answers`).

| Tình huống | Kết quả |
|---|---|
| `now <= deadline_at`, lượt thi `in_progress` | 200, đáp án được lưu hoặc đổi |
| `now > deadline_at` | **409** `Đã hết giờ làm bài...`; server chuyển lượt thi sang `expired` và chốt điểm |
| Lượt thi đã `expired` | 409 (như trên), đáp án không đổi |
| Lượt thi đã `submitted` | 409 `Bài thi đã kết thúc...` |
| Lượt thi không tồn tại hoặc của người khác | 404 |
| Câu hỏi không thuộc đề | 404 |
| Phương án không thuộc câu hỏi | 422 |

- Giờ kiểm tra là giờ **server** (UTC), không tin đồng hồ máy khách. `now == deadline_at` vẫn hợp lệ.
- Khi chốt (`expire_if_due` trong `app/attempts.py`): `status = expired`, `submitted_at = deadline_at`,
  `score` theo thang 0-100 = tổng `points` các câu đúng / tổng `points` của đề, `correct_count`,
  `passed = score >= pass_score`. Câu chưa trả lời tính 0 điểm. Đáp án gửi sau hạn không được lưu.
- Việc chốt diễn ra khi lượt thi được truy cập sau hạn (lười biếng). Các endpoint khác
  (`GET /attempts/{id}`, `submit`, `result`, `/me/attempts`) nên gọi `expire_if_due`, và có thể gọi
  `expire_overdue_attempts(db)` từ một tác vụ định kỳ để chốt những lượt không ai mở lại.
- Câu hỏi của lượt thi lấy từ `exams.questions`; đề `published` không sửa được danh sách và câu hỏi
  trong đề `published` bị khóa (US-07), nên không cần chép snapshot.
- Migration `0005` thêm `attempts` và `attempt_answers`. Chưa có endpoint bắt đầu lượt thi
  (`POST /exams/{id}/attempts`); test tạo lượt thi trực tiếp trong CSDL.

## Cơ sở dữ liệu: 8 bảng (T05F928)

Alembic (`migrations/versions/0001`–`0007`) tạo đủ 8 bảng: `users`, `subjects`, `exams`, `questions`,
`question_options`, `exam_questions`, `attempts`, `attempt_answers`. Bảng `exam_questions`
(migration `0007`) lưu thứ tự và điểm từng câu trong đề, khóa chính `(exam_id, question_id)`;
migration tự chép dữ liệu từ cột JSON `exams.questions` (bỏ qua câu trùng, không tồn tại hoặc điểm
ngoài khoảng 0–100). Cột JSON vẫn là nguồn dữ liệu mà các API hiện tại đọc/ghi; chuyển API sang bảng
mới là việc của task sau. Kiểm tra: `python -m alembic upgrade head`, `python -m pytest tests/test_migrations.py`.

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
  admin.py             # admin_router + require_admin (401/403 cho /admin/*)
  question_lock.py     # Chặn sửa/xóa câu hỏi nằm trong đề đã xuất bản (409)
  attempts.py          # PUT /attempts/{id}/answers/{question_id}, chấm khi hết giờ
  security.py          # Argon2id
migrations/            # Alembic migration tạo bảng users
tests/                 # Kiểm thử API và migration
```
