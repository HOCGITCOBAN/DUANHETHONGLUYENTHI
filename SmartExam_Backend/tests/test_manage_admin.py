import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, make_engine
from app.manage_admin import main
from app.models import User


@pytest.fixture
def database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'manage-admin.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = make_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                User(
                    id="target",
                    full_name="admin",
                    email="owner@example.com",
                    password_hash="existing-hash",
                    role="student",
                ),
                User(
                    id="other",
                    full_name="Other",
                    email="other@example.com",
                    password_hash="other-hash",
                    role="student",
                ),
            ]
        )
        session.commit()
    yield engine
    engine.dispose()


def test_promote_only_selected_email_and_preserve_account_data(database, capsys):
    assert main([" OWNER@EXAMPLE.COM "]) == 0
    assert "Đã cấp quyền admin" in capsys.readouterr().out
    with Session(database) as session:
        target = session.get(User, "target")
        assert target.role == "admin"
        assert target.full_name == "admin"
        assert target.password_hash == "existing-hash"
        assert session.get(User, "other").role == "student"
    assert main(["owner@example.com"]) == 0
    assert "đã có quyền admin" in capsys.readouterr().out


def test_prompt_accepts_email_locally(database, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _prompt: "owner@example.com")
    assert main([]) == 0
    with Session(database) as session:
        assert session.get(User, "target").role == "admin"


@pytest.mark.parametrize("email", ["missing@example.com", "admin", "not-an-email", ""])
def test_missing_or_invalid_email_never_grants_other_accounts(database, capsys, email):
    assert main([email]) == 1
    assert capsys.readouterr().err
    with Session(database) as session:
        assert list(session.scalars(select(User.role))) == ["student", "student"]


def test_uninitialized_database_shows_migration_guidance(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'empty.db'}")
    assert main(["owner@example.com"]) == 1
    assert "migration" in capsys.readouterr().err


def test_bad_database_configuration_does_not_echo_connection_details(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "invalid database connection")
    assert main(["owner@example.com"]) == 1
    error = capsys.readouterr().err
    assert "DATABASE_URL" in error
    assert "invalid database connection" not in error
