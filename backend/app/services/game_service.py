"""Server owns decks, transitions, scoring and exactly-once learning writes.

The client runs falling animation locally and submits resolution order after a round.
Wrong keystrokes are diagnostics only; only a MISSED word breaks a combo.
"""
from datetime import datetime, timezone
from uuid import uuid5, NAMESPACE_URL
import random
import re
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models.game import GameRun, GameRound
from app.models.user import User
from app.models.topic import Topic
from app.models.collection import Collection, CollectionWord
from app.models.learning import LearningProgress
from app.models.vocabulary import Vocabulary
from app.repositories.vocabulary_repository import get_all_vocabularies
from app.repositories.learning_repository import record_event, summary
from app.schemas.vocabulary import VocabularyResponse
from app.schemas.game import GameStart, GameFinish, GameResponse, GameRoundResponse

ROUND_SIZE = 20
RANDOM_STAGES = 5

def owned(db: Session, user_id: int, run_id: int, lock=False):
    query = select(GameRun).where(GameRun.run_id==run_id,GameRun.user_id==user_id)
    if lock: query=query.with_for_update()
    run=db.scalar(query)
    if run is None: raise HTTPException(404,"Game not found")
    return run

def rounds(db, run):
    return list(db.scalars(select(GameRound).where(GameRound.run_id==run.run_id).order_by(GameRound.sequence)).all())

def solved_ids(history):
    return {r['vocabulary_id'] for stage in history if stage.status=='PASSED'
            for r in stage.results if r['outcome']=='SOLVED'}

def response(db, run, current=None):
    history=rounds(db,run)
    stage=current or history[-1]
    solved=solved_ids(history)
    return GameResponse(run_id=run.run_id,source=run.source,topic_id=run.topic_id,
        pool_count=len(run.pool),remaining_count=sum(w['vocabulary_id'] not in solved for w in run.pool),
        completed=run.completed_at is not None,total_score=sum(r.score for r in history),
        round=GameRoundResponse(round_id=stage.round_id,stage=stage.stage,words=stage.words,
            results=stage.results,status=stage.status,correct_count=stage.correct_count,
            missed_count=stage.missed_count,max_combo=stage.max_combo,score=stage.score))

def pool_for(db, user, data):
    if data.source=='TOPIC' and db.get(Topic,data.topic_id) is None:
        raise HTTPException(404,"Topic not found")
    saved=set(db.scalars(select(CollectionWord.vocabulary_id).join(Collection,
        Collection.collection_id==CollectionWord.collection_id).where(Collection.user_id==user.user_id)).all())
    # A wrong answer remains difficult until its latest review succeeds.
    from app.models.learning import LearningEvent
    ranked=select(LearningEvent.event_id,func.row_number().over(
        partition_by=LearningEvent.vocabulary_id,
        order_by=(LearningEvent.created_at.desc(),LearningEvent.event_id.desc())).label('position')
        ).where(LearningEvent.user_id==user.user_id).subquery()
    latest=list(db.scalars(select(LearningEvent).join(ranked,ranked.c.event_id==LearningEvent.event_id)
        .where(ranked.c.position==1)).all())
    difficult={e.vocabulary_id for e in latest if not e.is_correct}
    # Legacy progress may have no events yet.
    difficult.update(db.scalars(select(LearningProgress.vocabulary_id).where(
        LearningProgress.user_id==user.user_id,LearningProgress.incorrect_count>LearningProgress.correct_count,
        LearningProgress.vocabulary_id.not_in([e.vocabulary_id for e in latest]))).all())
    scope={'SAVED':saved,'DIFFICULT':difficult,'REVIEW':saved|difficult}.get(data.source)
    level_rank={'A1':0,'A2':1,'B1':2,'B2':3,'BEGINNER':0,'INTERMEDIATE':2,'ADVANCED':3}
    max_rank=level_rank.get(user.cefr_level or 'A1',0)
    pool=[];seen=set()
    for word in get_all_vocabularies(db,data.topic_id):
        normalized=word.word.strip().lower()
        if not word.meanings or not word.meanings[0].meaning_vi.strip(): continue
        # Separators are prefilled by the game; unsupported alphabets are never untypeable targets.
        if not re.fullmatch(r"[a-z]+(?:[ '\-][a-z]+)*",normalized) or sum(c.isalpha() for c in normalized)>24: continue
        if normalized in seen or (scope is not None and word.vocabulary_id not in scope): continue
        if data.source=='RANDOM' and level_rank.get(word.level or 'A1',0)>max_rank: continue
        seen.add(normalized)
        item=VocabularyResponse.model_validate(word).model_dump(mode='json')
        item['word']=normalized
        pool.append(item)
    random.SystemRandom().shuffle(pool)
    if not pool: raise HTTPException(400,"No playable words in this source")
    return pool

