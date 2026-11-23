"""Create repeatable demo data for the SmartExam defense.

Run from SmartExam_Backend after applying Alembic migrations:
    python seed_demo.py
"""

from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.database import get_database_url, make_engine
from app.models import Exam, Question, QuestionOption, Subject, User
from app.security import hash_password


DEMO_USERS = [
    {
        "full_name": "Quản trị viên Demo",
        "email": "admin@smartexam.local",
        "password": "DemoAdmin123!",
        "role": "admin",
    },
    {
        "full_name": "Sinh viên Demo",
        "email": "student@smartexam.local",
        "password": "DemoStudent123!",
        "role": "student",
    },
]

DEMO_SUBJECTS = [
    {"name": "Toán học", "slug": "toan-hoc"},
    {"name": "Tin học", "slug": "tin-hoc"},
]

DEMO_QUESTIONS = [
    {
        "subject_slug": "toan-hoc",
        "text": "Kết quả của 2 + 3 × 4 là bao nhiêu?",
        "explanation": "Thực hiện phép nhân trước: 3 × 4 = 12, sau đó 2 + 12 = 14.",
        "difficulty": "easy",
        "options": [
            ("20", False),
            ("14", True),
            ("24", False),
            ("9", False),
        ],
    },
    {
        "subject_slug": "toan-hoc",
        "text": "Nghiệm của phương trình 2x - 6 = 0 là gì?",
        "explanation": "2x = 6 nên x = 3.",
        "difficulty": "easy",
        "options": [
            ("x = 2", False),
            ("x = 3", True),
            ("x = 4", False),
            ("x = 6", False),
        ],
    },
    {
        "subject_slug": "toan-hoc",
        "text": "Diện tích hình chữ nhật có chiều dài 8 cm và chiều rộng 5 cm là bao nhiêu?",
        "explanation": "Diện tích bằng chiều dài nhân chiều rộng: 8 × 5 = 40 cm².",
        "difficulty": "medium",
        "options": [
            ("13 cm²", False),
            ("26 cm²", False),
            ("40 cm²", True),
            ("80 cm²", False),
        ],
    },
    {
        "subject_slug": "tin-hoc",
        "text": "HTML được sử dụng chủ yếu để làm gì?",
        "explanation": "HTML mô tả cấu trúc và nội dung của trang web.",
        "difficulty": "easy",
        "options": [
            ("Quản lý cơ sở dữ liệu", False),
            ("Tạo cấu trúc nội dung trang web", True),
            ("Biên dịch hệ điều hành", False),
            ("Thiết kế mạng máy tính", False),
        ],
    },
    {
        "subject_slug": "tin-hoc",
        "text": "Trong Python, kiểu dữ liệu nào biểu diễn giá trị đúng hoặc sai?",
        "explanation": "Kiểu bool có hai giá trị True và False.",
        "difficulty": "easy",
        "options": [
            ("str", False),
            ("int", False),
            ("bool", True),
            ("list", False),
        ],
    },
    {
        "subject_slug": "tin-hoc",
        "text": "Lệnh nào dùng để hiển thị nội dung ra màn hình trong Python?",
        "explanation": "Hàm print() xuất nội dung ra màn hình.",
        "difficulty": "easy",
        "options": [
            ("input()", False),
            ("display()", False),
            ("print()", True),
            ("writeLine()", False),
        ],
    },
]


def ensure_schema(engine) -> None:
    required_tables = {"users", "subjects", "exams", "questions", "question_options"}
    existing_tables = set(inspect(engine).get_table_names())
    missing_tables = required_tables - existing_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(
            f"Database chưa có các bảng: {missing}. "
            "Hãy chạy 'python -m alembic upgrade head' trước."
        )


def seed_users(db: Session) -> None:
    for data in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == data["email"]))
        if user is None:
            user = User(
                full_name=data["full_name"],
                email=data["email"],
                password_hash=hash_password(data["password"]),
                role=data["role"],
            )
            db.add(user)
            print(f"Đã tạo tài khoản {data['role']}: {data['email']}")
        else:
            # Giữ mật khẩu hiện tại, nhưng đảm bảo role của tài khoản demo đúng mục đích.
            user.role = data["role"]
            print(f"Tài khoản đã tồn tại, giữ mật khẩu: {data['email']}")


