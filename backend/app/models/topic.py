from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Table, Column, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

vocabulary_topics = Table(
    "vocabulary_topics", Base.metadata,
    Column("topic_id", BigInteger, ForeignKey("topics.topic_id", ondelete="CASCADE"), primary_key=True),
    Column("vocabulary_id", BigInteger, ForeignKey("vocabularies.vocabulary_id", ondelete="CASCADE"), primary_key=True),
    Index("ix_vocabulary_topics_vocabulary_id", "vocabulary_id"),
)

class Topic(Base):
    __tablename__ = "topics"
    topic_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    vocabularies: Mapped[list["Vocabulary"]] = relationship(
        secondary=vocabulary_topics, back_populates="topics")
