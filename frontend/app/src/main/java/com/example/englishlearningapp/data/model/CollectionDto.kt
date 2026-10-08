package com.example.englishlearningapp.data.model
import com.google.gson.annotations.SerializedName

data class CollectionDto(
    @SerializedName("collection_id") val collectionId: Long,
    @SerializedName("collection_name") val collectionName: String,
    val words: List<VocabularyDto>
)
