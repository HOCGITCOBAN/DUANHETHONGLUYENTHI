"""US-06 / T05F917: admin question bank and answer options."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Question, QuestionOption, Subject
from app.schemas import Difficulty, QuestionPatch, QuestionResponse, QuestionWrite

# Included under admin_router so every operation inherits require_admin.
router = APIRouter(prefix="/questions", tags=["Ngân hàng câu hỏi"])
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[QuestionResponse])
def list_questions(
    db: Database,
    subject_id: str | None = None,
    difficulty: Difficulty | None = None,
    is_active: bool | None = None,
) -> list[Question]:
    statement = select(Question).options(selectinload(Question.options))
    if subject_id is not None:
        statement = statement.where(Question.subject_id == subject_id)
    if difficulty is not None:
        statement = statement.where(Question.difficulty == difficulty)
    if is_active is not None:
        statement = statement.where(Question.is_active == is_active)
    return list(db.scalars(statement.order_by(Question.text, Question.id)))


def require_subject(db: Session, subject_id: str) -> None:
    if db.get(Subject, subject_id) is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học.")


@router.post("", response_model=QuestionResponse, status_code=201)
def create_question(payload: QuestionWrite, db: Database) -> Question:
    require_subject(db, payload.subject_id)
    question = Question(**payload.model_dump(exclude={"options"}))
    question.options = [
        QuestionOption(**option.model_dump(), position=index)
        for index, option in enumerate(payload.options)
    ]
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.patch("/{question_id}", response_model=QuestionResponse)
def update_question(question_id: str, payload: QuestionPatch, db: Database) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    changes = payload.model_dump(exclude_unset=True, exclude={"options"})
    if "subject_id" in changes:
        require_subject(db, changes["subject_id"])
    for field, value in changes.items():
        setattr(question, field, value)
    if payload.options is not None:
        # Flush deletions before reusing IDs or positions; the entire edit commits together.
        question.options.clear()
        db.flush()
        question.options.extend(
            QuestionOption(**option.model_dump(), position=index)
            for index, option in enumerate(payload.options)
        )
    db.commit()
    db.refresh(question)
    return question
