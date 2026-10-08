package com.example.englishlearningapp.data.remote

import com.example.englishlearningapp.data.model.LoginRequest
import com.example.englishlearningapp.data.model.RegisterRequest
import com.example.englishlearningapp.data.model.RegisterResponse
import com.example.englishlearningapp.data.model.TokenResponse
import com.example.englishlearningapp.data.model.UserDto
import com.example.englishlearningapp.data.model.VocabularyDto
import com.example.englishlearningapp.data.model.TopicDto
import com.example.englishlearningapp.data.model.CollectionDto
import com.example.englishlearningapp.data.model.*
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.Response
import retrofit2.http.PUT
import retrofit2.http.DELETE
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path


interface ApiService {
    @PATCH("users/me")
    suspend fun updateProfile(@Body body: ProfileUpdateRequest,@Header("Authorization") authorization: String): Response<UserDto>
    @GET("learning/me")
    suspend fun getLearning(@Header("Authorization") authorization: String): Response<LearningSummaryDto>
    @POST("learning/me/reviews")
    suspend fun review(@Body body: ReviewRequest,@Header("Authorization") authorization: String): Response<LearningSummaryDto>
    @POST("quizzes")
    suspend fun startQuiz(@Body body: QuizStartRequest,@Header("Authorization") authorization: String): Response<QuizAttemptDto>
    @GET("quizzes/{id}")
    suspend fun getQuiz(@Path("id") id: Long,@Header("Authorization") authorization: String): Response<QuizAttemptDto>
    @POST("quizzes/{id}/answers")
    suspend fun answerQuiz(@Path("id") id: Long,@Body body: QuizAnswerRequest,@Header("Authorization") authorization: String): Response<QuizAnswerResponse>
    @POST("quizzes/{id}/complete")
    suspend fun completeQuiz(@Path("id") id: Long,@Header("Authorization") authorization: String): Response<QuizAttemptDto>
    @POST("quizzes/{id}/abort")
    suspend fun abortQuiz(@Path("id") id: Long,@Header("Authorization") authorization: String): Response<QuizAttemptDto>

    @GET("collections/me")
    suspend fun getMyCollection(@Header("Authorization") authorization: String): Response<CollectionDto>
    @PUT("collections/me/words/{wordId}")
    suspend fun saveWord(@Path("wordId") wordId: Long,@Header("Authorization") authorization: String): Response<CollectionDto>
    @DELETE("collections/me/words/{wordId}")
    suspend fun unsaveWord(@Path("wordId") wordId: Long,@Header("Authorization") authorization: String): Response<CollectionDto>

    @GET("topics")
    suspend fun getTopics(): Response<List<TopicDto>>

    @GET("topics/{topicId}/vocabularies")
    suspend fun getTopicVocabularies(@Path("topicId") topicId: Long): Response<List<VocabularyDto>>


    @POST("auth/register")
    suspend fun register(
        @Body body: RegisterRequest
    ): Response<RegisterResponse>


    @POST("auth/login")
    suspend fun login(
        @Body body: LoginRequest
    ): Response<TokenResponse>


    @GET("users/me")
    suspend fun me(@Header("Authorization") authorization: String): Response<UserDto>


    @GET("vocabularies")
    suspend fun getVocabularies(): Response<List<VocabularyDto>>


    @GET("vocabularies/{vocabularyId}")
    suspend fun getVocabulary(
        @Path("vocabularyId") vocabularyId: Long
    ): Response<VocabularyDto>
}