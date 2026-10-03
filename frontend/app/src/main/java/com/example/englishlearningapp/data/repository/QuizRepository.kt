package com.example.englishlearningapp.data.repository

import com.example.englishlearningapp.data.model.QuizQuestion
import kotlin.random.Random

/** Creates local questions from the same catalog that vocabulary screens display. */
class QuizRepository(private val catalog: WordRepository) {
    fun createSession(saved: Set<String>, count: Int = 8): List<String> {
        val savedIds = catalog.words.filter { it.id in saved }.map { it.id }.shuffled()
        val otherIds = catalog.words.filter { it.id !in saved }.map { it.id }.shuffled()
        return (savedIds + otherIds).take(count.coerceAtLeast(0))
    }

    fun question(wordId: String, position: Int): QuizQuestion {
        // Seeded choices stay identical after rotation or activity recreation.
        val random = Random(wordId.hashCode() xor position)
        val distractors = catalog.words.filter { it.id != wordId }.shuffled(random).take(3).map { it.id }
        return QuizQuestion(wordId, (distractors + wordId).shuffled(random))
    }
}
