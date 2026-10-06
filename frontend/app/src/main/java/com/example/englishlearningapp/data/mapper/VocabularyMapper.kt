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

        topic = "all",

        symbol = "📘"
    )
}