from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
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


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("duration_minutes BETWEEN 1 AND 300", name="ck_exams_duration"),
        CheckConstraint("pass_score BETWEEN 0 AND 100", name="ck_exams_pass_score"),
        CheckConstraint("max_attempts BETWEEN 1 AND 100", name="ck_exams_max_attempts"),
        CheckConstraint("difficulty IN ('easy', 'medium', 'hard')", name="ck_exams_difficulty"),
        CheckConstraint("status IN ('draft', 'published', 'archived')", name="ck_exams_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    pass_score: Mapped[float] = mapped_column(Float, nullable=False, default=70)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


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
