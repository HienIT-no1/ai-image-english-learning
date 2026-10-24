from datetime import date, datetime, timedelta
from pydantic import BaseModel, ConfigDict, field_validator
from app.repositories.learning_repository import LOCAL_TZ

class ReminderRequest(BaseModel):
    model_config=ConfigDict(extra="forbid")
    occurrence_date: date
    @field_validator("occurrence_date")
    @classmethod
    def recent_date(cls,value):
        today=datetime.now(LOCAL_TZ).date()
        if not today-timedelta(days=7)<=value<=today+timedelta(days=1):
            raise ValueError("Reminder date must be recent")
        return value

class NotificationResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    notification_id: int
    occurrence_date: date
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None

class NotificationPage(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
