from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exam

PUBLISHED_LOCK_MESSAGE = (
    "Câu hỏi đang nằm trong đề thi đã xuất bản nên không thể sửa hoặc xóa. "
    "Hãy lưu trữ đề thi trước."
)
IN_EXAM_MESSAGE = (
    "Câu hỏi đang được dùng trong đề thi nên không thể xóa. Hãy ẩn câu hỏi bằng is_active=false."
)


def _contains(items: object, question_id: str) -> bool:
    # exams.questions là danh sách {"question_id", "points"} do PUT /admin/exams/{id}/questions ghi.
    return isinstance(items, list) and any(
        isinstance(item, dict) and item.get("question_id") == question_id for item in items
    )


def is_in_published_exam(db: Session, question_id: str) -> bool:
    published = db.scalars(select(Exam.questions).where(Exam.status == "published"))
    return any(_contains(items, question_id) for items in published)


def is_in_any_exam(db: Session, question_id: str) -> bool:
    return any(_contains(items, question_id) for items in db.scalars(select(Exam.questions)))


def ensure_not_in_published_exam(db: Session, question_id: str) -> None:
    """Chặn sửa/xóa câu hỏi (kể cả các phương án của nó) đã nằm trong đề `published`."""
    if is_in_published_exam(db, question_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=PUBLISHED_LOCK_MESSAGE)


def ensure_not_in_any_exam(db: Session, question_id: str) -> None:
    if is_in_any_exam(db, question_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=IN_EXAM_MESSAGE)
