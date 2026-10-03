package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.mock.MockData
import com.example.englishlearningapp.data.model.Word
import java.text.Normalizer
import java.util.Locale

/** Catalog boundary. Replace the mock source here after the REST API is agreed. */
class WordRepository {
    val words get() = MockData.words
    val topics get() = MockData.topics

    fun find(id: String?): Word? = words.firstOrNull { it.id == id }

    fun search(query: String, filter: String, saved: Set<String>): List<Word> {
        val keyword = normalize(query.trim())
        return words.filter { word ->
            val inGroup = when (filter) {
                "all" -> true
                "saved" -> word.id in saved
                else -> word.topic == filter
            }
            inGroup && (normalize(word.english).contains(keyword) || normalize(word.meaning).contains(keyword))
        }
    }

    private fun normalize(value: String): String = Normalizer.normalize(value, Normalizer.Form.NFD)
        .replace("\\p{M}+".toRegex(), "").lowercase(Locale.ROOT).replace('đ', 'd')
}
