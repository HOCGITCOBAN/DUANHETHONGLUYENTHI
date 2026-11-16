from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Exam, Subject, User
from app.routes import current_user
from app.schemas import (
    ExamQuestionsWrite,
    ExamResponse,
    ExamWrite,
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
    exam.questions = [question.model_dump() for question in payload.questions]
    db.commit()
    db.refresh(exam)
    return exam
