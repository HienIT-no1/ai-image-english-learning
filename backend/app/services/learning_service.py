from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.repositories.learning_repository import record_event, summary
from app.schemas.learning import ReviewRequest

def review(db:Session,user:User,data:ReviewRequest):
    if db.get(Vocabulary,data.vocabulary_id) is None: raise HTTPException(404,'Vocabulary not found')
    record_event(db,user.user_id,data.vocabulary_id,data.event_key,'FLASHCARD',data.remembered)
    result=summary(db,user)
    user.current_streak=result.current_streak;user.longest_streak=result.longest_streak
    db.commit()
    return result
