from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import Base
from app.main import create_app
from app.models import Attempt, AttemptAnswer, Exam, Subject, User
from app.security import create_access_token, password_hasher

PASSWORD_HASH = password_hasher.hash("Secret password!")
START = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)
DEADLINE = START + timedelta(minutes=30)


@pytest.fixture
def clock(monkeypatch):
    state = {"now": START + timedelta(minutes=5)}
    monkeypatch.setattr("app.attempts.utc_now", lambda: state["now"])
    return state


@pytest.fixture
def env(tmp_path, clock):
    app = create_app(f"sqlite:///{tmp_path / 'submit.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        users = {
            name: User(
                full_name=name.title(),
                email=f"{name}@example.com",
                password_hash=PASSWORD_HASH,
                role="admin" if name == "admin" else "student",
            )
            for name in ("admin", "alice", "bob")
        }
        subject = Subject(name="Python", slug="python")
        session.add_all([*users.values(), subject])
        session.commit()
        ids = {name: user.id for name, user in users.items()}
        subject_id = subject.id
    with TestClient(app) as client:

        def headers(name):
            role = "admin" if name == "admin" else "student"
            return {"Authorization": f"Bearer {create_access_token(ids[name], role)}"}

        yield SimpleNamespace(
            app=app,
            client=client,
            clock=clock,
            subject_id=subject_id,
            ids=ids,
            admin=headers("admin"),
            alice=headers("alice"),
            bob=headers("bob"),
        )
    app.state.engine.dispose()


def create_question(env, text):
    response = env.client.post(
        "/admin/questions",
        headers=env.admin,
        json={
            "subject_id": env.subject_id,
            "text": text,
            "options": [
                {"text": "Sai", "is_correct": False},
                {"text": "Đúng", "is_correct": True},
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def option_id(question, correct):
    return next(o["id"] for o in question["options"] if o["is_correct"] is correct)


def make_attempt(env, points, owner="alice", pass_score=60):
    questions = [create_question(env, f"Câu {index}") for index in range(len(points))]
    with env.app.state.session_factory() as session:
        exam = Exam(
            title="Đề kiểm tra",
            description="",
            subject_id=env.subject_id,
            difficulty="medium",
            duration_minutes=30,
            pass_score=pass_score,
            max_attempts=3,
            status="published",
            questions=[
                {"question_id": question["id"], "points": value}
                for question, value in zip(questions, points, strict=True)
            ],
        )
        session.add(exam)
        session.commit()
        exam_id = exam.id

        attempt = Attempt(
            exam_id=exam_id,
            user_id=env.ids[owner],
            status="in_progress",
            started_at=START,
            deadline_at=DEADLINE,
        )
        session.add(attempt)
        session.commit()
        return attempt.id, questions


def test_submit_success_and_grading(env):
    """Nộp bài thành công: tính điểm đúng theo công thức 100 * (Điểm đúng / Tổng điểm)."""
    attempt_id, questions = make_attempt(env, [2, 3], pass_score=60)
    # Alice trả lời đúng câu 1 (2 điểm), bỏ trống câu 2
    env.client.put(
        f"/attempts/{attempt_id}/answers/{questions[0]['id']}",
        headers=env.alice,
        json={"option_id": option_id(questions[0], True)},
    )
    response = env.client.post(f"/attempts/{attempt_id}/submit", headers=env.alice)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "submitted"
    assert data["score"] == 40.0  # 100 * 2 / (2 + 3) = 40.0
    assert data["correct_count"] == 1
    assert data["passed"] is False  # 40 < 60
    assert data["submitted_at"] is not None


def test_submit_idempotent_no_duplicate_scoring(env):
    """Tính Idempotent: gọi submit nhiều lần không đổi điểm và không nhân đôi điểm."""
    attempt_id, questions = make_attempt(env, [5], pass_score=50)
    env.client.put(
        f"/attempts/{attempt_id}/answers/{questions[0]['id']}",
        headers=env.alice,
        json={"option_id": option_id(questions[0], True)},
    )
    # Lần 1
    res1 = env.client.post(f"/attempts/{attempt_id}/submit", headers=env.alice)
    assert res1.status_code == 200
    assert res1.json()["score"] == 100.0

    # Lần 2 (submit lại)
    res2 = env.client.post(f"/attempts/{attempt_id}/submit", headers=env.alice)
    assert res2.status_code == 200
    assert res2.json()["score"] == 100.0
    assert res2.json()["status"] == "submitted"


def test_submit_locks_subsequent_answers(env):
    """Khóa bài: không thể cập nhật đáp án sau khi đã submit."""
    attempt_id, questions = make_attempt(env, [1])
    env.client.post(f"/attempts/{attempt_id}/submit", headers=env.alice)

    # Cố gắng lưu đáp án sau khi nộp
    res = env.client.put(
        f"/attempts/{attempt_id}/answers/{questions[0]['id']}",
        headers=env.alice,
        json={"option_id": option_id(questions[0], True)},
    )
    assert res.status_code == 409


def test_submit_forbidden_for_other_user(env):
    """Không thể nộp bài của sinh viên khác."""
    attempt_id, _ = make_attempt(env, [1], owner="alice")
    res = env.client.post(f"/attempts/{attempt_id}/submit", headers=env.bob)
    assert res.status_code == 404
