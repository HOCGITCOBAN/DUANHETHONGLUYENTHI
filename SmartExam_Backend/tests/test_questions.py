from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError

from app.database import Base
from app.main import create_app
from app.models import Question, QuestionOption, Subject, User
from app.security import create_access_token


@pytest.fixture
def bank(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'questions.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        session.add_all(
            [
                User(
                    id="admin",
                    full_name="Admin",
                    email="admin@example.com",
                    password_hash="unused",
                    role="admin",
                ),
                User(
                    id="student",
                    full_name="Student",
                    email="student@example.com",
                    password_hash="unused",
                    role="student",
                ),
                Subject(id="js", name="JavaScript", slug="javascript"),
                Subject(id="sql", name="SQL", slug="sql", is_active=False),
            ]
        )
        session.commit()
    with TestClient(app) as client:
        yield app, client, {"Authorization": f"Bearer {create_access_token('admin', 'admin')}"}
    app.state.engine.dispose()


@pytest.fixture
def payload():
    return {
        "subject_id": "js",
        "text": " Từ khóa nào khai báo biến có phạm vi khối? ",
        "difficulty": "easy",
        "explanation": " let khai báo biến có phạm vi khối. ",
        "options": [
            {"id": "a", "text": " let ", "is_correct": True},
            {"id": "b", "text": " var ", "is_correct": False},
        ],
    }


def create(client, headers, payload):
    response = client.post("/admin/questions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/admin/questions"),
        ("POST", "/admin/questions"),
        ("PATCH", "/admin/questions/missing"),
    ],
)
@pytest.mark.parametrize(
    "identity,expected",
    [
        (None, 401),
        ("invalid", 401),
        ("student", 403),
        ("claimed-admin", 403),
    ],
)
def test_all_question_operations_require_real_admin(
    bank, payload, method, path, identity, expected
):
    _, client, _ = bank
    headers = {}
    if identity:
        role = "student" if identity == "student" else "admin"
        token = "invalid" if identity == "invalid" else create_access_token("student", role)
        headers = {"Authorization": f"Bearer {token}"}
    response = client.request(
        method, path, headers=headers, **({"json": payload} if method != "GET" else {})
    )
    assert response.status_code == expected
    assert "options" not in response.text


@pytest.mark.parametrize("option_count", [2, 6])
def test_create_persists_question_and_ordered_options(bank, payload, option_count):
    app, client, headers = bank
    payload["options"] += [
        {"text": f"Phương án {i}", "is_correct": False} for i in range(2, option_count)
    ]
    created = create(client, headers, payload)
    assert created["text"] == payload["text"].strip()
    assert created["explanation"] == payload["explanation"].strip()
    assert created["is_active"] is True
    assert len(created["options"]) == option_count
    assert all(option["id"] for option in created["options"])
    assert created["options"][0] == {"id": "a", "text": "let", "is_correct": True}
    assert client.get("/admin/questions", headers=headers).json() == [created]
    with app.state.session_factory() as session:
        saved = session.get(Question, created["id"])
        assert saved.subject_id == "js"
        assert [option.id for option in saved.options] == [o["id"] for o in created["options"]]
        assert sum(option.is_correct for option in saved.options) == 1


def test_edit_reorders_replaces_and_removes_options_then_hides_without_deleting(bank, payload):
    app, client, headers = bank
    original = create(client, headers, payload)
    options = [
        {"id": "b", "text": "const", "is_correct": True},
        {"id": "a", "text": "var", "is_correct": False},
        {"text": "static", "is_correct": False},
    ]
    path = f"/admin/questions/{original['id']}"
    edited = client.patch(
        path,
        headers=headers,
        json={
            "subject_id": "sql",
            "text": "Nội dung đã sửa",
            "difficulty": "hard",
            "explanation": "",
            "options": options,
        },
    )
    assert edited.status_code == 200, edited.text
    updated = edited.json()
    assert updated["id"] == original["id"]
    assert updated["subject_id"] == "sql"
    assert updated["difficulty"] == "hard"
    assert updated["explanation"] == ""
    assert [option["id"] for option in updated["options"][:2]] == ["b", "a"]
    assert updated["options"][0]["is_correct"] is True
    reduced = client.patch(path, headers=headers, json={"options": updated["options"][:2]})
    assert reduced.status_code == 200, reduced.text
    hidden = client.patch(path, headers=headers, json={"is_active": False})
    assert hidden.status_code == 200, hidden.text
    assert hidden.json() == {**reduced.json(), "is_active": False}
    assert client.get("/admin/questions", headers=headers).json() == [hidden.json()]
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Question)) == 1
        assert session.scalar(select(func.count()).select_from(QuestionOption)) == 2
    restored = client.patch(path, headers=headers, json={"is_active": True})
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


