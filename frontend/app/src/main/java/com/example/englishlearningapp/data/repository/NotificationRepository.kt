package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.remote.*
import kotlinx.coroutines.CancellationException

class NotificationRepository(private val api: ApiService,private val store: LearningStore,private val catalog: WordRepository) {
    private fun token()=store.token ?: error("Hãy đăng nhập để xem thông báo.")
    private fun check(expected: String) { if(store.token!=expected) throw CancellationException("Session changed") }
    suspend fun syncPending(): Result<Unit> = apiResult {
        val expected=token()
        for(date in store.pendingReminderDates.sorted()) {
            check(expected)
            try { api.recordReminder(ReminderRequest(date),"Bearer $expected").requireData() }
            catch(e: ApiException) { if(e.status!=422 && e.status!=409) throw e }
            check(expected);store.pendingReminderDates=store.pendingReminderDates-date
        }
    }
    suspend fun inbox(offset: Int=0): Result<NotificationPageDto> = apiResult {
        val expected=token();syncPending().getOrThrow();check(expected)
        val page=api.inbox(offset,"Bearer $expected").requireData();check(expected);page
    }
    suspend fun read(id: Long): Result<Unit> = apiResult {
        val expected=token();api.readNotification(id,"Bearer $expected").requireData();check(expected)
    }
    suspend fun readAll(): Result<Unit> = apiResult {
        val expected=token();api.readAllNotifications("Bearer $expected").requireData();check(expected)
    }
    suspend fun due(): Result<List<VocabularyDto>> = apiResult {
        val expected=token();val data=api.dueWords("Bearer $expected").requireData()
        check(expected);catalog.remember(data);data
    }
}
