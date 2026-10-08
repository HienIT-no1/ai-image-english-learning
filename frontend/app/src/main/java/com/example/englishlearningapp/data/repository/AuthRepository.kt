package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.LoginRequest
import com.example.englishlearningapp.data.model.RegisterRequest
import com.example.englishlearningapp.data.model.UserDto
import com.example.englishlearningapp.data.model.ProfileUpdateRequest
import com.example.englishlearningapp.data.remote.ApiService
import com.example.englishlearningapp.data.remote.apiResult
import com.example.englishlearningapp.data.remote.requireData
import kotlinx.coroutines.CancellationException

class AuthRepository(private val api: ApiService, private val store: LearningStore,
    private val onLogout: () -> Unit = {}) {
    suspend fun login(username: String, password: String): Result<UserDto> = apiResult {
        logout()
        val token = api.login(LoginRequest(username,password)).requireData().accessToken
        store.token = token
        val user = api.me("Bearer $token").requireData()
        if (store.token != token) throw CancellationException("Session changed")
        store.activateUser(user)
        user
    }
    suspend fun register(username: String, email: String, password: String): Result<UserDto> = apiResult {
        api.register(RegisterRequest(username,email,password)).requireData()
        login(username,password).getOrThrow()
    }
    suspend fun restore(): Result<UserDto?> = apiResult {
        val token = store.token
        if (token.isNullOrBlank()) null else {
            val user = api.me("Bearer $token").requireData()
            if (store.token != token) throw CancellationException("Session changed")
            store.activateUser(user,adoptLegacy=true)
            user
        }
    }
    suspend fun updateProfile(name: String,level: String,goal: Int,reminders: Boolean): Result<UserDto> = apiResult {
        val token=store.token ?: error("Hãy đăng nhập lại.")
        val user=api.updateProfile(ProfileUpdateRequest(name.trim(),level.substringBefore(" "),goal,reminders),"Bearer $token").requireData()
        if (store.token!=token) throw CancellationException("Session changed")
        store.activateUser(user)
        user
    }
    fun logout() { store.clearSession(); onLogout() }
}
