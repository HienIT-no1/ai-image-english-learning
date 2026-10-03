package com.example.englishlearningapp

import android.content.Context
import android.view.View
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.espresso.ViewAction
import androidx.test.espresso.UiController
import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.action.ViewActions.scrollTo
import androidx.test.espresso.action.ViewActions.replaceText
import androidx.test.espresso.action.ViewActions.closeSoftKeyboard
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.isDisplayed
import androidx.test.espresso.matcher.ViewMatchers.withId
import androidx.test.espresso.matcher.ViewMatchers.withText
import androidx.test.espresso.matcher.ViewMatchers.withContentDescription
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.mock.MockData
import com.example.englishlearningapp.data.repository.WordRepository
import com.example.englishlearningapp.data.repository.QuizRepository
import com.example.englishlearningapp.ui.Palette
import com.google.android.material.button.MaterialButton
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.Before
import org.junit.After
import org.junit.runner.RunWith

/** Regression test for navigation, persisted vocabulary and quiz state across recreation. */
@RunWith(AndroidJUnit4::class)
class LearningFlowTest {
    private val context get()=InstrumentationRegistry.getInstrumentation().targetContext
    private var scenario: ActivityScenario<MainActivity>?=null
    private var previousData: Map<String,Any?> = emptyMap()

    @Before fun preserveProfile() {
        val prefs=context.getSharedPreferences("learning_demo",Context.MODE_PRIVATE)
        previousData=prefs.all.mapValues { (_,value) -> if(value is Set<*>) value.toSet() else value }
        prefs.edit().clear().commit()
    }

    @After fun restoreProfile() {
        scenario?.close()
        val edit=context.getSharedPreferences("learning_demo",Context.MODE_PRIVATE).edit().clear()
        previousData.forEach { (key,value) ->
            when(value) {
                is String -> edit.putString(key,value)
                is Boolean -> edit.putBoolean(key,value)
                is Int -> edit.putInt(key,value)
                is Long -> edit.putLong(key,value)
                is Float -> edit.putFloat(key,value)
                is Set<*> -> edit.putStringSet(key,value.filterIsInstance<String>().toSet())
            }
        }
        assertTrue("Restore original local profile",edit.commit())
    }

    private fun tap(label: String) { onView(withText(label)).perform(scrollTo(),click()) }
    private fun currentQuestion(): String {
        var id=""
        onView(withId(R.id.quiz_prompt)).perform(object : ViewAction {
            override fun getConstraints()=withId(R.id.quiz_prompt)
            override fun getDescription()="Read current question identity"
            override fun perform(uiController: UiController,view: View) { id=view.tag as String }
        })
        return id
    }
    private fun launchSignedIn() {
        LearningStore(context).signedIn=true
        scenario=ActivityScenario.launch(MainActivity::class.java)
    }

