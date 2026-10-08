from sqlalchemy import select, delete, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, selectinload
from app.models.collection import Collection, CollectionWord
from app.models.vocabulary import Vocabulary

def get_or_create_default(db: Session, user_id: int) -> Collection:
    collection = db.scalar(select(Collection).where(Collection.user_id==user_id, Collection.is_default.is_(True)))
    if collection is None:
        db.execute(insert(Collection).values(user_id=user_id,collection_name="Từ đã lưu",is_default=True)
            .on_conflict_do_nothing(index_elements=[Collection.user_id],index_where=text("is_default")))
        db.flush()
        collection = db.scalar(select(Collection).where(Collection.user_id==user_id, Collection.is_default.is_(True)))
    return collection

def list_words(db: Session, collection_id: int) -> list[Vocabulary]:
    return list(db.scalars(select(Vocabulary).join(CollectionWord, CollectionWord.vocabulary_id==Vocabulary.vocabulary_id)
        .where(CollectionWord.collection_id==collection_id)
        .options(selectinload(Vocabulary.meanings), selectinload(Vocabulary.examples),
            selectinload(Vocabulary.relations), selectinload(Vocabulary.topics))
        .order_by(CollectionWord.added_at, Vocabulary.vocabulary_id)).all())

def add_word(db: Session, collection_id: int, vocabulary_id: int):
    # The existing unique pair makes repeated save requests idempotent.
    db.execute(text("""INSERT INTO collection_words(collection_id,vocabulary_id)
        VALUES(:collection,:word) ON CONFLICT(collection_id,vocabulary_id) DO NOTHING"""),
        {"collection":collection_id,"word":vocabulary_id})

def remove_word(db: Session, collection_id: int, vocabulary_id: int):
    db.execute(delete(CollectionWord).where(CollectionWord.collection_id==collection_id,
        CollectionWord.vocabulary_id==vocabulary_id))
