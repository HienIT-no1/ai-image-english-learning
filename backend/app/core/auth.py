
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id)

    if user is None:
        raise credentials_exception

    return user

def get_current_admin(user: User = Depends(get_current_user)) -> User:
    # Read the role from PostgreSQL on every request, never trust a role in JWT/client input.
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


oauth2_optional_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",
    auto_error=False
)


def get_optional_current_user(
    token: str | None = Depends(oauth2_optional_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return db.get(User, int(user_id))
    except Exception:
        return None

