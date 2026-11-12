"""Create questions, options and exams for US-07 (published question protection)."""

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
    op.create_table(
        "exams",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("subject_id", sa.String(36), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("pass_score", sa.Float(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(10), server_default="medium", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_exams_difficulty"),
        sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_exams_status"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], name="fk_exams_subject_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "exam_questions",
        sa.Column("exam_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("points", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["exams.id"], name="fk_exam_questions_exam_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name="fk_exam_questions_question_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("exam_id", "question_id"),
    )
    op.create_index("ix_exam_questions_question_id", "exam_questions", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_questions_question_id", table_name="exam_questions")
    op.drop_table("exam_questions")
    op.drop_table("exams")
    op.drop_table("question_options")
    op.drop_table("questions")
