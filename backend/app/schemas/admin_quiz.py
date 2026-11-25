from datetime import datetime
from typing import Literal

from pydantic import BaseModel


QuizStatus = Literal["IN_PROGRESS", "COMPLETED", "ABORTED"]


class AdminQuizRow(BaseModel):
    attempt_id: int
    user_id: int
    username: str
    full_name: str | None
    quiz_type: str
    status: QuizStatus
    total_questions: int
    answered_count: int
    correct_answers: int
    started_at: datetime | None
    completed_at: datetime | None
    aborted_at: datetime | None


class AdminQuizPage(BaseModel):
    items: list[AdminQuizRow]
    total: int
    offset: int
    limit: int


class AdminQuizOption(BaseModel):
    word: str
    meaning_vi: str | None = None


class AdminQuizQuestion(BaseModel):
    position: int
    question_type: str
    word: str
    meaning_vi: str | None = None
    options: list[AdminQuizOption]
    user_answer: str | None = None
    correct_answer: str | None = None
    is_correct: bool | None = None
    answered_at: datetime | None = None


class AdminQuizDetail(AdminQuizRow):
    questions: list[AdminQuizQuestion]


class QuizStatusCounts(BaseModel):
    total: int
    completed: int
    in_progress: int
    aborted: int


class QuizTypeCounts(QuizStatusCounts):
    quiz_type: str


class QuizQuestionCounts(BaseModel):
    question_type: str
    answered: int
    correct: int


class QuizMissedWord(BaseModel):
    vocabulary_id: int
    word: str
    answered: int
    missed: int


class AdminQuizSummary(QuizStatusCounts):
    by_quiz_type: list[QuizTypeCounts]
    by_question_type: list[QuizQuestionCounts]
    common_misses: list[QuizMissedWord]
