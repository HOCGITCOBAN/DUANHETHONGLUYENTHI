"""Create exam_questions, the 8th table (exam <-> question link with order and points)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exam_questions",
        sa.Column("exam_id", sa.String(36), nullable=False),
        sa.Column("question_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("points", sa.Float(), server_default="1", nullable=False),
        sa.CheckConstraint("points > 0 AND points <= 100", name="ck_exam_questions_points"),
        sa.CheckConstraint("position >= 0", name="ck_exam_questions_position"),
        sa.ForeignKeyConstraint(
            ["exam_id"], ["exams.id"], name="fk_exam_questions_exam_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"], name="fk_exam_questions_question_id"
        ),
        sa.PrimaryKeyConstraint("exam_id", "question_id"),
        sa.UniqueConstraint("exam_id", "position", name="uq_exam_questions_exam_position"),
    )
    op.create_index("ix_exam_questions_question_id", "exam_questions", ["question_id"])
    if not context.is_offline_mode():
        _backfill_from_exam_json()


def _backfill_from_exam_json() -> None:
    """Copy the legacy exams.questions JSON into rows, skipping invalid or duplicate items."""
    bind = op.get_bind()
    exams = sa.table("exams", sa.column("id", sa.String), sa.column("questions", sa.JSON))
    questions = sa.table("questions", sa.column("id", sa.String))
    exam_questions = sa.table(
        "exam_questions",
        sa.column("exam_id", sa.String),
        sa.column("question_id", sa.String),
        sa.column("position", sa.Integer),
        sa.column("points", sa.Float),
    )
    known = {row[0] for row in bind.execute(sa.select(questions.c.id))}
    rows = []
    for exam_id, items in bind.execute(sa.select(exams.c.id, exams.c.questions)):
        seen: set[str] = set()
        for item in items or []:
            if not isinstance(item, dict):
                continue
            question_id, points = item.get("question_id"), item.get("points", 1)
            if (
                question_id not in known
                or question_id in seen
                or isinstance(points, bool)
                or not isinstance(points, int | float)
                or not 0 < points <= 100
            ):
                continue
            rows.append(
                {
                    "exam_id": exam_id,
                    "question_id": question_id,
                    "position": len(seen),
                    "points": float(points),
                }
            )
            seen.add(question_id)
    if rows:
        op.bulk_insert(exam_questions, rows)


def downgrade() -> None:
    op.drop_index("ix_exam_questions_question_id", table_name="exam_questions")
    op.drop_table("exam_questions")
