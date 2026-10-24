package com.example.englishlearningapp.notifications

import java.util.Calendar
import java.util.TimeZone

object ReminderTiming {
    fun nextDelay(nowMillis: Long,minutes: Int,zone: TimeZone=TimeZone.getDefault()): Long {
        val target=Calendar.getInstance(zone).apply {
            timeInMillis=nowMillis;set(Calendar.HOUR_OF_DAY,minutes/60);set(Calendar.MINUTE,minutes%60)
            set(Calendar.SECOND,0);set(Calendar.MILLISECOND,0)
        }
        if(target.timeInMillis<=nowMillis) target.add(Calendar.DAY_OF_YEAR,1)
        return target.timeInMillis-nowMillis
    }
}
