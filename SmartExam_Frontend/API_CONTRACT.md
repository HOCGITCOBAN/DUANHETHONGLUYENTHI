# Hợp đồng API đề xuất

Tất cả ID là chuỗi; response JSON, không bọc `data`. Danh sách trả mảng JSON trực tiếp.
Lỗi nghiệp vụ trả `{ "detail": "Thông báo tiếng Việt" }`; riêng lỗi kiểm tra dữ liệu
đăng ký (HTTP 422) trả `{ "detail": [{"loc": [], "msg": "...", "type": "..."}] }`.
Các mutation có thể trả JSON hoặc HTTP 204, riêng tạo đề phải trả `{id}`.
Auth dùng JSON, không phải form-urlencoded.

## Kiểu dữ liệu

```ts
type User = { id: string; name: string; email: string; role: 'admin'|'student' };
type Subject = { id: string; name: string; slug: string; is_active: boolean };
type Option = { id: string; text: string; is_correct?: boolean };
type Question = {
  id: string; subject_id: string; text: string; options: Option[];
  explanation?: string; difficulty:'easy'|'medium'|'hard'; is_active:boolean;
};
type Exam = {
  id:string; title:string; description:string; subject_id:string;
  duration_minutes:number; pass_score:number; max_attempts:number;
  difficulty:'easy'|'medium'|'hard'; status:'draft'|'published'|'archived';
  questions:{question_id:string;points:number}[];
  question_count?:number; used_attempts?:number;
};
type Attempt = {
  id:string; exam_id:string; user_id:string;
  started_at:string; deadline_at:number|string; // epoch milliseconds hoặc ISO 8601 có timezone
  status:'in_progress'|'submitted'|'expired';
  answers:Record<string,string>; // question_id -> option_id
  snapshot:Omit<Exam,'questions'> & {questions:(Question & {points:number})[]};
  score?:number; correct_count?:number; passed?:boolean; submitted_at?:string;
};
```

Trước khi nộp: snapshot câu hỏi không có `is_correct`/`explanation`. Sau khi nộp: result trả đủ hai trường để hiển thị lời giải. Phần `questions` của danh sách đề chỉ chứa question_id và points, không chứa đáp án. Có thể sửa adapter nếu BE dùng `content` thay vì `text`, hoặc DTO kết quả khác.

## Endpoint

| Method | URL | Request / Response |
|---|---|---|
| POST | /auth/register | `{name,email,password}` → HTTP 201 `{id,name,email,role:'student'}`; email trùng trả 409 |
| POST | /auth/login | `{email,password}` → `{access_token,token_type:'bearer'}` |
| GET | /auth/me | User |
| GET | /subjects | Subject[] chỉ môn mở |
| GET | /admin/subjects | Subject[] toàn bộ |
| POST/PATCH | /admin/subjects[/id] | `{name,slug,is_active}` |
| GET | /admin/questions | Question[] toàn bộ, có đáp án |
| POST/PATCH | /admin/questions[/id] | `{subject_id,text,options,explanation,difficulty,is_active}` |
| GET | /exams | Exam[] chỉ published/môn mở |
| GET | /admin/exams | Exam[] toàn bộ, có thứ tự questions |
| POST/PATCH | /admin/exams[/id] | Metadata của Exam, không có questions; POST trả `{id}` |
| PUT | /admin/exams/id/questions | `{questions:[{question_id,points}]}` theo thứ tự |
| POST | /admin/exams/id/publish | Không body |
| POST | /admin/exams/id/archive | Không body |
| POST | /exams/id/attempts | Không body → Attempt |
| GET | /attempts/id | Attempt, đáp án đã lưu và deadline gốc |
| PUT | /attempts/id/answers/question_id | `{option_id}` |
| POST | /attempts/id/submit | Không body, idempotent |
| GET | /attempts/id/result | Attempt đã chấm với snapshot chứa lời giải |
| GET | /me/attempts | `{id,exam_id,title,status,started_at,score?,passed?}[]`, mới nhất trước |
| GET | /admin/exams/id/stats | `{total_attempts,completed,average_score,pass_rate}` |

`average_score` và `pass_rate` là số hoặc null nếu không có lượt hoàn thành. `pass_rate` dùng thang 0–100. Điểm cũng dùng thang 0–100. Đề đã xuất bản và đề lưu trữ không sửa được; ẩn câu hỏi bằng `is_active:false` thay vì xóa cứng.

### US-01 đã triển khai — T05F912

Backend tại `../SmartExam_Backend` nhận họ tên `name` (hoặc alias tương thích `full_name`,
không gửi đồng thời cả hai). Họ tên sau trim dài 1–120 ký tự, email hợp lệ tối đa 254 ký tự,
mật khẩu 8–128 ký tự và không chỉ chứa khoảng trắng. Mật khẩu được giữ nguyên khi băm bằng Argon2id.
Email được trim, chuẩn hóa Unicode NFC trước khi xử lý hoa/thường và có ràng buộc UNIQUE
trong CSDL để chặn cả những địa chỉ có cách biểu diễn Unicode tương đương.
Client gửi trường ngoài hợp đồng, kể cả `role`, bị từ chối bằng 422; server luôn gán `student`.
Lỗi validation trả `{detail:[{loc,msg,type}]}` và không chứa dữ liệu đầu vào hay mật khẩu.
Các endpoint khác trong bảng là hợp đồng cho những user story tiếp theo.

Adapter gửi Authorization: Bearer ở mọi request khi có JWT. Với PATCH hiện tại có thể gửi cả `id`; Backend có thể bỏ qua hoặc loại bỏ tại api.js nếu schema forbid_extra. Tạo/sửa metadata đề và gán câu là hai request: BE cần cho phép retry PUT an toàn, frontend hiển thị lỗi nếu một bước thất bại. Nên gộp transaction ở BE hoặc trả mã đề đã tạo trong lỗi để tránh tạo lại đề khi retry sau lỗi mạng.

Luồng hết giờ: FE gọi submit khi countdown hết; server phải quyết định expired bằng giờ server và tự chốt cả khi client không còn mở. Chưa có endpoint thời gian server nên đồng hồ FE dựa vào đồng hồ máy khách; BE phải luôn xác thực deadline. Muốn đồng bộ chính xác hơn, trả thêm server_now và tính offset ở adapter.
