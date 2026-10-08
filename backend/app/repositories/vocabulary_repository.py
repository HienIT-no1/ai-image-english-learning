from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.vocabulary import Vocabulary


def get_all_vocabularies(
    db: Session,
    topic_id: int | None = None
) -> list[Vocabulary]:

    statement = (
        select(Vocabulary)
        .options(
            selectinload(Vocabulary.topics),
            selectinload(Vocabulary.meanings),
            selectinload(Vocabulary.examples),
            selectinload(Vocabulary.relations)
        )
        .order_by(Vocabulary.vocabulary_id)
    )

    if topic_id is not None:
        statement = statement.where(Vocabulary.topics.any(topic_id=topic_id))

    return list(
        db.execute(statement).scalars().all()
    )


def get_vocabulary_by_id(
    db: Session,
    vocabulary_id: int
) -> Vocabulary | None:

    statement = (
        select(Vocabulary)
        .options(
            selectinload(Vocabulary.topics),
            selectinload(Vocabulary.meanings),
            selectinload(Vocabulary.examples),
            selectinload(Vocabulary.relations)
        )
        .where(
            Vocabulary.vocabulary_id == vocabulary_id
        )
    )

    return db.execute(statement).scalar_one_or_none()