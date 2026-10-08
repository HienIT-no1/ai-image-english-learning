package com.example.englishlearningapp.data.mapper

import com.example.englishlearningapp.data.model.VocabularyDto
import com.example.englishlearningapp.data.model.Word


fun VocabularyDto.toWord(): Word {

    val firstMeaning = meanings.firstOrNull()
    val firstExample = examples.firstOrNull()

    return Word(
        id = vocabularyId.toString(),

        english = word,

        ipa = ipa ?: "",

        meaning = firstMeaning?.meaningVi ?: "",

        example = firstExample?.sentenceEn ?: "",

        translation = firstExample?.sentenceVi ?: "",

        topic = topics.firstOrNull()?.topicId?.toString() ?: "all",

        symbol = mapOf("cat" to "🐱","dog" to "🐶","apple" to "🍎","car" to "🚗","computer" to "💻","bank" to "🏦","rain" to "🌧️")[word.lowercase()] ?: topics.firstOrNull()?.symbol ?: "📘",
        topicIds = topics.map { it.topicId.toString() }
    )
}