from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from sqlalchemy import text
from tests.test_session_collection import api, register
from tests.test_topic_flow import isolated_db
from tests.test_game_flow import setup_game, resolved

ROOT='/games/word-defense'
def begin(client,h,request,mode='RECALL'):
    response=client.post(ROOT,headers=h,json=request|{'learning_mode':mode})
    assert response.status_code==200,response.text
    return response.json()
def round_url(data):return ROOT+f"/{data['run_id']}/rounds/{data['round']['round_id']}"

def test_defense_modes_isolation_and_exactly_once_learning(api,monkeypatch):
    client,engine,uid,h,other,request=setup_game(api,monkeypatch)
    request|={'learning_mode':'TYPING'}
    with ThreadPoolExecutor(max_workers=3) as pool:
        starts=list(pool.map(lambda _:client.post(ROOT,headers=h,json=request),range(3)))
    assert all(r.status_code==200 for r in starts)
    data=starts[0].json();assert all(r.json()==data for r in starts)
    assert data['game_type']=='WORD_DEFENSE' and data['learning_mode']=='TYPING'
    assert client.get(ROOT+f"/{data['run_id']}",headers=other).status_code==404
    assert client.get('/games/word-shooter/'+str(data['run_id']),headers=h).status_code==404
    assert client.post('/games/word-shooter',headers=h,json={k:v for k,v in request.items() if k!='learning_mode'}).status_code==409
    assert client.post(ROOT,headers=h,json=request|{'learning_mode':'RECALL'}).status_code==409
    assert client.post(ROOT,headers=h,json=request|{'learning_mode':'ADMIN'}).status_code==422
    assert client.post(ROOT,json=request).status_code==401
    body=resolved(data['round']['words'],[19]);url=round_url(data)
    assert client.post(url+'/next',headers=h).status_code==409
    with ThreadPoolExecutor(max_workers=3) as pool:
        finishes=list(pool.map(lambda _:client.post(url+'/finish',headers=h,json=body),range(3)))
    assert all(r.status_code==200 for r in finishes)
    score=finishes[0].json()['round'];assert score['max_combo']==19 and score['missed_count']==1
    assert client.post(url+'/finish',headers=h,json=resolved(data['round']['words'])).status_code==409
    progress=client.get('/learning/me',headers=h).json()
    assert progress['review_count']==20 and progress['mastered_count']==0
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM learning_events WHERE user_id=:u AND kind='GAME'"),{'u':uid})==20
        assert c.scalar(text('SELECT count(*) FROM learning_progress WHERE user_id=:u AND review_interval_days=1'),{'u':uid})==19
        assert c.scalar(text('SELECT count(*) FROM learning_progress WHERE user_id=:u AND review_interval_days=0'),{'u':uid})==1
    assert client.get('/learning/me',headers=other).json()['review_count']==0
    next_data=client.post(url+'/next',headers=h).json()
    correct={r['vocabulary_id'] for r in body['results'] if r['outcome']=='SOLVED'}
    assert not correct & {w['vocabulary_id'] for w in next_data['round']['words']}
    assert body['results'][-1]['vocabulary_id'] in {w['vocabulary_id'] for w in next_data['round']['words']}
    assert client.post(url+'/next',headers=h).json()==next_data

def test_defense_fourth_miss_retries_the_same_deck(api,monkeypatch):
    client,engine,uid,h,_,request=setup_game(api,monkeypatch)
    data=begin(client,h,request);url=round_url(data);words=data['round']['words']
    assert client.post(url+'/finish',headers=h,json=resolved(words[:3])).status_code==409
    bad=resolved(words);bad['results'][0]['answer']='not-the-word'
    assert client.post(url+'/finish',headers=h,json=bad).status_code==422
    result=client.post(url+'/finish',headers=h,json=resolved(words[:4],[0,1,2,3])).json()
    assert result['round']['status']=='FAILED'
    retry=client.post(url+'/next',headers=h).json()
    assert retry['round']['stage']==1 and retry['round']['words']==words
    assert client.get('/learning/me',headers=h).json()['review_count']==4

