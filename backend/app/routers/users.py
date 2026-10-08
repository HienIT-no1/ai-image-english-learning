from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.repositories.learning_repository import study_days,streaks,LOCAL_TZ
from datetime import datetime
router=APIRouter(prefix='/users',tags=['Users'])

@router.get('/me',response_model=ProfileResponse)
def get_my_profile(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    current,longest=streaks(study_days(db,current_user.user_id),datetime.now(LOCAL_TZ).date())
    data=ProfileResponse.model_validate(current_user)
    data.current_streak=current;data.longest_streak=max(longest,current_user.longest_streak or 0)
    return data

@router.patch('/me',response_model=ProfileResponse)
def update_my_profile(data:ProfileUpdate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    user.full_name=data.full_name;user.cefr_level=data.cefr_level;user.daily_goal=data.daily_goal
    user.reminders_enabled=data.reminders_enabled;user.onboarding_completed=True
    user.english_level={'A1':'BEGINNER','A2':'BEGINNER','B1':'INTERMEDIATE','B2':'ADVANCED'}[data.cefr_level]
    db.commit();db.refresh(user)
    return user
