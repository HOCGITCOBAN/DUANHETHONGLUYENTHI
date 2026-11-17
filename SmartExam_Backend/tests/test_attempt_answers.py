from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.attempts import as_utc, expire_overdue_attempts
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
    app = create_app(f"sqlite:///{tmp_path / 'attempts.sqlite3'}")
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


def make_attempt(env, points, owner="alice", pass_score=60, status="in_progress"):
    """Tạo đề published gồm các câu có điểm `points` và một lượt thi của `owner`."""
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
        session.flush()
        attempt = Attempt(
            exam_id=exam.id,
            user_id=env.ids[owner],
            status=status,
            started_at=START,
            deadline_at=DEADLINE,
        )
        session.add(attempt)
        session.commit()
        return SimpleNamespace(id=attempt.id, exam_id=exam.id, questions=questions)


def put_answer(env, attempt_id, question_id, chosen, headers=None):
    return env.client.put(
        f"/attempts/{attempt_id}/answers/{question_id}",
        headers=env.alice if headers is None else headers,
        json={"option_id": chosen},
    )


def saved_answers(env, attempt_id):
    with env.app.state.session_factory() as session:
        rows = session.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id)
        ).all()
        return {row.question_id: row.option_id for row in rows}


def load_attempt(env, attempt_id):
    with env.app.state.session_factory() as session:
        attempt = session.get(Attempt, attempt_id)
        return SimpleNamespace(
            status=attempt.status,
            score=attempt.score,
            correct_count=attempt.correct_count,
            passed=attempt.passed,
            submitted_at=as_utc(attempt.submitted_at) if attempt.submitted_at else None,
        )


# ---------------------------------------------------------------- US-14


def test_answer_is_saved_immediately_and_can_be_changed(env):
    attempt = make_attempt(env, [1])
    question = attempt.questions[0]

    first = put_answer(env, attempt.id, question["id"], option_id(question, correct=False))
    assert first.status_code == 200, first.text
    assert first.json() == {
        "question_id": question["id"],
        "option_id": option_id(question, correct=False),
    }
    assert saved_answers(env, attempt.id) == {question["id"]: option_id(question, correct=False)}

    changed = put_answer(env, attempt.id, question["id"], option_id(question, correct=True))
    assert changed.status_code == 200
    # Vẫn một bản ghi cho câu này, mang phương án mới nhất.
    assert saved_answers(env, attempt.id) == {question["id"]: option_id(question, correct=True)}


def test_answer_is_accepted_up_to_and_including_the_deadline(env):
    attempt = make_attempt(env, [1])
    question = attempt.questions[0]
    chosen = option_id(question, correct=True)

    env.clock["now"] = DEADLINE
    assert put_answer(env, attempt.id, question["id"], chosen).status_code == 200

    env.clock["now"] = DEADLINE + timedelta(microseconds=1)
    late = put_answer(env, attempt.id, question["id"], chosen)
    assert late.status_code == 409


def test_answer_validation(env):
    attempt = make_attempt(env, [1, 1])
    first, second = attempt.questions

    # Phương án của câu khác, hoặc không tồn tại.
    wrong_question = put_answer(env, attempt.id, first["id"], option_id(second, correct=True))
    assert wrong_question.status_code == 422
    assert wrong_question.json() == {"detail": "Phương án không thuộc câu hỏi này."}
    assert put_answer(env, attempt.id, first["id"], "missing").status_code == 422
    # Câu hỏi không thuộc đề.
    outsider = create_question(env, "Câu ngoài đề")
    not_in_exam = put_answer(env, attempt.id, outsider["id"], option_id(outsider, correct=True))
    assert not_in_exam.status_code == 404
    assert saved_answers(env, attempt.id) == {}

    url = f"/attempts/{attempt.id}/answers/{first['id']}"
    assert env.client.put(url, headers=env.alice, json={}).status_code == 422
    body = {"option_id": option_id(first, correct=True), "is_correct": True}
    assert env.client.put(url, headers=env.alice, json=body).status_code == 422


def test_only_the_owner_can_answer(env):
    attempt = make_attempt(env, [1])
    question = attempt.questions[0]
    chosen = option_id(question, correct=True)

    assert put_answer(env, attempt.id, question["id"], chosen, headers=env.bob).status_code == 404
    assert put_answer(env, attempt.id, question["id"], chosen, headers={}).status_code == 401
    assert put_answer(env, "missing", question["id"], chosen).status_code == 404
    assert saved_answers(env, attempt.id) == {}

    # Người khác gọi sau hạn cũng không làm thay đổi trạng thái lượt thi của chủ.
    env.clock["now"] = DEADLINE + timedelta(minutes=1)
    assert put_answer(env, attempt.id, question["id"], chosen, headers=env.bob).status_code == 404
    assert load_attempt(env, attempt.id).status == "in_progress"


