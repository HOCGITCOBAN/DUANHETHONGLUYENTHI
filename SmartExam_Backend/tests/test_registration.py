from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from argon2.exceptions import VerifyMismatchError
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import Base
from app.main import create_app
from app.models import User
from app.security import password_hasher


@pytest.fixture
def app(tmp_path):
    application = create_app(f"sqlite:///{tmp_path / 'registration.sqlite3'}")
    Base.metadata.create_all(application.state.engine)
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def registration():
    return {
        "name": "Nguyễn Minh Anh",
        "email": "student@example.com",
        "password": "Secret student password!",
    }


def user_count(app):
    with app.state.session_factory() as session:
        return session.scalar(select(func.count()).select_from(User))


def assert_sanitized_validation(response, password=None):
    assert response.status_code == 422, response.text
    body = response.json()
    assert isinstance(body.get("detail"), list)
    assert body["detail"]

    def inspect(value):
        if isinstance(value, dict):
            # Framework validation errors otherwise echo rejected request values.
            assert "input" not in value
            assert "ctx" not in value
            for child in value.values():
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)

    inspect(body)
    if password and not password.isspace():
        assert password not in response.text
    assert "$argon2" not in response.text


def test_register_persists_a_student_and_returns_only_public_fields(app, client, registration):
    registration["name"] = "  Nguyễn Minh Anh  "
    registration["email"] = "  Student@EXAMPLE.COM  "

    response = client.post("/auth/register", json=registration)

    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    result = response.json()
    assert set(result) == {"id", "name", "email", "role"}
    assert result["id"] is not None
    assert result["name"] == "Nguyễn Minh Anh"
    assert result["email"] == "student@example.com"
    assert result["role"] == "student"
    assert registration["password"] not in response.text

    with app.state.session_factory() as session:
        user = session.scalars(select(User)).one()
        assert str(user.id) == str(result["id"])
        assert user.full_name == result["name"]
        assert user.email == result["email"]
        assert user.role == "student"
        assert user.password_hash != registration["password"]
        assert user.password_hash.startswith("$argon2")
        assert password_hasher.verify(user.password_hash, registration["password"])


def test_identical_passwords_get_different_salted_hashes(app, client, registration):
    first = client.post("/auth/register", json=registration)
    second = client.post("/auth/register", json={**registration, "email": "other@example.com"})
    assert first.status_code == second.status_code == 201

    with app.state.session_factory() as session:
        hashes = session.scalars(select(User.password_hash)).all()
    assert len(hashes) == 2
    assert hashes[0] != hashes[1]
    assert all(password_hasher.verify(value, registration["password"]) for value in hashes)


def test_password_whitespace_and_unicode_are_preserved(app, client, registration):
    password = "  MậtKhẩu rất riêng!  "
    response = client.post("/auth/register", json={**registration, "password": password})
    assert response.status_code == 201, response.text

    with app.state.session_factory() as session:
        stored_hash = session.scalar(select(User.password_hash))
    assert password_hasher.verify(stored_hash, password)
    with pytest.raises(VerifyMismatchError):
        password_hasher.verify(stored_hash, password.strip())


@pytest.mark.parametrize(
    "duplicate_email",
    ["student@example.com", "STUDENT@EXAMPLE.COM", "  Student@example.com  "],
)
def test_duplicate_email_is_rejected_without_changing_the_existing_user(
    app, client, registration, duplicate_email
):
    original = client.post("/auth/register", json=registration)
    assert original.status_code == 201

    duplicate = client.post(
        "/auth/register",
        json={
            "name": "Different Person",
            "email": duplicate_email,
            "password": "Another secret password!",
        },
    )

    assert duplicate.status_code == 409, duplicate.text
    assert user_count(app) == 1
    assert "password_hash" not in duplicate.text
    with app.state.session_factory() as session:
        user = session.scalars(select(User)).one()
        assert user.full_name == registration["name"]
        assert password_hasher.verify(user.password_hash, registration["password"])

    # A rejected transaction must not prevent a later independent registration.
    followup = client.post("/auth/register", json={**registration, "email": "next@example.com"})
    assert followup.status_code == 201, followup.text


