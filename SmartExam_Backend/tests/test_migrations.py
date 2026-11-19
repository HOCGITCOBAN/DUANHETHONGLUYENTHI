import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect

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
        assert inspect(engine).get_unique_constraints("users")[0]["column_names"] == ["email"]
        alembic("downgrade", "base")
        assert "users" not in inspect(engine).get_table_names()
        alembic("upgrade", "head")
        assert "users" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


EXPECTED_TABLES = {
    "users",
    "subjects",
    "exams",
    "questions",
    "question_options",
    "exam_questions",
    "attempts",
    "attempt_answers",
}


def test_migration_creates_all_eight_tables(tmp_path):
    url = f"sqlite:///{tmp_path / 'tables.db'}"
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
        assert tables == EXPECTED_TABLES
        pk = inspect(engine).get_pk_constraint("exam_questions")["constrained_columns"]
        assert pk == ["exam_id", "question_id"]
    finally:
        engine.dispose()
