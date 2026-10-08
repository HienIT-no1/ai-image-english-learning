"""Integration tests use a disposable database; never insert fixtures in the app DB."""
import os
from pathlib import Path
import subprocess
import sys
import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.core.config import settings
from app.core.database import get_db
from main import app

@pytest.fixture()
def isolated_db():
    name = "test_topic_" + uuid.uuid4().hex
    url = make_url(os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL))
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    test_url = url.set(database=name)
    engine = create_engine(test_url)
    def migrate(target="head"):
        env = dict(os.environ, DATABASE_URL=test_url.render_as_string(hide_password=False))
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", target],
            env=env, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
    try:
        yield engine, migrate
    finally:
        engine.dispose()
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()

def add_cat(engine):
    with engine.begin() as c:
        ident = c.execute(text("INSERT INTO vocabularies(word,ipa) VALUES('cat','/kæt/') RETURNING vocabulary_id")).scalar_one()
        c.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:id,'con mèo')"), {"id": ident})
        c.execute(text("INSERT INTO vocabulary_examples(vocabulary_id,sentence_en,sentence_vi) VALUES(:id,'This is a cat.','Đây là con mèo.')"), {"id": ident})
        return ident

def test_fresh_database_and_repeated_upgrade(isolated_db):
    engine, migrate = isolated_db
    migrate()
    ident = add_cat(engine)
    migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM topics")).scalar_one() == 6
        assert c.execute(text("SELECT word FROM vocabularies WHERE vocabulary_id=:id"), {"id": ident}).scalar_one() == "cat"
        assert c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_learning"

def test_adopt_legacy_data_and_api(isolated_db):
    engine, migrate = isolated_db
    migrate("0001_legacy")
    ident = add_cat(engine)
    # Simulate a teammate's existing DB, without any Alembic history.
    with engine.begin() as c:
        c.execute(text("DROP TABLE alembic_version"))
    migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM vocabularies")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM vocabulary_meanings")).scalar_one() == 1
    def db_override():
        with Session(engine) as db: yield db
    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as client:
            response = client.get("/topics")
            assert response.status_code == 200
            topics = {t["slug"]: t for t in response.json()}
            assert topics["animals"]["vocabulary_count"] == 1
            assert topics["food"]["vocabulary_count"] == 0
            animal_id = topics["animals"]["topic_id"]
            food_id = topics["food"]["topic_id"]
            data = client.get(f"/topics/{animal_id}/vocabularies").json()
            assert len(data) == 1 and data[0]["vocabulary_id"] == ident
            assert data[0]["word"] == "cat"
            assert data[0]["meanings"][0]["meaning_vi"] == "con mèo"
            assert data[0]["examples"][0]["sentence_en"] == "This is a cat."
            assert data[0]["topics"][0]["topic_id"] == animal_id
            assert client.get(f"/topics/{food_id}/vocabularies").json() == []
            assert client.get("/topics/999999/vocabularies").status_code == 404
            assert client.get("/topics/0/vocabularies").status_code == 422
            assert client.get(f"/vocabularies/{ident}").json()["topics"] == data[0]["topics"]
            # A DB change must be reflected immediately in the API, including multiple memberships.
            with engine.begin() as c:
                c.execute(text("INSERT INTO vocabulary_topics(topic_id,vocabulary_id) VALUES(:t,:v)"), {"t":food_id,"v":ident})
            assert client.get(f"/topics/{food_id}/vocabularies").json()[0]["word"] == "cat"
            assert next(t for t in client.get("/topics").json() if t["slug"] == "food")["vocabulary_count"] == 1
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_demo_seed_is_repeatable(isolated_db, monkeypatch):
    import seed_demo
    engine, migrate = isolated_db
    migrate()
    monkeypatch.setattr(seed_demo, "engine", engine)
    seed_demo.main()
    with engine.begin() as c:
        c.execute(text("UPDATE vocabulary_meanings SET meaning_vi='Nội dung đã sửa' WHERE vocabulary_id=(SELECT vocabulary_id FROM vocabularies WHERE word='cat' LIMIT 1)"))
    seed_demo.main()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM vocabularies")).scalar_one() == 4
        assert c.execute(text("SELECT count(*) FROM vocabulary_topics")).scalar_one() == 4
        assert c.execute(text("SELECT meaning_vi FROM vocabulary_meanings WHERE vocabulary_id=(SELECT vocabulary_id FROM vocabularies WHERE word='cat' LIMIT 1)")).scalar_one() == "Nội dung đã sửa"
