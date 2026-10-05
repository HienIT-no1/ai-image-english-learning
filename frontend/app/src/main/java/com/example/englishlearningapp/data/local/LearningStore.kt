package com.example.englishlearningapp.data.local

import android.content.Context
import com.example.englishlearningapp.data.mock.MockData
import org.json.JSONArray
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

/** Persistent local demo data, replaced by repositories when a backend is available. */
class LearningStore(context: Context) {
    private val prefs = context.getSharedPreferences("learning_demo", Context.MODE_PRIVATE)
    var signedIn: Boolean
        get() = prefs.getBoolean("signed_in", false)
        set(value) { prefs.edit().putBoolean("signed_in", value).apply() }
    var token: String?
        get() = prefs.getString("token", null)
        set(value) {
            prefs.edit().apply { if (value == null) remove("token") else putString("token", value) }.apply()
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
        get() = prefs.getStringSet("saved", setOf("apple", "book", "coffee", "cat"))?.toSet() ?: emptySet()
        set(value) { prefs.edit().putStringSet("saved", value.toSet()).apply() }
    var mastered: Set<String>
        get() = prefs.getStringSet("mastered", emptySet())?.toSet() ?: emptySet()
        set(value) { prefs.edit().putStringSet("mastered", value.toSet()).apply() }
    var history: List<String>
        get() = readList("history", emptyList())
        set(value) { prefs.edit().putString("history", JSONArray(value).toString()).apply() }
    fun toggleSave(id: String) { saved = if (id in saved) saved - id else saved + id }
    fun practice(id: String, remembered: Boolean) {
        val rememberedIds = if (remembered) mastered + id else mastered - id
        val today = dateFormat().format(Date())
        val days = studyDays.toMutableSet().apply { add(today) }
        prefs.edit().putStringSet("mastered", rememberedIds).putStringSet("days", days).putInt("reviews", reviews + 1)
            .putInt("today_count", todayCount + 1).putString("last_day", today).apply()
    }
    val reviews get() = prefs.getInt("reviews", 0)
    val todayCount: Int get() = if (prefs.getString("last_day", "") == dateFormat().format(Date())) prefs.getInt("today_count", 0) else 0
    val studyDays get() = prefs.getStringSet("days", emptySet())?.toSet() ?: emptySet()
    val streak: Int get() {
        val calendar = Calendar.getInstance()
        if (dateFormat().format(calendar.time) !in studyDays) calendar.add(Calendar.DAY_OF_YEAR, -1)
        var count = 0
        while (dateFormat().format(calendar.time) in studyDays) { count++; calendar.add(Calendar.DAY_OF_YEAR, -1) }
        return count
    }
    fun dateFormat() = SimpleDateFormat("yyyy-MM-dd", Locale.US)
    var quizRuns: Int
        get() = prefs.getInt("quiz_runs", 0)
        set(value) { prefs.edit().putInt("quiz_runs", value).apply() }
    var quizCorrect: Int
        get() = prefs.getInt("quiz_correct", 0)
        set(value) { prefs.edit().putInt("quiz_correct", value).apply() }
    var quizTotal: Int
        get() = prefs.getInt("quiz_total", 0)
        set(value) { prefs.edit().putInt("quiz_total", value).apply() }
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
    fun saveProfile(name: String, level: String, goal: Int, reminders: Boolean) {
        require(name.isNotBlank())
        prefs.edit().putString("name",name.trim()).putString("level",level)
            .putInt("goal",goal.coerceAtLeast(1)).putBoolean("reminders",reminders).apply()
    }
    fun recordQuiz(sessionId: String, correct: Int, total: Int) {
        val sessions = prefs.getStringSet("quiz_sessions",emptySet())?.toSet() ?: emptySet()
        if (sessionId in sessions || total <= 0) return
        prefs.edit().putInt("quiz_runs",quizRuns + 1).putInt("quiz_correct",quizCorrect + correct.coerceIn(0,total))
            .putInt("quiz_total",quizTotal + total).putStringSet("quiz_sessions",sessions + sessionId).apply()
    }
    private fun readList(key: String, defaults: List<String>): List<String> = runCatching {
        val array = JSONArray(prefs.getString(key,JSONArray(defaults).toString()))
        (0 until array.length()).mapNotNull { array.opt(it) as? String }
    }.getOrDefault(defaults)
}

