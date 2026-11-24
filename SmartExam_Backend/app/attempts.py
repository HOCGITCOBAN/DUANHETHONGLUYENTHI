from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Attempt, AttemptAnswer, Exam, QuestionOption, User
from app.routes import current_user
from app.schemas import AnswerResponse, AnswerWrite

router = APIRouter(prefix="/attempts", tags=["Làm bài"])

TIME_UP_MESSAGE = "Đã hết giờ làm bài. Bài thi đã được chấm tự động, không thể lưu thêm đáp án."
FINISHED_MESSAGE = "Bài thi đã kết thúc, không thể lưu thêm đáp án."


def utc_now() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    # SQLite trả datetime không có múi giờ; mọi mốc thời gian ở đây đều lưu theo UTC.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def grade_attempt(db: Session, attempt: Attempt, exam: Exam) -> None:
    """Chấm các đáp án đã lưu: điểm thang 0-100 theo `points` từng câu, câu bỏ trống là 0."""
    points = {item["question_id"]: float(item["points"]) for item in exam.questions}
    correct_questions = set(
        db.scalars(
            select(AttemptAnswer.question_id)
            .join(
                QuestionOption,
                (QuestionOption.id == AttemptAnswer.option_id)
                & (QuestionOption.question_id == AttemptAnswer.question_id),
            )
            .where(AttemptAnswer.attempt_id == attempt.id, QuestionOption.is_correct.is_(True))
        )
    ) & points.keys()
    total = sum(points.values())
    earned = sum(points[question_id] for question_id in correct_questions)
    attempt.score = round(earned / total * 100, 2) if total > 0 else 0.0
    attempt.correct_count = len(correct_questions)
    attempt.passed = attempt.score >= exam.pass_score


def expire_if_due(db: Session, attempt: Attempt, now: datetime | None = None) -> bool:
    """US-17: nếu quá hạn thì chuyển sang `expired` và chốt điểm. Trả True nếu vừa chuyển."""
    if attempt.status != "in_progress":
        return False
    deadline = as_utc(attempt.deadline_at)
    if (now or utc_now()) <= deadline:
        return False
    grade_attempt(db, attempt, db.get(Exam, attempt.exam_id))
    attempt.status = "expired"
    attempt.submitted_at = deadline  # đáp án sau hạn không được nhận, nên mốc kết thúc là hạn chót
    db.commit()
    return True


def expire_overdue_attempts(db: Session, now: datetime | None = None) -> int:
    """Chốt hàng loạt các lượt thi quá hạn mà không ai còn truy cập (dùng cho tác vụ định kỳ)."""
    overdue = db.scalars(
        select(Attempt).where(
            Attempt.status == "in_progress", Attempt.deadline_at < (now or utc_now())
        )
    ).all()
    for attempt in overdue:
        expire_if_due(db, attempt, now)
    return len(overdue)


@router.put("/{attempt_id}/answers/{question_id}", response_model=AnswerResponse)
def save_answer(
    attempt_id: str,
    question_id: str,
    payload: AnswerWrite,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> AnswerResponse:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt thi.")

    now = utc_now()
    # US-14: chỉ nhận đáp án khi now <= deadline_at; quá hạn thì chốt điểm (US-17) rồi từ chối.
    if expire_if_due(db, attempt, now) or attempt.status == "expired":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=TIME_UP_MESSAGE)
    if attempt.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=FINISHED_MESSAGE)

    exam = db.get(Exam, attempt.exam_id)
    if question_id not in {item["question_id"] for item in exam.questions}:
        raise HTTPException(status_code=404, detail="Câu hỏi không thuộc lượt thi này.")
    option = db.get(QuestionOption, payload.option_id)
    if option is None or option.question_id != question_id:
        raise HTTPException(status_code=422, detail="Phương án không thuộc câu hỏi này.")

    answer = db.get(AttemptAnswer, (attempt_id, question_id))
    if answer is None:
        db.add(
            AttemptAnswer(
                attempt_id=attempt_id, question_id=question_id, option_id=option.id, answered_at=now
            )
        )
    else:
        answer.option_id = option.id
        answer.answered_at = now
    db.commit()
    return AnswerResponse(question_id=question_id, option_id=option.id)


@router.post("/{attempt_id}/submit")
def submit_attempt(
    attempt_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """T05F921: US-16 Chấm điểm tự động và nộp bài (Idempotent trong Transaction)."""
    stmt = select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == user.id)
    if db.bind and db.bind.dialect.name != "sqlite":
        stmt = stmt.with_for_update()
    attempt = db.scalar(stmt)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt thi.")

    # Idempotent: Nếu đã nộp trước đó, trả về ngay kết quả hiện có, không tính lại hay nhân đôi điểm
    if attempt.status in ("submitted", "expired"):
        return {
            "id": attempt.id,
            "exam_id": attempt.exam_id,
            "user_id": attempt.user_id,
            "status": attempt.status,
            "started_at": attempt.started_at.isoformat(),
            "deadline_at": attempt.deadline_at.isoformat(),
            "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
            "score": attempt.score,
            "correct_count": attempt.correct_count,
            "passed": attempt.passed,
        }

    now = utc_now()
    deadline = as_utc(attempt.deadline_at)
    is_overdue = now > deadline

    exam = db.get(Exam, attempt.exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi.")

    # Tính điểm: Điểm = 100 * (Điểm đúng / Tổng điểm)
    grade_attempt(db, attempt, exam)

    attempt.status = "expired" if is_overdue else "submitted"
    attempt.submitted_at = deadline if is_overdue else now
    db.commit()

    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "user_id": attempt.user_id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "deadline_at": attempt.deadline_at.isoformat(),
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "score": attempt.score,
        "correct_count": attempt.correct_count,
        "passed": attempt.passed,
    }
