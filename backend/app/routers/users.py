from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "english_level": current_user.english_level,
        "daily_goal": current_user.daily_goal,
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak
    }