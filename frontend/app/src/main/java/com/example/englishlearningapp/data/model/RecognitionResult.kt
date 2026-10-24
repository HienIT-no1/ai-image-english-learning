package com.example.englishlearningapp.data.model

import com.google.gson.annotations.SerializedName

data class BoundingBoxDto(
    @SerializedName("x1") val x1: Float,
    @SerializedName("y1") val y1: Float,
    @SerializedName("x2") val x2: Float,
    @SerializedName("y2") val y2: Float
)

data class VocabularyDetailDto(
    @SerializedName("vocabulary_id") val vocabularyId: Long?,
    @SerializedName("word") val word: String,
    @SerializedName("ipa") val ipa: String?,
    @SerializedName("part_of_speech") val partOfSpeech: String?,
    @SerializedName("meaning_vi") val meaningVi: String?,
    @SerializedName("audio_url") val audioUrl: String?
)

data class DetectionItemDto(
    @SerializedName("label") val label: String,
    @SerializedName("confidence") val confidence: Float,
    @SerializedName("box") val box: BoundingBoxDto,
    @SerializedName("vocabulary") val vocabulary: VocabularyDetailDto
)

data class CaptureDetectResponseDto(
    @SerializedName("image_id") val imageId: Long?,
    @SerializedName("image_url") val imageUrl: String,
    @SerializedName("image_width") val imageWidth: Int,
    @SerializedName("image_height") val imageHeight: Int,
    @SerializedName("count") val count: Int,
    @SerializedName("detections") val detections: List<DetectionItemDto>
)

data class RealtimeDetectResponseDto(
    @SerializedName("image_width") val imageWidth: Int,
    @SerializedName("image_height") val imageHeight: Int,
    @SerializedName("count") val count: Int,
    @SerializedName("detections") val detections: List<DetectionItemDto>
)