from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, func, delete
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
from app.repositories.learning_repository import summary as learning_summary
from app.models.game import GameRun, GameRound


def account(db: Session, ident: int, lock: bool = False):
    query = select(User).where(User.user_id == ident)
    user = db.scalar(query.with_for_update() if lock else query)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


def learner(db: Session, ident: int):
    user = account(db, ident, lock=True)
    if user.role != "USER":
        raise HTTPException(409, "Only learner accounts can be managed")
    return user


def set_user_lock(db: Session, ident: int, is_locked: bool):
    user = learner(db, ident)
    if user.is_locked != is_locked:
        user.is_locked = is_locked
        user.auth_version += 1
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, ident: int, username: str):
    user = learner(db, ident)
    if username != user.username:
        raise HTTPException(409, "Username confirmation does not match")
    # Database foreign keys cascade personal records and preserve the shared catalog.
    db.execute(delete(User).where(User.user_id == user.user_id))
    db.commit()
    return {"message": "User deleted"}


def user_detail(db: Session, ident: int):
    user = account(db, ident)
    progress = learning_summary(db, user)
    ids = [p.vocabulary_id for p in progress.progress]
    names = dict(db.execute(select(Vocabulary.vocabulary_id, Vocabulary.word)
        .where(Vocabulary.vocabulary_id.in_(ids))).all()) if ids else {}
    runs = db.scalar(select(func.count()).select_from(GameRun).where(GameRun.user_id == ident))
    score = db.scalar(select(func.coalesce(func.sum(GameRound.score), 0)).join(GameRun)
        .where(GameRun.user_id == ident))
    return {"user_id": user.user_id, "username": user.username, "email": user.email,
        "full_name": user.full_name, "role": user.role, "is_locked": user.is_locked,
        "created_at": user.created_at, "cefr_level": user.cefr_level,
        "learning": progress, "vocabulary_names": names, "game_runs": runs, "game_score": score}


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
        # Serialize edits to the same word, including changes to its child rows.
        word = db.scalar(select(Vocabulary).where(Vocabulary.vocabulary_id == ident).with_for_update())
        if word is None:
            raise HTTPException(404, "Vocabulary not found")
    word.word = data.word
    word.ipa = data.ipa or None
    word.topics = assigned
    if data.meanings is not None and data.examples is not None:
        replace_word_content(word, data)
    else:
        update_primary_word_content(word, data)
    commit(db)
    return VocabularyResponse.model_validate(get_vocabulary_by_id(db, word.vocabulary_id))


def replace_word_content(word: Vocabulary, data: VocabularyInput):
    meanings_by_id = {row.meaning_id: row for row in word.meanings}
    examples_by_id = {row.example_id: row for row in word.examples}
    meanings = []
    examples = []
    for item in data.meanings:
        row = VocabularyMeaning() if item.meaning_id is None else meanings_by_id.pop(item.meaning_id, None)
        if row is None:
            raise HTTPException(409, "Invalid or duplicate vocabulary meaning ID")
        row.meaning_vi = item.meaning_vi
        row.definition_en = item.definition_en or None
        meanings.append(row)
    for item in data.examples:
        row = VocabularyExample() if item.example_id is None else examples_by_id.pop(item.example_id, None)
        if row is None:
            raise HTTPException(409, "Invalid or duplicate vocabulary example ID")
        row.sentence_en = item.sentence_en
        row.sentence_vi = item.sentence_vi or None
        examples.append(row)
    # The relationships remove omitted records; existing rows keep their IDs.
    word.meanings = meanings
    word.examples = examples


def update_primary_word_content(word: Vocabulary, data: VocabularyInput):
    # Older clients edit primary content only and preserve additional rows.
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
