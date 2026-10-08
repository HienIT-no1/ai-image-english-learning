package com.example.englishlearningapp.data.model
import com.google.gson.annotations.SerializedName

data class ProfileUpdateRequest(
    @SerializedName("full_name") val fullName: String,
    @SerializedName("cefr_level") val cefrLevel: String,
    @SerializedName("daily_goal") val dailyGoal: Int,
    @SerializedName("reminders_enabled") val remindersEnabled: Boolean
)
data class ReviewRequest(
    @SerializedName("vocabulary_id") val vocabularyId: Long,
    val remembered: Boolean,
    @SerializedName("event_key") val eventKey: String
)
data class WordProgressDto(
    @SerializedName("vocabulary_id") val vocabularyId: Long,
    val status: String,
    @SerializedName("review_count") val reviewCount: Int
)
data class StudyDayDto(val date: String,val count: Int)
data class LearningSummaryDto(
    val today: String,
    @SerializedName("daily_goal") val dailyGoal: Int,
    @SerializedName("saved_count") val savedCount: Int,
    @SerializedName("mastered_count") val masteredCount: Int,
    @SerializedName("needs_review") val needsReview: Int,
    @SerializedName("review_count") val reviewCount: Int,
    @SerializedName("today_count") val todayCount: Int,
    @SerializedName("current_streak") val currentStreak: Int,
    @SerializedName("longest_streak") val longestStreak: Int,
    @SerializedName("quiz_runs") val quizRuns: Int,
    @SerializedName("quiz_correct") val quizCorrect: Int,
    @SerializedName("quiz_total") val quizTotal: Int,
    val days: List<StudyDayDto>,
    val progress: List<WordProgressDto>
)
data class QuizStartRequest(
    @SerializedName("quiz_type") val quizType: String,
    val count: Int=8,
    @SerializedName("client_session_id") val clientSessionId: String
)
data class QuizAnswerRequest(
    @SerializedName("question_id") val questionId: String,
    val answer: String
)
data class PendingQuizAnswer(val attemptId: Long,val request: QuizAnswerRequest)
data class QuizQuestionDto(
    @SerializedName("question_id") val questionId: String,
    @SerializedName("question_type") val questionType: String,
    val word: VocabularyDto,
    val options: List<VocabularyDto>
)
data class QuizFeedbackDto(
    @SerializedName("question_id") val questionId: String,
    @SerializedName("user_answer") val userAnswer: String?,
    @SerializedName("is_correct") val isCorrect: Boolean,
    @SerializedName("correct_answer") val correctAnswer: String,
    @SerializedName("correct_choice_key") val correctChoiceKey: String,
    val word: VocabularyDto
)
data class QuizAttemptDto(
    @SerializedName("attempt_id") val attemptId: Long,
    @SerializedName("quiz_type") val quizType: String,
    @SerializedName("total_questions") val totalQuestions: Int,
    @SerializedName("correct_answers") val correctAnswers: Int,
    @SerializedName("answered_count") val answeredCount: Int,
    val completed: Boolean,
    val aborted: Boolean,
    val questions: List<QuizQuestionDto>,
    val answers: List<QuizFeedbackDto>
)
data class QuizAnswerResponse(val feedback: QuizFeedbackDto,val progress: LearningSummaryDto)
