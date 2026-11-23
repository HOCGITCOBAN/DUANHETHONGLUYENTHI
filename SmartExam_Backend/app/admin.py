from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Exam, Question, QuestionOption, Subject, User
from app.question_lock import ensure_not_in_any_exam, ensure_not_in_published_exam
from app.routes import current_user
from app.schemas import (
    ExamQuestionsWrite,
    ExamResponse,
    ExamWrite,
    QuestionResponse,
    QuestionWrite,
    SubjectResponse,
    SubjectWrite,
)


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    # current_user trả 401 khi thiếu/sai/hết hạn token.
    # Ở đây là đã đăng nhập nhưng không phải admin.
    # Role lấy từ CSDL (không tin claim `role` trong token), nên đổi quyền có hiệu lực ngay.
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác này.",
        )
    return user


# Mọi route quản trị thêm vào router này tự động yêu cầu quyền admin (401/403).
admin_router = APIRouter(
    prefix="/admin",
    tags=["Quản trị"],
    dependencies=[Depends(require_admin)],
)


@admin_router.get("/subjects", response_model=list[SubjectResponse])
def list_subjects(db: Annotated[Session, Depends(get_db)]) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)))


@admin_router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectWrite, db: Annotated[Session, Depends(get_db)]) -> Subject:
    subject = Subject(**payload.model_dump())
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug môn học đã tồn tại.") from None
    db.refresh(subject)
    return subject


@admin_router.patch("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: str, payload: SubjectWrite, db: Annotated[Session, Depends(get_db)]
) -> Subject:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học.")
    for key, value in payload.model_dump().items():
        setattr(subject, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug môn học đã tồn tại.") from None
    db.refresh(subject)
    return subject


@admin_router.get("/exams", response_model=list[ExamResponse])
def list_exams(db: Annotated[Session, Depends(get_db)]) -> list[Exam]:
    return list(db.scalars(select(Exam).order_by(Exam.title)))


def ensure_subject(db: Session, subject_id: str) -> None:
    if db.get(Subject, subject_id) is None:
        raise HTTPException(status_code=422, detail="Môn học không tồn tại.")


@admin_router.post("/exams", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamWrite, db: Annotated[Session, Depends(get_db)]) -> Exam:
    ensure_subject(db, payload.subject_id)
    exam = Exam(**payload.model_dump(), status="draft", questions=[])
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@admin_router.patch("/exams/{exam_id}", response_model=ExamResponse)
def update_exam(exam_id: str, payload: ExamWrite, db: Annotated[Session, Depends(get_db)]) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi.")
    if exam.status != "draft":
        raise HTTPException(status_code=409, detail="Chỉ chỉnh sửa được đề nháp.")
    ensure_subject(db, payload.subject_id)
    for key, value in payload.model_dump().items():
        setattr(exam, key, value)
    db.commit()
    db.refresh(exam)
    return exam


def ensure_questions_exist(db: Session, question_ids: list[str]) -> None:
    if not question_ids:
        return
    found = set(db.scalars(select(Question.id).where(Question.id.in_(question_ids))))
    missing = [question_id for question_id in question_ids if question_id not in found]
    if missing:
        raise HTTPException(
            status_code=422, detail="Câu hỏi không tồn tại: " + ", ".join(missing) + "."
        )


@admin_router.put("/exams/{exam_id}/questions", response_model=ExamResponse)
def update_exam_questions(
    exam_id: str, payload: ExamQuestionsWrite, db: Annotated[Session, Depends(get_db)]
) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy đề thi.")
    if exam.status != "draft":
        raise HTTPException(status_code=409, detail="Chỉ chỉnh sửa được đề nháp.")
    question_ids = [question.question_id for question in payload.questions]
    if len(set(question_ids)) != len(question_ids):
        raise HTTPException(status_code=422, detail="Câu hỏi trong đề không được trùng.")
    ensure_questions_exist(db, question_ids)
    exam.questions = [question.model_dump() for question in payload.questions]
    db.commit()
    db.refresh(exam)
    return exam


def _fill_question(question: Question, payload: QuestionWrite) -> None:
    question.subject_id = payload.subject_id
    question.text = payload.text
    question.explanation = payload.explanation
    question.difficulty = payload.difficulty
    question.is_active = payload.is_active
    # Phương án luôn được thay trọn bộ cùng câu hỏi, nên chúng chịu cùng khóa với câu hỏi.
    question.options = [
        QuestionOption(text=option.text, is_correct=option.is_correct, position=index)
        for index, option in enumerate(payload.options)
    ]


def _get_question(db: Session, question_id: str) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    return question


@admin_router.get("/questions", response_model=list[QuestionResponse])
def list_questions(db: Annotated[Session, Depends(get_db)]) -> list[Question]:
    statement = select(Question).options(selectinload(Question.options)).order_by(Question.text)
    return list(db.scalars(statement))


@admin_router.post(
    "/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED
)
def create_question(payload: QuestionWrite, db: Annotated[Session, Depends(get_db)]) -> Question:
    ensure_subject(db, payload.subject_id)
    question = Question()
    _fill_question(question, payload)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@admin_router.patch("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: str, payload: QuestionWrite, db: Annotated[Session, Depends(get_db)]
) -> Question:
    question = _get_question(db, question_id)
    ensure_not_in_published_exam(db, question_id)  # US-07: 409 nếu nằm trong đề published
    ensure_subject(db, payload.subject_id)
    _fill_question(question, payload)
    db.commit()
    db.refresh(question)
    return question


@admin_router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: str, db: Annotated[Session, Depends(get_db)]) -> None:
    question = _get_question(db, question_id)
    ensure_not_in_published_exam(db, question_id)  # US-07
    ensure_not_in_any_exam(db, question_id)  # đã dùng trong đề thì ẩn bằng is_active=false
    db.delete(question)
    db.commit()
