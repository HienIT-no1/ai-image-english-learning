"""Provision an admin from a trusted server terminal, never from public registration."""
import argparse
import getpass
from pydantic import ValidationError
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import RegisterRequest

def create_admin(db, username: str, email: str, password: str, full_name: str | None = None):
    data = RegisterRequest(username=username.strip(), email=email.strip(), password=password)
    if db.scalar(select(User).where(or_(User.username == data.username, User.email == str(data.email)))):
        raise ValueError("Username/email exists; no existing user was modified")
    if full_name is not None and not 1 <= len(full_name.strip()) <= 100:
        raise ValueError("Full name must contain 1 to 100 characters")
    user = User(username=data.username, email=str(data.email), password_hash=hash_password(data.password),
        full_name=full_name.strip() if full_name else data.username, role="ADMIN", cefr_level="A1",
        english_level="BEGINNER", onboarding_completed=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Username/email exists; no existing user was modified") from None
    db.refresh(user)
    return user

def main():
    parser = argparse.ArgumentParser(description="Create a separate ADMIN account. Apply migrations first.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name")
    args = parser.parse_args()
    first = getpass.getpass("Admin password (8-128 characters): ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        parser.exit(1, "Passwords do not match; no account was created.\n")
    try:
        with SessionLocal() as db:
            user = create_admin(db, args.username, args.email, first, args.full_name)
            print(f"Created ADMIN: {user.username} (id={user.user_id}). Log in using the Android login screen.")
    except (ValueError, ValidationError) as error:
        # Do not print Pydantic input values (they can include passwords).
        message = "Invalid username/email/password/name" if isinstance(error, ValidationError) else str(error)
        parser.exit(1, message + "\n")

if __name__ == "__main__":
    main()
