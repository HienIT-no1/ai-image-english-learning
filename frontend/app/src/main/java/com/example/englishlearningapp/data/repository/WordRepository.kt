package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.mapper.toWord
import com.example.englishlearningapp.data.model.Topic
import com.example.englishlearningapp.data.model.Word
import com.example.englishlearningapp.data.mock.MockData
import com.example.englishlearningapp.data.remote.ApiService
import kotlinx.coroutines.CancellationException
import retrofit2.Response
import java.text.Normalizer
import java.util.Locale

class WordRepository(private val api: ApiService? = null) {
    private var cachedWords: List<Word> = if (api == null) MockData.words else emptyList()
    private var cachedTopics: List<Topic> = if (api == null) MockData.topics else emptyList()
    private var savedWords: List<Word> = emptyList()
    fun setSavedWords(value: List<Word>) { savedWords = value }
    fun remember(data: List<com.example.englishlearningapp.data.model.VocabularyDto>) {
        cachedWords=(cachedWords+data.map { it.toWord() }).distinctBy { it.id }
    }
    fun clearAccountData() { savedWords = emptyList() }
    private val topicWords = mutableMapOf<String, List<Word>>()
    val words: List<Word> get() = (cachedWords + savedWords).distinctBy { it.id }
    val topics: List<Topic> get() = cachedTopics

    private fun <T> Response<List<T>>.requiredBody(): List<T> {
        if (!isSuccessful) error("Máy chủ trả lỗi HTTP ${code()}. Hãy thử lại.")
        return body() ?: error("Máy chủ chưa trả dữ liệu hợp lệ.")
    }
    suspend fun loadCatalog(filter: String): Result<Unit> = try {
        val service = api ?: error("Chưa cấu hình kết nối máy chủ.")
        val fetchedTopics = service.getTopics().requiredBody().map {
            Topic(it.topicId.toString(), it.name, it.symbol, it.vocabularyCount)
        }
        val fetchedWords = (if (filter == "all" || filter == "saved") service.getVocabularies()
            else service.getTopicVocabularies(filter.toLong())).requiredBody().map { it.toWord() }
        cachedTopics = fetchedTopics
        if (filter == "all" || filter == "saved") {
            cachedWords = fetchedWords
            topicWords.clear()
        } else {
            topicWords[filter] = fetchedWords
            cachedWords = (cachedWords.filter { filter !in it.topicIds } + fetchedWords).distinctBy { it.id }
        }
        Result.success(Unit)
    } catch (e: CancellationException) { throw e }
    catch (e: Exception) { Result.failure(e) }

    suspend fun loadTopics(): Result<Unit> = try {
        val service = api ?: error("Chưa cấu hình kết nối máy chủ.")
        cachedTopics = service.getTopics().requiredBody().map {
            Topic(it.topicId.toString(), it.name, it.symbol, it.vocabularyCount)
        }
        Result.success(Unit)
    } catch (e: CancellationException) { throw e }
    catch (e: Exception) { Result.failure(e) }

    suspend fun loadFromApi(): Boolean = loadCatalog("all").isSuccess
    fun find(id: String?): Word? = words.firstOrNull { it.id == id }
    fun search(query: String, filter: String, saved: Set<String>): List<Word> {
        val keyword = normalize(query.trim())
        val source = if (filter == "saved" && api != null) savedWords else topicWords[filter] ?: words
        return source.filter { word ->
            val inGroup = when (filter) {
                "all" -> true
                "saved" -> word.id in saved
                else -> filter in word.topicIds
            }
            inGroup && (normalize(word.english).contains(keyword) || normalize(word.meaning).contains(keyword))
        }
    }
    private fun normalize(value: String): String = Normalizer.normalize(value, Normalizer.Form.NFD)
        .replace("\\p{M}+".toRegex(), "").lowercase(Locale.ROOT).replace('đ', 'd')
}
