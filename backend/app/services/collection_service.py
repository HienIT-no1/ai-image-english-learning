from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.vocabulary import Vocabulary
from app.repositories import collection_repository as repository
from app.schemas.collection import CollectionResponse

def read_collection(db: Session, user_id: int) -> CollectionResponse:
    collection = repository.get_or_create_default(db, user_id)
    result = CollectionResponse(collection_id=collection.collection_id,
        collection_name=collection.collection_name, words=repository.list_words(db,collection.collection_id))
    db.commit()
    return result

def save_word(db: Session, user_id: int, vocabulary_id: int) -> CollectionResponse:
    if db.get(Vocabulary,vocabulary_id) is None:
        raise HTTPException(status_code=404, detail="Vocabulary not found")
    collection = repository.get_or_create_default(db,user_id)
    repository.add_word(db,collection.collection_id,vocabulary_id)
    return read_collection(db,user_id)

def unsave_word(db: Session, user_id: int, vocabulary_id: int) -> CollectionResponse:
    collection = repository.get_or_create_default(db,user_id)
    repository.remove_word(db,collection.collection_id,vocabulary_id)
    return read_collection(db,user_id)
