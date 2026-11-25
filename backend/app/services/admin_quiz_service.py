from fastapi import HTTPException
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.quiz import QuizAnswer, QuizAttempt
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.schemas.admin_quiz import AdminQuizQuestion


ANSWER_COUNT = (
    select(func.count(QuizAnswer.answer_id))
    .where(QuizAnswer.attempt_id == QuizAttempt.attempt_id)
    .correlate(QuizAttempt)
    .scalar_subquery()
)
STATUS = case(
    (QuizAttempt.completed_at.is_not(None), "COMPLETED"),
    (QuizAttempt.aborted_at.is_not(None), "ABORTED"),
    else_="IN_PROGRESS",
)
ATTEMPT_FIELDS = (
    QuizAttempt.attempt_id,
    QuizAttempt.user_id,
    User.username,
    User.full_name,
    QuizAttempt.quiz_type,
    STATUS.label("status"),
    QuizAttempt.total_questions,
    ANSWER_COUNT.label("answered_count"),
    QuizAttempt.correct_answers,
    QuizAttempt.started_at,
    QuizAttempt.completed_at,
    QuizAttempt.aborted_at,
)


def list_attempts(db: Session, q: str, quiz_type: str | None, status: str | None, offset: int, limit: int):
    filters = []
    if query := q.strip():
        matches = [User.username.icontains(query, autoescape=True), User.full_name.icontains(query, autoescape=True)]
        if query.isascii() and query.isdecimal() and int(query) <= 2**63 - 1:
            matches.append(QuizAttempt.attempt_id == int(query))
        filters.append(or_(*matches))
    if quiz_type:
        filters.append(QuizAttempt.quiz_type == quiz_type)
    if status:
        filters.append(STATUS == status)

    total = db.scalar(select(func.count()).select_from(QuizAttempt).join(User).where(*filters))
    items = db.execute(
        select(*ATTEMPT_FIELDS).select_from(QuizAttempt).join(User).where(*filters)
        .order_by(QuizAttempt.started_at.desc().nulls_last(), QuizAttempt.attempt_id.desc())
        .offset(offset).limit(limit)
    ).mappings().all()
    return {"items": items, "total": total, "offset": offset, "limit": limit}


def summary(db: Session):
    by_quiz_type = {}
    totals = {"total": 0, "completed": 0, "in_progress": 0, "aborted": 0}
    status_totals = db.execute(
        select(QuizAttempt.quiz_type, STATUS, func.count()).group_by(QuizAttempt.quiz_type, STATUS)
        .order_by(QuizAttempt.quiz_type)
    )
    for kind, status, count in status_totals:
        group = by_quiz_type.setdefault(kind, {"quiz_type": kind, "total": 0, "completed": 0, "in_progress": 0, "aborted": 0})
        for counters in (group, totals):
            counters[status.lower()] += count
            counters["total"] += count

    answers = db.execute(
        select(QuizAnswer.question_type, func.count().label("answered"),
               func.count().filter(QuizAnswer.is_correct.is_(True)).label("correct"))
        .group_by(QuizAnswer.question_type).order_by(QuizAnswer.question_type)
    ).mappings().all()
    missed = func.count().filter(QuizAnswer.is_correct.is_(False))
    words = db.execute(
        select(Vocabulary.vocabulary_id, Vocabulary.word, func.count().label("answered"), missed.label("missed"))
        .join(QuizAnswer, QuizAnswer.vocabulary_id == Vocabulary.vocabulary_id)
        .group_by(Vocabulary.vocabulary_id, Vocabulary.word).having(missed > 0)
        .order_by(missed.desc(), Vocabulary.vocabulary_id).limit(10)
    ).mappings().all()
    return {**totals, "by_quiz_type": list(by_quiz_type.values()), "by_question_type": answers, "common_misses": words}


def _meaning(word: dict) -> str | None:
    meanings = word.get("meanings") or []
    return meanings[0].get("meaning_vi") if meanings else None


def _answer_details(answer: QuizAnswer, choices: dict):
    user_answer = answer.user_answer
    if answer.question_type != "FILL_BLANK":
        user_answer = choices.get(user_answer, user_answer)
    correct_answer = choices.get(str(answer.vocabulary_id), answer.correct_answer)
    return {"user_answer": user_answer, "correct_answer": correct_answer,
            "is_correct": answer.is_correct, "answered_at": answer.answered_at}


def detail(db: Session, ident: int):
    attempt = db.execute(
        select(*ATTEMPT_FIELDS, QuizAttempt.question_payload).select_from(QuizAttempt)
        .join(User).where(QuizAttempt.attempt_id == ident)
    ).mappings().one_or_none()
    if attempt is None:
        raise HTTPException(404, "Quiz not found")

    answers = list(db.scalars(
        select(QuizAnswer).where(QuizAnswer.attempt_id == ident)
        .order_by(QuizAnswer.question_index.asc().nulls_last(), QuizAnswer.answer_id)
    ))
    by_id = {answer.question_id: answer for answer in answers if answer.question_id is not None}
    by_index = {answer.question_index: answer for answer in answers if answer.question_id is None}
    used = set()
    questions = []
    for index, question in enumerate((attempt["question_payload"] or {}).get("questions", [])):
        word = question["word"]
        kind = question["question_type"]
        options = question["options"] if kind != "FILL_BLANK" else []
        choices = {
            str(option["vocabulary_id"]): (_meaning(option) or option["word"]) if kind == "WORD_TO_IMAGE" else option["word"]
            for option in options
        }
        answer = by_id.get(question["question_id"]) or by_index.get(index)
        recorded = {}
        if answer is not None:
            used.add(answer.answer_id)
            recorded = _answer_details(answer, choices)
        else:
            recorded["correct_answer"] = choices.get(str(word["vocabulary_id"]), word["word"])
        questions.append(AdminQuizQuestion(
            position=index + 1, question_type=kind, word=word["word"], meaning_vi=_meaning(word),
            options=[{"word": option["word"], "meaning_vi": _meaning(option)} for option in options], **recorded,
        ))

    # Older attempts may only have answer rows. Keep their recorded results visible.
    for answer in answers:
        if answer.answer_id not in used:
            questions.append(AdminQuizQuestion(
                position=len(questions) + 1, question_type=answer.question_type, word=answer.correct_answer,
                options=[], **_answer_details(answer, {}),
            ))
    return {key: value for key, value in attempt.items() if key != "question_payload"} | {"questions": questions}