@pytest.mark.parametrize(
    "change",
    [
        {"options": []},
        {"options": [{"text": "Only one", "is_correct": True}]},
        {"options": [{"text": "A", "is_correct": i == 0} for i in range(7)]},
        {"options": [{"text": "A"}, {"text": "B"}]},
        {"options": [{"text": "A", "is_correct": True}, {"text": "B", "is_correct": True}]},
        {"options": [{"id": "same", "text": "A", "is_correct": True}, {"id": "same", "text": "B"}]},
        {"options": [{"text": " ", "is_correct": True}, {"text": "B"}]},
        {"options": [{"text": "a" * 1001, "is_correct": True}, {"text": "B"}]},
        {"options": [{"id": " ", "text": "A", "is_correct": True}, {"text": "B"}]},
        {"options": [{"text": "A", "is_correct": "false"}, {"text": "B", "is_correct": True}]},
        {"options": [{"text": "A", "is_correct": True, "question_id": "other"}, {"text": "B"}]},
        {"text": " "},
        {"text": "a" * 2001},
        {"difficulty": "expert"},
        {"subject_id": " "},
        {"is_active": "false"},
        {"id": "injected"},
        {"explanation": "a" * 5001},
    ],
)
def test_invalid_create_and_patch_are_rejected_without_changing_saved_data(bank, payload, change):
    _, client, headers = bank
    original = create(client, headers, payload)
    invalid = {**deepcopy(payload), **change}
    assert client.post("/admin/questions", headers=headers, json=invalid).status_code == 422
    response = client.patch(f"/admin/questions/{original['id']}", headers=headers, json=change)
    assert response.status_code == 422, response.text
    assert client.get("/admin/questions", headers=headers).json() == [original]


@pytest.mark.parametrize("change", [{}, {"options": None}, {"text": None}, {"is_active": None}])
def test_empty_or_null_patch_does_not_erase_data(bank, payload, change):
    _, client, headers = bank
    original = create(client, headers, payload)
    assert (
        client.patch(f"/admin/questions/{original['id']}", headers=headers, json=change).status_code
        == 422
    )
    assert client.get("/admin/questions", headers=headers).json() == [original]


def test_unknown_question_or_subject_returns_404_without_partial_update(bank, payload):
    _, client, headers = bank
    assert (
        client.post(
            "/admin/questions", headers=headers, json={**payload, "subject_id": "missing"}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            "/admin/questions/missing", headers=headers, json={"is_active": False}
        ).status_code
        == 404
    )
    original = create(client, headers, payload)
    assert (
        client.patch(
            f"/admin/questions/{original['id']}",
            headers=headers,
            json={"subject_id": "missing", "text": "Must not persist"},
        ).status_code
        == 404
    )
    assert client.get("/admin/questions", headers=headers).json() == [original]


def test_list_can_filter_by_subject_difficulty_and_active_status(bank, payload):
    _, client, headers = bank
    easy = create(client, headers, payload)
    hard = create(client, headers, {**payload, "subject_id": "sql", "difficulty": "hard"})
    hidden = create(client, headers, {**payload, "difficulty": "hard", "is_active": False})
    for query, expected in [
        ({"subject_id": "sql"}, [hard]),
        ({"difficulty": "easy"}, [easy]),
        ({"is_active": "false"}, [hidden]),
        ({"subject_id": "js", "difficulty": "hard", "is_active": "false"}, [hidden]),
        ({"subject_id": "missing"}, []),
    ]:
        assert client.get("/admin/questions", headers=headers, params=query).json() == expected
    assert client.get("/admin/questions?difficulty=invalid", headers=headers).status_code == 422


def test_database_failure_rolls_back_content_and_option_replacement(bank, payload):
    app, client, headers = bank
    original = create(client, headers, payload)

    def fail_insert(_mapper, _connection, option):
        raise RuntimeError("Simulated storage failure")

    event.listen(QuestionOption, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="Simulated storage failure"):
            client.patch(
                f"/admin/questions/{original['id']}",
                headers=headers,
                json={
                    "text": "Must roll back",
                    "options": [
                        {"text": "New A", "is_correct": True},
                        {"text": "New B"},
                    ],
                },
            )
    finally:
        event.remove(QuestionOption, "before_insert", fail_insert)
    assert client.get("/admin/questions", headers=headers).json() == [original]
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(QuestionOption)) == 2


def test_sqlite_enforces_subject_foreign_key(bank):
    app, _, _ = bank
    with app.state.session_factory() as session:
        session.add(Question(subject_id="missing", text="A", difficulty="easy"))
        with pytest.raises(IntegrityError):
            session.commit()
