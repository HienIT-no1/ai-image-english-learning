package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.remote.*
import com.google.gson.Gson
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class LearningRepository(private val api: ApiService,private val store: LearningStore) {
    private val gson=Gson()
    private val mutex=Mutex()
    private val changed=MutableStateFlow(0)
    val changes=changed.asStateFlow()
    var snapshot: LearningSummaryDto?=null
        private set
    fun reset() { snapshot=null;changed.value++ }
    fun apply(data: LearningSummaryDto,token: String) {
        if (store.token!=token || store.userId==null) throw CancellationException("Session changed")
        snapshot=data;store.applyLearning(data);changed.value++
    }
    private suspend fun flush(token: String) {
        val pending=store.pendingReview ?: return
        val request=gson.fromJson(pending,ReviewRequest::class.java)
        apply(api.review(request,"Bearer $token").requireData(),token)
        store.pendingReview=null
    }
    // Serialize quiz feedback with progress reads so an older read cannot replace a newer result.
    suspend fun answerQuiz(id: Long,request: QuizAnswerRequest,token: String): QuizAnswerResponse = mutex.withLock {
        if (store.token!=token) throw CancellationException("Session changed")
        val response=api.answerQuiz(id,request,"Bearer $token").requireData()
        apply(response.progress,token)
        response
    }
    suspend fun load(): Result<Unit> = apiResult {
        val token=store.token ?: error("Hãy đăng nhập để xem tiến độ.")
        mutex.withLock {
            if (store.token!=token) throw CancellationException("Session changed")
            flush(token);apply(api.getLearning("Bearer $token").requireData(),token)
        }
    }
    suspend fun review(request: ReviewRequest): Result<Unit> = apiResult {
        val token=store.token ?: error("Hãy đăng nhập để học.")
        mutex.withLock {
            if (store.token!=token) throw CancellationException("Session changed")
            val pending=store.pendingReview?.let { gson.fromJson(it,ReviewRequest::class.java) }
            if (pending!=null && pending!=request) flush(token)
            store.pendingReview=gson.toJson(request)
            apply(api.review(request,"Bearer $token").requireData(),token)
            store.pendingReview=null
        }
    }
}
