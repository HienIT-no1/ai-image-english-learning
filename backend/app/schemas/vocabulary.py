from pydantic import BaseModel, ConfigDict, Field
from app.schemas.topic import TopicSummary


class VocabularyMeaningResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    meaning_id: int
    meaning_vi: str
    definition_en: str | None = None


class VocabularyExampleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    example_id: int
    sentence_en: str
    sentence_vi: str | None = None


class VocabularyRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    relation_id: int
    relation_type: str
    related_vocabulary_id: int | None = None
    related_text: str | None = None


class VocabularyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    topics: list[TopicSummary] = Field(default_factory=list)
    vocabulary_id: int
    word: str
    ipa: str | None = None
    part_of_speech: str | None = None
    level: str | None = None
    audio_url: str | None = None
    meanings: list[VocabularyMeaningResponse]
    examples: list[VocabularyExampleResponse]
    relations: list[VocabularyRelationResponse]