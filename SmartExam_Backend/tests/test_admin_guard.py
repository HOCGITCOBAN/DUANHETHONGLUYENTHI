import base64
import json
import time

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.admin import admin_router, require_admin
from app.database import Base
from app.main import create_app
from app.models import User
from app.security import create_access_token, password_hasher

PASSWORD = "Secret student password!"


@pytest.fixture
def app(tmp_path):
    application = create_app(f"sqlite:///{tmp_path / 'admin.sqlite3'}")
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_client(app):
    """App nhỏ có một route /admin dùng đúng dependency require_admin, chung CSDL với `app`."""
    probe = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])

    @probe.get("/probe")
    def probe_route() -> dict[str, bool]:
        return {"ok": True}

    probe_app = FastAPI()
    probe_app.state.session_factory = app.state.session_factory
    probe_app.include_router(probe)
    with TestClient(probe_app) as test_client:
        yield test_client


def make_user(app, email, role, name="Người Dùng"):
    with app.state.session_factory() as session:
        user = User(
            full_name=name,
            email=email,
            password_hash=password_hasher.hash(PASSWORD),
            role=role,
        )
        session.add(user)
        session.commit()
        return user.id


def set_role(app, user_id, role):
    with app.state.session_factory() as session:
        session.get(User, user_id).role = role
        session.commit()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@pytest.mark.parametrize("role", ["student", "admin"])
def test_me_returns_the_profile_with_role(app, client, role):
    user_id = make_user(app, f"{role}@example.com", role, name="Nguyễn Minh Anh")

    response = client.get("/auth/me", headers=bearer(create_access_token(user_id, role)))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": user_id,
        "name": "Nguyễn Minh Anh",
        "email": f"{role}@example.com",
        "role": role,
    }


def test_login_then_me_then_admin_guard_for_a_student(app, client, admin_client):
    registration = {"name": "Sinh Viên", "email": "new@example.com", "password": PASSWORD}
    assert client.post("/auth/register", json=registration).status_code == 201

    login = client.post("/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    assert client.get("/auth/me", headers=bearer(token)).json()["role"] == "student"
    assert admin_client.get("/admin/probe", headers=bearer(token)).status_code == 403


def forged_tokens(user_id):
    valid = create_access_token(user_id, "student")
    header, claims, signature = valid.split(".")
    elevated = json.loads(b64url_decode(claims))
    elevated["role"] = "admin"
    return {
        "expired": create_access_token(user_id, "student", now=int(time.time()) - 7200),
        "payload edited, signature kept": ".".join(
            [header, b64url(json.dumps(elevated).encode()), signature]
        ),
        "alg none": ".".join([b64url(b'{"alg":"none","typ":"JWT"}'), claims, ""]),
        "unknown user": create_access_token("00000000-0000-0000-0000-000000000000", "student"),
        "garbage": "not-a-jwt",
    }


@pytest.mark.parametrize(
    "case",
    ["expired", "payload edited, signature kept", "alg none", "unknown user", "garbage"],
)
def test_invalid_tokens_get_401_on_me_and_on_admin_routes(app, client, admin_client, case):
    user_id = make_user(app, "student@example.com", "student")
    token = forged_tokens(user_id)[case]

    assert client.get("/auth/me", headers=bearer(token)).status_code == 401
    assert admin_client.get("/admin/probe", headers=bearer(token)).status_code == 401


def test_missing_or_non_bearer_credentials_get_401(client, admin_client):
    assert client.get("/auth/me").status_code == 401
    assert admin_client.get("/admin/probe").status_code == 401
    basic = {"Authorization": "Basic YTpi"}
    assert admin_client.get("/admin/probe", headers=basic).status_code == 401


def test_admin_route_gives_403_for_student_and_200_for_admin(app, admin_client):
    student = make_user(app, "student@example.com", "student")
    admin = make_user(app, "admin@example.com", "admin")

    forbidden = admin_client.get(
        "/admin/probe", headers=bearer(create_access_token(student, "student"))
    )
    assert forbidden.status_code == 403
    assert forbidden.json() == {"detail": "Bạn không có quyền thực hiện thao tác này."}

    allowed = admin_client.get("/admin/probe", headers=bearer(create_access_token(admin, "admin")))
    assert allowed.status_code == 200
    assert allowed.json() == {"ok": True}


def test_role_claim_in_the_token_is_ignored_in_favour_of_the_database(app, client, admin_client):
    student = make_user(app, "student@example.com", "student")
    # Token ký hợp lệ nhưng khai role=admin cho một tài khoản student trong CSDL.
    claimed_admin = create_access_token(student, "admin")

    assert admin_client.get("/admin/probe", headers=bearer(claimed_admin)).status_code == 403
    assert client.get("/auth/me", headers=bearer(claimed_admin)).json()["role"] == "student"


def test_role_changes_take_effect_without_a_new_token(app, admin_client):
    user_id = make_user(app, "user@example.com", "student")
    token = create_access_token(user_id, "student")
    assert admin_client.get("/admin/probe", headers=bearer(token)).status_code == 403

    set_role(app, user_id, "admin")
    assert admin_client.get("/admin/probe", headers=bearer(token)).status_code == 200

    set_role(app, user_id, "student")
    assert admin_client.get("/admin/probe", headers=bearer(token)).status_code == 403


def test_every_route_added_to_admin_router_requires_admin(app):
    assert admin_router.prefix == "/admin"
    assert any(dep.dependency is require_admin for dep in admin_router.dependencies)
