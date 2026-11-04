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


# Reuse the deck/scoring rules, with ownership also checked against game_type.
from app.schemas.game import DefenseStart
defense_router=APIRouter(prefix="/games/word-defense",tags=["Games"])

@defense_router.post("",response_model=GameResponse)
def start_defense(data:DefenseStart,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.start(db,user,data,"WORD_DEFENSE")

@defense_router.get("/{run_id}",response_model=GameResponse)
def read_defense(run_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.response(db,service.owned(db,user.user_id,run_id,game_type="WORD_DEFENSE"))

@defense_router.post("/{run_id}/rounds/{round_id}/finish",response_model=GameResponse)
def finish_defense(data:GameFinish,run_id:int=Path(gt=0),round_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.finish(db,user,run_id,round_id,data,"WORD_DEFENSE")

@defense_router.post("/{run_id}/rounds/{round_id}/next",response_model=GameResponse)
def advance_defense(run_id:int=Path(gt=0),round_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.advance(db,user,run_id,round_id,"WORD_DEFENSE")

@defense_router.post("/{run_id}/complete",response_model=GameResponse)
def complete_defense(run_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return service.complete_defense(db,user,run_id)