    @Test fun demoLearningJourney() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val context=instrumentation.targetContext
        scenario=ActivityScenario.launch(MainActivity::class.java)
        instrumentation.waitForIdleSync()
        tap("Khám phá bằng hồ sơ mẫu")
        tap("A2 • Cơ bản")
        tap("Bắt đầu khám phá  →")
        onView(withId(R.id.wordsFragment)).perform(click())
        tap("Apple")
        tap("★  Đã lưu • Bấm để bỏ lưu")
        assertTrue("Unsave must persist", "apple" !in LearningStore(context).saved)
        tap("＋  Lưu vào bộ sưu tập")
        assertTrue("Save must persist", "apple" in LearningStore(context).saved)
        androidx.test.espresso.Espresso.pressBack()
        onView(withId(R.id.practiceFragment)).perform(click())
        tap("Bắt đầu Flashcard  →")
        tap("Lật thẻ")
        tap("✓  Đã nhớ")
        assertEquals(1,LearningStore(context).reviews)
        assertTrue(LearningStore(context).mastered.isNotEmpty())
        androidx.test.espresso.Espresso.pressBack()
        tap("Nhìn ảnh chọn từ")
        repeat(8) { index ->
            var questionId=""
            onView(withId(R.id.quiz_prompt)).perform(object : ViewAction {
                override fun getConstraints() = withId(R.id.quiz_prompt)
                override fun getDescription() = "Read the current question identity"
                override fun perform(uiController: UiController, view: View) { questionId=view.tag as String }
            })
            tap(MockData.words.first { it.id==questionId }.english)
            if(index==0) {
                scenario!!.recreate()
                instrumentation.waitForIdleSync()
                onView(withText("✓  Chính xác!")).check(matches(isDisplayed()))
            }
            tap(if(index==7) "Xem kết quả  →" else "Câu tiếp theo  →")
        }
        onView(withText("8 / 8")).check(matches(isDisplayed()))
        assertEquals(1,LearningStore(context).quizRuns)
        assertEquals(8,LearningStore(context).quizCorrect)
        assertEquals(8,LearningStore(context).quizTotal)
        assertEquals(9,LearningStore(context).reviews)
        assertEquals(1,LearningStore(context).streak)
        assertEquals("A2 • Cơ bản",LearningStore(context).level)
    }

    @Test fun wrongAnswerIsRedAndCanBeSavedFromResult() {
        launchSignedIn()
        onView(withId(R.id.practiceFragment)).perform(click())
        tap("Nhìn ảnh chọn từ")
        val catalog=WordRepository()
        val correctId=currentQuestion()
        val wrongId=QuizRepository(catalog).question(correctId,0).optionIds.first { it!=correctId }
        val wrongWord=catalog.find(wrongId)!!
        tap(wrongWord.english)
        fun assertAnswerColors() {
            onView(withContentDescription("${wrongWord.english}. Bạn đã chọn sai")).check { view,_ ->
                val button=view as MaterialButton
                assertEquals(Palette.red,button.backgroundTintList!!.defaultColor)
                assertEquals(Palette.white,button.currentTextColor)
                assertTrue(!button.isClickable)
            }
            onView(withContentDescription("${catalog.find(correctId)!!.english}. Đáp án đúng")).check { view,_ ->
                assertEquals(Palette.green,(view as MaterialButton).backgroundTintList!!.defaultColor)
            }
        }
        assertAnswerColors()
        scenario!!.recreate()
        assertAnswerColors()
        tap("Câu tiếp theo  →")
        repeat(7) { i ->
            tap(catalog.find(currentQuestion())!!.english)
            tap(if(i==6) "Xem kết quả  →" else "Câu tiếp theo  →")
        }
        onView(withText("7 / 8")).check(matches(isDisplayed()))
        assertEquals(1,LearningStore(context).quizRuns)
        val wasSaved=correctId in LearningStore(context).saved
        tap(if(wasSaved) "✓  Đã lưu • Bỏ lưu" else "＋  Lưu vào bộ sưu tập")
        assertEquals(!wasSaved,correctId in LearningStore(context).saved)
        onView(withText(catalog.find(correctId)!!.english)).check(matches(isDisplayed()))
        tap("Ôn các từ trả lời sai")
        tap("Lật thẻ")
        tap("✓  Đã nhớ")
        onView(withText("Một bước tiến thật tốt!")).check(matches(isDisplayed()))
        assertEquals(1,LearningStore(context).quizRuns)
    }

    @Test fun settingsDraftSurvivesRecreationAndOnlySavesOnRequest() {
        launchSignedIn()
        onView(withId(R.id.profileFragment)).perform(click())
        tap("Cài đặt")
        onView(withId(R.id.input_settings_name)).perform(scrollTo(),replaceText("Tên chưa lưu"),closeSoftKeyboard())
        tap("A1 • Mới bắt đầu")
        onView(withText("A2 • Cơ bản")).perform(click())
        scenario!!.recreate()
        onView(withId(R.id.input_settings_name)).check(matches(withText("Tên chưa lưu")))
        assertEquals("Bạn học",LearningStore(context).name)
        assertEquals("A1 • Mới bắt đầu",LearningStore(context).level)
        androidx.test.espresso.Espresso.pressBack()
        tap("Cài đặt")
        onView(withId(R.id.input_settings_name)).check(matches(withText("Bạn học")))
        onView(withId(R.id.input_settings_name)).perform(scrollTo(),replaceText("Tên đã lưu"),closeSoftKeyboard())
        tap("Lưu thay đổi")
        assertEquals("Tên đã lưu",LearningStore(context).name)
        onView(withId(R.id.wordsFragment)).perform(click())
        tap("Tất cả")
        onView(withId(R.id.input_word_search)).perform(scrollTo(),replaceText("ca phe"),closeSoftKeyboard())
        onView(withText("Coffee")).check(matches(isDisplayed()))
    }
}
