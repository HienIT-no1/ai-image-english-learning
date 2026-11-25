from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.admin_analytics import GameAnalytics, GameType, LearningAnalytics
from app.services import admin_analytics as service


router = APIRouter(prefix="/analytics")


@router.get("/learning", response_model=LearningAnalytics)
def learning(db: Annotated[Session, Depends(get_db)], days: Annotated[int, Query(ge=1, le=90)] = 30):
    return service.learning(db, days)


@router.get("/games", response_model=GameAnalytics)
def games(
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
    game_type: GameType | None = None,
):
    return service.games(db, days, game_type)
