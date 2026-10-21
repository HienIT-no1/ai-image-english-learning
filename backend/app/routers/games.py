from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.game import GameStart, GameFinish, GameResponse
from app.services import game_service as service
router=APIRouter(prefix="/games/word-shooter",tags=["Games"])

@router.post("",response_model=GameResponse)
def start(data:GameStart,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.start(db,user,data)

@router.get("/{run_id}",response_model=GameResponse)
def read(run_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.response(db,service.owned(db,user.user_id,run_id))

@router.post("/{run_id}/rounds/{round_id}/finish",response_model=GameResponse)
def finish(data:GameFinish,run_id:int=Path(gt=0),round_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.finish(db,user,run_id,round_id,data)

@router.post("/{run_id}/rounds/{round_id}/next",response_model=GameResponse)
def advance(run_id:int=Path(gt=0),round_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.advance(db,user,run_id,round_id)
