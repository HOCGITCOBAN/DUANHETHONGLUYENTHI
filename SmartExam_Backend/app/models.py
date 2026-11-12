from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('student', 'admin')", name="ck_users_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="student", server_default=text("'student'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.current_timestamp(),
    )


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("slug", name="uq_subjects_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_questions_difficulty"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", name="fk_questions_subject_id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium", server_default="medium"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.position",
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", name="fk_question_options_question_id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    question: Mapped["Question"] = relationship(back_populates="options")


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_exams_difficulty"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_exams_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    subject_id: Mapped[str] = mapped_column(
        ForeignKey("subjects.id", name="fk_exams_subject_id"), nullable=False
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    pass_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium", server_default="medium"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (Index("ix_exam_questions_question_id", "question_id"),)

    exam_id: Mapped[str] = mapped_column(
        ForeignKey("exams.id", name="fk_exam_questions_exam_id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("questions.id", name="fk_exam_questions_question_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    points: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
