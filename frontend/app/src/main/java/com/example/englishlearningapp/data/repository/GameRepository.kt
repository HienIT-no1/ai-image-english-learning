package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.remote.*
import com.google.gson.Gson
import java.util.UUID
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class GameRepository(private val api: ApiService,private val store: LearningStore,
    private val learning: LearningRepository, private val gameType: String = "WORD_SHOOTER") {
    private val path get() = if(gameType=="WORD_DEFENSE") "word-defense" else "word-shooter"
    private var active: String?
        get() = if(gameType=="WORD_DEFENSE") store.activeDefense else store.activeGame
        set(value) { if(gameType=="WORD_DEFENSE") store.activeDefense=value else store.activeGame=value }
    private var pending: String?
        get() = if(gameType=="WORD_DEFENSE") store.pendingDefenseFinish else store.pendingGameFinish
        set(value) { if(gameType=="WORD_DEFENSE") store.pendingDefenseFinish=value else store.pendingGameFinish=value }
    private fun clearLocal() { if(gameType=="WORD_DEFENSE") store.localDefenseState=null else store.localGameState=null }
    private val gson=Gson()
    private val mutex=Mutex()
    val canResume get() = active!=null
    private fun token()=store.token ?: error("Hãy đăng nhập để chơi.")
    private fun check(expected: String) { if (store.token!=expected) throw CancellationException("Session changed") }
    private suspend fun flush(expected: String) {
        val queued=pending?.let { gson.fromJson(it,PendingGameFinish::class.java) } ?: return
        api.finishGame(queued.runId,queued.roundId,queued.request,"Bearer $expected",path).requireData()
        check(expected);pending=null
        learning.load();check(expected)
    }
    suspend fun syncPending(): Result<Unit> = apiResult {
        val expected=token();mutex.withLock { check(expected);flush(expected) }
    }
    suspend fun start(source: String?=null,topicId: Long?=null,learningMode: String="RECALL"): Result<GameRunDto> = apiResult {
        val expected=token()
        mutex.withLock {
            check(expected)
            flush(expected)
            val request=if(source==null) {
                active?.let { gson.fromJson(it,GameStartRequest::class.java) } ?: error("Chưa có lượt chơi để tiếp tục.")
            } else {
                GameStartRequest(UUID.randomUUID().toString(),source,topicId,if(gameType=="WORD_DEFENSE") learningMode else null).also {
                    active=gson.toJson(it);clearLocal()
                }
            }
            val result=api.startGame(request,"Bearer $expected",path).requireData()
            check(expected);result
        }
    }
    suspend fun finish(run: GameRunDto,request: GameFinishRequest): Result<GameRunDto> = apiResult {
        val expected=token()
        val result=mutex.withLock {
            check(expected)
            val queued=PendingGameFinish(run.runId,run.round.roundId,request)
            pending=gson.toJson(queued)
            val response=api.finishGame(queued.runId,queued.roundId,request,"Bearer $expected",path).requireData()
            check(expected);pending=null;response
        }
        learning.load();check(expected);result
    }
    suspend fun next(run: GameRunDto): Result<GameRunDto> = apiResult {
        val expected=token()
        mutex.withLock {
            check(expected);flush(expected)
            val response=api.nextGame(run.runId,run.round.roundId,"Bearer $expected",path).requireData()
            check(expected);clearLocal();response
        }
    }
    suspend fun complete(run: GameRunDto): Result<GameRunDto> = apiResult {
        val expected=token()
        mutex.withLock {
            check(expected);flush(expected)
            val response=api.completeDefense(run.runId,"Bearer $expected").requireData()
            check(expected);response
        }
    }
}
