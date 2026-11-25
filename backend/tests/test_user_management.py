from uuid import uuid4
from sqlalchemy import text
from tests.test_topic_flow import isolated_db
from tests.test_session_collection import api, register
from tests.test_admin_flow import admin


def test_account_management_requires_admin_and_protects_admin_accounts(api):
    client, engine, _ = api
    uid, learner = register(client, "managed_user")
    aid, manager = admin(client, engine)
    for method, path, body in [
        ("GET", f"/admin/users/{uid}", None),
        ("PATCH", f"/admin/users/{uid}/lock", {"is_locked": True}),
        ("DELETE", f"/admin/users/{uid}", {"username": "managed_user"}),
    ]:
        assert client.request(method, path, json=body).status_code == 401
        assert client.request(method, path, headers=learner, json=body).status_code == 403
    assert client.patch(f"/admin/users/{aid}/lock", headers=manager, json={"is_locked": True}).status_code == 409
    assert client.request("DELETE", f"/admin/users/{aid}", headers=manager, json={"username": "admin_test"}).status_code == 409
    assert client.get("/admin/users/999999", headers=manager).status_code == 404
    assert client.patch(f"/admin/users/{uid}/lock", headers=manager, json={"is_locked": "false"}).status_code == 422
    assert client.patch("/users/me", headers=learner, json={"full_name": "User", "cefr_level": "A1", "daily_goal": 10, "is_locked": False}).status_code == 422


def test_lock_blocks_login_and_old_tokens_stay_revoked_after_unlock(api):
    client, engine, cat = api
    uid, old = register(client, "lock_user")
    _, manager = admin(client, engine)
    path = f"/admin/users/{uid}/lock"
    for _ in range(2):
        response = client.patch(path, headers=manager, json={"is_locked": True})
        assert response.status_code == 200 and response.json()["is_locked"]
    assert client.get("/users/me", headers=old).status_code == 401
    assert client.put(f"/collections/me/words/{cat}", headers=old).status_code == 401
    assert client.post("/auth/login", json={"username": "lock_user", "password": "test-password-9374"}).status_code == 403
    assert client.patch(path, headers=manager, json={"is_locked": False}).status_code == 200
    assert client.get("/users/me", headers=old).status_code == 401
    login = client.post("/auth/login", json={"username": "lock_user", "password": "test-password-9374"})
    fresh = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/users/me", headers=fresh).status_code == 200
    # Repeating an unlock is idempotent and does not kill a newly issued session.
    client.patch(path, headers=manager, json={"is_locked": False})
    assert client.get("/users/me", headers=fresh).status_code == 200


def test_progress_detail_and_delete_cascade_preserve_other_accounts(api):
    client, engine, cat = api
    uid, learner = register(client, "delete_user")
    other_id, other = register(client, "surviving_user")
    _, manager = admin(client, engine)
    for headers in (learner, other):
        assert client.put(f"/collections/me/words/{cat}", headers=headers).status_code == 200
        assert client.post("/learning/me/reviews", headers=headers, json={"vocabulary_id": cat, "remembered": True, "event_key": str(uuid4())}).status_code == 200
    quiz = client.post("/quizzes", headers=learner, json={"quiz_type": "FILL_BLANK", "count": 1, "client_session_id": str(uuid4())}).json()
    attempt = quiz["attempt_id"]
    assert client.post(f"/quizzes/{attempt}/answers", headers=learner, json={"question_id": quiz["questions"][0]["question_id"], "answer": "cat"}).status_code == 200
    assert client.post(f"/quizzes/{attempt}/complete", headers=learner).status_code == 200
    game = client.post("/games/word-shooter", headers=learner, json={"source": "SAVED", "client_session_id": str(uuid4())})
    assert game.status_code == 200
    run = game.json()
    assert client.post(f"/games/word-shooter/{run['run_id']}/rounds/{run['round']['round_id']}/finish", headers=learner,
        json={"results": [{"vocabulary_id": cat, "outcome": "SOLVED", "answer": "cat", "wrong_letters": 0}]}).status_code == 200
    with engine.begin() as c:
        c.execute(text("INSERT INTO images(user_id,image_url,source_type) VALUES(:u,'https://example.com/test.jpg','CAMERA')"), {"u": uid})
        c.execute(text("INSERT INTO notifications(user_id,occurrence_date,title,body) VALUES(:u,CURRENT_DATE,'Test','Review')"), {"u": uid})
    detail = client.get(f"/admin/users/{uid}", headers=manager)
    assert detail.status_code == 200
    data = detail.json()
    assert data["learning"]["review_count"] == 3
    assert data["learning"]["quiz_runs"] == 1
    assert data["learning"]["quiz_correct"] == 1
    assert data["vocabulary_names"][str(cat)] == "cat"
    assert data["game_runs"] == 1 and data["game_score"] == 100
    assert len(data["learning"]["days"]) == 7
    assert "password_hash" not in data and "auth_version" not in data
    path = f"/admin/users/{uid}"
    assert client.request("DELETE", path, headers=manager, json={"username": "wrong"}).status_code == 409
    assert client.get("/users/me", headers=learner).status_code == 200
    assert client.request("DELETE", path, headers=manager, json={"username": "delete_user"}).status_code == 200
    assert client.get("/users/me", headers=learner).status_code == 401
    assert client.get(path, headers=manager).status_code == 404
    for table in ("users", "collections", "learning_progress", "learning_events", "quiz_attempts", "game_runs", "images", "notifications"):
        column = "user_id"
        with engine.connect() as c:
            assert c.execute(text(f"SELECT count(*) FROM {table} WHERE {column}=:u"), {"u": uid}).scalar_one() == 0
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM quiz_answers WHERE attempt_id=:a"), {"a": attempt}).scalar_one() == 0
        assert c.execute(text("SELECT count(*) FROM game_rounds WHERE run_id=:r"), {"r": run["run_id"]}).scalar_one() == 0
    assert client.get("/learning/me", headers=other).json()["review_count"] == 1
    assert client.get(f"/vocabularies/{cat}").status_code == 200


def test_management_migration_preserves_existing_users(isolated_db):
    engine, migrate = isolated_db
    migrate("0009_word_defense")
    with engine.begin() as c:
        c.execute(text("INSERT INTO users(username,email,password_hash) VALUES('existing','existing@example.com','preserved')"))
    migrate(); migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT password_hash,is_locked,auth_version FROM users WHERE username='existing'")).one() == ("preserved", False, 0)
