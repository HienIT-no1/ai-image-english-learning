from uuid import uuid4
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from jose import jwt
from create_admin import create_admin
from app.core.config import settings
from app.core.security import verify_password
from tests.test_topic_flow import isolated_db, add_cat
from tests.test_session_collection import api, register


def admin(client, engine, username="admin_test"):
    password="admin-test-secret-8301"
    with Session(engine) as db:
        user=create_admin(db,username,username+"@example.com",password,"Admin Test")
        ident=user.user_id
    result=client.post("/auth/login",json={"username":username,"password":password})
    assert result.status_code==200
    return ident,{"Authorization":"Bearer "+result.json()["access_token"]}


def test_registration_and_profile_cannot_grant_admin(api):
    client,engine,_=api
    body={"username":"intruder","email":"intruder@example.com","password":"test-secret-9834","role":"ADMIN"}
    assert client.post("/auth/register",json=body).status_code==422
    ident,headers=register(client,"normal_user")
    assert client.get("/users/me",headers=headers).json()["role"]=="USER"
    profile={"full_name":"Fake Admin","cefr_level":"A1","daily_goal":5,"role":"ADMIN"}
    assert client.patch("/users/me",headers=headers,json=profile).status_code==422
    with engine.connect() as c:
        assert c.execute(text("SELECT role FROM users WHERE user_id=:u"),{"u":ident}).scalar_one()=="USER"
        assert c.execute(text("SELECT count(*) FROM users WHERE username='intruder'")).scalar_one()==0


def test_all_admin_routes_enforce_current_database_role(api):
    client,engine,cat=api
    user,headers=register(client,"ordinary_user")
    routes=[("get","/admin/summary",None),("get","/admin/users",None),("get","/admin/topics",None),
        ("get","/admin/vocabularies",None),("post","/admin/topics",{"name":"Test","slug":"test","symbol":"x"}),
        ("put","/admin/topics/1",{"name":"Test","slug":"test","symbol":"x"}),
        ("delete","/admin/topics/1",None),
        ("post","/admin/vocabularies",{"word":"test","meaning_vi":"thử"}),
        ("put",f"/admin/vocabularies/{cat}",{"word":"test","meaning_vi":"thử"})]
    for method,path,body in routes:
        assert client.request(method,path,headers=headers,json=body).status_code==403
        assert client.request(method,path,json=body).status_code==401
    # Even a valid signed JWT claiming ADMIN cannot override the database role.
    forged=jwt.encode({"sub":str(user),"role":"ADMIN","exp":datetime.now(timezone.utc)+timedelta(minutes=10)},settings.JWT_SECRET_KEY,algorithm=settings.JWT_ALGORITHM)
    assert client.get("/admin/summary",headers={"Authorization":"Bearer "+forged}).status_code==403
    ident,ha=admin(client,engine)
    assert client.get("/users/me",headers=ha).json()["role"]=="ADMIN"
    assert client.get("/admin/summary",headers=ha).status_code==200
    users=client.get("/admin/users",headers=ha).json()
    assert all(set(u)=={"user_id","username","email","full_name","role"} for u in users)
    with engine.begin() as c: c.execute(text("UPDATE users SET role='USER' WHERE user_id=:u"),{"u":ident})
    assert client.get("/admin/summary",headers=ha).status_code==403
    assert client.get("/users/me",headers=ha).json()["role"]=="USER"


