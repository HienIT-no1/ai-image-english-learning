from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ReviewRequest(BaseModel):
    vocabulary_id: int = Field(gt=0)
    remembered: bool
    event_key: UUID

class WordProgress(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    vocabulary_id: int
    status: str
    review_count: int
    correct_count: int
    incorrect_count: int
    last_reviewed_at: datetime | None

class StudyDay(BaseModel):
    date: date
    count: int

class LearningSummary(BaseModel):
    today: date
    daily_goal: int
    saved_count: int
    mastered_count: int
    needs_review: int
    review_count: int
    today_count: int
    current_streak: int
    longest_streak: int
    quiz_runs: int
    quiz_correct: int
    quiz_total: int
    days: list[StudyDay]
    progress: list[WordProgress]
