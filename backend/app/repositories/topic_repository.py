from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.topic import Topic, vocabulary_topics

def list_topics(db: Session):
    return db.execute(
        select(Topic, func.count(vocabulary_topics.c.vocabulary_id))
        .outerjoin(vocabulary_topics, Topic.topic_id == vocabulary_topics.c.topic_id)
        .group_by(Topic.topic_id).order_by(Topic.topic_id)
    ).all()

def find_topic(db: Session, topic_id: int) -> Topic | None:
    return db.get(Topic, topic_id)
