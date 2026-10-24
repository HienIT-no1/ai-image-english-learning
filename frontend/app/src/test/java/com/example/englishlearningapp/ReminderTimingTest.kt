package com.example.englishlearningapp

import com.example.englishlearningapp.notifications.ReminderTiming
import org.junit.Assert.*
import org.junit.Test
import java.util.Calendar
import java.util.TimeZone

class ReminderTimingTest {
    private val zone=TimeZone.getTimeZone("Asia/Ho_Chi_Minh")
    private fun time(hour: Int,minute: Int)=Calendar.getInstance(zone).apply {
        clear();set(2026,9,24,hour,minute,0)
    }.timeInMillis
    @Test fun upcomingReminderIsToday() { assertEquals(30*60*1000L,ReminderTiming.nextDelay(time(19,30),1200,zone)) }
    @Test fun pastReminderMovesToTomorrow() { assertEquals(23*60*60*1000L,ReminderTiming.nextDelay(time(21,0),1200,zone)) }
    @Test fun midnightAndExactTimeDoNotLoopImmediately() {
        assertEquals(60*1000L,ReminderTiming.nextDelay(time(23,59),0,zone))
        assertEquals(24*60*60*1000L,ReminderTiming.nextDelay(time(20,0),1200,zone))
    }
    @Test fun scheduleUsesChosenTimezone() {
        assertEquals(7*60*60*1000L,ReminderTiming.nextDelay(time(20,0),1200,TimeZone.getTimeZone("UTC")))
    }
}
