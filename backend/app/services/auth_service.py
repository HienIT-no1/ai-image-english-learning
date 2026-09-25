from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import (
    create_user,
    get_user_by_email,
    get_user_by_username,
)
from app.schemas.auth import LoginRequest, RegisterRequest


def register_user(
    db: Session,
    data: RegisterRequest
) -> User:

    existing_username = get_user_by_username(
        db,
        data.username
    )

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    existing_email = get_user_by_email(
        db,
        data.email
    )

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password)
    )

    return create_user(db, user)


def login_user(
    db: Session,
    data: LoginRequest
) -> User:

    user = get_user_by_username(
        db,
        data.username
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    password_valid = verify_password(
        data.password,
        user.password_hash
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    return user