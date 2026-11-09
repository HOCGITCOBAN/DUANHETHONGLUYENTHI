from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.routes import current_user


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
