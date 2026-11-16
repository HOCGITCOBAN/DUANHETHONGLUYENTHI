from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import Subject, User
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
        admin_id, subject_id = admin.id, subject.id
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
                json={"questions": [{"question_id": "question-1", "points": 2}]},
            )
            assert associated.status_code == 200, associated.text
            assert associated.json()["questions"] == [{"question_id": "question-1", "points": 2.0}]

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
                        {"question_id": "question-1", "points": 1},
                        {"question_id": "question-1", "points": 2},
                    ]
                },
            )
            assert duplicate.status_code == 422
            assert client.get("/admin/exams", headers={}).status_code == 401
    finally:
        app.state.engine.dispose()
