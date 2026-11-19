"""Create draft exam records for US-08."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exams",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("pass_score", sa.Float(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.CheckConstraint("duration_minutes BETWEEN 1 AND 300", name="ck_exams_duration"),
        sa.CheckConstraint("pass_score BETWEEN 0 AND 100", name="ck_exams_pass_score"),
        sa.CheckConstraint("max_attempts BETWEEN 1 AND 100", name="ck_exams_max_attempts"),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_exams_difficulty"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_exams_status"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("exams")
