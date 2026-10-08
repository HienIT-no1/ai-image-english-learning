from typing import Literal
from uuid import UUID
from pydantic import BaseModel,Field,ConfigDict
from app.schemas.vocabulary import VocabularyResponse
from app.schemas.learning import LearningSummary

QuizType=Literal['IMAGE_TO_WORD','WORD_TO_IMAGE','LISTENING','FILL_BLANK','MIXED']
class QuizStart(BaseModel):
    model_config=ConfigDict(extra="forbid")
    quiz_type: QuizType
    count: int=Field(default=8,ge=1,le=20)
    client_session_id: UUID
class QuizSubmit(BaseModel):
    model_config=ConfigDict(extra="forbid")
    question_id: UUID
    answer: str=Field(min_length=1,max_length=100)
class QuizQuestionResponse(BaseModel):
    question_id: str
    question_type: str
    word: VocabularyResponse
    options: list[VocabularyResponse]
class QuizFeedback(BaseModel):
    question_id: str
    user_answer: str | None
    is_correct: bool
    correct_answer: str
    correct_choice_key: str
    word: VocabularyResponse
class QuizResponse(BaseModel):
    attempt_id: int
    quiz_type: str
    total_questions: int
    correct_answers: int
    answered_count: int
    completed: bool
    aborted: bool
    questions: list[QuizQuestionResponse]
    answers: list[QuizFeedback]
class AnswerResponse(BaseModel):
    feedback: QuizFeedback
    progress: LearningSummary
