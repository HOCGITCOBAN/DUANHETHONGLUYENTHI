from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subject, User
from app.questions import router as questions_router
from app.routes import current_user
from app.schemas import SubjectResponse, SubjectWrite


def require_admin(user: Annotated[User, Depends(current_user)]) -> User:
    # current_user trả 401 khi thiếu/sai/hết hạn token. Ở đây là đã đăng nhập nhưng không phải admin.
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
admin_router.include_router(questions_router)


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
