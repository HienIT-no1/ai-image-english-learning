from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.learning import ReviewRequest, LearningSummary
from app.repositories.learning_repository import summary
from app.services.learning_service import review
router=APIRouter(prefix='/learning/me',tags=['Learning'])

@router.get('',response_model=LearningSummary)
def my_progress(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return summary(db,user)

@router.post('/reviews',response_model=LearningSummary)
def submit_review(data:ReviewRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return review(db,user,data)
