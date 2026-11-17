from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Attempt, Exam, Question, QuestionOption, Subject, User
from app.security import create_access_token, password_hasher


def create_exam(db, subject_id, *, max_attempts=2, title="Algebra"):
    question = Question(
        subject_id=subject_id,
        text="2 + 2?",
        options=[
            QuestionOption(text="4", is_correct=True, position=0),
            QuestionOption(text="5", is_correct=False, position=1),
        ],
    )
    db.add(question)
    db.flush()
    exam = Exam(
        title=title,
        description="Basic arithmetic",
        subject_id=subject_id,
        difficulty="easy",
        duration_minutes=25,
        pass_score=70,
        max_attempts=max_attempts,
        status="published",
        questions=[{"question_id": question.id, "points": 2}],
    )
    db.add(exam)
    db.flush()
    return exam


def test_start_attempt_creates_deadline_and_safe_question_snapshot(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'attempt-start.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as db:
        student = User(
            full_name="Student",
            email="student@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="student",
        )
        subject = Subject(name="Math", slug="math")
        db.add_all([student, subject])
        db.flush()
        exam = create_exam(db, subject.id)
        student_id, exam_id = student.id, exam.id
        db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(student_id, 'student')}"}
    try:
        with TestClient(app) as client:
            response = client.post(f"/exams/{exam_id}/attempts", headers=headers)
            assert response.status_code == 201, response.text
            attempt = response.json()
            assert attempt["status"] == "in_progress"
            assert attempt["exam_id"] == exam_id
            assert attempt["started_at"] < attempt["deadline_at"]
            assert attempt["snapshot"]["duration_minutes"] == 25
            question = attempt["snapshot"]["questions"][0]
            assert question["text"] == "2 + 2?"
            assert question["points"] == 2
            assert "explanation" not in question
            assert all("is_correct" not in option for option in question["options"])

            resumed = client.post(f"/exams/{exam_id}/attempts", headers=headers)
            assert resumed.status_code == 201
            assert resumed.json()["id"] == attempt["id"]
    finally:
        app.state.engine.dispose()


def test_start_attempt_enforces_student_role_remaining_tries_and_single_active(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'attempt-rules.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as db:
        student = User(
            full_name="Student",
            email="student@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="student",
        )
        admin = User(
            full_name="Admin",
            email="admin@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="admin",
        )
        subject = Subject(name="Math", slug="math")
        db.add_all([student, admin, subject])
        db.flush()
        first = create_exam(db, subject.id, max_attempts=1, title="First")
        second = create_exam(db, subject.id, title="Second")
        student_id, admin_id, first_id, second_id = (
            student.id,
            admin.id,
            first.id,
            second.id,
        )
        db.commit()
    student_headers = {"Authorization": f"Bearer {create_access_token(student_id, 'student')}"}
    admin_headers = {"Authorization": f"Bearer {create_access_token(admin_id, 'admin')}"}
    try:
        with TestClient(app) as client:
            assert client.post(f"/exams/{first_id}/attempts").status_code == 401
            assert (
                client.post(f"/exams/{first_id}/attempts", headers=admin_headers).status_code == 403
            )
            started = client.post(f"/exams/{first_id}/attempts", headers=student_headers)
            assert started.status_code == 201
            conflict = client.post(f"/exams/{second_id}/attempts", headers=student_headers)
            assert conflict.status_code == 409

            with app.state.session_factory() as db:
                db.get(Attempt, started.json()["id"]).status = "submitted"
                db.commit()
            exhausted = client.post(f"/exams/{first_id}/attempts", headers=student_headers)
            assert exhausted.status_code == 409
    finally:
        app.state.engine.dispose()
