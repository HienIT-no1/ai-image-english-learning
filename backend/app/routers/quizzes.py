from fastapi import APIRouter,Depends,Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.quiz import QuizAttempt
from app.schemas.quiz import QuizStart,QuizSubmit,QuizResponse,AnswerResponse
from app.services import quiz_service as service
router=APIRouter(prefix='/quizzes',tags=['Quizzes'])

@router.post('',response_model=QuizResponse)
def start(data:QuizStart,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.start(db,user,data)

@router.get('/{attempt_id}',response_model=QuizResponse)
def read(attempt_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.response(db,service.owned(db,user.user_id,attempt_id))

@router.post('/{attempt_id}/answers',response_model=AnswerResponse)
def answer(data:QuizSubmit,attempt_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.answer(db,user,attempt_id,data)

@router.post('/{attempt_id}/complete',response_model=QuizResponse)
def complete(attempt_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.complete(db,user,attempt_id)

@router.post('/{attempt_id}/abort',response_model=QuizResponse)
def abort(attempt_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.abort(db,user,attempt_id)