def seed_subjects(db: Session) -> dict[str, Subject]:
    subjects: dict[str, Subject] = {}
    for data in DEMO_SUBJECTS:
        subject = db.scalar(select(Subject).where(Subject.slug == data["slug"]))
        if subject is None:
            subject = Subject(name=data["name"], slug=data["slug"], is_active=True)
            db.add(subject)
            db.flush()
            print(f"Đã tạo môn học: {data['name']}")
        subjects[data["slug"]] = subject
    return subjects


def seed_questions(db: Session, subjects: dict[str, Subject]) -> dict[str, Question]:
    questions: dict[str, Question] = {}
    for data in DEMO_QUESTIONS:
        question = db.scalar(select(Question).where(Question.text == data["text"]))
        if question is None:
            question = Question(
                subject_id=subjects[data["subject_slug"]].id,
                text=data["text"],
                explanation=data["explanation"],
                difficulty=data["difficulty"],
                is_active=True,
                options=[
                    QuestionOption(text=option_text, is_correct=is_correct, position=index)
                    for index, (option_text, is_correct) in enumerate(data["options"])
                ],
            )
            db.add(question)
            db.flush()
            print(f"Đã tạo câu hỏi: {data['text'][:55]}...")
        questions[data["text"]] = question
    return questions


def seed_exams(
    db: Session,
    subjects: dict[str, Subject],
    questions: dict[str, Question],
) -> None:
    exam_definitions = [
        {
            "title": "Đề Demo Toán học",
            "description": "Đề thi mẫu môn Toán học dùng cho buổi bảo vệ SmartExam.",
            "subject_slug": "toan-hoc",
            "question_texts": [
                "Kết quả của 2 + 3 × 4 là bao nhiêu?",
                "Nghiệm của phương trình 2x - 6 = 0 là gì?",
                "Diện tích hình chữ nhật có chiều dài 8 cm và chiều rộng 5 cm là bao nhiêu?",
            ],
            "difficulty": "easy",
            "status": "published",
        },
        {
            "title": "Đề Demo Tin học",
            "description": "Đề thi mẫu môn Tin học dùng cho buổi bảo vệ SmartExam.",
            "subject_slug": "tin-hoc",
            "question_texts": [
                "HTML được sử dụng chủ yếu để làm gì?",
                "Trong Python, kiểu dữ liệu nào biểu diễn giá trị đúng hoặc sai?",
                "Lệnh nào dùng để hiển thị nội dung ra màn hình trong Python?",
            ],
            "difficulty": "easy",
            "status": "draft",
        },
    ]

    for data in exam_definitions:
        exam_questions = [
            {"question_id": questions[text].id, "points": 10.0}
            for text in data["question_texts"]
        ]
        exam = db.scalar(select(Exam).where(Exam.title == data["title"]))
        if exam is None:
            exam = Exam(
                title=data["title"],
                description=data["description"],
                subject_id=subjects[data["subject_slug"]].id,
                difficulty=data["difficulty"],
                duration_minutes=30,
                pass_score=60,
                max_attempts=3,
                status=data["status"],
                questions=exam_questions,
            )
            db.add(exam)
            print(f"Đã tạo đề thi: {data['title']}")
        else:
            exam.description = data["description"]
            exam.subject_id = subjects[data["subject_slug"]].id
            exam.difficulty = data["difficulty"]
            exam.duration_minutes = 30
            exam.pass_score = 60
            exam.max_attempts = 3
            exam.status = data["status"]
            exam.questions = exam_questions
            print(f"Đã cập nhật dữ liệu đề thi: {data['title']}")


def main() -> None:
    engine = make_engine(get_database_url())
    try:
        ensure_schema(engine)
        with Session(engine) as db:
            try:
                seed_users(db)
                subjects = seed_subjects(db)
                questions = seed_questions(db, subjects)
                seed_exams(db, subjects, questions)
                db.commit()
            except Exception:
                db.rollback()
                raise
    finally:
        engine.dispose()

    print("\nSeed dữ liệu Demo hoàn tất.")
    print("Admin:   admin@smartexam.local / DemoAdmin123!")
    print("Student: student@smartexam.local / DemoStudent123!")
    print("Đề Toán học: Published | Đề Tin học: Draft")


if __name__ == "__main__":
    main()