def test_defense_sources_and_small_decks(api,monkeypatch):
    client,engine,uid,h,_,request=setup_game(api,monkeypatch)
    assert client.post(ROOT,headers=h,json=request|{'source':'SAVED'}).status_code==400
    catalog=client.get('/vocabularies').json()[:3]
    for word in catalog:client.put('/collections/me/words/'+str(word['vocabulary_id']),headers=h)
    saved=begin(client,h,request|{'source':'SAVED'})
    assert len(saved['round']['words'])==3
    client.delete('/collections/me/words/'+str(catalog[0]['vocabulary_id']),headers=h)
    assert client.get(ROOT+f"/{saved['run_id']}",headers=h).json()['round']['words']==saved['round']['words']
    done=client.post(round_url(saved)+'/finish',headers=h,json=resolved(saved['round']['words'])).json()
    assert done['completed'] and done['remaining_count']==0
    word=catalog[0]['vocabulary_id']
    client.post('/learning/me/reviews',headers=h,json={'vocabulary_id':word,'remembered':False,'event_key':str(uuid4())})
    difficult=begin(client,h,request|{'source':'DIFFICULT','client_session_id':str(uuid4())})
    assert [w['vocabulary_id'] for w in difficult['round']['words']]==[word]
    review=begin(client,h,request|{'source':'REVIEW','client_session_id':str(uuid4())})
    assert {w['vocabulary_id'] for w in review['round']['words']}=={w['vocabulary_id'] for w in catalog}
    topic=client.get('/topics').json()[0]['topic_id']
    topic_run=begin(client,h,request|{'source':'TOPIC','topic_id':topic,'client_session_id':str(uuid4())})
    assert all(topic in [t['topic_id'] for t in w['topics']] for w in topic_run['round']['words'])

def test_defense_checkpoint_can_continue_or_stop_without_repeating_words(api,monkeypatch):
    client,engine,uid,h,other,request=setup_game(api,monkeypatch)
    # More than 100 words prove this game is not automatically stopped at five stages.
    with engine.begin() as c:
        for i in range(30):
            word='extra'+chr(97+i//26)+chr(97+i%26)
            ident=c.scalar(text('INSERT INTO vocabularies(word,created_at) VALUES(:w,now()) RETURNING vocabulary_id'),{'w':word})
            c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:v,'từ bổ sung')"),{'v':ident})
    run=begin(client,h,request)
    base=ROOT+f"/{run['run_id']}"
    assert client.post(base+'/complete',headers=h).status_code==409
    seen=set()
    for stage in range(1,6):
        current=run['round'];ids={w['vocabulary_id'] for w in current['words']}
        assert current['stage']==stage and not ids&seen;seen|=ids
        url=round_url(run)
        run=client.post(url+'/finish',headers=h,json=resolved(current['words'])).json()
        assert not run['completed'] and run['checkpoint']==(stage==5)
        if stage<5:run=client.post(url+'/next',headers=h).json()
    assert client.post(base+'/complete',headers=other).status_code==404
    # Complete/next race is serialized: whichever wins leaves one consistent result.
    finished=client.post(base+'/complete',headers=h)
    assert finished.status_code==200 and finished.json()['completed']
    assert client.post(base+'/complete',headers=h).json()==finished.json()
    assert client.post(round_url(run)+'/next',headers=h).status_code==409
    # A second run chooses continue at its checkpoint.
    second=begin(client,h,request|{'client_session_id':str(uuid4())})
    for stage in range(1,6):
        url=round_url(second)
        second=client.post(url+'/finish',headers=h,json=resolved(second['round']['words'])).json()
        if stage<5:second=client.post(url+'/next',headers=h).json()
    next_data=client.post(round_url(second)+'/next',headers=h).json()
    assert next_data['round']['stage']==6 and not next_data['checkpoint'] and not next_data['completed']

def test_defense_migration_keeps_existing_shooter_rounds(isolated_db):
    engine,migrate=isolated_db;migrate('0008_ai_senses')
    with engine.begin() as c:
        uid=c.scalar(text("INSERT INTO users(username,email,password_hash) VALUES('old_game','oldgame@example.com','fixture') RETURNING user_id"))
        run=c.scalar(text("INSERT INTO game_runs(user_id,client_session_id,source,pool) VALUES(:u,:key,'RANDOM','[]') RETURNING run_id"),{'u':uid,'key':uuid4()})
        c.execute(text("INSERT INTO game_rounds(run_id,sequence,stage,words,status,score) VALUES(:r,1,1,'[]','PASSED',250)"),{'r':run})
    migrate();migrate()
    with engine.connect() as c:
        assert c.execute(text('SELECT game_type,learning_mode FROM game_runs')).one()==('WORD_SHOOTER','RECALL')
        assert c.scalar(text('SELECT score FROM game_rounds'))==250
