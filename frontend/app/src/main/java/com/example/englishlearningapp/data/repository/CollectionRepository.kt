package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.mapper.toWord
import com.example.englishlearningapp.data.model.CollectionDto
import com.example.englishlearningapp.data.remote.ApiService
import com.example.englishlearningapp.data.remote.apiResult
import com.example.englishlearningapp.data.remote.requireData
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

class CollectionRepository(private val api: ApiService, private val store: LearningStore,
    private val catalog: WordRepository) {
    private val mutex = Mutex()
    private val changed = MutableStateFlow(0)
    val changes = changed.asStateFlow()
    private var pending: Set<String> = emptySet()
    var loaded = false
        private set
    fun isSaving(id: String) = id in pending
    private fun changed() { changed.value++ }
    fun reset() { loaded = false; pending = emptySet(); catalog.clearAccountData(); changed() }
    private fun apply(data: CollectionDto, token: String) {
        if (store.token != token || store.userId == null) throw CancellationException("Session changed")
        store.saved = data.words.map { it.vocabularyId.toString() }.toSet()
        catalog.setSavedWords(data.words.map { it.toWord() })
        loaded = true; changed()
    }
    suspend fun load(): Result<Unit> = apiResult {
        val token = store.token ?: error("Hãy đăng nhập để xem bộ sưu tập.")
        mutex.withLock {
            if (store.token != token) throw CancellationException("Session changed")
            apply(api.getMyCollection("Bearer $token").requireData(),token)
        }
    }
    suspend fun toggle(id: String): Result<Unit> {
        if (id in pending) return Result.success(Unit)
        val token = store.token ?: return Result.failure(Exception("Hãy đăng nhập để lưu từ."))
        pending = pending + id; changed()
        return try {
            apiResult {
                mutex.withLock {
                    if (store.token != token) throw CancellationException("Session changed")
                    val wordId = id.toLongOrNull() ?: error("Từ mẫu này chưa có trong kho từ trên máy chủ.")
                    if (!loaded) apply(api.getMyCollection("Bearer $token").requireData(),token)
                    val response = if (id in store.saved) api.unsaveWord(wordId,"Bearer $token") else api.saveWord(wordId,"Bearer $token")
                    apply(response.requireData(),token)
                }
            }
        } finally { if (store.token == token) { pending = pending - id; changed() } }
    }
}
