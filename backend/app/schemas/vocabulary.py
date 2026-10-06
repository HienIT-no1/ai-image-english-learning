from pydantic import BaseModel


class VocabularyMeaningResponse(BaseModel):
    meaning_id: int
    meaning_vi: str
    definition_en: str | None = None


class VocabularyExampleResponse(BaseModel):
    example_id: int
    sentence_en: str
    sentence_vi: str | None = None


class VocabularyRelationResponse(BaseModel):
    relation_id: int
    relation_type: str
    related_vocabulary_id: int | None = None
    related_text: str | None = None


class VocabularyResponse(BaseModel):
    vocabulary_id: int
    word: str
    ipa: str | None = None
    part_of_speech: str | None = None
    level: str | None = None
    audio_url: str | None = None
    meanings: list[VocabularyMeaningResponse]
    examples: list[VocabularyExampleResponse]
    relations: list[VocabularyRelationResponse]