from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.collection import CollectionResponse
from app.services import collection_service as service

router = APIRouter(prefix="/collections/me", tags=["Personal collection"])

@router.get("", response_model=CollectionResponse)
def my_collection(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.read_collection(db,user.user_id)

@router.put("/words/{vocabulary_id}", response_model=CollectionResponse)
def save_word(vocabulary_id: int = Path(gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.save_word(db,user.user_id,vocabulary_id)

@router.delete("/words/{vocabulary_id}", response_model=CollectionResponse)
def unsave_word(vocabulary_id: int = Path(gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return service.unsave_word(db,user.user_id,vocabulary_id)
