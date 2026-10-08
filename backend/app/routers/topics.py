from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.topic import TopicResponse
from app.schemas.vocabulary import VocabularyResponse
from app.services.topic_service import get_topics, get_topic_vocabularies

router = APIRouter(prefix="/topics", tags=["Topics"])

@router.get("", response_model=list[TopicResponse])
def topics(db: Session = Depends(get_db)):
    return get_topics(db)

@router.get("/{topic_id}/vocabularies", response_model=list[VocabularyResponse])
def topic_vocabularies(topic_id: int = Path(gt=0), db: Session = Depends(get_db)):
    return get_topic_vocabularies(db, topic_id)
