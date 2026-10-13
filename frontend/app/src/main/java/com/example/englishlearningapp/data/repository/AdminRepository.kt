package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.remote.*
import kotlinx.coroutines.CancellationException
import retrofit2.Response

class AdminRepository(private val api: ApiService,private val store: LearningStore) {
    private suspend fun <T> request(call: suspend (String) -> Response<T>): Result<T> = apiResult {
        val token=store.token ?: throw ApiException(401,"Hãy đăng nhập lại.")
        if (!store.isAdmin) throw ApiException(403,"Tài khoản không có quyền quản trị.")
        try {
            val result=call("Bearer $token").requireData()
            if (store.token!=token) throw CancellationException("Session changed")
            result
        } catch (error: ApiException) {
            if (error.status==403 && store.token==token) store.role="USER"
            throw error
        }
    }
    suspend fun summary() = request { api.adminSummary(it) }
    suspend fun users(offset: Int) = request { api.adminUsers(offset,it) }
    suspend fun topics() = request { api.adminTopics(it) }
    suspend fun words() = request { api.adminWords(it) }
    suspend fun saveTopic(id: Long?,body: AdminTopicRequest) = request {
        if(id==null) api.createTopic(body,it) else api.updateTopic(id,body,it)
    }
    suspend fun deleteTopic(id: Long) = request { api.deleteTopic(id,it) }
    suspend fun saveWord(id: Long?,body: AdminWordRequest) = request {
        if(id==null) api.createWord(body,it) else api.updateWord(id,body,it)
    }
}
