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
