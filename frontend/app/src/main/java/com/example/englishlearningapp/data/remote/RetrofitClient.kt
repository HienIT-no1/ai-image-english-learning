package com.example.englishlearningapp.data.remote

import com.example.englishlearningapp.data.local.LearningStore
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // Dùng adb reverse tcp:8000 tcp:8000 để chuyển kết nối từ thiết bị về máy tính.
    private const val BASE_URL = "http://127.0.0.1:8000/"

    fun create(store: LearningStore, onExpired: (String) -> Unit = {}): ApiService {
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val token = chain.request().header("Authorization")?.removePrefix("Bearer ") ?: store.token
                val request = chain.request().newBuilder().apply {
                    if (chain.request().header("Authorization")==null && !token.isNullOrBlank()) addHeader("Authorization", "Bearer $token")
                }.build()
                val response = chain.proceed(request)
                val authRequest = request.url.encodedPath.startsWith("/auth/")
                if (response.code == 401 && !authRequest && !token.isNullOrBlank()) onExpired(token)
                response
            }
            // Log request status without passwords, tokens or response bodies.
            .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
            .build()

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}