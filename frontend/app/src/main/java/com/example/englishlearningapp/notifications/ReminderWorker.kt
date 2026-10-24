package com.example.englishlearningapp.notifications

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.model.ReminderRequest
import com.example.englishlearningapp.data.remote.*
import kotlinx.coroutines.CancellationException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class ReminderWorker(context: Context,parameters: WorkerParameters) : CoroutineWorker(context,parameters) {
    override suspend fun doWork(): Result {
        val store=LearningStore(applicationContext)
        val user=inputData.getLong("user",0L)
        val token=store.token ?: return Result.success()
        fun current()=store.signedIn && store.userId==user && store.token==token
        if(!current() || !ReminderNotifier.allowed(applicationContext)) return Result.success()
        val date=SimpleDateFormat("yyyy-MM-dd",Locale.US).format(Date())
        val preview=inputData.getBoolean("preview",false)
        if(preview) {
            if(current()) ReminderNotifier.show(applicationContext,user,"Thông báo thử • LensLearn",
                "Nhắc ôn tập đã sẵn sàng. Bấm để xem từ vựng đến hạn.",date,preview=true)
            return Result.success()
        }
        if(!store.reminders || store.lastReminderDate==date) return Result.success()
        var title="Đến giờ ôn tập cùng LensLearn"
        var body="Dành vài phút ôn từ vựng và duy trì thói quen học hôm nay nhé!"
        var notificationId=0L
        var online=false
        try {
            val api=RetrofitClient.create(store)
            val profile=api.me("Bearer $token").requireData()
            if(!current() || profile.userId!=user) return Result.success()
            store.activateUser(profile)
            if(!profile.remindersEnabled || profile.reminderMinutes!=inputData.getInt("minutes",1200)) return Result.success()
            val progress=api.getLearning("Bearer $token").requireData()
            if(!current()) return Result.success()
            store.applyLearning(progress)
            if(progress.dueCount==0 && progress.todayCount>=progress.dailyGoal) return Result.success()
            val item=api.recordReminder(ReminderRequest(date),"Bearer $token").requireData()
            if(!current()) return Result.success()
            title=item.title;body=item.body;notificationId=item.notificationId;online=true
        } catch(e: CancellationException) { throw e }
        catch(e: ApiException) {
            if(e.status==401 || e.status==409) {
                if(current()) ReminderScheduler.cancel(applicationContext)
                return Result.success()
            }
        } catch(_: Exception) { /* Offline: keep a local reminder and sync its date when the app reconnects. */ }
        if(!current() || !store.reminders) return Result.success()
        if(!online && store.summaryDate==date && store.dueCount==0 && store.todayCount>=store.goal) return Result.success()
        if(ReminderNotifier.show(applicationContext,user,title,body,date,notificationId)) {
            if(current()) {
                store.lastReminderDate=date
                if(!online) store.pendingReminderDates=(store.pendingReminderDates+date).sorted().takeLast(7).toSet()
            }
        }
        return Result.success()
    }
}
