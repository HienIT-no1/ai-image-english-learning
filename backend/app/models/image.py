"""Legacy image mapping needed for collection_words.image_id foreign key."""
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Image(Base):
    __tablename__ = "images"
    image_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id",ondelete="CASCADE"), nullable=False)
    image_url: Mapped[str] = mapped_column(Text,nullable=False)
    source_type: Mapped[str] = mapped_column(String(20),nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),server_default=func.now())
