from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Exam, ExamQuestion, Subject, User
from app.question_lock import IN_EXAM_MESSAGE, PUBLISHED_LOCK_MESSAGE
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


def edit_question(env, question_id, **overrides):
    return env.client.patch(
        f"/admin/questions/{question_id}",
        headers=env.admin,
        json=question_body(env.subject_id, **overrides),
    )


def list_questions(env):
    response = env.client.get("/admin/questions", headers=env.admin)
    assert response.status_code == 200, response.text
    return response.json()


def add_exam(env, status, question_ids, title="Đề kiểm tra"):
    with env.app.state.session_factory() as session:
        exam = Exam(
            title=title,
            description="",
            subject_id=env.subject_id,
            duration_minutes=30,
            pass_score=50.0,
            max_attempts=1,
            difficulty="medium",
            status=status,
        )
        session.add(exam)
        session.flush()
        for position, question_id in enumerate(question_ids):
            session.add(
                ExamQuestion(
                    exam_id=exam.id, question_id=question_id, points=1.0, position=position
                )
            )
        session.commit()
        return exam.id


def set_exam_status(env, exam_id, status):
    with env.app.state.session_factory() as session:
        session.get(Exam, exam_id).status = status
        session.commit()


def test_question_crud_when_it_is_not_in_any_exam(env):
    created = create_question(env)
    assert created["text"] == "Python là ngôn ngữ gì?"
    assert created["difficulty"] == "easy"
    assert [option["is_correct"] for option in created["options"]] == [False, True]

    edited = edit_question(
        env,
        created["id"],
        text="Python chạy theo cách nào?",
        options=[
            {"text": "Biên dịch", "is_correct": False},
            {"text": "Thông dịch", "is_correct": False},
            {"text": "Cả hai tùy cài đặt", "is_correct": True},
        ],
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["text"] == "Python chạy theo cách nào?"
    assert len(edited.json()["options"]) == 3
    assert [question["id"] for question in list_questions(env)] == [created["id"]]

    deleted = env.client.delete(f"/admin/questions/{created['id']}", headers=env.admin)
    assert deleted.status_code == 204
    assert list_questions(env) == []
    assert edit_question(env, "missing").status_code == 404
    assert env.client.delete("/admin/questions/missing", headers=env.admin).status_code == 404


def test_question_endpoints_require_admin(env):
    body = question_body(env.subject_id)
    for method, url in [
        ("GET", "/admin/questions"),
        ("POST", "/admin/questions"),
        ("PATCH", "/admin/questions/x"),
        ("DELETE", "/admin/questions/x"),
    ]:
        kwargs = {"json": body} if method in {"POST", "PATCH"} else {}
        assert env.client.request(method, url, headers=env.student, **kwargs).status_code == 403
        assert env.client.request(method, url, **kwargs).status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"options": [{"text": "A", "is_correct": False}, {"text": "B", "is_correct": False}]},
        {"options": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": True}]},
        {"options": [{"text": "A", "is_correct": True}]},
        {"options": [{"text": str(index), "is_correct": index == 0} for index in range(7)]},
        {"text": "   "},
        {"difficulty": "impossible"},
        {"role": "admin"},
    ],
)
def test_invalid_question_payloads_get_422(env, overrides):
    response = env.client.post(
        "/admin/questions", headers=env.admin, json=question_body(env.subject_id, **overrides)
    )
    assert response.status_code == 422, response.text


def test_question_needs_an_existing_subject(env):
    response = env.client.post(
        "/admin/questions", headers=env.admin, json=question_body("missing-subject")
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Môn học không tồn tại."}


def test_question_in_a_published_exam_cannot_be_edited_or_deleted(env):
    locked = create_question(env, text="Câu đã xuất bản")
    free = create_question(env, text="Câu chưa dùng")
    add_exam(env, "published", [locked["id"]])
    before = list_questions(env)

    changed_text = edit_question(env, locked["id"], text="Đã sửa")
    changed_option = edit_question(
        env,
        locked["id"],
        text="Câu đã xuất bản",
        options=[{"text": "A", "is_correct": True}, {"text": "B", "is_correct": False}],
    )
    hidden = edit_question(env, locked["id"], text="Câu đã xuất bản", is_active=False)
    deleted = env.client.delete(f"/admin/questions/{locked['id']}", headers=env.admin)

    for response in (changed_text, changed_option, hidden, deleted):
        assert response.status_code == 409, response.text
        assert response.json() == {"detail": PUBLISHED_LOCK_MESSAGE}
    assert list_questions(env) == before  # nội dung, id câu hỏi và id phương án giữ nguyên

    assert edit_question(env, free["id"], text="Vẫn sửa được").status_code == 200
    assert env.client.delete(f"/admin/questions/{free['id']}", headers=env.admin).status_code == 204


def test_only_published_exams_lock_edits_but_any_exam_blocks_delete(env):
    in_draft = create_question(env, text="Trong đề nháp")
    in_archived = create_question(env, text="Trong đề lưu trữ")
    add_exam(env, "draft", [in_draft["id"]])
    add_exam(env, "archived", [in_archived["id"]])

    for question in (in_draft, in_archived):
        assert edit_question(env, question["id"], text="Sửa được").status_code == 200
        deleted = env.client.delete(f"/admin/questions/{question['id']}", headers=env.admin)
        assert deleted.status_code == 409
        assert deleted.json() == {"detail": IN_EXAM_MESSAGE}
    assert len(list_questions(env)) == 2


def test_question_shared_with_a_published_exam_stays_locked(env):
    shared = create_question(env)
    add_exam(env, "draft", [shared["id"]], title="Đề nháp")
    add_exam(env, "published", [shared["id"]], title="Đề đã xuất bản")

    assert edit_question(env, shared["id"], text="Đã sửa").status_code == 409


def test_archiving_the_published_exam_releases_the_lock(env):
    question = create_question(env)
    exam_id = add_exam(env, "published", [question["id"]])
    assert edit_question(env, question["id"], text="Lần 1").status_code == 409

    set_exam_status(env, exam_id, "archived")
    assert edit_question(env, question["id"], text="Lần 2").status_code == 200

    set_exam_status(env, exam_id, "published")
    assert edit_question(env, question["id"], text="Lần 3").status_code == 409


def test_missing_question_is_404_even_when_published_exams_exist(env):
    question = create_question(env)
    add_exam(env, "published", [question["id"]])

    assert edit_question(env, "missing").status_code == 404
    assert env.client.delete("/admin/questions/missing", headers=env.admin).status_code == 404
