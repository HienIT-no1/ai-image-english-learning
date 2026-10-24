from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from sqlalchemy import text
from tests.test_session_collection import api,register
from tests.test_topic_flow import isolated_db,add_cat


def profile(minutes=1200,enabled=True):
    return {'full_name':'Reminder tester','cefr_level':'A1','daily_goal':10,'reminders_enabled':enabled,'reminder_minutes':minutes}

def review(client,h,cat,known):
    return client.post('/learning/me/reviews',headers=h,json={'vocabulary_id':cat,'remembered':known,'event_key':str(uuid4())})


def test_reminder_time_validation_compatibility_and_account_isolation(api):
    client,engine,cat=api
    user,h=register(client,'reminder_a');_,other=register(client,'reminder_b')
    assert client.get('/users/me',headers=h).json()['reminder_minutes']==1200
    assert client.patch('/users/me',headers=h,json=profile(7*60+30)).json()['reminder_minutes']==450
    old=profile();old.pop('reminder_minutes')
    assert client.patch('/users/me',headers=h,json=old).json()['reminder_minutes']==450
    for invalid in [-1,1440]: assert client.patch('/users/me',headers=h,json=profile(invalid)).status_code==422
    assert client.get('/users/me',headers=other).json()['reminder_minutes']==1200
    with engine.connect() as c:
        assert c.scalar(text('SELECT reminder_minutes FROM users WHERE user_id=:u'),{'u':user})==450


def test_due_schedule_growth_failure_and_exactly_once(api):
    client,engine,cat=api
    user,h=register(client,'due_a');_,other=register(client,'due_b')
    client.put(f'/collections/me/words/{cat}',headers=h)
    assert len(client.get('/learning/me/due',headers=h).json())==1
    assert client.get('/learning/me',headers=h).json()['due_count']==1
    assert client.get('/learning/me/due',headers=other).json()==[]
    assert client.get('/learning/me/due').status_code==401
    for days in [1,3,7,14,28,30,30]:
        request={'vocabulary_id':cat,'remembered':True,'event_key':str(uuid4())}
        before=datetime.now(timezone.utc)
        result=client.post('/learning/me/reviews',headers=h,json=request)
        assert result.status_code==200,result.text
        progress=result.json()['progress'][0]
        assert progress['review_interval_days']==days
        due=datetime.fromisoformat(progress['next_review_at'])
        assert before+timedelta(days=days)-timedelta(seconds=1)<=due<=datetime.now(timezone.utc)+timedelta(days=days)
        assert client.post('/learning/me/reviews',headers=h,json=request).json()['progress'][0]['next_review_at']==progress['next_review_at']
        assert client.get('/learning/me/due',headers=h).json()==[]
    result=review(client,h,cat,False).json()['progress'][0]
    assert result['review_interval_days']==0
    assert datetime.now(timezone.utc)+timedelta(minutes=9)<datetime.fromisoformat(result['next_review_at'])<datetime.now(timezone.utc)+timedelta(minutes=11)
    with engine.begin() as c:
        c.execute(text("UPDATE learning_progress SET next_review_at=now()-interval '1 minute' WHERE user_id=:u"),{'u':user})
    assert client.get('/learning/me/due',headers=h).json()[0]['vocabulary_id']==cat


def test_notification_inbox_retry_read_and_ownership(api):
    client,engine,cat=api
    user,h=register(client,'inbox_a');_,other=register(client,'inbox_b')
    body={'occurrence_date':datetime.now(timezone(timedelta(hours=7))).date().isoformat()}
    assert client.post('/notifications/reminders',headers=h,json=body).status_code==409
    client.patch('/users/me',headers=h,json=profile())
    client.put(f'/collections/me/words/{cat}',headers=h)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.post('/notifications/reminders',headers=h,json=body),range(8)))
    assert all(r.status_code==200 for r in responses)
    assert len({r.json()['notification_id'] for r in responses})==1
    data=client.get('/notifications',headers=h).json()
    assert data['unread_count']==1 and len(data['items'])==1 and '1 từ' in data['items'][0]['body']
    ident=data['items'][0]['notification_id']
    assert client.get('/notifications').status_code==401
    assert client.get('/notifications',headers=other).json()['items']==[]
    assert client.post(f'/notifications/{ident}/read',headers=other).status_code==404
    read=client.post(f'/notifications/{ident}/read',headers=h).json()
    assert read['read_at'] is not None
    assert client.post(f'/notifications/{ident}/read',headers=h).json()['read_at']==read['read_at']
    assert client.get('/notifications',headers=h).json()['unread_count']==0
    yesterday={'occurrence_date':(datetime.now(timezone(timedelta(hours=7))).date()-timedelta(days=1)).isoformat()}
    assert client.post('/notifications/reminders',headers=h,json=yesterday).status_code==200
    assert client.post('/notifications/read-all',headers=h).status_code==200
    assert client.get('/notifications',headers=h).json()['unread_count']==0
    assert client.post('/notifications/reminders',headers=h,json={'occurrence_date':'2100-01-01'}).status_code==422
    with engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM notifications WHERE user_id=:u'),{'u':user})==2


def test_reminder_migration_preserves_learning_history(isolated_db):
    engine,migrate=isolated_db;migrate('0006_word_shooter');cat=add_cat(engine)
    with engine.begin() as c:
        user=c.scalar(text("INSERT INTO users(username,email,password_hash,reminders_enabled) VALUES('legacy_reminder','legacy_reminder@example.com','fixture',true) RETURNING user_id"))
        c.execute(text("INSERT INTO learning_progress(user_id,vocabulary_id,status,review_count,correct_count,last_reviewed_at) VALUES(:u,:v,'MASTERED',3,3,now())"),{'u':user,'v':cat})
    migrate();migrate()
    with engine.connect() as c:
        assert c.execute(text('SELECT reminder_minutes,reminders_enabled FROM users')).one()==(1200,True)
        row=c.execute(text('SELECT review_count,correct_count,review_interval_days,next_review_at FROM learning_progress')).one()
        assert row[:3]==(3,3,7) and row[3] is not None
        assert c.scalar(text('SELECT count(*) FROM notifications'))==0
