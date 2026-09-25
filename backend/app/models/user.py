from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    full_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    english_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    daily_goal: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False
    )

    current_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    longest_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "english_level IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')",
            name="users_english_level_check"
        ),
        CheckConstraint(
            "daily_goal > 0",
            name="users_daily_goal_check"
        ),
    )