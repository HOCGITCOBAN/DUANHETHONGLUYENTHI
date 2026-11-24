from fastapi.testclient import TestClient

from app.database import Base
from app.main import create_app
from app.models import User
from app.security import create_access_token, password_hasher


def test_subject_catalog_permissions_and_crud(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'subjects.sqlite3'}")
    Base.metadata.create_all(app.state.engine)
    with app.state.session_factory() as session:
        admin = User(
            full_name="Admin",
            email="admin@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="admin",
        )
        student = User(
            full_name="Student",
            email="student@example.com",
            password_hash=password_hasher.hash("Secret password!"),
            role="student",
        )
        session.add_all([admin, student])
        session.commit()
        admin_id, student_id = admin.id, student.id
    headers = {"Authorization": f"Bearer {create_access_token(admin_id, 'admin')}"}
    student_headers = {"Authorization": f"Bearer {create_access_token(student_id, 'student')}"}
    try:
        with TestClient(app) as client:
            assert client.get("/admin/subjects", headers=student_headers).status_code == 403
            created = client.post(
                "/admin/subjects",
                headers=headers,
                json={"name": "JavaScript", "slug": "javascript", "is_active": True},
            )
            assert created.status_code == 201, created.text
            subject_id = created.json()["id"]
            assert client.get("/subjects", headers=student_headers).json()[0]["slug"] == "javascript"
            edited = client.patch(
                f"/admin/subjects/{subject_id}",
                headers=headers,
                json={"name": "Java nâng cao", "slug": "java-nang-cao", "is_active": True},
            )
            assert edited.status_code == 200, edited.text
            assert client.get("/subjects", headers=student_headers).json()[0]["name"] == "Java nâng cao"
            hidden = client.patch(
                f"/admin/subjects/{subject_id}",
                headers=headers,
                json={"name": "Java nâng cao", "slug": "java-nang-cao", "is_active": False},
            )
            assert hidden.status_code == 200, hidden.text
            assert client.get("/subjects", headers=student_headers).json() == []
            assert client.get("/admin/subjects", headers=headers).json()[0]["is_active"] is False
            assert (
                client.patch(
                    "/admin/subjects/missing",
                    headers=headers,
                    json={"name": "X", "slug": "x", "is_active": True},
                ).status_code
                == 404
            )
    finally:
        app.state.engine.dispose()


def test_cors_allows_local_frontend_ports_and_patch(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'cors.sqlite3'}")
    try:
        with TestClient(app) as client:
            response = client.options(
                "/admin/subjects/example",
                headers={
                    "Origin": "http://localhost:5501",
                    "Access-Control-Request-Method": "PATCH",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:5501"
        assert "PATCH" in response.headers["access-control-allow-methods"]
    finally:
        app.state.engine.dispose()
