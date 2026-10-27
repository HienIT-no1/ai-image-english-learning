import io
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from PIL import Image
from jose import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import ai_service, ai_detection, cloudinary_service
from app.services.ai_detection import Candidate, reconcile
from app.services.cloudinary_service import UploadedImage, ImageStorageError
from tests.test_topic_flow import isolated_db
from tests.test_session_collection import api, register


def photo():
    out=io.BytesIO();Image.new('RGB',(24,32),'white').save(out,'PNG');return out.getvalue()

def capture(client, headers, raw=None):
    return client.post('/ai/detect/capture',headers=headers,files={'file':('photo.png',photo() if raw is None else raw,'image/png')})

def count(engine, table):
    with engine.connect() as c:return c.scalar(text('SELECT count(*) FROM '+table))

@pytest.fixture()
def detections(monkeypatch):
    monkeypatch.setattr(ai_service,'detect_candidates',lambda image,conf:[Candidate('Laptop',.8,(1,2,20,30))])

def test_capture_requires_valid_session_before_side_effects(api,monkeypatch):
    client,engine,_=api
    uid,headers=register(client,'ai_owner')
    def forbidden(*args,**kwargs):raise AssertionError('Unauthenticated request reached inference/upload')
    monkeypatch.setattr(ai_service,'detect_candidates',forbidden)
    monkeypatch.setattr(ai_service,'upload_image_bytes',forbidden)
    expired=jwt.encode({'sub':str(uid),'exp':datetime.now(timezone.utc)-timedelta(seconds=1)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    for token in [None,'invalid',expired]:
        response=capture(client,{} if token is None else {'Authorization':'Bearer '+token})
        assert response.status_code==401
    assert count(engine,'images')==0 and count(engine,'vocabularies')==1

def test_invalid_files_use_client_errors_and_limits(api,monkeypatch):
    client,engine,_=api
    _,headers=register(client,'ai_invalid')
    for path in ['/ai/detect/realtime','/ai/detect/capture']:
        for raw in [b'',b'not an image']:
            assert client.post(path,headers=headers,files={'file':('bad.jpg',raw,'image/jpeg')}).status_code==400
        assert client.post(path,headers=headers,files={'file':('huge.jpg',b'x'*(ai_detection.MAX_IMAGE_BYTES+1),'image/jpeg')}).status_code==413
    assert count(engine,'images')==0

def test_realtime_does_not_create_vocabulary(api,detections):
    client,engine,_=api
    result=client.post('/ai/detect/realtime',files={'file':('photo.png',photo(),'image/png')})
    assert result.status_code==200
    data=result.json();assert data['image_width']==24 and data['image_height']==32
    assert data['detections'][0]['vocabulary']['vocabulary_id'] is None
    assert count(engine,'vocabularies')==1

def test_upload_failure_keeps_database_unchanged(api,detections,monkeypatch):
    client,engine,_=api
    _,headers=register(client,'ai_upload_fail')
    def fail(*args,**kwargs):raise ImageStorageError('Temporary upload failure')
    monkeypatch.setattr(ai_service,'upload_image_bytes',fail)
    result=capture(client,headers)
    assert result.status_code==503
    assert count(engine,'vocabularies')==1 and count(engine,'images')==0

def test_capture_commits_image_and_word_then_save_collection(api,detections,monkeypatch):
    client,engine,_=api
    uid,headers=register(client,'ai_capture')
    monkeypatch.setattr(ai_service,'upload_image_bytes',lambda *a,**k:UploadedImage('https://example.test/qa.jpg','qa/capture'))
    result=capture(client,headers);assert result.status_code==200
    data=result.json();vid=data['detections'][0]['vocabulary']['vocabulary_id']
    assert vid and data['image_id']
    with engine.connect() as c:
        assert c.scalar(text('SELECT user_id FROM images WHERE image_id=:i'),{'i':data['image_id']})==uid
        assert c.scalar(text('SELECT meaning_vi FROM vocabulary_meanings WHERE vocabulary_id=:v'),{'v':vid})=='máy tính xách tay'
    assert client.put(f'/collections/me/words/{vid}',headers=headers).status_code==200
    assert client.get('/collections/me',headers=headers).json()['words'][0]['word']=='laptop'

def test_db_failure_rolls_back_word_and_deletes_upload(api,detections,monkeypatch):
    client,engine,_=api
    _,headers=register(client,'ai_db_fail');deleted=[]
    monkeypatch.setattr(ai_service,'upload_image_bytes',lambda *a,**k:UploadedImage('https://example.test/qa.jpg','qa/rollback'))
    monkeypatch.setattr(ai_service,'delete_uploaded_image',deleted.append)
    def fail_commit(self):raise RuntimeError('QA failed commit')
    with monkeypatch.context() as patch:
        patch.setattr(Session,'commit',fail_commit)
        response=capture(client,headers)
    assert response.status_code==503 and deleted==['qa/rollback']
    assert count(engine,'images')==0 and count(engine,'vocabularies')==1

def test_concurrent_captures_share_one_word(api,detections,monkeypatch):
    client,engine,_=api
    uid,headers=register(client,'ai_parallel')
    monkeypatch.setattr(ai_service,'upload_image_bytes',lambda *a,**k:UploadedImage('https://example.test/qa.jpg','qa/parallel'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:capture(client,headers),range(4)))
    assert all(r.status_code==200 for r in results)
    ids={r.json()['detections'][0]['vocabulary']['vocabulary_id'] for r in results}
    assert len(ids)==1 and count(engine,'vocabularies')==2 and count(engine,'images')==4
    with engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM vocabulary_meanings WHERE vocabulary_id=:v'),{'v':ids.pop()})==1

def test_mouse_lookup_does_not_reuse_animal(api):
    client,engine,_=api
    with engine.begin() as c:
        animal=c.scalar(text("INSERT INTO vocabularies(word,created_at) VALUES('mouse',now()) RETURNING vocabulary_id"))
        c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:v,'con chuột')"),{'v':animal})
    with Session(engine) as db:
        preview=ai_service.lookup_vocabulary(db,'Mouse')
        assert preview.word=='computer mouse' and preview.vocabulary_id is None
        confirmed=ai_service.lookup_vocabulary(db,'Mouse',auto_create=True)
        assert confirmed.vocabulary_id!=animal and confirmed.meaning_vi=='chuột máy tính'
        db.commit()
    assert client.get(f'/vocabularies/{animal}').json()['meanings'][0]['meaning_vi']=='con chuột'
    assert client.get(f'/vocabularies/{confirmed.vocabulary_id}').json()['meanings'][0]['meaning_vi']=='chuột máy tính'

def test_mouse_migration_preserves_existing_word_and_collection(isolated_db):
    engine,migrate=isolated_db;migrate('0007_reminders')
    with engine.begin() as c:
        uid=c.scalar(text("INSERT INTO users(username,email,password_hash) VALUES('legacy_mouse','mouse@example.com','fixture') RETURNING user_id"))
        animal=c.scalar(text("INSERT INTO vocabularies(word,created_at) VALUES('mouse',now()) RETURNING vocabulary_id"))
        c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:v,'con chuột')"),{'v':animal})
        col=c.scalar(text("INSERT INTO collections(user_id,collection_name) VALUES(:u,'Legacy') RETURNING collection_id"),{'u':uid})
        c.execute(text('INSERT INTO collection_words(collection_id,vocabulary_id) VALUES(:c,:v)'),{'c':col,'v':animal})
    migrate();migrate()
    with engine.connect() as c:
        computer=c.scalar(text("SELECT vocabulary_id FROM vocabularies WHERE word='computer mouse'"))
        assert computer and computer!=animal
        assert c.scalar(text('SELECT vocabulary_id FROM collection_words WHERE collection_id=:c'),{'c':col})==animal
        assert c.scalar(text('SELECT meaning_vi FROM vocabulary_meanings WHERE vocabulary_id=:v'),{'v':animal})=='con chuột'
        assert c.scalar(text("SELECT count(*) FROM vocabulary_topics JOIN topics USING(topic_id) WHERE vocabulary_id=:v AND slug='objects'"),{'v':computer})==1

