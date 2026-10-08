from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from jose import jwt
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.database import get_db
from main import app
from tests.test_topic_flow import isolated_db, add_cat

@pytest.fixture()
def api(isolated_db):
    engine, migrate = isolated_db
    migrate()
    ident = add_cat(engine)
    def override():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as client: yield client, engine, ident
    finally: app.dependency_overrides.pop(get_db, None)

def register(client, username):
    password = "test-password-9374"
    result=client.post("/auth/register",json={"username":username,"email":username+"@example.com","password":password})
    assert result.status_code==201
    login=client.post("/auth/login",json={"username":username,"password":password})
    assert login.status_code==200
    return result.json()["user"]["user_id"], {"Authorization":"Bearer "+login.json()["access_token"]}

def test_restore_identity_and_reject_expired_token(api):
    client,engine,ident=api
    user_id,headers=register(client,"session_a")
    assert client.get("/users/me",headers=headers).json()["user_id"]==user_id
    assert client.get("/collections/me").status_code==401
    expired=jwt.encode({"sub":str(user_id),"exp":datetime.now(timezone.utc)-timedelta(minutes=1)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    expired_headers={"Authorization":"Bearer "+expired}
    assert client.get("/users/me",headers=expired_headers).status_code==401
    assert client.put(f"/collections/me/words/{ident}",headers=expired_headers).status_code==401
    assert client.get("/collections/me",headers=headers).json()["words"]==[]

def test_save_restore_unsave_and_account_isolation(api):
    client,engine,ident=api
    a,ha=register(client,"collection_a")
    b,hb=register(client,"collection_b")
    assert client.get("/collections/me",headers=ha).json()["words"]==[]
    saved=client.put(f"/collections/me/words/{ident}",headers=ha)
    assert saved.status_code==200
    assert saved.json()["words"][0]["word"]=="cat"
    assert saved.json()["words"][0]["meanings"][0]["meaning_vi"]=="con mèo"
    # Repeat save and a new read represent retry/reopen on another client/device.
    assert len(client.put(f"/collections/me/words/{ident}",headers=ha).json()["words"])==1
    assert len(client.get("/collections/me",headers=ha).json()["words"])==1
    assert client.get(f"/collections/me?user_id={a}",headers=hb).json()["words"]==[]
    client.delete(f"/collections/me/words/{ident}",headers=hb)
    assert len(client.get("/collections/me",headers=ha).json()["words"])==1
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM collection_words w JOIN collections c USING(collection_id) WHERE c.user_id=:user"),{"user":a}).scalar_one()==1
    assert client.delete(f"/collections/me/words/{ident}",headers=ha).json()["words"]==[]
    assert client.delete(f"/collections/me/words/{ident}",headers=ha).status_code==200
    assert client.get("/collections/me",headers=ha).json()["words"]==[]

def test_invalid_word_and_concurrent_retries(api):
    client,engine,ident=api
    _,headers=register(client,"concurrent_a")
    assert client.put("/collections/me/words/999999",headers=headers).status_code==404
    assert client.put("/collections/me/words/0",headers=headers).status_code==422
    # Requests race to create the default collection and save the same word.
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses=list(pool.map(lambda _:client.put(f"/collections/me/words/{ident}",headers=headers),range(8)))
    assert all(r.status_code==200 for r in responses)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM collections WHERE is_default")).scalar_one()==1
        assert c.execute(text("SELECT count(*) FROM collection_words")).scalar_one()==1

def test_migration_preserves_existing_collections(isolated_db):
    engine,migrate=isolated_db
    migrate("0002_topics")
    ident=add_cat(engine)
    with engine.begin() as c:
        user=c.execute(text("INSERT INTO users(username,email,password_hash) VALUES('legacy_collection','legacy@example.com','fixture-hash') RETURNING user_id")).scalar_one()
        first=c.execute(text("INSERT INTO collections(user_id,collection_name) VALUES(:u,'First') RETURNING collection_id"),{"u":user}).scalar_one()
        second=c.execute(text("INSERT INTO collections(user_id,collection_name) VALUES(:u,'Second') RETURNING collection_id"),{"u":user}).scalar_one()
        c.execute(text("INSERT INTO collection_words(collection_id,vocabulary_id) VALUES(:c,:v)"),{"c":second,"v":ident})
    migrate()
    migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM collections")).scalar_one()==2
        assert c.execute(text("SELECT collection_id FROM collections WHERE is_default")).scalar_one()==first
        assert c.execute(text("SELECT count(*) FROM collection_words WHERE vocabulary_id=:v"),{"v":ident}).scalar_one()==2
