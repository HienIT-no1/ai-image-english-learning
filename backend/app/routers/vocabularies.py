from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.vocabulary import VocabularyResponse
from app.services.vocabulary_service import (
    get_vocabulary,
    get_vocabularies,
)


router = APIRouter(
    prefix="/vocabularies",
    tags=["Vocabularies"]
)


@router.get(
    "",
    response_model=list[VocabularyResponse]
)
def get_all_vocabularies(
    db: Session = Depends(get_db)
):
    return get_vocabularies(db)


@router.get(
    "/{vocabulary_id}",
    response_model=VocabularyResponse
)
def get_vocabulary_detail(
    vocabulary_id: int,
    db: Session = Depends(get_db)
):
    vocabulary = get_vocabulary(
        db,
        vocabulary_id
    )

    if vocabulary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary not found"
        )

    return vocabulary