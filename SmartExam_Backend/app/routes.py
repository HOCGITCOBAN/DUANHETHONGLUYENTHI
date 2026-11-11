from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subject, User
from app.schemas import LoginRequest, RegisterRequest, SubjectResponse, TokenResponse, UserResponse
from app.security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Đăng ký"])
bearer = HTTPBearer(auto_error=False)
subjects_router = APIRouter(tags=["Subjects"])


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise unauthorized from None
    user = db.get(User, claims["sub"])
    if user is None:
        raise unauthorized
    return user


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
        password_hash=hash_password(payload.password.get_secret_value()),
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


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập và cấp JWT",
    responses={401: {"description": "Email hoặc mật khẩu không đúng"}},
)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    valid_password = needs_rehash = False
    if user is not None:
        valid_password, needs_rehash = verify_password(
            user.password_hash, payload.password.get_secret_value()
        )
    if not valid_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if needs_rehash:
        user.password_hash = hash_password(payload.password.get_secret_value())
        db.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role))


@router.get("/me", response_model=UserResponse, summary="Thông tin tài khoản đang đăng nhập")
def me(user: Annotated[User, Depends(current_user)]) -> User:
    return user


@subjects_router.get("/subjects", response_model=list[SubjectResponse])
def list_open_subjects(
    _user: Annotated[User, Depends(current_user)], db: Annotated[Session, Depends(get_db)]
) -> list[Subject]:
    return list(db.scalars(select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.name)))
