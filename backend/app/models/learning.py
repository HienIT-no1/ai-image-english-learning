from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class LearningProgress(Base):
    __tablename__="learning_progress"
    progress_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    user_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("users.user_id",ondelete="CASCADE"))
    vocabulary_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("vocabularies.vocabulary_id",ondelete="CASCADE"))
    status: Mapped[str]=mapped_column(String(20),server_default=text("'NEW'"))
    review_count: Mapped[int]=mapped_column(Integer,server_default=text("0"))
    correct_count: Mapped[int]=mapped_column(Integer,server_default=text("0"))
    incorrect_count: Mapped[int]=mapped_column(Integer,server_default=text("0"))
    last_reviewed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint("user_id","vocabulary_id",name="learning_progress_user_id_vocabulary_id_key"),
        CheckConstraint("status IN ('NEW','LEARNING','REVIEWING','MASTERED')",name="learning_progress_status_check"),
        CheckConstraint("review_count >= 0",name="learning_progress_review_count_check"),
        CheckConstraint("correct_count >= 0",name="learning_progress_correct_count_check"),
        CheckConstraint("incorrect_count >= 0",name="learning_progress_incorrect_count_check"))

class LearningEvent(Base):
    __tablename__="learning_events"
    event_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    user_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("users.user_id",ondelete="CASCADE"))
    vocabulary_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("vocabularies.vocabulary_id",ondelete="CASCADE"))
    event_key: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True))
    kind: Mapped[str]=mapped_column(String(20))
    is_correct: Mapped[bool]=mapped_column(Boolean)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint("user_id","event_key",name="uq_learning_event_user_key"),
        Index("ix_learning_events_user_date","user_id","created_at"),
        CheckConstraint("kind IN ('FLASHCARD','QUIZ')",name="learning_events_kind_check"))
