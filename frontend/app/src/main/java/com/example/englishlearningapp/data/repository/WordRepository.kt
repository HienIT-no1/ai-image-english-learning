package com.example.englishlearningapp.data.repository

import android.util.Log
import com.example.englishlearningapp.data.mapper.toWord
import com.example.englishlearningapp.data.model.Topic
import com.example.englishlearningapp.data.model.Word
import com.example.englishlearningapp.data.mock.MockData
import com.example.englishlearningapp.data.remote.ApiService
import java.text.Normalizer
import java.util.Locale

class WordRepository(
    private val api: ApiService? = null
) {

    private var cachedWords: List<Word> = MockData.words

    val words: List<Word>
        get() = cachedWords

    val topics: List<Topic>
        get() = MockData.topics

    suspend fun loadFromApi(): Boolean {
        val service = api ?: return false

        return try {
            val response = service.getVocabularies()

            Log.d(
                "VOCAB_API",
                "HTTP status: ${response.code()}"
            )

            if (!response.isSuccessful) {
                Log.e(
                    "VOCAB_API",
                    "API error: ${response.code()} ${response.message()}"
                )

                Log.e(
                    "VOCAB_API",
                    "Error body: ${response.errorBody()?.string()}"
                )

                false
            } else {
                val vocabularyDtos = response.body().orEmpty()

                cachedWords = vocabularyDtos.map { dto ->
                    dto.toWord()
                }

                Log.d(
                    "VOCAB_API",
                    "Loaded ${cachedWords.size} vocabularies from API"
                )

                true
            }
        } catch (e: Exception) {

            Log.e(
                "VOCAB_API",
                "Exception while loading vocabularies",
                e
            )

            false
        }
    }

    fun find(id: String?): Word? =
        words.firstOrNull { it.id == id }

    fun search(
        query: String,
        filter: String,
        saved: Set<String>
    ): List<Word> {

        val keyword = normalize(query.trim())

        return words.filter { word ->

            val inGroup = when (filter) {
                "all" -> true
                "saved" -> word.id in saved
                else -> word.topic == filter
            }

            inGroup && (
                    normalize(word.english).contains(keyword) ||
                            normalize(word.meaning).contains(keyword)
                    )
        }
    }

    private fun normalize(value: String): String =
        Normalizer.normalize(
            value,
            Normalizer.Form.NFD
        )
            .replace("\\p{M}+".toRegex(), "")
            .lowercase(Locale.ROOT)
            .replace('đ', 'd')
}