from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import RegisterRequest, UserResponse
from app.security import password_hasher

router = APIRouter(prefix="/auth", tags=["Đăng ký"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản sinh viên",
    responses={409: {"description": "Email đã được đăng ký"}},
)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> User:
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=password_hasher.hash(payload.password.get_secret_value()),
        role="student",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # The UNIQUE constraint also protects concurrent registration requests.
        if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email đã được đăng ký.",
            ) from None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo tài khoản. Vui lòng thử lại.",
        ) from None
    db.refresh(user)
    return user
