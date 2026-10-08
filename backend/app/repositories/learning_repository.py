from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, case
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.learning import LearningEvent, LearningProgress
from app.models.collection import Collection, CollectionWord
from app.models.quiz import QuizAttempt
from app.models.user import User
from app.schemas.learning import LearningSummary, StudyDay

LOCAL_TZ=timezone(timedelta(hours=7))

def record_event(db: Session,user_id:int,vocabulary_id:int,event_key,kind:str,correct:bool):
    inserted=db.scalar(insert(LearningEvent).values(user_id=user_id,vocabulary_id=vocabulary_id,
        event_key=event_key,kind=kind,is_correct=correct)
        .on_conflict_do_nothing(constraint='uq_learning_event_user_key').returning(LearningEvent.event_id))
    if inserted is None:
        existing=db.scalar(select(LearningEvent).where(LearningEvent.user_id==user_id,LearningEvent.event_key==event_key))
        if (existing.vocabulary_id,existing.kind,existing.is_correct)!=(vocabulary_id,kind,correct):
            raise HTTPException(409,'Review key already used for different data')
        return
    now=datetime.now(timezone.utc)
    status=('MASTERED' if correct else 'LEARNING') if kind=='FLASHCARD' else 'LEARNING'
    next_status=status if kind=='FLASHCARD' else case((LearningProgress.status=='NEW','LEARNING'),else_=LearningProgress.status)
    db.execute(insert(LearningProgress).values(user_id=user_id,vocabulary_id=vocabulary_id,status=status,
        review_count=1,correct_count=int(correct),incorrect_count=int(not correct),last_reviewed_at=now,updated_at=now)
        .on_conflict_do_update(constraint='learning_progress_user_id_vocabulary_id_key',set_={
            'status':next_status,'review_count':LearningProgress.review_count+1,
            'correct_count':LearningProgress.correct_count+int(correct),
            'incorrect_count':LearningProgress.incorrect_count+int(not correct),
            'last_reviewed_at':now,'updated_at':now}))
    db.flush()

def study_days(db:Session,user_id:int):
    local_date=func.date(func.timezone('Asia/Ho_Chi_Minh',LearningEvent.created_at))
    return dict(db.execute(select(local_date,func.count()).where(LearningEvent.user_id==user_id)
        .group_by(local_date).order_by(local_date)).all())

def streaks(days,today):
    cursor=today if today in days else today-timedelta(days=1)
    current=0
    while cursor in days:
        current+=1;cursor-=timedelta(days=1)
    longest=run=0; previous=None
    for day in sorted(days):
        run=run+1 if previous is not None and day==previous+timedelta(days=1) else 1
        longest=max(longest,run);previous=day
    return current,longest

def summary(db:Session,user:User)->LearningSummary:
    today=datetime.now(LOCAL_TZ).date()
    days=study_days(db,user.user_id)
    current,longest=streaks(days,today)
    progresses=list(db.scalars(select(LearningProgress).where(LearningProgress.user_id==user.user_id)
        .order_by(LearningProgress.vocabulary_id)).all())
    saved_ids=set(db.scalars(select(CollectionWord.vocabulary_id).join(Collection,
        Collection.collection_id==CollectionWord.collection_id).where(Collection.user_id==user.user_id,
        Collection.is_default.is_(True))).all())
    mastered={p.vocabulary_id for p in progresses if p.status=='MASTERED'}
    quizzes=db.execute(select(func.count(),func.coalesce(func.sum(QuizAttempt.correct_answers),0),
        func.coalesce(func.sum(QuizAttempt.total_questions),0)).where(QuizAttempt.user_id==user.user_id,
        QuizAttempt.completed_at.is_not(None))).one()
    return LearningSummary(today=today,daily_goal=user.daily_goal or 10,saved_count=len(saved_ids),
        mastered_count=len(mastered),needs_review=len(saved_ids-mastered),review_count=sum(p.review_count for p in progresses),
        today_count=days.get(today,0),current_streak=current,longest_streak=max(longest,user.longest_streak or 0),
        quiz_runs=quizzes[0],quiz_correct=quizzes[1],quiz_total=quizzes[2],
        days=[StudyDay(date=today-timedelta(days=i),count=days.get(today-timedelta(days=i),0)) for i in range(6,-1,-1)],
        progress=progresses)
