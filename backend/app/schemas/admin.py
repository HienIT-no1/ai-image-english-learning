from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator
from datetime import datetime
from app.schemas.learning import LearningSummary

class AdminInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class TopicInput(AdminInput):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    symbol: str = Field(default="📚", min_length=1, max_length=20)

class VocabularyMeaningInput(AdminInput):
    meaning_id: PositiveInt | None = None
    meaning_vi: str = Field(min_length=1, max_length=2000)
    definition_en: str | None = Field(default=None, max_length=2000)


class VocabularyExampleInput(AdminInput):
    example_id: PositiveInt | None = None
    sentence_en: str = Field(min_length=1, max_length=2000)
    sentence_vi: str | None = Field(default=None, max_length=2000)


class VocabularyInput(AdminInput):
    word: str = Field(min_length=1, max_length=100)
    ipa: str = Field(default="", max_length=100)
    meaning_vi: str | None = Field(default=None, min_length=1, max_length=2000)
    sentence_en: str = Field(default="", max_length=2000)
    sentence_vi: str = Field(default="", max_length=2000)
    meanings: list[VocabularyMeaningInput] | None = Field(default=None, min_length=1, max_length=50)
    examples: list[VocabularyExampleInput] | None = Field(default=None, max_length=50)
    topic_ids: list[PositiveInt] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_content_input(self):
        if self.model_fields_set & {"meanings", "examples"}:
            if self.meanings is None or self.examples is None:
                raise ValueError("Both meanings and examples must be provided")
            if self.model_fields_set & {"meaning_vi", "sentence_en", "sentence_vi"}:
                raise ValueError("Send either the full lists or the primary meaning and example")
        elif self.meaning_vi is None:
            raise ValueError("At least one Vietnamese meaning is required")
        return self

class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    username: str
    email: str
    full_name: str | None
    role: Literal["USER", "ADMIN"]
    is_locked: bool


class UserLockInput(AdminInput):
    is_locked: bool = Field(strict=True)


class UserDeleteInput(AdminInput):
    username: str = Field(min_length=3, max_length=50)


class AdminUserDetail(AdminUserResponse):
    created_at: datetime
    cefr_level: str | None
    learning: LearningSummary
    vocabulary_names: dict[int, str]
    game_runs: int
    game_score: int

class AdminSummary(BaseModel):
    users: int
    admins: int
    topics: int
    vocabularies: int
    completed_quizzes: int
