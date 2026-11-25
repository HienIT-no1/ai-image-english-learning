from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.admin_quiz import AdminQuizDetail, AdminQuizPage, AdminQuizSummary, QuizStatus
from app.schemas.quiz import QuizType
from app.services import admin_quiz_service as service


# Mounted under the ADMIN-protected router.
router = APIRouter(prefix="/quizzes")


@router.get("", response_model=AdminQuizPage)
def quizzes(
    q: str = Query(default="", max_length=100),
    quiz_type: QuizType | None = None,
    status: QuizStatus | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_attempts(db, q, quiz_type, status, offset, limit)


@router.get("/summary", response_model=AdminQuizSummary)
def quiz_summary(db: Session = Depends(get_db)):
    return service.summary(db)


@router.get("/{ident}", response_model=AdminQuizDetail)
def quiz_detail(ident: int = Path(gt=0), db: Session = Depends(get_db)):
    return service.detail(db, ident)
