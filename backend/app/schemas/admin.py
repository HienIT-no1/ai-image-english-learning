from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, PositiveInt

class AdminInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class TopicInput(AdminInput):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    symbol: str = Field(default="📚", min_length=1, max_length=20)

class VocabularyInput(AdminInput):
    word: str = Field(min_length=1, max_length=100)
    ipa: str = Field(default="", max_length=100)
    meaning_vi: str = Field(min_length=1, max_length=2000)
    sentence_en: str = Field(default="", max_length=2000)
    sentence_vi: str = Field(default="", max_length=2000)
    topic_ids: list[PositiveInt] = Field(default_factory=list, max_length=50)

class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    username: str
    email: str
    full_name: str | None
    role: Literal["USER", "ADMIN"]

class AdminSummary(BaseModel):
    users: int
    admins: int
    topics: int
    vocabularies: int
    completed_quizzes: int
