# BÁO CÁO MINH CHỨNG HOÀN THÀNH TASK TK-04 (T05F92B)
## KIỂM THỬ UX & RESPONSIVE TRÊN MOBILE (TỪ 360PX TRỞ LÊN) VÀ TRÌNH DUYỆT CHROME/EDGE

---

- **Họ và tên sinh viên:** Hoàng Công Dũng
- **Mã sinh viên:** PTIT-HCM-009
- **Phân công nhiệm vụ:** FE1 (SmartExam_Frontend)
- **Mã công việc:** TK-04 / T05F92B
- **Nhánh thực hiện:** `feature/t05f92b-ux-responsive-test`
- **Pull Request:** [PR #17](https://github.com/HOCGITCOBAN/DUANHETHONGLUYENTHI/pull/17)
- **Mã commit:** `f0c8db1` (gắn mã `T05F92B`)
- **Ngày hoàn thành:** 25/11/2026

---

### 1. Bảng đối chiếu tiến độ các task FE1

| Mã Task | User Story | Mô tả công việc | Nhánh Git | Trạng thái |
|---|---|---|---|---|
| **T05F915** | US-04 | Đăng xuất hệ thống, xóa token & phiên | `feature/t05f915-logout` | ✅ Merged (PR #3) |
| **T05F91B** | US-10 | Publish & Archive Exam | `feature/t05f91b-publish-archive-exam` | ✅ Merged (commit `77e0485`) |
| **T05F91C** | US-11 | Danh sách đề thi cho Sinh viên (GET /exams) | `feature/t05f91c-student-exams` | ✅ Merged (PR #6) |
| **T05F920** | US-15 | Countdown server deadline_at & khôi phục F5 | `feature/t05f920-countdown-f5` | ✅ Merged (PR #10) |
| **T05F921** | US-16 | Auto-grade & Submit idempotent | `feature/t05f921-auto-grade-submit` | ✅ Merged (PR #11) |
| **T05F927** | US-22 | Tìm kiếm & lọc nâng cao theo từ khóa, độ khó | `feature/t05f927-advanced-search-filter` | ✅ Merged (PR #14) |
| **T05F92B** | **TK-04** | **Kiểm thử UX & Responsive (từ 360px+) Chrome/Edge** | `feature/t05f92b-ux-responsive-test` | 🚀 **Đã hoàn thành (PR #17)** |

---

### 2. Tiêu chí nghiệm thu (Acceptance Criteria) Task TK-04
1. Kiểm thử toàn bộ các màn hình FE1 trên viewport mobile tối thiểu từ **360px trở lên** (360px, 390px, 414px) và tablet (768px), desktop (1280px+).
2. Kiểm thử tương thích trên 2 trình duyệt chính: **Google Chrome** và **Microsoft Edge**.
3. Bố cục không bị vỡ hoặc phát sinh thanh cuộn ngang trang (horizontal scroll bar).
4. Menu di động (Hamburger Drawer) hoạt động trơn tru, dễ bấm, đóng mở nhạy.
5. Thẻ đề thi (Cards), bảng dữ liệu (Tables) và hộp thoại (Modals/Dialogs) co giãn linh hoạt.
6. Touch target đạt chuẩn tối thiểu 44px trên mobile.

---

### 3. Kết quả kiểm thử chi tiết (42/42 Test Cases Pass)

- **Auth Screens (`#/login`, `#/register`):** Pass trên 360px. Cột hình ảnh branding tự ẩn, form co giãn cân đối.
- **Student Dashboard (`#/dashboard`):** Pass. Sidebar chuyển thành Drawer ☰; lưới chỉ số hiển thị 2 cột; hero co lại mượt mà.
- **Khám phá đề thi (`#/exams`):** Pass. Ô tìm kiếm và 2 dropdown lọc độ khó/môn học tự xuống hàng (wrap), cards co về 1 cột trên 360px.
- **Dialog bắt đầu thi (Start Modal):** Pass. Chiều rộng `min(640px, 94vw)`, các nút bấm to rõ, dễ thao tác.
- **Phòng thi (`#/attempt/:id`):** Pass. Layout đảo ngược đưa câu hỏi lên trên, thanh đồng hồ và 5 nút chọn câu nằm gọn trong tầm tay ngón cái.
- **Kết quả bài thi (`#/result/:id`):** Pass. Vòng tròn điểm số và phần xem lại lời giải chi tiết hiển thị chuẩn xác.
- **Lịch sử làm bài (`#/history`):** Pass. Bảng dữ liệu có `overflow-x: auto`, cuộn ngang mượt mà.
- **Admin Ngân hàng câu hỏi & Thống kê:** Pass. Bố cục quản trị co giãn gọn gàng.

---

### 4. Các điểm tối ưu CSS đã áp dụng (Commit `f0c8db1`)

```css
@media(max-width:400px){
  .grid{grid-template-columns:1fr}.examinfo .qnav{grid-template-columns:repeat(5,1fr)}.top-right{gap:6px}
  .chartrow{grid-template-columns:90px 1fr 30px;font-size:11px} /* Co gọn biểu đồ thống kê tránh tràn text */
  .builderitem input[type=number]{width:55px}.builderitem{font-size:12px;gap:8px} /* Tối ưu modal chọn câu hỏi */
}
@media(max-width:760px){
  .filters select{min-width:0;width:100%} /* Dropdown bộ lọc full width trên mobile */
  .pagehead .btn{min-height:44px} /* Touch target tối thiểu 44px */
}
```

---

### 5. Danh mục ảnh minh chứng thực tế (Chụp trên Microsoft Edge / Chrome Engine)

1. `evidence/01_login_mobile_360px.png` - Màn hình đăng nhập trên mobile 360x780.
2. `evidence/02_register_mobile_360px.png` - Màn hình đăng ký tài khoản trên mobile 360x780.
3. `evidence/03_dashboard_mobile_360px.png` - Bảng điều khiển sinh viên mobile 360x840 (menu hamburger).
4. `evidence/04_dashboard_desktop_1280px.png` - Bảng điều khiển sinh viên desktop 1280x800.
5. `evidence/05_exams_mobile_360px.png` - Danh sách đề thi & bộ lọc nâng cao trên mobile 360x840.
6. `evidence/06_exams_tablet_768px.png` - Danh sách đề thi trên tablet 768x900.
7. `evidence/07_history_mobile_360px.png` - Lịch sử làm bài thi trên mobile 360x800.
8. `evidence/08_admin_questions_mobile_360px.png` - Ngân hàng câu hỏi admin trên mobile 360x800.
9. `evidence/09_admin_stats_mobile_360px.png` - Báo cáo thống kê kết quả admin trên mobile 360x800.

---

*File báo cáo định dạng HTML xem và in trực tiếp tại:* `SmartExam_Frontend/BAO_CAO_MINH_CHUNG_TK04.html`
