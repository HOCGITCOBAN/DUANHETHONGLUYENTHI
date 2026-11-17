from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.attempt_payload import attempt_payload
from app.attempts import expire_if_due
from app.database import get_db
from app.models import Attempt, User
from app.routes import current_user

router = APIRouter(prefix="/attempts", tags=["Làm bài"])


@router.get("/{attempt_id}")
def get_attempt(
    attempt_id: str,
    user: Annotated[User, Depends(current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    attempt = db.scalar(select(Attempt).where(Attempt.id == attempt_id, Attempt.user_id == user.id))
    if attempt is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy lượt thi.")
    expire_if_due(db, attempt, datetime.now(UTC))
    return attempt_payload(db, attempt)
