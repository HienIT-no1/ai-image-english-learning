from datetime import datetime, timezone
from sqlalchemy import select, or_, and_, func
from sqlalchemy.orm import selectinload
from app.models.collection import Collection, CollectionWord
from app.models.learning import LearningProgress
from app.models.vocabulary import Vocabulary

def due_ids(user_id,now=None):
    now=now or datetime.now(timezone.utc)
    saved=select(CollectionWord.vocabulary_id).join(Collection,
        Collection.collection_id==CollectionWord.collection_id).where(Collection.user_id==user_id)
    return select(Vocabulary.vocabulary_id,LearningProgress.next_review_at).outerjoin(LearningProgress,
        and_(LearningProgress.vocabulary_id==Vocabulary.vocabulary_id,LearningProgress.user_id==user_id)).where(
            or_(LearningProgress.next_review_at<=now,
                and_(LearningProgress.next_review_at.is_(None),Vocabulary.vocabulary_id.in_(saved))))

def due_count(db,user_id,now=None):
    return db.scalar(select(func.count()).select_from(due_ids(user_id,now).subquery())) or 0

def due_words(db,user_id,limit=100):
    ids=list(db.execute(due_ids(user_id).order_by(LearningProgress.next_review_at.asc().nullsfirst(),
        Vocabulary.vocabulary_id).limit(limit)).scalars())
    if not ids: return []
    words=list(db.scalars(select(Vocabulary).where(Vocabulary.vocabulary_id.in_(ids)).options(
        selectinload(Vocabulary.topics),selectinload(Vocabulary.meanings),
        selectinload(Vocabulary.examples),selectinload(Vocabulary.relations))).all())
    by_id={w.vocabulary_id:w for w in words}
    return [by_id[i] for i in ids]
