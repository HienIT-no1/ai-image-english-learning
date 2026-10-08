from datetime import datetime,timezone
from uuid import UUID,uuid4
import random
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.models.quiz import QuizAttempt,QuizAnswer
from app.models.user import User
from app.models.vocabulary import Vocabulary
from app.models.collection import Collection,CollectionWord
from app.repositories.vocabulary_repository import get_all_vocabularies
from app.repositories.learning_repository import record_event,summary
from app.schemas.quiz import QuizStart,QuizSubmit,QuizResponse,QuizFeedback,AnswerResponse
from app.schemas.vocabulary import VocabularyResponse

KINDS=['IMAGE_TO_WORD','WORD_TO_IMAGE','LISTENING','FILL_BLANK']

def owned(db:Session,user_id:int,attempt_id:int,lock=False)->QuizAttempt:
    query=select(QuizAttempt).where(QuizAttempt.attempt_id==attempt_id,QuizAttempt.user_id==user_id)
    if lock: query=query.with_for_update()
    attempt=db.scalar(query)
    if attempt is None: raise HTTPException(404,'Quiz not found')
    return attempt

def feedback(answer:QuizAnswer,question:dict)->QuizFeedback:
    return QuizFeedback(question_id=question['question_id'],user_answer=answer.user_answer,
        is_correct=answer.is_correct,correct_answer=answer.correct_answer,
        correct_choice_key=str(question['word']['vocabulary_id']),word=question['word'])

def response(db:Session,attempt:QuizAttempt)->QuizResponse:
    questions=attempt.question_payload.get('questions',[])
    by_id={q['question_id']:q for q in questions}
    answers=list(db.scalars(select(QuizAnswer).where(QuizAnswer.attempt_id==attempt.attempt_id)
        .order_by(QuizAnswer.question_index,QuizAnswer.answer_id)).all())
    return QuizResponse(attempt_id=attempt.attempt_id,quiz_type=attempt.quiz_type,
        total_questions=attempt.total_questions,correct_answers=attempt.correct_answers,
        answered_count=len(answers),completed=attempt.completed_at is not None,aborted=attempt.aborted_at is not None,
        questions=questions,answers=[feedback(a,by_id[a.question_id]) for a in answers if a.question_id in by_id])

def start(db:Session,user:User,data:QuizStart)->QuizResponse:
    existing=db.scalar(select(QuizAttempt).where(QuizAttempt.user_id==user.user_id,QuizAttempt.client_session_id==data.client_session_id))
    if existing is not None:
        if existing.quiz_type!=data.quiz_type or existing.question_payload.get('requested_count')!=data.count:
            raise HTTPException(409,'Quiz session key already used for different data')
        return response(db,existing)
    catalog=[v for v in get_all_vocabularies(db) if v.meanings and v.word.strip()]
    if not catalog: raise HTTPException(400,'No vocabulary with meanings available')
    rng=random.SystemRandom()
    saved=set(db.scalars(select(CollectionWord.vocabulary_id).join(Collection,
        Collection.collection_id==CollectionWord.collection_id).where(Collection.user_id==user.user_id,Collection.is_default.is_(True))).all())
    priority=[v for v in catalog if v.vocabulary_id in saved];rest=[v for v in catalog if v.vocabulary_id not in saved]
    rng.shuffle(priority);rng.shuffle(rest)
    questions=[]
    for index,word in enumerate((priority+rest)[:data.count]):
        kind=KINDS[index%4] if data.quiz_type=='MIXED' else data.quiz_type
        alternatives=[v for v in catalog if v.vocabulary_id!=word.vocabulary_id and v.word.casefold()!=word.word.casefold()]
        rng.shuffle(alternatives)
        seen={word.meanings[0].meaning_vi.strip().casefold() if kind=='WORD_TO_IMAGE' else word.word.strip().casefold()}
        options=[word]
        for candidate in alternatives:
            label=candidate.meanings[0].meaning_vi if kind=='WORD_TO_IMAGE' else candidate.word
            if label.strip().casefold() not in seen:
                options.append(candidate);seen.add(label.strip().casefold())
            if len(options)==4: break
        rng.shuffle(options)
        questions.append({'question_id':str(uuid4()),'question_type':kind,
            'word':VocabularyResponse.model_validate(word).model_dump(mode='json'),
            'options':[VocabularyResponse.model_validate(v).model_dump(mode='json') for v in options]})
    db.execute(insert(QuizAttempt).values(user_id=user.user_id,quiz_type=data.quiz_type,total_questions=len(questions),
        correct_answers=0,client_session_id=data.client_session_id,question_payload={'requested_count':data.count,'questions':questions})
        .on_conflict_do_nothing(constraint='uq_quiz_user_session'))
    db.flush()
    attempt=db.scalar(select(QuizAttempt).where(QuizAttempt.user_id==user.user_id,QuizAttempt.client_session_id==data.client_session_id))
    if attempt.quiz_type!=data.quiz_type or attempt.question_payload.get('requested_count')!=data.count:
        raise HTTPException(409,'Quiz session key already used for different data')
    result=response(db,attempt);db.commit();return result

