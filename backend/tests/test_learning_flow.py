from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text
from tests.test_session_collection import api, register
from tests.test_topic_flow import isolated_db, add_cat
from app.repositories.learning_repository import streaks


def test_profile_validation_and_isolation(api):
    client, engine, cat = api
    a, ha = register(client, "profile_a")
    b, hb = register(client, "profile_b")
    data = {"full_name": "  Hiếu  ", "cefr_level": "A2", "daily_goal": 5, "reminders_enabled": True}
    result = client.patch("/users/me", headers=ha, json=data)
    assert result.status_code == 200
    assert result.json()["full_name"] == "Hiếu"
    assert result.json()["cefr_level"] == "A2" and result.json()["onboarding_completed"]
    assert result.json()["english_level"] == "BEGINNER"
    assert client.get("/users/me", headers=ha).json()["daily_goal"] == 5
    assert not client.get("/users/me", headers=hb).json()["onboarding_completed"]
    for patch in [{"full_name": "   "}, {"cefr_level": "C9"}, {"daily_goal": 0}, {"daily_goal": 201}]:
        assert client.patch("/users/me", headers=ha, json=data | patch).status_code == 422
    assert client.patch("/users/me", json=data).status_code == 401
    assert client.get("/learning/me", headers=ha).json()["daily_goal"] == 5
    with engine.connect() as c:
        assert c.execute(text("SELECT full_name FROM users WHERE user_id=:u"), {"u": a}).scalar_one() == "Hiếu"


def test_flashcard_retries_status_and_isolation(api):
    client, engine, cat = api
    a, ha = register(client, "flash_a")
    _, hb = register(client, "flash_b")
    client.put(f"/collections/me/words/{cat}", headers=ha)
    request = {"vocabulary_id": cat, "remembered": True, "event_key": str(uuid4())}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.post("/learning/me/reviews", headers=ha, json=request), range(8)))
    assert all(r.status_code == 200 for r in results)
    data = client.get("/learning/me", headers=ha).json()
    assert (data["review_count"], data["today_count"], data["mastered_count"], data["current_streak"], data["needs_review"]) == (1, 1, 1, 1, 0)
    assert data["days"][-1]["count"] == 1
    assert data["progress"][0]["correct_count"] == 1
    assert client.post("/learning/me/reviews", headers=ha, json=request | {"remembered": False}).status_code == 409
    request.update(remembered=False, event_key=str(uuid4()))
    assert client.post("/learning/me/reviews", headers=ha, json=request).status_code == 200
    data = client.get("/learning/me", headers=ha).json()
    assert (data["review_count"], data["today_count"], data["mastered_count"], data["needs_review"]) == (2, 2, 0, 1)
    assert data["progress"][0]["status"] == "LEARNING"
    assert client.get(f"/learning/me?user_id={a}", headers=hb).json()["progress"] == []
    assert client.get("/learning/me").status_code == 401
    assert client.post("/learning/me/reviews", headers=ha, json=request | {"vocabulary_id": 999999, "event_key": str(uuid4())}).status_code == 404
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM learning_events")).scalar_one() == 2
        assert c.execute(text("SELECT review_count FROM learning_progress")).scalar_one() == 2


@pytest.mark.parametrize("kind", ["IMAGE_TO_WORD", "WORD_TO_IMAGE", "LISTENING", "FILL_BLANK", "MIXED"])
def test_quiz_server_scoring_retry_resume_and_ownership(api, monkeypatch, kind):
    import seed_demo
    client, engine, cat = api
    monkeypatch.setattr(seed_demo, "engine", engine)
    seed_demo.main()
    a, ha = register(client, "quiz_a")
    _, hb = register(client, "quiz_b")
    client.put(f"/collections/me/words/{cat}", headers=ha)
    client.post("/learning/me/reviews", headers=ha, json={"vocabulary_id": cat, "remembered": True, "event_key": str(uuid4())})
    request = {"quiz_type": kind, "count": 8, "client_session_id": str(uuid4())}
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda _: client.post("/quizzes", headers=ha, json=request), range(3)))
    assert all(r.status_code == 200 for r in responses)
    quiz = responses[0].json()
    assert all(r.json() == quiz for r in responses)
    assert quiz["total_questions"] == 4
    assert quiz["questions"][0]["word"]["vocabulary_id"] == cat
    attempt = quiz["attempt_id"]
    base = f"/quizzes/{attempt}"
    assert client.get(base, headers=hb).status_code == 404
    assert client.post(base+"/complete", headers=ha).status_code == 409
    q1, q2 = quiz["questions"][:2]
    assert client.post(base+"/answers", headers=ha, json={"question_id": q2["question_id"], "answer": "1"}).status_code == 409
    assert client.post(base+"/answers", headers=ha, json={"question_id": q1["question_id"], "answer": "x", "is_correct": True}).status_code == 422
    assert client.post("/quizzes", headers=ha, json=request | {"count": 1}).status_code == 409
    for i, q in enumerate(quiz["questions"]):
        if q["question_type"] == "FILL_BLANK":
            value = "unknown-answer" if i == 0 else "  " + q["word"]["word"].upper() + "  "
        else:
            value = str(next(v["vocabulary_id"] for v in q["options"] if (v["vocabulary_id"] != q["word"]["vocabulary_id"]) == (i == 0)))
        body = {"question_id": q["question_id"], "answer": value}
        assert client.post(base+"/answers", headers=hb, json=body).status_code == 404
        with ThreadPoolExecutor(max_workers=3) as pool:
            responses = list(pool.map(lambda _: client.post(base+"/answers", headers=ha, json=body), range(3)))
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["feedback"]["is_correct"] == (i != 0) for r in responses)
        assert client.post(base+"/answers", headers=ha, json=body | {"answer": "different-answer"}).status_code == 409
        # Reopening/starting with the same client session restores exactly the same questions and score.
        resumed = client.post("/quizzes", headers=ha, json=request).json()
        assert resumed["questions"] == quiz["questions"]
        assert resumed["answered_count"] == i + 1
        assert resumed["correct_answers"] == i
    result = client.post(base+"/complete", headers=ha)
    assert result.status_code == 200
    assert result.json()["completed"] and result.json()["correct_answers"] == 3
    assert client.post(base+"/complete", headers=ha).json() == result.json()
    data = client.get("/learning/me", headers=ha).json()
    assert (data["quiz_runs"], data["quiz_correct"], data["quiz_total"], data["today_count"], data["review_count"]) == (1, 3, 4, 5, 5)
    # A quiz error does not undo explicit Flashcard self-assessment.
    assert next(p for p in data["progress"] if p["vocabulary_id"] == cat)["status"] == "MASTERED"
    assert client.get("/learning/me", headers=hb).json()["quiz_runs"] == 0
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM quiz_attempts")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM quiz_answers")).scalar_one() == 4
        assert c.execute(text("SELECT count(*) FROM learning_events")).scalar_one() == 5


