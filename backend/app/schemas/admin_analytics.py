from datetime import date
from typing import Literal

from pydantic import BaseModel


GameType = Literal["WORD_SHOOTER", "WORD_DEFENSE"]


class AnalyticsPeriod(BaseModel):
    start_date: date
    end_date: date


class LearningMetrics(BaseModel):
    active_learners: int
    study_events: int
    correct_events: int
    accuracy_rate: float | None
    eligible_learner_days: int
    returned_learner_days: int
    next_day_return_rate: float | None


class LearningDay(LearningMetrics):
    date: date


class DifficultWord(BaseModel):
    vocabulary_id: int
    word: str
    attempts: int
    incorrect: int
    incorrect_rate: float


class LearningAnalytics(AnalyticsPeriod, LearningMetrics):
    daily: list[LearningDay]
    hardest_words: list[DifficultWord]


class GameMetrics(BaseModel):
    game_runs: int
    scored_runs: int
    average_score: float | None
    passed_rounds: int


class GameDay(GameMetrics):
    date: date


class MissedWord(BaseModel):
    vocabulary_id: int
    word: str
    misses: int


class GameAnalytics(AnalyticsPeriod, GameMetrics):
    game_type: GameType | None
    daily: list[GameDay]
    most_missed_words: list[MissedWord]
