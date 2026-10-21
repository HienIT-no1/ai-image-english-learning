from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.schemas.vocabulary import VocabularyResponse

class GameStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_session_id: UUID
    source: Literal["RANDOM","TOPIC","SAVED","DIFFICULT","REVIEW"]
    topic_id: int | None = Field(default=None,gt=0)
    @model_validator(mode="after")
    def validate_topic(self):
        if (self.source == "TOPIC") != (self.topic_id is not None):
            raise ValueError("Choose a topic only for TOPIC mode")
        return self

class GameOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vocabulary_id: int = Field(gt=0)
    outcome: Literal["SOLVED","MISSED"]
    answer: str | None = Field(default=None,max_length=100)
    wrong_letters: int = Field(default=0,ge=0,le=100000)

class GameFinish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    results: list[GameOutcome] = Field(min_length=1,max_length=20)

class GameRoundResponse(BaseModel):
    round_id: int
    stage: int
    words: list[VocabularyResponse]
    results: list[GameOutcome]
    status: str
    correct_count: int
    missed_count: int
    max_combo: int
    score: int

class GameResponse(BaseModel):
    run_id: int
    source: str
    topic_id: int | None
    pool_count: int
    remaining_count: int
    completed: bool
    total_score: int
    round: GameRoundResponse
