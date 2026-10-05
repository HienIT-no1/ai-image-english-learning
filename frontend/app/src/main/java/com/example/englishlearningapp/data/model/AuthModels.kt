package com.example.englishlearningapp.data.model

import com.google.gson.annotations.SerializedName

data class RegisterRequest(
    val username: String,
    val email: String,
    val password: String
)

data class LoginRequest(
    val username: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)

data class UserDto(
    @SerializedName("user_id") val userId: Long?,
    val username: String?,
    val email: String?,
    @SerializedName("full_name") val fullName: String?,
    @SerializedName("english_level") val englishLevel: String?,
    @SerializedName("daily_goal") val dailyGoal: Int?,
    @SerializedName("current_streak") val currentStreak: Int?,
    @SerializedName("longest_streak") val longestStreak: Int?
)

data class RegisterResponse(
    val message: String?,
    val user: UserDto?
)