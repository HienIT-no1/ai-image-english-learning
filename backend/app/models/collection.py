from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Collection(Base):
    __tablename__ = "collections"
    collection_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    collection_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    __table_args__ = (
        Index("uq_collections_default_user", "user_id", unique=True, postgresql_where=text("is_default")),
        Index("ix_collections_user_id", "user_id"),
    )

class CollectionWord(Base):
    __tablename__ = "collection_words"
    collection_word_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    collection_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("collections.collection_id", ondelete="CASCADE"), nullable=False)
    vocabulary_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vocabularies.vocabulary_id", ondelete="CASCADE"), nullable=False)
    image_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("images.image_id", ondelete="SET NULL"))
    added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("collection_id", "vocabulary_id", name="collection_words_collection_id_vocabulary_id_key"),)