def start(db: Session,user: User,data: GameStart):
    run=db.scalar(select(GameRun).where(GameRun.user_id==user.user_id,GameRun.client_session_id==data.client_session_id))
    if run is None:
        db.execute(insert(GameRun).values(user_id=user.user_id,client_session_id=data.client_session_id,
            source=data.source,topic_id=data.topic_id,pool=pool_for(db,user,data))
            .on_conflict_do_nothing(constraint='uq_game_user_session'))
        db.flush()
        run=db.scalar(select(GameRun).where(GameRun.user_id==user.user_id,GameRun.client_session_id==data.client_session_id).with_for_update())
        if not rounds(db,run):
            db.add(GameRound(run_id=run.run_id,sequence=1,stage=1,words=run.pool[:ROUND_SIZE]))
            db.flush()
    if (run.source,run.topic_id)!=(data.source,data.topic_id):
        raise HTTPException(409,"Game session key already used for different data")
    result=response(db,run);db.commit();return result

def finish(db: Session,user: User,run_id: int,round_id: int,data: GameFinish):
    run=owned(db,user.user_id,run_id,True)
    stage=db.scalar(select(GameRound).where(GameRound.run_id==run_id,GameRound.round_id==round_id))
    if stage is None: raise HTTPException(404,"Round not found")
    payload=[r.model_dump(mode='json') for r in data.results]
    if stage.status!='PLAYING':
        if stage.results!=payload: raise HTTPException(409,"Round already submitted differently")
        return response(db,run,stage)
    if rounds(db,run)[-1].round_id!=round_id: raise HTTPException(409,"Round is not current")
    by_id={w['vocabulary_id']:w for w in stage.words}
    seen=set();missed=correct=combo=best=score=0
    for index,item in enumerate(payload):
        ident=item['vocabulary_id']
        if ident not in by_id or ident in seen: raise HTTPException(422,"Unknown or duplicate game word")
        seen.add(ident)
        if item['outcome']=='SOLVED':
            if (item['answer'] or '').strip().casefold()!=by_id[ident]['word'].casefold():
                raise HTTPException(422,"Solved word answer does not match")
            correct+=1;combo+=1;best=max(best,combo)
            score+=100+(combo//5)*25
        else:
            if item['answer'] is not None: raise HTTPException(422,"Missed word must not have an answer")
            missed+=1;combo=0
            if missed==4 and index!=len(payload)-1: raise HTTPException(422,"Game must stop at fourth miss")
    if missed<4 and len(seen)!=len(by_id): raise HTTPException(409,"Round incomplete")
    # Validation finishes before any learning data is written.
    for item in payload:
        ident=item['vocabulary_id']
        if db.get(Vocabulary,ident) is None: raise HTTPException(409,"Game vocabulary changed; start a new game")
        record_event(db,user.user_id,ident,uuid5(NAMESPACE_URL,f'word-shooter:{round_id}:{ident}'),
            'GAME',item['outcome']=='SOLVED')
    stage.results=payload;stage.correct_count=correct;stage.missed_count=missed
    stage.max_combo=best;stage.score=score;stage.status='FAILED' if missed==4 else 'PASSED'
    stage.completed_at=datetime.now(timezone.utc)
    db.flush()
    solved=solved_ids(rounds(db,run))
    if stage.status=='PASSED' and (len(solved)==len(run.pool) or (run.source=='RANDOM' and stage.stage>=RANDOM_STAGES)):
        run.completed_at=datetime.now(timezone.utc)
    progress=summary(db,user)
    user.current_streak=progress.current_streak;user.longest_streak=progress.longest_streak
    result=response(db,run,stage);db.commit();return result

def advance(db: Session,user: User,run_id: int,round_id: int):
    run=owned(db,user.user_id,run_id,True)
    history=rounds(db,run)
    previous=next((r for r in history if r.round_id==round_id),None)
    if previous is None: raise HTTPException(404,"Round not found")
    if previous.status=='PLAYING': raise HTTPException(409,"Round incomplete")
    # Retry of a transition returns its existing successor, never skips a round.
    successor=next((r for r in history if r.sequence==previous.sequence+1),None)
    if successor is not None: return response(db,run,successor)
    if run.completed_at is not None: raise HTTPException(409,"Game is complete")
    if previous.status=='FAILED':
        words=previous.words;number=previous.stage
    else:
        solved=solved_ids(history)
        wrong={r['vocabulary_id'] for r in previous.results if r['outcome']=='MISSED'}
        remaining=[w for w in run.pool if w['vocabulary_id'] not in solved]
        carried=[w for w in remaining if w['vocabulary_id'] in wrong]
        fresh=[w for w in remaining if w['vocabulary_id'] not in wrong]
        words=(carried+fresh)[:ROUND_SIZE]
        random.SystemRandom().shuffle(words)
        number=previous.stage+1
    db.add(GameRound(run_id=run_id,sequence=previous.sequence+1,stage=number,words=words))
    db.flush();result=response(db,run);db.commit();return result
