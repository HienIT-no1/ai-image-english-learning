from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.user import User
from app.repositories.vocabulary_repository import get_all_vocabularies
from app.schemas.admin import AdminSummary, AdminUserResponse, TopicInput, VocabularyInput
from app.schemas.topic import TopicResponse
from app.schemas.vocabulary import VocabularyResponse
from app.services import admin_service as service

# Every route, including reads, inherits this server-side authorization check.
router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin)])

@router.get("/summary", response_model=AdminSummary)
def summary(db: Session = Depends(get_db)):
    return service.summary(db)

@router.get("/users", response_model=list[AdminUserResponse])
def users(offset: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100), db: Session = Depends(get_db)):
    return list(db.scalars(select(User).order_by(User.user_id).offset(offset).limit(limit)).all())

@router.get("/topics", response_model=list[TopicResponse])
def topics(db: Session = Depends(get_db)):
    return service.topics(db)

@router.post("/topics", response_model=TopicResponse, status_code=201)
def create_topic(data: TopicInput, db: Session = Depends(get_db)):
    return service.save_topic(db, data)

@router.put("/topics/{ident}", response_model=TopicResponse)
def update_topic(data: TopicInput, ident: int = Path(gt=0), db: Session = Depends(get_db)):
    return service.save_topic(db, data, ident)

@router.delete("/topics/{ident}")
def delete_topic(ident: int = Path(gt=0), db: Session = Depends(get_db)):
    return service.delete_topic(db, ident)

@router.get("/vocabularies", response_model=list[VocabularyResponse])
def vocabularies(db: Session = Depends(get_db)):
    return get_all_vocabularies(db)

@router.post("/vocabularies", response_model=VocabularyResponse, status_code=201)
def create_word(data: VocabularyInput, db: Session = Depends(get_db)):
    return service.save_vocabulary(db, data)

@router.put("/vocabularies/{ident}", response_model=VocabularyResponse)
def update_word(data: VocabularyInput, ident: int = Path(gt=0), db: Session = Depends(get_db)):
    return service.save_vocabulary(db, data, ident)
