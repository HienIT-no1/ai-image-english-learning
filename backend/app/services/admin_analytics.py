"""Aggregate learner activity using the same UTC+7 calendar as the app."""
from datetime import datetime, time, timedelta

from sqlalchemy import BigInteger, Date, cast, column, distinct, func, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.models.game import GameRound, GameRun
from app.models.learning import LearningEvent
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.repositories.learning_repository import LOCAL_TZ
from app.schemas.admin_analytics import GameType


def period(days: int):
    today = datetime.now(LOCAL_TZ).date()
    dates = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    start = datetime.combine(dates[0], time.min, LOCAL_TZ)
    stop = datetime.combine(today + timedelta(days=1), time.min, LOCAL_TZ)
    return dates, start, stop


def local_date(timestamp):
    return cast(func.timezone("Asia/Ho_Chi_Minh", timestamp), Date)


def percentage(numerator: int, denominator: int) -> float | None:
    return round(100 * numerator / denominator, 2) if denominator else None


def learning_metrics(active: int, events: int, correct: int, eligible: int, returned: int):
    return {
        "active_learners": active,
        "study_events": events,
        "correct_events": correct,
        "accuracy_rate": percentage(correct, events),
        "eligible_learner_days": eligible,
        "returned_learner_days": returned,
        "next_day_return_rate": percentage(returned, eligible),
    }


def learning(db: Session, days: int):
    dates, start, stop = period(days)
    events = (
        select(
            local_date(LearningEvent.created_at).label("day"),
            LearningEvent.user_id,
            LearningEvent.vocabulary_id,
            LearningEvent.is_correct,
        )
        .join(User, User.user_id == LearningEvent.user_id)
        .where(User.role == "USER", LearningEvent.created_at >= start, LearningEvent.created_at < stop)
        .subquery()
    )
    per_day = {
        day: (active, attempts, correct)
        for day, active, attempts, correct in db.execute(
            select(events.c.day, func.count(distinct(events.c.user_id)), func.count(),
                   func.count().filter(events.c.is_correct.is_(True))).group_by(events.c.day)
        )
    }
    total_active = db.scalar(select(func.count(distinct(events.c.user_id))))

    # Each learner contributes once per active day, including when they study several times.
    activity = select(events.c.user_id, events.c.day).distinct().subquery()
    streak = select(
        activity.c.day,
        func.lead(activity.c.day).over(partition_by=activity.c.user_id, order_by=activity.c.day).label("next_day"),
    ).subquery()
    # Today's target is partial, so yesterday and today both lack a fully observed next day.
    mature_before = dates[-1] - timedelta(days=1)
    returns = {
        day: (eligible, returned)
        for day, eligible, returned in db.execute(
            select(streak.c.day, func.count(), func.count().filter(streak.c.next_day == streak.c.day + 1))
            .where(streak.c.day < mature_before)
            .group_by(streak.c.day)
        )
    }

    attempts = func.count()
    incorrect = func.count().filter(events.c.is_correct.is_(False))
    hardest = db.execute(
        select(Vocabulary.vocabulary_id, Vocabulary.word, attempts, incorrect)
        .join(events, events.c.vocabulary_id == Vocabulary.vocabulary_id)
        .group_by(Vocabulary.vocabulary_id, Vocabulary.word)
        .having(incorrect > 0)
        .order_by((incorrect / attempts).desc(), attempts.desc(), Vocabulary.vocabulary_id)
        .limit(10)
    )

    return {
        "start_date": dates[0],
        "end_date": dates[-1],
        **learning_metrics(
            total_active,
            sum(row[1] for row in per_day.values()),
            sum(row[2] for row in per_day.values()),
            sum(row[0] for row in returns.values()),
            sum(row[1] for row in returns.values()),
        ),
        "daily": [
            {"date": day, **learning_metrics(*per_day.get(day, (0, 0, 0)), *returns.get(day, (0, 0)))}
            for day in dates
        ],
        "hardest_words": [
            {"vocabulary_id": ident, "word": word, "attempts": attempts, "incorrect": incorrect,
             "incorrect_rate": percentage(incorrect, attempts)}
            for ident, word, attempts, incorrect in hardest
        ],
    }


def game_metrics(runs: int, scored: int, score, passed: int):
    return {
        "game_runs": runs,
        "scored_runs": scored,
        "average_score": round(float(score), 2) if score is not None else None,
        "passed_rounds": passed,
    }


def games(db: Session, days: int, game_type: GameType | None):
    dates, start, stop = period(days)
    learner_runs = (
        select(GameRun.run_id, GameRun.created_at)
        .join(User, User.user_id == GameRun.user_id)
        .where(User.role == "USER")
    )
    if game_type is not None:
        learner_runs = learner_runs.where(GameRun.game_type == game_type)
    runs = learner_runs.subquery()
    run_day = local_date(runs.c.created_at)
    starts_by_day = dict(db.execute(
        select(run_day, func.count()).where(runs.c.created_at >= start, runs.c.created_at < stop)
        .group_by(run_day)
    ).all())

    # Use round completion dates so a run started before the interval can still contribute a result.
    rounds = (
        select(GameRound.run_id, GameRound.status, GameRound.score, GameRound.results,
               local_date(GameRound.completed_at).label("day"))
        .join(runs, runs.c.run_id == GameRound.run_id)
        .where(GameRound.status.in_(("PASSED", "FAILED")),
               GameRound.completed_at >= start, GameRound.completed_at < stop)
        .subquery()
    )
    per_run_day = (
        select(rounds.c.day, rounds.c.run_id, func.sum(rounds.c.score).label("score"),
               func.count().filter(rounds.c.status == "PASSED").label("passed"))
        .group_by(rounds.c.day, rounds.c.run_id)
        .cte("run_scores_by_day")
    )
    scores_by_day = {
        day: (count, average, passed)
        for day, count, average, passed in db.execute(
            select(per_run_day.c.day, func.count(), func.avg(per_run_day.c.score), func.sum(per_run_day.c.passed))
            .group_by(per_run_day.c.day)
        )
    }
    per_run = (
        select(func.sum(per_run_day.c.score).label("score"), func.sum(per_run_day.c.passed).label("passed"))
        .group_by(per_run_day.c.run_id)
        .subquery()
    )
    scored, average, passed = db.execute(
        select(func.count(), func.avg(per_run.c.score), func.coalesce(func.sum(per_run.c.passed), 0))
    ).one()

    # Report the persisted MISSED outcomes rather than guessing from words in the deck.
    results = func.jsonb_array_elements(rounds.c.results).table_valued(column("value", JSONB)).lateral()
    word_id = cast(results.c.value["vocabulary_id"].astext, BigInteger)
    misses = func.count()
    top_misses = db.execute(
        select(word_id, Vocabulary.word, misses)
        .select_from(rounds)
        .join(results, true())
        .outerjoin(Vocabulary, Vocabulary.vocabulary_id == word_id)
        .where(results.c.value["outcome"].astext == "MISSED")
        .group_by(word_id, Vocabulary.word)
        .order_by(misses.desc(), word_id)
        .limit(10)
    )

    return {
        "start_date": dates[0],
        "end_date": dates[-1],
        "game_type": game_type,
        **game_metrics(sum(starts_by_day.values()), scored, average, passed),
        "daily": [
            {"date": day, **game_metrics(starts_by_day.get(day, 0), *scores_by_day.get(day, (0, None, 0)))}
            for day in dates
        ],
        "most_missed_words": [
            {"vocabulary_id": ident, "word": word or f"#{ident}", "misses": count}
            for ident, word, count in top_misses
        ],
    }
