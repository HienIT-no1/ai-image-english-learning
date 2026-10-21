package com.example.englishlearningapp.data.model

import com.google.gson.annotations.SerializedName

data class GameStartRequest(
    @SerializedName("client_session_id") val clientSessionId: String,
    val source: String,
    @SerializedName("topic_id") val topicId: Long? = null
)
data class GameOutcomeDto(
    @SerializedName("vocabulary_id") val vocabularyId: Long,
    val outcome: String,
    val answer: String? = null,
    @SerializedName("wrong_letters") val wrongLetters: Int = 0
)
data class GameFinishRequest(val results: List<GameOutcomeDto>)
data class PendingGameFinish(val runId: Long,val roundId: Long,val request: GameFinishRequest)
data class GameRoundDto(
    @SerializedName("round_id") val roundId: Long,
    val stage: Int,
    val words: List<VocabularyDto>,
    val results: List<GameOutcomeDto>,
    val status: String,
    @SerializedName("correct_count") val correctCount: Int,
    @SerializedName("missed_count") val missedCount: Int,
    @SerializedName("max_combo") val maxCombo: Int,
    val score: Int
)
data class GameRunDto(
    @SerializedName("run_id") val runId: Long,
    val source: String,
    @SerializedName("topic_id") val topicId: Long?,
    @SerializedName("pool_count") val poolCount: Int,
    @SerializedName("remaining_count") val remainingCount: Int,
    val completed: Boolean,
    @SerializedName("total_score") val totalScore: Int,
    val round: GameRoundDto
)
