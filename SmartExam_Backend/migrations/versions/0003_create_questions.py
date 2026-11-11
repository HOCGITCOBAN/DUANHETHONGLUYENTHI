"""Create questions and ordered answer options for US-06 / T05F917."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("explanation", sa.String(5000), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')", name="ck_questions_difficulty"
        ),
    )
    op.create_index("ix_questions_subject_id", "questions", ["subject_id"])
    op.create_table(
        "question_options",
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("question_id", "id"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("question_id", "position", name="uq_question_options_position"),
        sa.CheckConstraint("position >= 0 AND position < 6", name="ck_question_options_position"),
    )


def downgrade() -> None:
    op.drop_table("question_options")
    op.drop_index("ix_questions_subject_id", table_name="questions")
    op.drop_table("questions")
