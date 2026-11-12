from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exam, ExamQuestion

PUBLISHED_LOCK_MESSAGE = (
    "Câu hỏi đang nằm trong đề thi đã xuất bản nên không thể sửa hoặc xóa. "
    "Hãy lưu trữ đề thi trước."
)
IN_EXAM_MESSAGE = (
    "Câu hỏi đang được dùng trong đề thi nên không thể xóa. Hãy ẩn câu hỏi bằng is_active=false."
)


def is_in_published_exam(db: Session, question_id: str) -> bool:
    statement = (
        select(ExamQuestion.question_id)
        .join(Exam, Exam.id == ExamQuestion.exam_id)
        .where(ExamQuestion.question_id == question_id, Exam.status == "published")
        .limit(1)
    )
    return db.scalar(statement) is not None


def is_in_any_exam(db: Session, question_id: str) -> bool:
    statement = select(ExamQuestion.question_id).where(ExamQuestion.question_id == question_id)
    return db.scalar(statement.limit(1)) is not None


def ensure_not_in_published_exam(db: Session, question_id: str) -> None:
    """Chặn sửa/xóa câu hỏi (kể cả các phương án của nó) đã nằm trong đề `published`."""
    if is_in_published_exam(db, question_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=PUBLISHED_LOCK_MESSAGE)


def ensure_not_in_any_exam(db: Session, question_id: str) -> None:
    if is_in_any_exam(db, question_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IN_EXAM_MESSAGE)