def test_abort_and_empty_catalog(api):
    client, engine, cat = api
    _, ha = register(client, "abort_a")
    request = {"quiz_type": "FILL_BLANK", "count": 1, "client_session_id": str(uuid4())}
    quiz = client.post("/quizzes", headers=ha, json=request).json()
    base = f"/quizzes/{quiz['attempt_id']}"
    assert client.post(base+"/abort", headers=ha).json()["aborted"]
    assert client.post(base+"/abort", headers=ha).status_code == 200
    assert client.post(base+"/answers", headers=ha, json={"question_id": quiz["questions"][0]["question_id"], "answer": "cat"}).status_code == 409
    assert client.post(base+"/complete", headers=ha).status_code == 409
    with engine.begin() as c: c.execute(text("DELETE FROM vocabulary_meanings"))
    request["client_session_id"] = str(uuid4())
    assert client.post("/quizzes", headers=ha, json=request).status_code == 400


def test_migration_preserves_legacy_profile_progress_and_quiz(isolated_db):
    engine, migrate = isolated_db
    migrate("0003_collection")
    cat = add_cat(engine)
    with engine.begin() as c:
        u = c.execute(text("INSERT INTO users(username,email,password_hash,english_level) VALUES('old_a','old@example.com','fixture','INTERMEDIATE') RETURNING user_id")).scalar_one()
        c.execute(text("INSERT INTO learning_progress(user_id,vocabulary_id,status,review_count,correct_count) VALUES(:u,:v,'MASTERED',3,3)"), {"u": u, "v": cat})
        attempt = c.execute(text("INSERT INTO quiz_attempts(user_id,quiz_type,total_questions,correct_answers,completed_at) VALUES(:u,'FILL_BLANK',1,1,now()) RETURNING attempt_id"), {"u": u}).scalar_one()
        c.execute(text("INSERT INTO quiz_answers(attempt_id,vocabulary_id,question_type,user_answer,correct_answer,is_correct) VALUES(:a,:v,'FILL_BLANK','cat','cat',true)"), {"a": attempt, "v": cat})
    migrate(); migrate()
    with engine.connect() as c:
        assert c.execute(text("SELECT cefr_level,onboarding_completed FROM users")).one() == ("B1", True)
        assert c.execute(text("SELECT review_count FROM learning_progress")).scalar_one() == 3
        assert c.execute(text("SELECT correct_answers FROM quiz_attempts")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM quiz_answers")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM learning_events")).scalar_one() == 0


def test_streak_day_boundaries_and_gaps():
    today = date(2026, 10, 8)
    assert streaks({}, today) == (0, 0)
    assert streaks({today, today-timedelta(days=1)}, today) == (2, 2)
    assert streaks({today-timedelta(days=i) for i in [1,2,3,5]}, today) == (3, 3)
    assert streaks({today-timedelta(days=i) for i in [2,3,4]}, today) == (0, 3)


def test_study_days_use_vietnam_midnight(api):
    from sqlalchemy.orm import Session
    from app.repositories.learning_repository import study_days
    client, engine, cat = api
    u, _ = register(client, "timezone_a")
    with engine.begin() as c:
        for instant in ["2026-10-07T16:59:00+00:00", "2026-10-07T17:01:00+00:00"]:
            c.execute(text("INSERT INTO learning_events(user_id,vocabulary_id,event_key,kind,is_correct,created_at) VALUES(:u,:v,:key,'FLASHCARD',true,:instant)"),
                {"u": u, "v": cat, "key": uuid4(), "instant": instant})
    with Session(engine) as db:
        assert study_days(db, u) == {date(2026, 10, 7): 1, date(2026, 10, 8): 1}
