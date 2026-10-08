package com.example.englishlearningapp.data.model
import com.google.gson.annotations.SerializedName

data class Topic(val id: String, val name: String, val symbol: String, val vocabularyCount: Int = 0)
data class TopicDto(
    @SerializedName("topic_id") val topicId: Long,
    val slug: String, val name: String, val symbol: String,
    @SerializedName("vocabulary_count") val vocabularyCount: Int = 0
)
