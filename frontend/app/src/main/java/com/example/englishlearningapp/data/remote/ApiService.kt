package com.example.englishlearningapp.data.remote

import com.example.englishlearningapp.data.model.LoginRequest
import com.example.englishlearningapp.data.model.RegisterRequest
import com.example.englishlearningapp.data.model.RegisterResponse
import com.example.englishlearningapp.data.model.TokenResponse
import com.example.englishlearningapp.data.model.UserDto
import com.example.englishlearningapp.data.model.VocabularyDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path


interface ApiService {

    @POST("auth/register")
    suspend fun register(
        @Body body: RegisterRequest
    ): Response<RegisterResponse>


    @POST("auth/login")
    suspend fun login(
        @Body body: LoginRequest
    ): Response<TokenResponse>


    @GET("users/me")
    suspend fun me(): Response<UserDto>


    @GET("vocabularies")
    suspend fun getVocabularies(): Response<List<VocabularyDto>>


    @GET("vocabularies/{vocabularyId}")
    suspend fun getVocabulary(
        @Path("vocabularyId") vocabularyId: Long
    ): Response<VocabularyDto>
}