def test_admin_topic_word_flow_visible_to_learners(api):
    client,engine,cat=api
    _,ha=admin(client,engine)
    topic={"name":"Test School","slug":"test-school","symbol":"📚"}
    created=client.post("/admin/topics",headers=ha,json=topic)
    assert created.status_code==201
    tid=created.json()["topic_id"]
    assert client.post("/admin/topics",headers=ha,json=topic).status_code==409
    assert client.post("/admin/topics",headers=ha,json=topic|{"name":"   ","slug":"empty"}).status_code==422
    word={"word":"pencil","meaning_vi":"bút chì","ipa":"/pensəl/","sentence_en":"This is a pencil.","sentence_vi":"Đây là bút chì.","topic_ids":[tid]}
    response=client.post("/admin/vocabularies",headers=ha,json=word)
    assert response.status_code==201
    wid=response.json()["vocabulary_id"]
    assert client.get(f"/topics/{tid}/vocabularies").json()[0]["word"]=="pencil"
    assert client.delete(f"/admin/topics/{tid}",headers=ha).status_code==409
    assert client.post("/admin/vocabularies",headers=ha,json=word|{"word":"PENCIL"}).status_code==409
    assert client.put(f"/admin/vocabularies/{wid}",headers=ha,json=word|{"meaning_vi":"wrong change","topic_ids":[999999]}).status_code==404
    assert client.get(f"/vocabularies/{wid}").json()["meanings"][0]["meaning_vi"]=="bút chì"
    updated=client.put(f"/admin/vocabularies/{wid}",headers=ha,json=word|{"meaning_vi":"cây bút chì","topic_ids":[]})
    assert updated.status_code==200
    assert client.get(f"/vocabularies/{wid}").json()["meanings"][0]["meaning_vi"]=="cây bút chì"
    assert client.put(f"/admin/topics/{tid}",headers=ha,json=topic|{"name":"Updated"}).json()["name"]=="Updated"
    assert client.delete(f"/admin/topics/{tid}",headers=ha).status_code==200
    assert client.get(f"/topics/{tid}/vocabularies").status_code==404
    summary=client.get("/admin/summary",headers=ha).json()
    assert summary["admins"]==1 and summary["vocabularies"]==2


def test_word_edit_preserves_extra_meanings_and_examples(api):
    client,engine,cat=api
    _,ha=admin(client,engine)
    with engine.begin() as c:
        c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi,definition_en) VALUES(:v,'additional meaning','additional definition')"),{"v":cat})
        c.execute(text("INSERT INTO vocabulary_examples(vocabulary_id,sentence_en) VALUES(:v,'Another example.')"),{"v":cat})
    result=client.put(f"/admin/vocabularies/{cat}",headers=ha,json={"word":"cat","meaning_vi":"mèo","sentence_en":"A cat.","topic_ids":[]})
    assert result.status_code==200
    assert len(result.json()["meanings"])==2 and len(result.json()["examples"])==2
    assert result.json()["meanings"][1]["definition_en"]=="additional definition"
    assert client.put(f"/admin/vocabularies/{cat}",headers=ha,json={"word":"cat","meaning_vi":"mèo"}).status_code==422
    assert client.get(f"/vocabularies/{cat}").json()["examples"][0]["sentence_en"]=="A cat."


def test_admin_provisioning_hashes_password_and_never_promotes_existing_user(api):
    client,engine,_=api
    ident,headers=register(client,"existing_user")
    with Session(engine) as db:
        with pytest.raises(ValueError): create_admin(db,"existing_user","other@example.com","admin-password-9374")
        with pytest.raises(ValueError): create_admin(db,"other_user","existing_user@example.com","admin-password-9374")
        created=create_admin(db,"separate_admin","separate@example.com","admin-password-9374")
        assert created.role=="ADMIN" and created.onboarding_completed
        assert created.password_hash!="admin-password-9374"
        assert verify_password("admin-password-9374",created.password_hash)
    assert client.get("/users/me",headers=headers).json()["role"]=="USER"


def test_role_migration_preserves_users_and_grants_no_admin(isolated_db):
    engine,migrate=isolated_db
    migrate("0004_learning")
    with engine.begin() as c:
        c.execute(text("INSERT INTO users(username,email,password_hash) VALUES('legacy','legacy@example.com','keep-this-hash')"))
    migrate();migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT username,password_hash,role FROM users")).one()==("legacy","keep-this-hash","USER")