def test_concurrent_duplicate_registration_creates_exactly_one_account(app, client, registration):
    barrier = Barrier(2)

    def register(email):
        barrier.wait(timeout=10)
        return client.post("/auth/register", json={**registration, "email": email})

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(register, "student@example.com"),
            executor.submit(register, " STUDENT@EXAMPLE.COM "),
        ]
        responses = [future.result(timeout=30) for future in futures]

    assert sorted(response.status_code for response in responses) == [201, 409], [
        response.text for response in responses
    ]
    assert user_count(app) == 1


@pytest.mark.parametrize("missing_field", ["name", "email", "password"])
def test_required_fields(app, client, registration, missing_field):
    password = registration["password"]
    registration.pop(missing_field)
    response = client.post("/auth/register", json=registration)
    assert_sanitized_validation(response, password)
    assert user_count(app) == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "   "),
        ("name", "n" * 121),
        ("name", None),
        ("name", 42),
        ("email", ""),
        ("email", "not-an-email"),
        ("email", "student@"),
        ("email", "student\n@example.com"),
        ("email", "x" * 255 + "@example.com"),
        ("email", None),
        ("password", ""),
        ("password", "short7!"),
        ("password", " " * 8),
        ("password", "\t\n " * 4),
        ("password", "PrivateTooLong!" * 10),
        ("password", None),
        ("password", 12345678),
    ],
)
def test_invalid_input_is_rejected_without_exposing_secrets(
    app, client, registration, field, value
):
    registration[field] = value
    response = client.post("/auth/register", json=registration)
    password = registration.get("password")
    assert_sanitized_validation(response, password if isinstance(password, str) else None)
    assert user_count(app) == 0


@pytest.mark.parametrize("extra_field", ["role", "is_admin", "password_hash"])
def test_extra_fields_cannot_be_used_to_escalate_privileges(app, client, registration, extra_field):
    response = client.post("/auth/register", json={**registration, extra_field: "admin"})
    assert_sanitized_validation(response, registration["password"])
    assert user_count(app) == 0


@pytest.mark.parametrize("password_length", [8, 128])
def test_password_length_boundaries_are_accepted(client, registration, password_length):
    response = client.post(
        "/auth/register", json={**registration, "password": "p" * password_length}
    )
    assert response.status_code == 201, response.text


def test_full_name_length_boundary_is_accepted(client, registration):
    name = "N" * 120
    response = client.post("/auth/register", json={**registration, "name": name})
    assert response.status_code == 201, response.text
    assert response.json()["name"] == name


def test_maximum_length_valid_email_is_accepted(client, registration):
    email = "x" * 64 + "@" + "a" * 63 + "." + "b" * 63 + "." + "c" * 57 + ".com"
    assert len(email) == 254
    response = client.post("/auth/register", json={**registration, "email": email})
    assert response.status_code == 201, response.text
    assert response.json()["email"] == email


def test_email_expanded_by_unicode_casefold_is_validated_before_insert(app, client, registration):
    domain = "a" * 63 + "." + "b" * 63 + "." + "c" * 53 + ".com"
    email = "İ" * 32 + "@" + domain
    assert len(email.encode("utf-8")) == 250
    assert len(email.casefold().encode("utf-8")) == 282
    response = client.post("/auth/register", json={**registration, "email": email})
    assert_sanitized_validation(response, registration["password"])
    assert user_count(app) == 0


def test_full_name_alias_remains_compatible(client, registration):
    name = registration.pop("name")
    response = client.post("/auth/register", json={**registration, "full_name": name})
    assert response.status_code == 201, response.text
    assert response.json()["name"] == name


def test_ambiguous_name_fields_are_rejected(app, client, registration):
    response = client.post("/auth/register", json={**registration, "full_name": "Other Name"})
    assert_sanitized_validation(response, registration["password"])
    assert user_count(app) == 0


def test_existing_frontend_is_served_with_same_origin_real_api_configuration(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'src="app.js"' in response.text
    config = client.get("/config.js")
    assert config.status_code == 200
    assert "mode: 'api'" in config.text
    assert "baseUrl: ''" in config.text
    assert config.headers["cache-control"] == "no-store"
    assert client.get("/app.js").status_code == 200


@pytest.mark.parametrize("origin", ["http://localhost:5500", "http://127.0.0.1:5500"])
def test_standalone_frontend_registration_preflight(client, origin):
    response = client.options(
        "/auth/register",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
