from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Exam, Question, QuestionOption, Subject, User
from app.security import create_access_token, password_hasher


def test_admin_can_create_and_edit_draft_exam(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'exams.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        admin = User(
            full_name="Admin",
            email="admin@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="admin",
        )
        subject = Subject(name="JavaScript", slug="javascript")
        session.add_all([admin, subject])
        session.commit()
        question = Question(
            subject_id=subject.id,
            text="Câu hỏi 1",
            options=[
                QuestionOption(text="A", is_correct=True, position=0),
                QuestionOption(text="B", is_correct=False, position=1),
            ],
        )
        session.add(question)
        session.commit()
        admin_id, subject_id, question_id = admin.id, subject.id, question.id
    headers = {"Authorization": f"Bearer {create_access_token(admin_id, 'admin')}"}
    payload = {
        "title": "Đề nháp",
        "description": "Ôn tập",
        "subject_id": subject_id,
        "difficulty": "medium",
        "duration_minutes": 30,
        "pass_score": 70,
        "max_attempts": 3,
    }
    try:
        with TestClient(app) as client:
            created = client.post("/admin/exams", headers=headers, json=payload)
            assert created.status_code == 201, created.text
            exam = created.json()
            assert exam["status"] == "draft"
            assert exam["questions"] == []
            exam_id = exam["id"]

            associated = client.put(
                f"/admin/exams/{exam_id}/questions",
                headers=headers,
                json={"questions": [{"question_id": question_id, "points": 2}]},
            )
            assert associated.status_code == 200, associated.text
            assert associated.json()["questions"] == [{"question_id": question_id, "points": 2.0}]

            edited = client.patch(
                f"/admin/exams/{exam_id}",
                headers=headers,
                json={**payload, "title": "Đề nháp đã sửa", "duration_minutes": 45},
            )
            assert edited.status_code == 200, edited.text
            assert edited.json()["title"] == "Đề nháp đã sửa"
            assert edited.json()["duration_minutes"] == 45
            assert client.get("/admin/exams", headers=headers).json()[0]["id"] == exam_id

            invalid = client.post(
                "/admin/exams",
                headers=headers,
                json={**payload, "duration_minutes": 0},
            )
            assert invalid.status_code == 422
            duplicate = client.put(
                f"/admin/exams/{exam_id}/questions",
                headers=headers,
                json={
                    "questions": [
                        {"question_id": question_id, "points": 1},
                        {"question_id": question_id, "points": 2},
                    ]
                },
            )
            assert duplicate.status_code == 422
            assert client.get("/admin/exams", headers={}).status_code == 401
    finally:
        app.state.engine.dispose()


def test_admin_publishes_exam_and_student_can_discover_it_without_answers(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'publish.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        admin = User(full_name="Admin", email="admin@example.com", password_hash="x", role="admin")
        student = User(full_name="Student", email="student@example.com", password_hash="x")
        subject = Subject(name="Python", slug="python")
        session.add_all([admin, student, subject])
        session.flush()
        question = Question(
            subject_id=subject.id,
            text="2 + 2?",
            options=[
                QuestionOption(text="4", is_correct=True, position=0),
                QuestionOption(text="5", is_correct=False, position=1),
            ],
        )
        exam = Exam(
            title="Python cơ bản",
            description="",
            subject_id=subject.id,
            difficulty="easy",
            duration_minutes=10,
            pass_score=70,
            max_attempts=2,
            status="draft",
            questions=[],
        )
        session.add_all([question, exam])
        session.commit()
        admin_id, student_id, exam_id, question_id = admin.id, student.id, exam.id, question.id
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_id, 'admin')}"}
    student_headers = {"Authorization": f"Bearer {create_access_token(student_id, 'student')}"}
    try:
        with TestClient(app) as client:
            assert (
                client.put(
                    f"/admin/exams/{exam_id}/questions",
                    headers=admin_headers,
                    json={"questions": [{"question_id": question_id, "points": 1}]},
                ).status_code
                == 200
            )
            assert (
                client.post(f"/admin/exams/{exam_id}/publish", headers=admin_headers).status_code
                == 200
            )
            visible = client.get("/exams", headers=student_headers)
            assert visible.status_code == 200
            assert visible.json()[0]["id"] == exam_id
            assert "is_correct" not in str(visible.json())
            assert (
                client.post(f"/admin/exams/{exam_id}/archive", headers=admin_headers).status_code
                == 200
            )
            assert client.get("/exams", headers=student_headers).json() == []
    finally:
        app.state.engine.dispose()
