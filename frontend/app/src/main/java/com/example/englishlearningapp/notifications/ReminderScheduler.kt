package com.example.englishlearningapp.notifications

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import androidx.work.*
import com.example.englishlearningapp.data.local.LearningStore
import java.util.concurrent.TimeUnit

object ReminderScheduler {
    const val NAME="daily-study-reminder"
    fun sync(context: Context,reset: Boolean=false) {
        val app=context.applicationContext
        val store=LearningStore(app)
        ReminderNotifier.channels(app)
        if(!store.signedIn || store.userId==null || store.token.isNullOrBlank() || !store.reminders || !ReminderNotifier.allowed(app)) {
            WorkManager.getInstance(app).cancelUniqueWork(NAME)
            app.getSharedPreferences("reminder_schedule",0).edit().clear().apply();return
        }
        val prefs=app.getSharedPreferences("reminder_schedule",0)
        val fingerprint="${store.userId}:${store.reminderMinutes}"
        val changed=reset || prefs.getString("fingerprint",null)!=fingerprint
        val work=PeriodicWorkRequestBuilder<ReminderWorker>(24,TimeUnit.HOURS)
            .setInitialDelay(ReminderTiming.nextDelay(System.currentTimeMillis(),store.reminderMinutes),TimeUnit.MILLISECONDS)
            .setInputData(workDataOf("user" to store.userId!!,"minutes" to store.reminderMinutes))
            .addTag("study-reminders").build()
        WorkManager.getInstance(app).enqueueUniquePeriodicWork(NAME,
            if(changed) ExistingPeriodicWorkPolicy.CANCEL_AND_REENQUEUE else ExistingPeriodicWorkPolicy.KEEP,work)
        prefs.edit().putString("fingerprint",fingerprint).apply()
    }
    fun cancel(context: Context) {
        WorkManager.getInstance(context.applicationContext).cancelUniqueWork(NAME)
        context.getSharedPreferences("reminder_schedule",0).edit().clear().apply()
        NotificationManagerCompat.from(context).cancelAll()
    }
    fun preview(context: Context) {
        val user=LearningStore(context).userId ?: return
        val work=OneTimeWorkRequestBuilder<ReminderWorker>().setInputData(workDataOf("user" to user,"preview" to true)).build()
        WorkManager.getInstance(context).enqueue(work)
    }
}

class ReminderClockReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context,intent: Intent) { ReminderScheduler.sync(context,reset=true) }
}
