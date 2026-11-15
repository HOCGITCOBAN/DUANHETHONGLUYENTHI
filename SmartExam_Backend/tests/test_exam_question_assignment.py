from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Exam, Subject, User
from app.security import create_access_token, password_hasher

PASSWORD_HASH = password_hasher.hash("Secret password!")


@pytest.fixture
def env(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'questions.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        admin = User(
            full_name="Admin", email="admin@example.com", password_hash=PASSWORD_HASH, role="admin"
        )
        student = User(
            full_name="Student",
            email="student@example.com",
            password_hash=PASSWORD_HASH,
            role="student",
        )
        subject = Subject(name="Python", slug="python")
        session.add_all([admin, student, subject])
        session.commit()
        admin_id, student_id, subject_id = admin.id, student.id, subject.id
    with TestClient(app) as client:
        yield SimpleNamespace(
            app=app,
            client=client,
            subject_id=subject_id,
            admin={"Authorization": f"Bearer {create_access_token(admin_id, 'admin')}"},
            student={"Authorization": f"Bearer {create_access_token(student_id, 'student')}"},
        )
    app.state.engine.dispose()


def question_body(subject_id, **overrides):
    body = {
        "subject_id": subject_id,
        "text": "Python là ngôn ngữ gì?",
        "options": [
            {"text": "Biên dịch hoàn toàn", "is_correct": False},
            {"text": "Thông dịch", "is_correct": True},
        ],
        "explanation": "Python thường được thông dịch.",
        "difficulty": "easy",
        "is_active": True,
    }
    body.update(overrides)
    return body


def create_question(env, **overrides):
    response = env.client.post(
        "/admin/questions", headers=env.admin, json=question_body(env.subject_id, **overrides)
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_exam(env, title="Đề kiểm tra"):
    response = env.client.post(
        "/admin/exams", headers=env.admin, json={"title": title, "subject_id": env.subject_id}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def set_exam_status(env, exam_id, status):
    with env.app.state.session_factory() as session:
        session.get(Exam, exam_id).status = status
        session.commit()


def put_questions(env, exam_id, items, headers=None):
    return env.client.put(
        f"/admin/exams/{exam_id}/questions",
        headers=env.admin if headers is None else headers,
        json={"questions": items},
    )


def get_exam_questions(env, exam_id):
    exams = env.client.get("/admin/exams", headers=env.admin).json()
    return next(exam["questions"] for exam in exams if exam["id"] == exam_id)


def test_admin_assigns_questions_in_order_with_their_own_points(env):
    q1, q2, q3 = (create_question(env, text=f"Câu {index}")["id"] for index in (1, 2, 3))
    exam_id = create_exam(env)

    response = put_questions(
        env,
        exam_id,
        [
            {"question_id": q3, "points": 2.5},
            {"question_id": q1, "points": 1},
            {"question_id": q2, "points": 3},
        ],
    )

    assert response.status_code == 200, response.text
    expected = [
        {"question_id": q3, "points": 2.5},
        {"question_id": q1, "points": 1.0},
        {"question_id": q2, "points": 3.0},
    ]
    assert response.json()["questions"] == expected
    assert get_exam_questions(env, exam_id) == expected  # thứ tự và điểm được lưu lại


def test_putting_again_replaces_reorders_and_can_clear_the_list(env):
    q1, q2, q3 = (create_question(env, text=f"Câu {index}")["id"] for index in (1, 2, 3))
    exam_id = create_exam(env)
    put_questions(env, exam_id, [{"question_id": q, "points": 1} for q in (q1, q2, q3)])

    swapped = put_questions(
        env, exam_id, [{"question_id": q2, "points": 4}, {"question_id": q1, "points": 1}]
    )
    assert swapped.status_code == 200
    assert [item["question_id"] for item in get_exam_questions(env, exam_id)] == [q2, q1]

    cleared = put_questions(env, exam_id, [])
    assert cleared.status_code == 200
    assert get_exam_questions(env, exam_id) == []


def test_the_same_question_cannot_be_selected_twice(env):
    q1 = create_question(env, text="Câu 1")["id"]
    q2 = create_question(env, text="Câu 2")["id"]
    exam_id = create_exam(env)
    assert put_questions(env, exam_id, [{"question_id": q1, "points": 1}]).status_code == 200

    duplicate = put_questions(
        env,
        exam_id,
        [
            {"question_id": q2, "points": 1},
            {"question_id": q1, "points": 1},
            {"question_id": q2, "points": 5},
        ],
    )

    assert duplicate.status_code == 422
    assert duplicate.json() == {"detail": "Câu hỏi trong đề không được trùng."}
    assert get_exam_questions(env, exam_id) == [{"question_id": q1, "points": 1.0}]


def test_unknown_questions_are_rejected_and_nothing_is_saved(env):
    q1 = create_question(env)["id"]
    exam_id = create_exam(env)
    assert put_questions(env, exam_id, [{"question_id": q1, "points": 1}]).status_code == 200

    response = put_questions(
        env,
        exam_id,
        [{"question_id": q1, "points": 1}, {"question_id": "does-not-exist", "points": 1}],
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "Câu hỏi không tồn tại: does-not-exist."}
    assert get_exam_questions(env, exam_id) == [{"question_id": q1, "points": 1.0}]


@pytest.mark.parametrize("points", [0, -1, 100.5, "abc", None])
def test_points_must_be_a_positive_number_up_to_100(env, points):
    question_id = create_question(env)["id"]
    exam_id = create_exam(env)

    response = put_questions(env, exam_id, [{"question_id": question_id, "points": points}])

    assert response.status_code == 422, response.text
    assert get_exam_questions(env, exam_id) == []


def test_each_item_needs_question_id_and_points_and_nothing_else(env):
    question_id = create_question(env)["id"]
    exam_id = create_exam(env)

    for item in (
        {"question_id": question_id},
        {"points": 1},
        {"question_id": question_id, "points": 1, "position": 3},
    ):
        assert put_questions(env, exam_id, [item]).status_code == 422
    body_without_questions = env.client.put(
        f"/admin/exams/{exam_id}/questions", headers=env.admin, json={}
    )
    assert body_without_questions.status_code == 422


@pytest.mark.parametrize("status", ["published", "archived"])
def test_only_draft_exams_can_change_their_questions(env, status):
    q1 = create_question(env, text="Câu 1")["id"]
    q2 = create_question(env, text="Câu 2")["id"]
    exam_id = create_exam(env)
    put_questions(env, exam_id, [{"question_id": q1, "points": 1}])
    set_exam_status(env, exam_id, status)

    response = put_questions(env, exam_id, [{"question_id": q2, "points": 1}])

    assert response.status_code == 409
    assert response.json() == {"detail": "Chỉ chỉnh sửa được đề nháp."}
    assert get_exam_questions(env, exam_id) == [{"question_id": q1, "points": 1.0}]


def test_missing_exam_is_404(env):
    question_id = create_question(env)["id"]
    items = [{"question_id": question_id, "points": 1}]
    assert put_questions(env, "missing", items).status_code == 404


def test_assigning_questions_requires_admin(env):
    question_id = create_question(env)["id"]
    exam_id = create_exam(env)
    items = [{"question_id": question_id, "points": 1}]

    assert put_questions(env, exam_id, items, headers=env.student).status_code == 403
    assert put_questions(env, exam_id, items, headers={}).status_code == 401
    assert get_exam_questions(env, exam_id) == []
