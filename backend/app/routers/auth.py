from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import login_user, register_user


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    user = register_user(
        db,
        data
    )

    return {
        "message": "User registered successfully",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "english_level": user.english_level,
            "daily_goal": user.daily_goal
        }
    }


@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = login_user(
        db,
        data
    )

    access_token = create_access_token(
        user_id=user.user_id,
        username=user.username
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }