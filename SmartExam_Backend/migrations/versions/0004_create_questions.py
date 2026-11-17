"""Create the question bank (questions and options) for US-07 / US-09."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(10), server_default="medium", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(
            "difficulty IN ('easy', 'medium', 'hard')", name="ck_questions_difficulty"
        ),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_questions_subject_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "question_options",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name="fk_question_options_question_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("question_options")
    op.drop_table("questions")
