package com.example.englishlearningapp

import android.content.Context
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.*
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.After
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

/** Session-entry regressions; API/database flows are tested by backend integration and emulator checks. */
@RunWith(AndroidJUnit4::class)
class LearningFlowTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private var previous: Map<String,Any?> = emptyMap()
    private var scenario: ActivityScenario<MainActivity>? = null
    @Before fun preserveSession() {
        val prefs=context.getSharedPreferences("learning_demo",Context.MODE_PRIVATE)
        previous=prefs.all.mapValues { (_,v) -> if(v is Set<*>) v.toSet() else v }
        prefs.edit().clear().commit()
    }
    @After fun restoreSession() {
        scenario?.close()
        val editor=context.getSharedPreferences("learning_demo",Context.MODE_PRIVATE).edit().clear()
        previous.forEach { (key,value) -> when(value) {
            is String -> editor.putString(key,value)
            is Boolean -> editor.putBoolean(key,value)
            is Int -> editor.putInt(key,value)
            is Long -> editor.putLong(key,value)
            is Float -> editor.putFloat(key,value)
            is Set<*> -> editor.putStringSet(key,value.filterIsInstance<String>().toSet())
        } }
        editor.commit()
    }
    private fun awaitLogin() {
        repeat(30) {
            try { onView(withId(R.id.input_auth_name)).check(matches(isDisplayed()));return }
            catch (_: AssertionError) { Thread.sleep(100) }
            catch (_: androidx.test.espresso.NoMatchingViewException) { Thread.sleep(100) }
        }
        onView(withId(R.id.input_auth_name)).check(matches(isDisplayed()))
    }
    @Test fun noTokenRequiresLoginAfterRecreation() {
        scenario=ActivityScenario.launch(MainActivity::class.java);awaitLogin()
        onView(withId(R.id.bottom_nav)).check(matches(withEffectiveVisibility(Visibility.GONE)))
        scenario!!.recreate();awaitLogin()
        onView(withText("Đăng nhập  →")).check(matches(isDisplayed()))
    }
    @Test fun invalidUsernameIsRejectedBeforeRequest() {
        scenario=ActivityScenario.launch(MainActivity::class.java);awaitLogin()
        onView(withId(R.id.input_auth_name)).perform(replaceText("a"),closeSoftKeyboard())
        onView(withText("Đăng nhập  →")).perform(scrollTo(),click())
        onView(withId(R.id.input_auth_name)).check(matches(hasErrorText("Tên đăng nhập từ 3 đến 50 ký tự")))
    }
}
