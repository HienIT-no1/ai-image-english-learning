from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import text
from tests.test_session_collection import api, register
from tests.test_topic_flow import isolated_db


def setup_game(api,monkeypatch,source='RANDOM'):
    import seed_game
    client,engine,cat=api
    monkeypatch.setattr(seed_game,'engine',engine)
    seed_game.main()
    uid,headers=register(client,'game_a')
    _,other=register(client,'game_b')
    request={'source':source,'client_session_id':str(uuid4())}
    return client,engine,uid,headers,other,request


def resolved(words,misses=()):
    return {'results':[{'vocabulary_id':w['vocabulary_id'],'outcome':'MISSED' if i in misses else 'SOLVED',
        'answer':None if i in misses else w['word'],'wrong_letters':7 if i==6 else 0}
        for i,w in enumerate(words)]}


def test_game_scoring_retry_transition_and_ownership(api,monkeypatch):
    client,engine,uid,h,other,request=setup_game(api,monkeypatch)
    with ThreadPoolExecutor(max_workers=3) as pool:
        starts=list(pool.map(lambda _:client.post('/games/word-shooter',headers=h,json=request),range(3)))
    assert all(r.status_code==200 for r in starts)
    data=starts[0].json();assert all(r.json()==data for r in starts)
    assert len(data['round']['words'])==20
    base=f"/games/word-shooter/{data['run_id']}"
    finish=base+f"/rounds/{data['round']['round_id']}/finish"
    next_url=base+f"/rounds/{data['round']['round_id']}/next"
    assert client.get(base,headers=other).status_code==404
    assert client.get(base).status_code==401
    assert client.post(finish,headers=other,json=resolved(data['round']['words'])).status_code==404
    assert client.post(next_url,headers=h).status_code==409
    assert client.post('/games/word-shooter',headers=h,json=request|{'source':'SAVED'}).status_code==409
    body=resolved(data['round']['words'],[10,15,19])
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(lambda _:client.post(finish,headers=h,json=body),range(3)))
    assert all(r.status_code==200 for r in results)
    result=results[0].json()['round']
    # Mistyping 7 letters on word 7 does not reset the 10-word streak.
    assert (result['status'],result['correct_count'],result['missed_count'],result['max_combo'])==('PASSED',17,3,10)
    assert result['score']==1875
    assert client.post(finish,headers=h,json=resolved(data['round']['words'])).status_code==409
    progress=client.get('/learning/me',headers=h).json()
    assert (progress['today_count'],progress['review_count'],progress['mastered_count'])==(20,20,0)
    assert client.get('/learning/me',headers=other).json()['today_count']==0
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM learning_events WHERE kind='GAME'"))==20
    with ThreadPoolExecutor(max_workers=3) as pool:
        nexts=list(pool.map(lambda _:client.post(next_url,headers=h),range(3)))
    assert all(r.status_code==200 for r in nexts)
    following=nexts[0].json();assert all(r.json()==following for r in nexts)
    previous_correct={r['vocabulary_id'] for r in body['results'] if r['outcome']=='SOLVED'}
    previous_wrong={r['vocabulary_id'] for r in body['results'] if r['outcome']=='MISSED'}
    next_ids={w['vocabulary_id'] for w in following['round']['words']}
    assert previous_wrong<=next_ids and not previous_correct&next_ids
    assert following['round']['stage']==2 and len(next_ids)==20


def test_fourth_miss_failure_retry_and_validation(api,monkeypatch):
    client,engine,uid,h,_,request=setup_game(api,monkeypatch)
    data=client.post('/games/word-shooter',headers=h,json=request).json()
    base=f"/games/word-shooter/{data['run_id']}";rid=data['round']['round_id']
    url=base+f'/rounds/{rid}/finish';words=data['round']['words']
    assert client.post(url,headers=h,json=resolved(words[:3])).status_code==409
    bad=resolved(words);bad['results'][0]['answer']='wrong'
    assert client.post(url,headers=h,json=bad).status_code==422
    bad=resolved(words);bad['results'][1]=bad['results'][0]
    assert client.post(url,headers=h,json=bad).status_code==422
    bad=resolved(words[:5],[0,1,2,3])
    assert client.post(url,headers=h,json=bad).status_code==422
    body=resolved(words[:7],[0,2,4,6])
    result=client.post(url,headers=h,json=body)
    assert result.status_code==200 and result.json()['round']['status']=='FAILED'
    following=client.post(base+f'/rounds/{rid}/next',headers=h).json()
    assert following['round']['stage']==1 and following['round']['words']==words
    assert following['round']['round_id']!=rid
    assert client.get('/learning/me',headers=h).json()['review_count']==7