def test_submitted_attempt_does_not_accept_answers(env):
    attempt = make_attempt(env, [1], status="submitted")
    question = attempt.questions[0]

    response = put_answer(env, attempt.id, question["id"], option_id(question, correct=True))

    assert response.status_code == 409
    assert response.json() == {"detail": "Bài thi đã kết thúc, không thể lưu thêm đáp án."}
    assert saved_answers(env, attempt.id) == {}
    assert load_attempt(env, attempt.id).status == "submitted"


# ---------------------------------------------------------------- US-17


def test_late_answer_expires_the_attempt_and_grades_the_saved_answers(env):
    attempt = make_attempt(env, [1, 2, 3], pass_score=60)
    q1, q2, q3 = attempt.questions
    assert put_answer(env, attempt.id, q1["id"], option_id(q1, correct=True)).status_code == 200
    assert put_answer(env, attempt.id, q2["id"], option_id(q2, correct=False)).status_code == 200
    assert put_answer(env, attempt.id, q3["id"], option_id(q3, correct=True)).status_code == 200

    env.clock["now"] = DEADLINE + timedelta(seconds=1)
    late = put_answer(env, attempt.id, q2["id"], option_id(q2, correct=True))

    assert late.status_code == 409
    assert late.json() == {
        "detail": "Đã hết giờ làm bài. Bài thi đã được chấm tự động, không thể lưu thêm đáp án."
    }
    result = load_attempt(env, attempt.id)
    assert result.status == "expired"
    assert result.correct_count == 2
    assert result.score == 66.67  # (1 + 3) / (1 + 2 + 3) * 100
    assert result.passed is True
    assert result.submitted_at == DEADLINE
    # Đáp án gửi sau hạn không được lưu; đáp án cũ giữ nguyên.
    assert saved_answers(env, attempt.id)[q2["id"]] == option_id(q2, correct=False)


def test_expired_attempt_stays_locked_and_is_graded_only_once(env):
    attempt = make_attempt(env, [1, 1])
    q1, q2 = attempt.questions
    put_answer(env, attempt.id, q1["id"], option_id(q1, correct=True))

    env.clock["now"] = DEADLINE + timedelta(minutes=1)
    assert put_answer(env, attempt.id, q2["id"], option_id(q2, correct=True)).status_code == 409
    graded = load_attempt(env, attempt.id)

    env.clock["now"] = DEADLINE + timedelta(hours=2)
    assert put_answer(env, attempt.id, q2["id"], option_id(q2, correct=True)).status_code == 409
    assert put_answer(env, attempt.id, q1["id"], option_id(q1, correct=False)).status_code == 409
    again = load_attempt(env, attempt.id)

    assert (again.status, again.score, again.correct_count, again.submitted_at) == (
        graded.status,
        graded.score,
        graded.correct_count,
        graded.submitted_at,
    )
    assert saved_answers(env, attempt.id) == {q1["id"]: option_id(q1, correct=True)}


def test_attempt_without_answers_expires_with_zero_score(env):
    attempt = make_attempt(env, [2, 3], pass_score=60)
    question = attempt.questions[0]

    env.clock["now"] = DEADLINE + timedelta(minutes=1)
    assert put_answer(env, attempt.id, question["id"], option_id(question, True)).status_code == 409

    result = load_attempt(env, attempt.id)
    assert (result.status, result.score, result.correct_count, result.passed) == (
        "expired",
        0.0,
        0,
        False,
    )


def test_score_is_rounded_to_two_decimals_and_compared_with_pass_score(env):
    attempt = make_attempt(env, [1, 1, 1], pass_score=40)
    q1, *_ = attempt.questions
    put_answer(env, attempt.id, q1["id"], option_id(q1, correct=True))

    env.clock["now"] = DEADLINE + timedelta(minutes=1)
    put_answer(env, attempt.id, q1["id"], option_id(q1, correct=True))

    result = load_attempt(env, attempt.id)
    assert result.score == 33.33
    assert result.passed is False


def test_expire_overdue_attempts_grades_only_overdue_in_progress_attempts(env):
    overdue_a = make_attempt(env, [1])
    overdue_b = make_attempt(env, [1], owner="bob")
    on_time = make_attempt(env, [1])
    finished = make_attempt(env, [1], status="submitted")
    question = overdue_a.questions[0]
    put_answer(env, overdue_a.id, question["id"], option_id(question, correct=True))
    with env.app.state.session_factory() as session:
        session.get(Attempt, on_time.id).deadline_at = DEADLINE + timedelta(hours=1)
        session.commit()

    env.clock["now"] = DEADLINE + timedelta(minutes=1)
    with env.app.state.session_factory() as session:
        assert expire_overdue_attempts(session) == 2
    with env.app.state.session_factory() as session:
        assert expire_overdue_attempts(session) == 0

    assert load_attempt(env, overdue_a.id).status == "expired"
    assert load_attempt(env, overdue_a.id).score == 100.0
    assert load_attempt(env, overdue_b.id).status == "expired"
    assert load_attempt(env, overdue_b.id).score == 0.0
    assert load_attempt(env, on_time.id).status == "in_progress"
    assert load_attempt(env, finished.id).status == "submitted"
