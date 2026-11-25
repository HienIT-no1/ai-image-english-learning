from datetime import datetime
from uuid import uuid4

from sqlalchemy import insert, text

from app.models.game import GameRound, GameRun
from app.models.learning import LearningEvent
from app.services import admin_analytics
from tests.test_admin_flow import admin
from tests.test_session_collection import api, register
from tests.test_topic_flow import isolated_db


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromisoformat("2026-04-12T12:00:00+07:00").astimezone(tz)


def instant(value: str):
    return datetime.fromisoformat(value)


def test_learning_activity_uses_local_days_and_only_fully_observed_returns(api, monkeypatch):
    client, engine, cat = api
    aid, manager = admin(client, engine)
    a, learner = register(client, "analytics_a")
    b, _ = register(client, "analytics_b")
    c, _ = register(client, "analytics_c")
    monkeypatch.setattr(admin_analytics, "datetime", FrozenDatetime)

    with engine.begin() as conn:
        rare = conn.scalar(text("INSERT INTO vocabularies(word) VALUES('rare') RETURNING vocabulary_id"))
        for user, word, stamp, correct, kind in [
            (a, cat, "2026-04-08T16:59:59+00:00", True, "QUIZ"),  # Before the period.
            (a, cat, "2026-04-08T17:00:00+00:00", True, "QUIZ"),
            (a, cat, "2026-04-09T16:59:59+00:00", False, "FLASHCARD"),
            (b, rare, "2026-04-09T08:00:00+07:00", False, "GAME"),
            (a, cat, "2026-04-09T17:00:00+00:00", True, "GAME"),
            (c, cat, "2026-04-11T08:00:00+07:00", False, "QUIZ"),
            (b, cat, "2026-04-12T08:00:00+07:00", True, "QUIZ"),
            (c, cat, "2026-04-12T09:00:00+07:00", True, "FLASHCARD"),
            (aid, cat, "2026-04-12T08:00:00+07:00", True, "QUIZ"),  # Admin usage does not count.
            (b, cat, "2026-04-13T00:00:00+07:00", True, "QUIZ"),  # Exclusive end.
        ]:
            conn.execute(insert(LearningEvent).values(user_id=user, vocabulary_id=word, event_key=uuid4(),
                kind=kind, is_correct=correct, created_at=instant(stamp)))

    path = "/admin/analytics/learning?days=4"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=learner).status_code == 403
    assert client.get("/admin/analytics/learning?days=0", headers=manager).status_code == 422
    response = client.get(path, headers=manager)
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["start_date"], data["end_date"]) == ("2026-04-09", "2026-04-12")
    assert (data["active_learners"], data["study_events"], data["correct_events"], data["accuracy_rate"]) == (3, 7, 4, 57.14)
    assert (data["eligible_learner_days"], data["returned_learner_days"], data["next_day_return_rate"]) == (3, 1, 33.33)
    assert [(d["active_learners"], d["study_events"], d["next_day_return_rate"]) for d in data["daily"]] == [
        (2, 3, 50), (1, 1, 0), (1, 1, None), (2, 2, None),
    ]
    assert data["hardest_words"] == [
        {"vocabulary_id": rare, "word": "rare", "attempts": 1, "incorrect": 1, "incorrect_rate": 100},
        {"vocabulary_id": cat, "word": "cat", "attempts": 6, "incorrect": 2, "incorrect_rate": 33.33},
    ]
    empty_day = client.get("/admin/analytics/learning?days=5", headers=manager).json()["daily"][0]
    assert empty_day["study_events"] == 1  # Expanding the period includes the just-before-midnight event.
    zero_day = client.get("/admin/analytics/learning?days=6", headers=manager).json()["daily"][0]
    assert zero_day["study_events"] == 0 and zero_day["accuracy_rate"] is None


def test_game_stats_use_starts_and_submitted_rounds_with_game_type_filter(api, monkeypatch):
    client, engine, cat = api
    aid, manager = admin(client, engine)
    uid, learner = register(client, "analytics_games")
    monkeypatch.setattr(admin_analytics, "datetime", FrozenDatetime)

    with engine.begin() as conn:
        rare = conn.scalar(text("INSERT INTO vocabularies(word) VALUES('rare') RETURNING vocabulary_id"))

        def run(user, game_type, created_at):
            return conn.scalar(insert(GameRun).values(user_id=user, client_session_id=uuid4(),
                game_type=game_type, source="SAVED", pool=[], created_at=instant(created_at)).returning(GameRun.run_id))

        def finish(run_id, sequence, stamp, score, status, missed):
            results = [{"vocabulary_id": ident, "outcome": "MISSED"} for ident in missed]
            results.append({"vocabulary_id": cat, "outcome": "SOLVED"})
            conn.execute(insert(GameRound).values(run_id=run_id, sequence=sequence, stage=sequence,
                words=[], results=results, score=score, status=status, completed_at=instant(stamp)))

        shooter = run(uid, "WORD_SHOOTER", "2026-04-09T16:59:59+00:00")
        finish(shooter, 1, "2026-04-09T17:00:00+00:00", 100, "PASSED", [cat])
        finish(shooter, 2, "2026-04-11T08:00:00+07:00", 200, "PASSED", [cat, rare])
        finish(shooter, 3, "2026-04-13T00:00:00+07:00", 900, "PASSED", [cat])
        defense = run(uid, "WORD_DEFENSE", "2026-04-10T08:00:00+07:00")
        finish(defense, 1, "2026-04-10T08:15:00+07:00", 0, "FAILED", [cat])
        unsubmitted = run(uid, "WORD_SHOOTER", "2026-04-11T08:00:00+07:00")
        conn.execute(insert(GameRound).values(run_id=unsubmitted, sequence=1, stage=1, words=[]))
        admin_run = run(aid, "WORD_SHOOTER", "2026-04-11T08:00:00+07:00")
        finish(admin_run, 1, "2026-04-11T09:00:00+07:00", 100, "PASSED", [cat])

    path = "/admin/analytics/games?days=3"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=learner).status_code == 403
    assert client.get(path + "&game_type=OTHER", headers=manager).status_code == 422
    response = client.get(path, headers=manager)
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["game_runs"], data["scored_runs"], data["average_score"], data["passed_rounds"]) == (2, 2, 150, 2)
    assert [(d["game_runs"], d["scored_runs"], d["average_score"], d["passed_rounds"]) for d in data["daily"]] == [
        (1, 2, 50, 1), (1, 1, 200, 1), (0, 0, None, 0),
    ]
    assert data["most_missed_words"] == [
        {"vocabulary_id": cat, "word": "cat", "misses": 3},
        {"vocabulary_id": rare, "word": "rare", "misses": 1},
    ]
    filtered = client.get(path + "&game_type=WORD_DEFENSE", headers=manager).json()
    assert (filtered["game_runs"], filtered["scored_runs"], filtered["average_score"], filtered["passed_rounds"]) == (1, 1, 0, 0)
    assert filtered["most_missed_words"] == [{"vocabulary_id": cat, "word": "cat", "misses": 1}]
