"""Create attempts and attempt_answers for US-14 / US-17."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("exam_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("correct_count", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.CheckConstraint(
            "status IN ('in_progress', 'submitted', 'expired')", name="ck_attempts_status"
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], name="fk_attempts_exam_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_attempts_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "attempt_answers",
        sa.Column("attempt_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("option_id", sa.String(36), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["attempts.id"],
            name="fk_attempt_answers_attempt_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="fk_attempt_answers_question_id"
        ),
        sa.ForeignKeyConstraint(
            ["option_id"], ["question_options.id"], name="fk_attempt_answers_option_id"
        ),
        sa.PrimaryKeyConstraint("attempt_id", "question_id"),
    )


def downgrade() -> None:
    op.drop_table("attempt_answers")
    op.drop_table("attempts")
