from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.topic import Topic
from app.models.vocabulary import Vocabulary, VocabularyMeaning, VocabularyExample
from app.models.quiz import QuizAttempt
from app.repositories.topic_repository import list_topics
from app.repositories.vocabulary_repository import get_vocabulary_by_id
from app.schemas.admin import AdminSummary, TopicInput, VocabularyInput
from app.schemas.topic import TopicResponse
from app.schemas.vocabulary import VocabularyResponse


def summary(db: Session) -> AdminSummary:
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where))
    return AdminSummary(users=count(User), admins=count(User, User.role == "ADMIN"),
        topics=count(Topic), vocabularies=count(Vocabulary),
        completed_quizzes=count(QuizAttempt, QuizAttempt.completed_at.is_not(None)))


def topics(db: Session):
    return [TopicResponse(topic_id=t.topic_id, name=t.name, slug=t.slug, symbol=t.symbol,
        vocabulary_count=count) for t, count in list_topics(db)]


def commit(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Data conflict; name or slug already exists") from None


def save_topic(db: Session, data: TopicInput, ident: int | None = None):
    if ident is None:
        topic = Topic(**data.model_dump())
        db.add(topic)
    else:
        topic = db.get(Topic, ident)
        if topic is None:
            raise HTTPException(404, "Topic not found")
        for key, value in data.model_dump().items():
            setattr(topic, key, value)
    commit(db)
    return next(t for t in topics(db) if t.topic_id == topic.topic_id)


def delete_topic(db: Session, ident: int):
    topic = db.scalar(select(Topic).where(Topic.topic_id == ident).with_for_update())
    if topic is None:
        raise HTTPException(404, "Topic not found")
    if topic.vocabularies:
        raise HTTPException(409, "Topic still contains vocabulary")
    db.delete(topic)
    commit(db)
    return {"message": "Topic deleted"}


def save_vocabulary(db: Session, data: VocabularyInput, ident: int | None = None):
    ids = set(data.topic_ids)
    assigned = list(db.scalars(select(Topic).where(Topic.topic_id.in_(ids))).all()) if ids else []
    if len(assigned) != len(ids):
        raise HTTPException(404, "Topic not found")
    duplicate = db.scalar(select(Vocabulary).where(func.lower(Vocabulary.word) == data.word.lower(),
        Vocabulary.vocabulary_id != ident if ident is not None else True))
    if duplicate is not None:
        raise HTTPException(409, "Data conflict; name or slug already exists")
    if ident is None:
        word = Vocabulary(word=data.word, created_at=datetime.now(timezone.utc), level="BEGINNER")
        db.add(word)
    else:
        word = get_vocabulary_by_id(db, ident)
        if word is None:
            raise HTTPException(404, "Vocabulary not found")
    word.word = data.word
    word.ipa = data.ipa or None
    word.topics = assigned
    # Edit primary content only; preserve additional meanings, translations and relations.
    meaning = min(word.meanings, key=lambda x: x.meaning_id) if word.meanings else None
    if meaning is None:
        word.meanings.append(VocabularyMeaning(meaning_vi=data.meaning_vi))
    else:
        meaning.meaning_vi = data.meaning_vi
    example = min(word.examples, key=lambda x: x.example_id) if word.examples else None
    if data.sentence_en:
        if example is None:
            word.examples.append(VocabularyExample(sentence_en=data.sentence_en, sentence_vi=data.sentence_vi or None))
        else:
            example.sentence_en = data.sentence_en
            example.sentence_vi = data.sentence_vi or None
    elif example is not None:
        # A blank edit must not silently erase a pre-existing example.
        raise HTTPException(422, "Existing example cannot be cleared in this editor")
    commit(db)
    return VocabularyResponse.model_validate(get_vocabulary_by_id(db, word.vocabulary_id))
