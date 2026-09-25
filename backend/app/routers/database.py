from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db


router = APIRouter(
    prefix="/database",
    tags=["Database"]
)


@router.get("/test")
def test_database_connection(
    db: Session = Depends(get_db)
):
    result = db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": result.scalar()
    }