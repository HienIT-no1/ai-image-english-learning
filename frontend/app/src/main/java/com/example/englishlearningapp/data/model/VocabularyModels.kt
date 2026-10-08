package com.example.englishlearningapp.data.model

import com.google.gson.annotations.SerializedName


data class VocabularyMeaningDto(
    @SerializedName("meaning_id")
    val meaningId: Long,

    @SerializedName("meaning_vi")
    val meaningVi: String,

    @SerializedName("definition_en")
    val definitionEn: String?
)


data class VocabularyExampleDto(
    @SerializedName("example_id")
    val exampleId: Long,

    @SerializedName("sentence_en")
    val sentenceEn: String,

    @SerializedName("sentence_vi")
    val sentenceVi: String?
)


data class VocabularyRelationDto(
    @SerializedName("relation_id")
    val relationId: Long,

    @SerializedName("relation_type")
    val relationType: String,

    @SerializedName("related_vocabulary_id")
    val relatedVocabularyId: Long?,

    @SerializedName("related_text")
    val relatedText: String?
)


data class VocabularyDto(
    @SerializedName("vocabulary_id")
    val vocabularyId: Long,

    val word: String,

    val ipa: String?,

    @SerializedName("part_of_speech")
    val partOfSpeech: String?,

    val level: String?,

    @SerializedName("audio_url")
    val audioUrl: String?,

    val meanings: List<VocabularyMeaningDto>,

    val examples: List<VocabularyExampleDto>,

    val relations: List<VocabularyRelationDto>,
    val topics: List<TopicDto> = emptyList()
)