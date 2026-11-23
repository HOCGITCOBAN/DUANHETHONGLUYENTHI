import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_migration_upgrade_matches_models_and_can_be_reversed(tmp_path):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    env = {**os.environ, "DATABASE_URL": url}

    def alembic(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    alembic("upgrade", "head")
    alembic("check")
    engine = create_engine(url)
    try:
        assert "users" in inspect(engine).get_table_names()
        assert {"questions", "question_options"} <= set(inspect(engine).get_table_names())
        assert inspect(engine).get_foreign_keys("questions")[0]["referred_table"] == "subjects"
        assert (
            inspect(engine).get_foreign_keys("question_options")[0]["referred_table"] == "questions"
        )
        assert inspect(engine).get_unique_constraints("users")[0]["column_names"] == ["email"]
        alembic("downgrade", "base")
        assert "users" not in inspect(engine).get_table_names()
        assert "questions" not in inspect(engine).get_table_names()
        assert "question_options" not in inspect(engine).get_table_names()
        alembic("upgrade", "head")
        assert "users" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_question_upgrade_preserves_existing_users_and_subjects(tmp_path):
    url = f"sqlite:///{tmp_path / 'existing.db'}"
    env = {**os.environ, "DATABASE_URL": url}

    def alembic(*args):
        subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

    alembic("upgrade", "0002")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, full_name, email, password_hash, role) "
                    "VALUES ('existing-user', 'Student', "
                    "'student@example.com', 'unused', 'student')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO subjects (id, name, slug, is_active) "
                    "VALUES ('existing-subject', 'JavaScript', 'javascript', 1)"
                )
            )
        alembic("upgrade", "head")
        alembic("check")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT email FROM users")) == "student@example.com"
            assert connection.scalar(text("SELECT slug FROM subjects")) == "javascript"
        assert {"questions", "question_options"} <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
