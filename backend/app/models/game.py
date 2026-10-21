"""Separate game sessions so new games can be added without changing quiz history."""
from datetime import datetime
from uuid import UUID
from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class GameRun(Base):
    __tablename__ = "game_runs"
    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"))
    client_session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    game_type: Mapped[str] = mapped_column(String(30), server_default="WORD_SHOOTER")
    source: Mapped[str] = mapped_column(String(20))
    topic_id: Mapped[int | None] = mapped_column(BigInteger)
    pool: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("user_id", "client_session_id", name="uq_game_user_session"),
        CheckConstraint("source IN ('RANDOM','TOPIC','SAVED','DIFFICULT','REVIEW')", name="game_runs_source_check"),
        CheckConstraint("game_type = 'WORD_SHOOTER'", name="game_runs_type_check"),
    )

class GameRound(Base):
    __tablename__ = "game_rounds"
    round_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("game_runs.run_id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    stage: Mapped[int] = mapped_column(Integer)
    words: Mapped[list] = mapped_column(JSONB)
    results: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    correct_count: Mapped[int] = mapped_column(Integer, server_default="0")
    missed_count: Mapped[int] = mapped_column(Integer, server_default="0")
    max_combo: Mapped[int] = mapped_column(Integer, server_default="0")
    score: Mapped[int] = mapped_column(Integer, server_default="0")
    status: Mapped[str] = mapped_column(String(10), server_default="PLAYING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_game_round_sequence"),
        CheckConstraint("status IN ('PLAYING','PASSED','FAILED')", name="game_rounds_status_check"),
        CheckConstraint("stage > 0 AND sequence > 0", name="game_rounds_stage_check"),
        CheckConstraint("correct_count >= 0 AND missed_count BETWEEN 0 AND 4 AND max_combo >= 0 AND score >= 0", name="game_rounds_counts_check"),
    )
