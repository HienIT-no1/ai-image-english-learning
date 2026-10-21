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
    private val learning: LearningRepository) {
    private val gson=Gson()
    private val mutex=Mutex()
    val canResume get() = store.activeGame!=null
    private fun token()=store.token ?: error("Hãy đăng nhập để chơi.")
    private fun check(expected: String) { if (store.token!=expected) throw CancellationException("Session changed") }
    private suspend fun flush(expected: String) {
        val pending=store.pendingGameFinish?.let { gson.fromJson(it,PendingGameFinish::class.java) } ?: return
        api.finishGame(pending.runId,pending.roundId,pending.request,"Bearer $expected").requireData()
        check(expected);store.pendingGameFinish=null
        learning.load();check(expected)
    }
    suspend fun syncPending(): Result<Unit> = apiResult {
        val expected=token();mutex.withLock { check(expected);flush(expected) }
    }
    suspend fun start(source: String?=null,topicId: Long?=null): Result<GameRunDto> = apiResult {
        val expected=token()
        mutex.withLock {
            check(expected)
            val request=if(source==null) {
                store.activeGame?.let { gson.fromJson(it,GameStartRequest::class.java) } ?: error("Chưa có lượt chơi để tiếp tục.")
            } else {
                GameStartRequest(UUID.randomUUID().toString(),source,topicId).also {
                    store.activeGame=gson.toJson(it);store.localGameState=null
                }
            }
            flush(expected)
            val result=api.startGame(request,"Bearer $expected").requireData()
            check(expected);result
        }
    }
    suspend fun finish(run: GameRunDto,request: GameFinishRequest): Result<GameRunDto> = apiResult {
        val expected=token()
        val result=mutex.withLock {
            check(expected)
            val pending=PendingGameFinish(run.runId,run.round.roundId,request)
            store.pendingGameFinish=gson.toJson(pending)
            val response=api.finishGame(pending.runId,pending.roundId,request,"Bearer $expected").requireData()
            check(expected);store.pendingGameFinish=null;response
        }
        learning.load();check(expected);result
    }
    suspend fun next(run: GameRunDto): Result<GameRunDto> = apiResult {
        val expected=token()
        mutex.withLock {
            check(expected);flush(expected)
            val response=api.nextGame(run.runId,run.round.roundId,"Bearer $expected").requireData()
            check(expected);store.localGameState=null;response
        }
    }
}
