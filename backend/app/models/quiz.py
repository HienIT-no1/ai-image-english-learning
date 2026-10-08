from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped,mapped_column
from app.core.database import Base

class QuizAttempt(Base):
    __tablename__="quiz_attempts"
    attempt_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    user_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("users.user_id",ondelete="CASCADE"))
    quiz_type: Mapped[str]=mapped_column(String(30))
    total_questions: Mapped[int]=mapped_column(Integer,server_default=text("0"))
    correct_answers: Mapped[int]=mapped_column(Integer,server_default=text("0"))
    started_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),server_default=func.now())
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    aborted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    client_session_id: Mapped[UUID|None]=mapped_column(PGUUID(as_uuid=True))
    question_payload: Mapped[dict]=mapped_column(JSONB,server_default=text("'{}'::jsonb"))
    __table_args__=(UniqueConstraint("user_id","client_session_id",name="uq_quiz_user_session"),
        Index("ix_quiz_attempts_user_completed","user_id","completed_at"),
        CheckConstraint("correct_answers >= 0 AND correct_answers <= total_questions",name="quiz_attempts_check"),
        CheckConstraint("total_questions >= 0",name="quiz_attempts_total_questions_check"),
        CheckConstraint("quiz_type IN ('IMAGE_TO_WORD','WORD_TO_IMAGE','LISTENING','FILL_BLANK','MIXED')",name="quiz_attempts_quiz_type_check"))

class QuizAnswer(Base):
    __tablename__="quiz_answers"
    answer_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    attempt_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("quiz_attempts.attempt_id",ondelete="CASCADE"))
    vocabulary_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("vocabularies.vocabulary_id",ondelete="CASCADE"))
    question_type: Mapped[str]=mapped_column(String(30))
    user_answer: Mapped[str|None]=mapped_column(Text)
    correct_answer: Mapped[str]=mapped_column(Text)
    is_correct: Mapped[bool]=mapped_column(Boolean)
    answered_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),server_default=func.now())
    question_id: Mapped[str|None]=mapped_column(String(36))
    question_index: Mapped[int|None]=mapped_column(Integer)
    __table_args__=(UniqueConstraint("attempt_id","question_id",name="uq_quiz_answer_question"),
        UniqueConstraint("attempt_id","question_index",name="uq_quiz_answer_index"),
        CheckConstraint("question_type IN ('IMAGE_TO_WORD','WORD_TO_IMAGE','LISTENING','FILL_BLANK')",name="quiz_answers_question_type_check"))
