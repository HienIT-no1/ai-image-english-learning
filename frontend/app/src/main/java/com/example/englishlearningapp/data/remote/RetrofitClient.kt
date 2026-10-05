package com.example.englishlearningapp.data.remote

import com.example.englishlearningapp.data.local.LearningStore
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // Emulator: 10.0.2.2 trỏ tới máy tính chạy backend.
    // Máy thật: đổi thành http://<IP LAN của PC>:8000/
    private const val BASE_URL = "http://127.0.0.1:8000/"

    fun create(store: LearningStore): ApiService {
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .addInterceptor { chain ->
                val token = store.token
                val request = chain.request().newBuilder().apply {
                    if (!token.isNullOrBlank()) addHeader("Authorization", "Bearer $token")
                }.build()
                chain.proceed(request)
            }
            // BODY in cả mật khẩu và token ra Logcat: chỉ dùng khi debug
            .addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BODY })
            .build()

        return Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}