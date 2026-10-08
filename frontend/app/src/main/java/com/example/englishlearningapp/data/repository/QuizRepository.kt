package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.remote.*
import com.google.gson.Gson
import kotlinx.coroutines.CancellationException
import java.util.UUID
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class QuizRepository(private val api: ApiService,private val store: LearningStore,
    private val catalog: WordRepository,private val learning: LearningRepository) {
    private val gson=Gson()
    private val mutex=Mutex()
    val resumeMode: String? get() = store.activeQuiz?.let {
        val type=gson.fromJson(it,QuizStartRequest::class.java).quizType
        when(type) { "IMAGE_TO_WORD"->"image";"WORD_TO_IMAGE"->"word";"LISTENING"->"listen";"FILL_BLANK"->"fill";else->"mixed" }
    }
    private fun token() = store.token ?: error("Hãy đăng nhập để làm Quiz.")
    private fun check(expected: String) { if (store.token!=expected) throw CancellationException("Session changed") }
    private fun remember(data: QuizAttemptDto) {
        catalog.remember(data.questions.flatMap { listOf(it.word)+it.options })
    }
    private suspend fun flush(expected: String) {
        val data=store.pendingQuizAnswer?.let { gson.fromJson(it,PendingQuizAnswer::class.java) } ?: return
        val response=learning.answerQuiz(data.attemptId,data.request,expected)
        check(expected);catalog.remember(listOf(response.feedback.word))
        store.pendingQuizAnswer=null
    }
    suspend fun syncPending(): Result<Unit> = apiResult {
        val expected=token();mutex.withLock { check(expected);flush(expected) }
    }
    suspend fun start(mode: String): Result<QuizAttemptDto> = apiResult {
        val expected=token()
        mutex.withLock {
        check(expected);flush(expected)
        val type=when(mode) { "image"->"IMAGE_TO_WORD";"word"->"WORD_TO_IMAGE";"listen"->"LISTENING";"fill"->"FILL_BLANK";else->"MIXED" }
        val previous=store.activeQuiz?.let { gson.fromJson(it,QuizStartRequest::class.java) }
        if (previous!=null && previous.quizType!=type) {
            val old=api.startQuiz(previous,"Bearer $expected").requireData()
            if (!old.completed && !old.aborted) api.abortQuiz(old.attemptId,"Bearer $expected").requireData()
            check(expected)
        }
        val request=if (previous?.quizType==type) previous else QuizStartRequest(type,8,UUID.randomUUID().toString())
        check(expected);store.activeQuiz=gson.toJson(request)
        var data=api.startQuiz(request,"Bearer $expected").requireData()
        check(expected)
        if (data.aborted) {
            val replacement=QuizStartRequest(type,8,UUID.randomUUID().toString())
            store.activeQuiz=gson.toJson(replacement);data=api.startQuiz(replacement,"Bearer $expected").requireData();check(expected)
        }
        remember(data)
        if (data.completed) store.activeQuiz=null
        data
    } }
    suspend fun answer(id: Long,questionId: String,value: String): Result<QuizAnswerResponse> = apiResult {
        val expected=token()
        mutex.withLock {
        check(expected)
        val request=QuizAnswerRequest(questionId,value)
        store.pendingQuizAnswer=gson.toJson(PendingQuizAnswer(id,request))
        val result=learning.answerQuiz(id,request,expected)
        check(expected);catalog.remember(listOf(result.feedback.word))
        store.pendingQuizAnswer=null
        result
    } }
    suspend fun complete(id: Long): Result<QuizAttemptDto> = apiResult {
        val expected=token()
        mutex.withLock {
        check(expected);val result=api.completeQuiz(id,"Bearer $expected").requireData();check(expected)
        store.activeQuiz=null;remember(result);learning.load();result
    } }
}
