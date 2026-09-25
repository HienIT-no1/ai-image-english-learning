from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Vocabulary(Base):
    __tablename__ = "vocabularies"

    vocabulary_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    word: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    ipa: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    part_of_speech: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    audio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        nullable=False
    )
    