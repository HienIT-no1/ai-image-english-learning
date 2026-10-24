from datetime import date, datetime
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Notification(Base):
    __tablename__="notifications"
    notification_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    user_id: Mapped[int]=mapped_column(BigInteger,ForeignKey("users.user_id",ondelete="CASCADE"))
    occurrence_date: Mapped[date]=mapped_column(Date)
    title: Mapped[str]=mapped_column(String(180))
    body: Mapped[str]=mapped_column(String(500))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    read_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    __table_args__=(UniqueConstraint("user_id","occurrence_date",name="uq_notification_user_day"),
        Index("ix_notifications_user_created","user_id","created_at"))
