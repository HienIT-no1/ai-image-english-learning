from sqlalchemy.orm import Session

from app.models.vocabulary import Vocabulary
from app.repositories.vocabulary_repository import (
    get_all_vocabularies,
    get_vocabulary_by_id,
)


def get_vocabularies(
    db: Session
) -> list[Vocabulary]:
    return get_all_vocabularies(db)


def get_vocabulary(
    db: Session,
    vocabulary_id: int
) -> Vocabulary | None:
    return get_vocabulary_by_id(
        db,
        vocabulary_id
    )