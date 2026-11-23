from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Attempt, AttemptAnswer, Exam, Question


def attempt_payload(db: Session, attempt: Attempt, exam: Exam | None = None) -> dict:
    exam = exam or db.get(Exam, attempt.exam_id)
    question_ids = [item["question_id"] for item in exam.questions]
    questions = db.scalars(
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.id.in_(question_ids))
    ).all()
    questions_by_id = {question.id: question for question in questions}
    snapshot_questions = []
    for item in exam.questions:
        question = questions_by_id[item["question_id"]]
        snapshot_questions.append(
            {
                "id": question.id,
                "subject_id": question.subject_id,
                "text": question.text,
                "options": [{"id": option.id, "text": option.text} for option in question.options],
                "difficulty": question.difficulty,
                "is_active": question.is_active,
                "points": item["points"],
            }
        )
    answers = {
        answer.question_id: answer.option_id
        for answer in db.scalars(
            select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt.id)
        )
    }
    return {
        "id": attempt.id,
        "exam_id": attempt.exam_id,
        "user_id": attempt.user_id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "deadline_at": attempt.deadline_at.isoformat(),
        "answers": answers,
        "snapshot": {
            "id": exam.id,
            "title": exam.title,
            "description": exam.description,
            "subject_id": exam.subject_id,
            "difficulty": exam.difficulty,
            "duration_minutes": exam.duration_minutes,
            "pass_score": exam.pass_score,
            "max_attempts": exam.max_attempts,
            "status": exam.status,
            "questions": snapshot_questions,
        },
    }
