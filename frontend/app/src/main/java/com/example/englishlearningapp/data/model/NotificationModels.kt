package com.example.englishlearningapp.data.model
import com.google.gson.annotations.SerializedName

data class ReminderRequest(@SerializedName("occurrence_date") val occurrenceDate: String)
data class NotificationDto(
    @SerializedName("notification_id") val notificationId: Long,
    @SerializedName("occurrence_date") val occurrenceDate: String,
    val title: String,val body: String,
    @SerializedName("created_at") val createdAt: String,
    @SerializedName("read_at") val readAt: String?
)
data class NotificationPageDto(val items: List<NotificationDto>,@SerializedName("unread_count") val unreadCount: Int)