def answer(db:Session,user:User,attempt_id:int,data:QuizSubmit)->AnswerResponse:
    attempt=owned(db,user.user_id,attempt_id,lock=True)
    questions=attempt.question_payload.get('questions',[])
    position=next((i for i,q in enumerate(questions) if q['question_id']==str(data.question_id)),None)
    if position is None: raise HTTPException(404,'Question not found')
    question=questions[position]
    prior=db.scalar(select(QuizAnswer).where(QuizAnswer.attempt_id==attempt_id,QuizAnswer.question_id==str(data.question_id)))
    submitted=data.answer.strip()
    if prior is not None:
        if (prior.user_answer or '').strip().casefold()!=submitted.casefold():
            raise HTTPException(409,'Question already answered differently')
        return AnswerResponse(feedback=feedback(prior,question),progress=summary(db,user))
    if attempt.completed_at or attempt.aborted_at: raise HTTPException(409,'Quiz is closed')
    answered=len(list(db.scalars(select(QuizAnswer.answer_id).where(QuizAnswer.attempt_id==attempt_id)).all()))
    if position!=answered: raise HTTPException(409,'Answer questions in order')
    word=question['word'];word_id=word['vocabulary_id']
    if db.get(Vocabulary,word_id) is None: raise HTTPException(404,'Vocabulary not found')
    if question['question_type']=='FILL_BLANK': correct=submitted.casefold()==word['word'].strip().casefold()
    else:
        if submitted not in {str(option['vocabulary_id']) for option in question['options']}:
            raise HTTPException(422,'Answer must be one of the provided choices')
        correct=submitted==str(word_id)
    row=QuizAnswer(attempt_id=attempt_id,vocabulary_id=word_id,question_type=question['question_type'],
        user_answer=submitted,correct_answer=word['word'],is_correct=correct,
        question_id=str(data.question_id),question_index=position)
    db.add(row);attempt.correct_answers+=int(correct)
    record_event(db,user.user_id,word_id,data.question_id,'QUIZ',correct)
    db.flush()
    progress=summary(db,user)
    user.current_streak=progress.current_streak;user.longest_streak=progress.longest_streak
    result=AnswerResponse(feedback=feedback(row,question),progress=progress)
    db.commit();return result

def complete(db:Session,user:User,attempt_id:int)->QuizResponse:
    attempt=owned(db,user.user_id,attempt_id,lock=True)
    result=response(db,attempt)
    if attempt.aborted_at: raise HTTPException(409,'Quiz is closed')
    if result.answered_count!=attempt.total_questions or not attempt.total_questions:
        raise HTTPException(409,'Quiz incomplete')
    if attempt.completed_at is None: attempt.completed_at=datetime.now(timezone.utc)
    db.flush();result=response(db,attempt);db.commit();return result

def abort(db:Session,user:User,attempt_id:int)->QuizResponse:
    attempt=owned(db,user.user_id,attempt_id,lock=True)
    if attempt.completed_at is None and attempt.aborted_at is None: attempt.aborted_at=datetime.now(timezone.utc)
    db.flush();result=response(db,attempt);db.commit();return result