def test_sources_small_pool_snapshot_and_completion(api,monkeypatch):
    client,engine,uid,h,_,request=setup_game(api,monkeypatch)
    root='/games/word-shooter'
    assert client.post(root,headers=h,json=request|{'source':'SAVED'}).status_code==400
    assert client.post(root,headers=h,json=request|{'source':'TOPIC'}).status_code==422
    assert client.post(root,headers=h,json=request|{'source':'TOPIC','topic_id':999999}).status_code==404
    with engine.connect() as c:
        ids=c.execute(text('SELECT vocabulary_id FROM vocabularies ORDER BY vocabulary_id LIMIT 3')).scalars().all()
    for ident in ids: client.put(f'/collections/me/words/{ident}',headers=h)
    data=client.post(root,headers=h,json=request|{'source':'SAVED'}).json()
    assert {w['vocabulary_id'] for w in data['round']['words']}==set(ids)
    # The deck remains stable even if saved words change during play.
    client.delete(f'/collections/me/words/{ids[0]}',headers=h)
    assert client.get(root+f"/{data['run_id']}",headers=h).json()['round']['words']==data['round']['words']
    result=client.post(root+f"/{data['run_id']}/rounds/{data['round']['round_id']}/finish",headers=h,json=resolved(data['round']['words'])).json()
    assert result['completed'] and result['remaining_count']==0
    assert client.post(root+f"/{data['run_id']}/rounds/{data['round']['round_id']}/next",headers=h).status_code==409
    topic=client.get('/topics').json()[0]['topic_id']
    data=client.post(root,headers=h,json={'source':'TOPIC','topic_id':topic,'client_session_id':str(uuid4())}).json()
    assert all(topic in [t['topic_id'] for t in w['topics']] for w in data['round']['words'])
    word=data['round']['words'][0]
    client.post('/learning/me/reviews',headers=h,json={'vocabulary_id':word['vocabulary_id'],'remembered':False,'event_key':str(uuid4())})
    difficult=client.post(root,headers=h,json={'source':'DIFFICULT','client_session_id':str(uuid4())}).json()
    assert [w['vocabulary_id'] for w in difficult['round']['words']]==[word['vocabulary_id']]
    with engine.connect() as c:
        before=c.scalar(text('SELECT count(*) FROM vocabularies'))
    import seed_game
    seed_game.main()
    with engine.connect() as c: assert c.scalar(text('SELECT count(*) FROM vocabularies'))==before


def test_random_chapter_ends_after_five_passed_stages(api,monkeypatch):
    client,engine,uid,h,_,request=setup_game(api,monkeypatch)
    root='/games/word-shooter'
    data=client.post(root,headers=h,json=request).json();seen=set()
    for stage in range(1,6):
        current=data['round'];ids={w['vocabulary_id'] for w in current['words']}
        assert len(ids)==20 and not ids&seen;seen|=ids
        base=root+f"/{data['run_id']}/rounds/{current['round_id']}"
        data=client.post(base+'/finish',headers=h,json=resolved(current['words'])).json()
        assert data['completed']==(stage==5)
        assert data['round']['max_combo']==20
        if stage<5: data=client.post(base+'/next',headers=h).json()
    assert client.get('/learning/me',headers=h).json()['today_count']==100


def test_difficult_uses_latest_answer_and_preserves_mastery(api):
    client,engine,cat=api
    uid,h=register(client,'game_difficult')
    for _ in range(3):
        client.post('/learning/me/reviews',headers=h,json={'vocabulary_id':cat,'remembered':False,'event_key':str(uuid4())})
    root='/games/word-shooter'
    request={'source':'DIFFICULT','client_session_id':str(uuid4())}
    data=client.post(root,headers=h,json=request).json()
    assert len(data['round']['words'])==1
    client.post(root+f"/{data['run_id']}/rounds/{data['round']['round_id']}/finish",headers=h,json=resolved(data['round']['words']))
    assert client.post(root,headers=h,json=request|{'client_session_id':str(uuid4())}).status_code==400
    # Explicit Flashcard mastery remains intact after successful or failed game play.
    client.post('/learning/me/reviews',headers=h,json={'vocabulary_id':cat,'remembered':True,'event_key':str(uuid4())})
    data=client.post(root,headers=h,json={'source':'RANDOM','client_session_id':str(uuid4())}).json()
    client.post(root+f"/{data['run_id']}/rounds/{data['round']['round_id']}/finish",headers=h,json=resolved(data['round']['words'],[0]))
    assert client.get('/learning/me',headers=h).json()['progress'][0]['status']=='MASTERED'


def test_game_migration_preserves_existing_rows(isolated_db):
    from tests.test_topic_flow import add_cat
    engine,migrate=isolated_db
    migrate('0005_admin_roles');cat=add_cat(engine)
    with engine.begin() as c:
        user=c.scalar(text("INSERT INTO users(username,email,password_hash,role) VALUES('old_admin','old_admin@example.com','fixture','ADMIN') RETURNING user_id"))
        c.execute(text("INSERT INTO learning_progress(user_id,vocabulary_id,status,review_count,correct_count) VALUES(:u,:v,'MASTERED',8,8)"),{'u':user,'v':cat})
        c.execute(text("INSERT INTO learning_events(user_id,vocabulary_id,event_key,kind,is_correct) VALUES(:u,:v,:key,'QUIZ',true)"),{'u':user,'v':cat,'key':uuid4()})
    migrate();migrate()
    with engine.connect() as c:
        assert c.scalar(text('SELECT role FROM users'))=='ADMIN'
        assert c.scalar(text('SELECT review_count FROM learning_progress'))==8
        assert c.scalar(text('SELECT kind FROM learning_events'))=='QUIZ'
        assert c.scalar(text('SELECT count(*) FROM game_runs'))==0