def test_reference_corrects_only_stronger_same_object_predictions():
    original=Candidate('pomegranate',.692,(0,0,100,100))
    apple=Candidate('apple',.893,(1,1,99,99))
    assert reconcile([original],[apple])[0].label=='apple'
    # Nearby different objects, low confidence, or unsupported generic labels do not override.
    assert reconcile([original],[Candidate('apple',.99,(200,200,300,300))])==[original]
    assert reconcile([original],[Candidate('apple',.74,(0,0,100,100))])==[original]
    assert reconcile([original],[Candidate('bottle',.99,(0,0,100,100))])==[original]
    assert reconcile([Candidate('pomegranate',.9,original.box)],[apple])[0].label=='pomegranate'

def test_cloudinary_errors_do_not_expose_provider_credentials(monkeypatch):
    for key in ['CLOUDINARY_CLOUD_NAME','CLOUDINARY_API_KEY','CLOUDINARY_API_SECRET']:
        monkeypatch.setattr(settings,key,'QA-placeholder')
    def fail(*a,**k):raise RuntimeError('api_secret=DO-NOT-EXPOSE')
    monkeypatch.setattr(cloudinary_service.cloudinary.uploader,'upload',fail)
    with pytest.raises(ImageStorageError) as error:cloudinary_service.upload_image_bytes(photo())
    assert 'DO-NOT-EXPOSE' not in str(error.value)
