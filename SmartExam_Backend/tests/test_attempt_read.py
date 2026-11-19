from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Attempt, Exam, Question, QuestionOption, Subject, User
from app.security import create_access_token, password_hasher


def test_get_attempt_returns_safe_snapshot_and_only_owner_can_read(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'attempt-read.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as db:
        owner = User(
            full_name="Student",
            email="student@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="student",
        )
        stranger = User(
            full_name="Stranger",
            email="stranger@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="student",
        )
        subject = Subject(name="Math", slug="math")
        db.add_all([owner, stranger, subject])
        db.flush()
        question = Question(
            subject_id=subject.id,
            text="2 + 2?",
            options=[
                QuestionOption(text="4", is_correct=True, position=0),
                QuestionOption(text="5", is_correct=False, position=1),
            ],
            explanation="Basic addition.",
        )
        db.add(question)
        db.flush()
        exam = Exam(
            title="Arithmetic",
            description="",
            subject_id=subject.id,
            difficulty="easy",
            duration_minutes=25,
            pass_score=70,
            max_attempts=1,
            status="published",
            questions=[{"question_id": question.id, "points": 1}],
        )
        db.add(exam)
        db.flush()
        attempt = Attempt(
            exam_id=exam.id,
            user_id=owner.id,
            status="in_progress",
            started_at=datetime.now(UTC) - timedelta(minutes=30),
            deadline_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        db.add(attempt)
        db.commit()
        attempt_id, owner_id, stranger_id = attempt.id, owner.id, stranger.id

    owner_headers = {"Authorization": f"Bearer {create_access_token(owner_id, 'student')}"}
    stranger_headers = {"Authorization": f"Bearer {create_access_token(stranger_id, 'student')}"}
    try:
        with TestClient(app) as client:
            response = client.get(f"/attempts/{attempt_id}", headers=owner_headers)
            assert response.status_code == 200, response.text
            result = response.json()
            assert result["status"] == "expired"
            assert result["snapshot"]["questions"][0]["text"] == "2 + 2?"
            options = result["snapshot"]["questions"][0]["options"]
            assert all(set(option) == {"id", "text"} for option in options)
            assert "explanation" not in result["snapshot"]["questions"][0]
            assert client.get(f"/attempts/{attempt_id}").status_code == 401
            assert (
                client.get(f"/attempts/{attempt_id}", headers=stranger_headers).status_code == 404
            )
    finally:
        app.state.engine.dispose()
