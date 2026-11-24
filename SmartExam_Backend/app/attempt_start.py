from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.attempt_payload import attempt_payload
from app.attempts import expire_if_due
from app.database import get_db
from app.models import Attempt, Exam, Question, Subject, User
from app.routes import current_user

router = APIRouter(prefix="/exams", tags=["Làm bài"])


@router.post("/{exam_id}/attempts", status_code=status.HTTP_201_CREATED)
def start_attempt(
    exam_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Chỉ sinh viên mới được bắt đầu lượt thi.")

    now = datetime.now(UTC)
    active = db.scalar(
        select(Attempt)
        .where(Attempt.user_id == user.id, Attempt.status == "in_progress")
        .with_for_update()
    )
    if active is not None:
        if expire_if_due(db, active, now):
            active = None
        elif active.exam_id == exam_id:
            return attempt_payload(db, active)
        else:
            raise HTTPException(status_code=409, detail="Bạn đang có một lượt thi chưa hoàn thành.")

    exam = db.get(Exam, exam_id)
    if exam is None or exam.status != "published":
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi khả dụng.")
    subject = db.get(Subject, exam.subject_id)
    if subject is None or not subject.is_active:
        raise HTTPException(status_code=409, detail="Môn học của đề thi hiện không khả dụng.")

    used_attempts = db.scalar(
        select(func.count())
        .select_from(Attempt)
        .where(Attempt.user_id == user.id, Attempt.exam_id == exam.id)
    )
    if used_attempts >= exam.max_attempts:
        raise HTTPException(status_code=409, detail="Bạn đã hết lượt thi.")

    question_ids = [item["question_id"] for item in exam.questions]
    if not question_ids:
        raise HTTPException(status_code=409, detail="Đề thi chưa có câu hỏi.")
    questions = db.scalars(
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.id.in_(question_ids))
    ).all()
    question_map = {question.id: question for question in questions}
    for question_id in question_ids:
        question = question_map.get(question_id)
        if (
            question is None
            or not question.is_active
            or question.subject_id != exam.subject_id
            or len(question.options) < 2
            or sum(option.is_correct for option in question.options) != 1
        ):
            raise HTTPException(status_code=409, detail="Đề thi có câu hỏi không còn khả dụng.")

    attempt = Attempt(
        exam_id=exam.id,
        user_id=user.id,
        status="in_progress",
        started_at=now,
        deadline_at=now + timedelta(minutes=exam.duration_minutes),
    )
    db.add(attempt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bạn đã có một lượt thi đang làm.") from None
    db.refresh(attempt)
    return attempt_payload(db, attempt, exam)
