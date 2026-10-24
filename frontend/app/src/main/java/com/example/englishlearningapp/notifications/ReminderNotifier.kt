package com.example.englishlearningapp.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.englishlearningapp.MainActivity
import com.example.englishlearningapp.R

object ReminderNotifier {
    const val CHANNEL="study_reminders"
    const val ID=2401
    fun channels(context: Context) {
        if(Build.VERSION.SDK_INT>=26) context.getSystemService(NotificationManager::class.java)
            .createNotificationChannel(NotificationChannel(CHANNEL,"Nhắc ôn tập",NotificationManager.IMPORTANCE_DEFAULT).apply {
                description="Nhắc học theo giờ bạn chọn và từ vựng đến hạn."
            })
    }
    fun allowed(context: Context): Boolean {
        if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(context,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) return false
        if(!NotificationManagerCompat.from(context).areNotificationsEnabled()) return false
        return Build.VERSION.SDK_INT<26 || context.getSystemService(NotificationManager::class.java).getNotificationChannel(CHANNEL)?.importance!=NotificationManager.IMPORTANCE_NONE
    }
    fun show(context: Context,userId: Long,title: String,body: String,date: String,notificationId: Long=0,preview: Boolean=false): Boolean {
        channels(context)
        if(!allowed(context)) return false
        val intent=Intent(context,MainActivity::class.java).apply {
            flags=Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            data=Uri.parse("lenslearn://review/$userId/$date")
            putExtra("notification_user",userId);putExtra("notification_id",notificationId)
            if(!preview) putExtra("notification_date",date)
        }
        val pending=PendingIntent.getActivity(context,0,intent,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification=NotificationCompat.Builder(context,CHANNEL)
            .setSmallIcon(R.drawable.ic_notification).setContentTitle(title).setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body)).setColor(0xFF1B63AC.toInt())
            .setContentIntent(pending).setAutoCancel(true).setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_REMINDER).setVisibility(NotificationCompat.VISIBILITY_PRIVATE).build()
        return try { NotificationManagerCompat.from(context).notify(if(preview) ID+1 else ID,notification);true }
        catch(_: SecurityException) { false }
    }
}
