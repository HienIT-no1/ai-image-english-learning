from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import ReminderRequest, NotificationResponse, NotificationPage
from app.repositories.review_repository import due_count
router=APIRouter(prefix="/notifications",tags=["Notifications"])

def owned(db,user_id,ident):
    row=db.scalar(select(Notification).where(Notification.notification_id==ident,Notification.user_id==user_id))
    if row is None: raise HTTPException(404,"Notification not found")
    return row

@router.get("",response_model=NotificationPage)
def inbox(offset:int=Query(default=0,ge=0),limit:int=Query(default=50,ge=1,le=100),
          user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=list(db.scalars(select(Notification).where(Notification.user_id==user.user_id)
        .order_by(Notification.created_at.desc(),Notification.notification_id.desc()).offset(offset).limit(limit)))
    count=db.scalar(select(func.count()).select_from(Notification).where(
        Notification.user_id==user.user_id,Notification.read_at.is_(None)))
    return NotificationPage(items=rows,unread_count=count)

@router.post("/reminders",response_model=NotificationResponse)
def reminder(data:ReminderRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if not user.reminders_enabled: raise HTTPException(409,"Reminders are disabled")
    count=due_count(db,user.user_id)
    body=f"Bạn có {count} từ đến hạn ôn. Dành vài phút để ghi nhớ lâu hơn nhé!" if count else "Dành vài phút ôn từ vựng và duy trì thói quen học hôm nay nhé!"
    db.execute(insert(Notification).values(user_id=user.user_id,occurrence_date=data.occurrence_date,
        title="Đến giờ ôn tập cùng LensLearn",body=body)
        .on_conflict_do_nothing(constraint="uq_notification_user_day"))
    db.flush()
    row=db.scalar(select(Notification).where(Notification.user_id==user.user_id,Notification.occurrence_date==data.occurrence_date))
    result=NotificationResponse.model_validate(row);db.commit();return result

@router.post("/read-all")
def read_all(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    db.execute(update(Notification).where(Notification.user_id==user.user_id,Notification.read_at.is_(None))
        .values(read_at=datetime.now(timezone.utc)))
    db.commit();return {"message":"Notifications marked read"}

@router.post("/{notification_id}/read",response_model=NotificationResponse)
def read(notification_id:int=Path(gt=0),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    row=owned(db,user.user_id,notification_id)
    if row.read_at is None: row.read_at=datetime.now(timezone.utc)
    db.commit();db.refresh(row);return row
