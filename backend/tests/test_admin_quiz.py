from uuid import uuid4

from sqlalchemy import text

from tests.test_admin_flow import admin
from tests.test_session_collection import api, register
from tests.test_topic_flow import isolated_db


def _start(client, headers, quiz_type, count):
    response = client.post("/quizzes", headers=headers, json={
        "quiz_type": quiz_type, "count": count, "client_session_id": str(uuid4()),
    })
    assert response.status_code == 200
    return response.json()


def _answer(client, headers, quiz, question_id, answer):
    response = client.post(f"/quizzes/{quiz['attempt_id']}/answers", headers=headers, json={
        "question_id": question_id, "answer": answer,
    })
    assert response.status_code == 200


def test_admin_quiz_overview_pagination_filters_and_detail(api):
    client, engine, cat_id = api
    user_id, learner = register(client, "quiz_learner")
    _, other = register(client, "second_learner")
    _, manager = admin(client, engine)
    with engine.begin() as conn:
        dog_id = conn.execute(text("INSERT INTO vocabularies(word) VALUES ('dog') RETURNING vocabulary_id")).scalar_one()
        conn.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id, meaning_vi) VALUES (:id, 'con chó')"), {"id": dog_id})

    completed = _start(client, learner, "WORD_TO_IMAGE", 1)
    question = completed["questions"][0]
    correct = question["word"]["vocabulary_id"]
    wrong = dog_id if correct == cat_id else cat_id
    _answer(client, learner, completed, question["question_id"], str(wrong))
    assert client.post(f"/quizzes/{completed['attempt_id']}/complete", headers=learner).status_code == 200
    in_progress = _start(client, other, "MIXED", 2)
    aborted = _start(client, learner, "FILL_BLANK", 2)
    assert client.post(f"/quizzes/{aborted['attempt_id']}/abort", headers=learner).status_code == 200

    historical_word = question["word"]["word"]
    with engine.begin() as conn:
        conn.execute(text("UPDATE vocabularies SET word='renamed' WHERE vocabulary_id=:v"), {"v": correct})
        legacy_id = conn.execute(text("""
            INSERT INTO quiz_attempts(user_id, quiz_type, total_questions, correct_answers, completed_at)
            VALUES (:u, 'FILL_BLANK', 1, 1, now()) RETURNING attempt_id
        """), {"u": user_id}).scalar_one()
        conn.execute(text("""
            INSERT INTO quiz_answers(attempt_id, vocabulary_id, question_type, user_answer, correct_answer, is_correct)
            VALUES (:a, :v, 'FILL_BLANK', :w, :w, true)
        """), {"a": legacy_id, "v": correct, "w": historical_word})

    base = "/admin/quizzes"
    for path in (base, f"{base}/summary", f"{base}/{completed['attempt_id']}"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=learner).status_code == 403
    assert client.get(f"{base}/9999999", headers=manager).status_code == 404

    page = client.get(base, headers=manager, params={"limit": 1, "offset": 1}).json()
    assert page["total"] == 4 and page["offset"] == 1 and page["limit"] == 1
    assert page["items"][0]["attempt_id"] == aborted["attempt_id"]
    selected = client.get(base, headers=manager, params={"q": "QUIZ_LEARNER", "status": "COMPLETED", "quiz_type": "WORD_TO_IMAGE"}).json()
    assert selected["total"] == 1
    row = selected["items"][0]
    assert (row["attempt_id"], row["answered_count"], row["correct_answers"], row["status"]) == (completed["attempt_id"], 1, 0, "COMPLETED")
    assert client.get(base, headers=manager, params={"q": "%"}).json()["total"] == 0
    assert client.get(base, headers=manager, params={"q": str(in_progress["attempt_id"]), "status": "IN_PROGRESS"}).json()["total"] == 1

    stats = client.get(f"{base}/summary", headers=manager).json()
    assert (stats["total"], stats["completed"], stats["in_progress"], stats["aborted"]) == (4, 2, 1, 1)
    assert [item for item in stats["by_quiz_type"] if item["quiz_type"] == "FILL_BLANK"] == [
        {"quiz_type": "FILL_BLANK", "total": 2, "completed": 1, "in_progress": 0, "aborted": 1},
    ]
    assert {"question_type": "WORD_TO_IMAGE", "answered": 1, "correct": 0} in stats["by_question_type"]
    assert stats["common_misses"] == [{"vocabulary_id": correct, "word": "renamed", "answered": 2, "missed": 1}]

    detail = client.get(f"{base}/{completed['attempt_id']}", headers=manager).json()
    shown = detail["questions"][0]
    assert shown["word"] == historical_word
    assert shown["is_correct"] is False
    assert shown["user_answer"] == next(option["meanings"][0]["meaning_vi"] for option in question["options"] if option["vocabulary_id"] == wrong)
    assert shown["correct_answer"] == question["word"]["meanings"][0]["meaning_vi"]
    assert {option["word"] for option in shown["options"]} == {"cat", "dog"}
    unanswered = client.get(f"{base}/{in_progress['attempt_id']}", headers=manager).json()
    assert len(unanswered["questions"]) == 2 and unanswered["answered_count"] == 0
    assert all(item["is_correct"] is None for item in unanswered["questions"])
    legacy = client.get(f"{base}/{legacy_id}", headers=manager).json()
    assert legacy["questions"][0]["word"] == historical_word
    assert legacy["questions"][0]["is_correct"] is True
