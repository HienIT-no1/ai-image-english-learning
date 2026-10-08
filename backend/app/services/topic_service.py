from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.topic_repository import list_topics, find_topic
from app.repositories.vocabulary_repository import get_all_vocabularies
from app.schemas.topic import TopicResponse

def get_topics(db: Session) -> list[TopicResponse]:
    return [
        TopicResponse(topic_id=topic.topic_id, slug=topic.slug, name=topic.name,
                      symbol=topic.symbol, vocabulary_count=count)
        for topic, count in list_topics(db)]

def get_topic_vocabularies(db: Session, topic_id: int):
    if find_topic(db, topic_id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return get_all_vocabularies(db, topic_id=topic_id)
