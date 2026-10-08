from pydantic import BaseModel
from app.schemas.vocabulary import VocabularyResponse

class CollectionResponse(BaseModel):
    collection_id: int
    collection_name: str
    words: list[VocabularyResponse]
