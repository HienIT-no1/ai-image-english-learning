package com.example.englishlearningapp.data.local

import android.content.Context
import com.example.englishlearningapp.data.mock.MockData
import org.json.JSONArray

/** Session, per-account API cache and retry requests. PostgreSQL owns learning results. */
class LearningStore(private val context: Context) {
    private val sessionPrefs = context.getSharedPreferences("learning_demo", Context.MODE_PRIVATE)
    val userId: Long? get() = sessionPrefs.getLong("active_user_id", 0).takeIf { it > 0 }
    private val prefs get() = context.getSharedPreferences("learning_user_${userId ?: "guest"}", Context.MODE_PRIVATE)

    fun activateUser(user: com.example.englishlearningapp.data.model.UserDto, adoptLegacy: Boolean = false) {
        val id = requireNotNull(user.userId)
        require(id > 0)
        val migrate = adoptLegacy && userId == null && !sessionPrefs.contains("legacy_owner_id") && sessionPrefs.getBoolean("signed_in", false)
        sessionPrefs.edit().putLong("active_user_id", id).apply()
        if (migrate) {
            // Preserve old local learning data for the validated owner; saved words now come from the server.
            val editor = prefs.edit()
            val keys = setOf("name","level","goal","reminders","mastered","history","reviews","today_count","last_day","days","quiz_runs","quiz_correct","quiz_total","quiz_sessions")
            for ((key, value) in sessionPrefs.all) if (key in keys) when (value) {
                is String -> editor.putString(key,value)
                is Int -> editor.putInt(key,value)
                is Boolean -> editor.putBoolean(key,value)
                is Set<*> -> editor.putStringSet(key,value.filterIsInstance<String>().toSet())
            }
            editor.apply()
            sessionPrefs.edit().putLong("legacy_owner_id",id).apply()
        }
        name = user.fullName ?: user.username ?: "Bạn học"
        level = levelLabel(user.cefrLevel ?: when(user.englishLevel) {
            "INTERMEDIATE" -> "B1"; "ADVANCED" -> "B2"; else -> "A1"
        })
        goal = user.dailyGoal ?: 10
        reminders = user.remindersEnabled
        onboardingCompleted = user.onboardingCompleted
        signedIn = true
    }

    fun clearSession() {
        sessionPrefs.edit().remove("token").remove("active_user_id").putBoolean("signed_in",false).apply()
    }
    var signedIn: Boolean
        get() = sessionPrefs.getBoolean("signed_in", false)
        set(value) { sessionPrefs.edit().putBoolean("signed_in", value).apply() }
    var token: String?
        get() = sessionPrefs.getString("token", null)
        set(value) {
            sessionPrefs.edit().apply { if (value == null) remove("token") else putString("token", value) }.apply()
        }
    var name: String
        get() = prefs.getString("name", "Bạn học") ?: "Bạn học"
        set(value) { prefs.edit().putString("name", value).apply() }
    var level: String
        get() = prefs.getString("level", "A1 • Mới bắt đầu") ?: "A1 • Mới bắt đầu"
        set(value) { prefs.edit().putString("level", value).apply() }
    var goal: Int
        get() = prefs.getInt("goal", 10)
        set(value) { prefs.edit().putInt("goal", value).apply() }
    var reminders: Boolean
        get() = prefs.getBoolean("reminders", false)
        set(value) { prefs.edit().putBoolean("reminders", value).apply() }
    var saved: Set<String>
        get() = prefs.getStringSet("saved", emptySet())?.toSet() ?: emptySet()
        set(value) { prefs.edit().putStringSet("saved", value.toSet()).apply() }
    var mastered: Set<String>
        get() = prefs.getStringSet("mastered", emptySet())?.toSet() ?: emptySet()
        set(value) { prefs.edit().putStringSet("mastered", value.toSet()).apply() }
    var history: List<String>
        get() = readList("history", emptyList())
        set(value) { prefs.edit().putString("history", JSONArray(value).toString()).apply() }
    var pendingReview: String?
        get() = prefs.getString("pending_review",null)
        set(value) { prefs.edit().putString("pending_review",value).apply() }
    var activeQuiz: String?
        get() = prefs.getString("active_quiz",null)
        set(value) { prefs.edit().putString("active_quiz",value).apply() }
    var pendingQuizAnswer: String?
        get() = prefs.getString("pending_quiz_answer",null)
        set(value) { prefs.edit().putString("pending_quiz_answer",value).apply() }
    var onboardingCompleted: Boolean
        get() = prefs.getBoolean("onboarding_completed",false)
        set(value) { prefs.edit().putBoolean("onboarding_completed",value).apply() }
    fun levelLabel(code: String) = when(code) {
        "A2" -> "A2 • Cơ bản"; "B1" -> "B1 • Trung cấp"; "B2" -> "B2 • Khá"; else -> "A1 • Mới bắt đầu"
    }
    fun applyLearning(data: com.example.englishlearningapp.data.model.LearningSummaryDto) {
        prefs.edit().putStringSet("mastered",data.progress.filter { it.status=="MASTERED" }.map { it.vocabularyId.toString() }.toSet())
            .putInt("reviews",data.reviewCount).putInt("today_count",data.todayCount)
            .putInt("server_streak",data.currentStreak).putInt("quiz_runs",data.quizRuns)
            .putInt("quiz_correct",data.quizCorrect).putInt("quiz_total",data.quizTotal)
            .putStringSet("days",data.days.filter { it.count>0 }.map { it.date }.toSet()).apply()
        goal=data.dailyGoal
    }
    val reviews get() = prefs.getInt("reviews",0)
    val todayCount get() = prefs.getInt("today_count",0)
    val streak get() = prefs.getInt("server_streak",0)
    val studyDays get() = prefs.getStringSet("days",emptySet())?.toSet() ?: emptySet()
    val quizRuns get() = prefs.getInt("quiz_runs",0)
    val quizCorrect get() = prefs.getInt("quiz_correct",0)
    val quizTotal get() = prefs.getInt("quiz_total",0)
    fun adminItems(kind: String): List<String> {
        val defaults = when (kind) {
            "users" -> listOf("Minh Anh • A1", "Hoàng Nam • A2", "Thu Hà • B1")
            "topics" -> MockData.topics.map { it.name }
            "quiz" -> listOf("Nhìn ảnh chọn từ", "Nhìn từ chọn ảnh", "Nghe chọn đáp án", "Điền từ")
            "content" -> listOf("Mẹo học từ vựng mỗi ngày", "Hướng dẫn Flashcard", "Ôn tập ngắt quãng")
            else -> MockData.words.map { "${it.english} • ${it.meaning}" }
        }
        return readList("admin_$kind", defaults)
    }
    fun saveAdminItems(kind: String, items: List<String>) { prefs.edit().putString("admin_$kind", JSONArray(items).toString()).apply() }
    private fun readList(key: String, defaults: List<String>): List<String> = runCatching {
        val array = JSONArray(prefs.getString(key,JSONArray(defaults).toString()))
        (0 until array.length()).mapNotNull { array.opt(it) as? String }
    }.getOrDefault(defaults)
}

