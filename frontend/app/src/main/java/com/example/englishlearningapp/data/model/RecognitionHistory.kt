package com.example.englishlearningapp.data.model

import com.google.gson.Gson
import com.google.gson.JsonParser

/** Snapshot keeps history readable when a word is missing from the current cache. */
data class RecognitionHistoryEntry(
    val vocabularyId: String?, val word: String, val ipa: String,
    val meaning: String, val timestamp: String
)

object RecognitionHistoryCodec {
    private val gson = Gson()
    fun encode(entry: RecognitionHistoryEntry): String = gson.toJson(entry)
    fun decode(raw: String, resolve: (String) -> Word?): RecognitionHistoryEntry? {
        if (raw.trimStart().startsWith("{")) return runCatching {
            val value = JsonParser.parseString(raw).asJsonObject
            fun text(key: String) = value.get(key)?.takeUnless { it.isJsonNull }?.asString.orEmpty()
            val word = text("word")
            if (word.isBlank()) null else RecognitionHistoryEntry(
                text("vocabularyId").takeIf { it.isNotBlank() }, word, text("ipa"), text("meaning"), text("timestamp")
            )
        }.getOrNull()
        // Existing versions wrote either an English word or an ID, followed by |date.
        val parts = raw.split("|", limit = 2)
        val key = parts.firstOrNull()?.trim().orEmpty()
        if (key.isBlank()) return null
        val found = resolve(key)
        return RecognitionHistoryEntry(found?.id, found?.english ?: key, found?.ipa.orEmpty(),
            found?.meaning.orEmpty(), parts.getOrElse(1) { "" })
    }
}
