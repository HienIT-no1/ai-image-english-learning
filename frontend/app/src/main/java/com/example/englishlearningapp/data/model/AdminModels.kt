package com.example.englishlearningapp.data.model
import com.google.gson.annotations.SerializedName

data class AdminSummaryDto(val users: Int,val admins: Int,val topics: Int,val vocabularies: Int,
    @SerializedName("completed_quizzes") val completedQuizzes: Int)
data class AdminUserDto(@SerializedName("user_id") val userId: Long,val username: String,val email: String,
    @SerializedName("full_name") val fullName: String?,val role: String)
data class AdminTopicRequest(val name: String,val slug: String,val symbol: String)
data class AdminWordRequest(val word: String,val ipa: String,
    @SerializedName("meaning_vi") val meaningVi: String,
    @SerializedName("sentence_en") val sentenceEn: String,
    @SerializedName("sentence_vi") val sentenceVi: String,
    @SerializedName("topic_ids") val topicIds: List<Long>)
data class MessageDto(val message: String)
