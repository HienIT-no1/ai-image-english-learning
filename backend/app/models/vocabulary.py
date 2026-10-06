from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    meanings: Mapped[list["VocabularyMeaning"]] = relationship(
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    examples: Mapped[list["VocabularyExample"]] = relationship(
        back_populates="vocabulary",
        cascade="all, delete-orphan"
    )

    relations: Mapped[list["VocabularyRelation"]] = relationship(
        back_populates="vocabulary",
        foreign_keys="VocabularyRelation.vocabulary_id"
    )


class VocabularyMeaning(Base):
    __tablename__ = "vocabulary_meanings"

    meaning_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabularies.vocabulary_id"),
        nullable=False
    )

    meaning_vi: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    definition_en: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    vocabulary: Mapped["Vocabulary"] = relationship(
        back_populates="meanings"
    )


class VocabularyExample(Base):
    __tablename__ = "vocabulary_examples"

    example_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabularies.vocabulary_id"),
        nullable=False
    )

    sentence_en: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    sentence_vi: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    vocabulary: Mapped["Vocabulary"] = relationship(
        back_populates="examples"
    )


class VocabularyRelation(Base):
    __tablename__ = "vocabulary_relations"

    relation_id: Mapped[int] = mapped_column(
        primary_key=True
    )

    vocabulary_id: Mapped[int] = mapped_column(
        ForeignKey("vocabularies.vocabulary_id"),
        nullable=False
    )

    related_vocabulary_id: Mapped[int | None] = mapped_column(
        ForeignKey("vocabularies.vocabulary_id"),
        nullable=True
    )

    related_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    relation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    vocabulary: Mapped["Vocabulary"] = relationship(
        back_populates="relations",
        foreign_keys=[vocabulary_id]
    )