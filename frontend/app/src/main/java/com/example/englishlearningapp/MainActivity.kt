package com.example.englishlearningapp

import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.View
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.navigation.NavOptions
import androidx.navigation.fragment.NavHostFragment
import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.repository.WordRepository
import com.example.englishlearningapp.data.repository.QuizRepository
import com.google.android.material.bottomnavigation.BottomNavigationView
import java.util.Locale

class MainActivity : AppCompatActivity() {
    lateinit var store: LearningStore
        private set
    private var tts: TextToSpeech? = null
    private var speechReady = false
    val words = WordRepository()
    val quizzes = QuizRepository(words)
    override fun onCreate(savedInstanceState: Bundle?) {
        store = LearningStore(this)
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime())
            v.setPadding(bars.left,bars.top,bars.right,bars.bottom)
            insets
        }
        val nav = (supportFragmentManager.findFragmentById(R.id.nav_host) as NavHostFragment).navController
        if (savedInstanceState == null && store.signedIn) {
            nav.navigate(R.id.homeFragment, null, NavOptions.Builder().setPopUpTo(R.id.loginFragment,true).build())
        }
        val bottom = findViewById<BottomNavigationView>(R.id.bottom_nav)
        val tabs = setOf(R.id.homeFragment,R.id.cameraFragment,R.id.wordsFragment,R.id.practiceFragment,R.id.profileFragment)
        bottom.setOnItemSelectedListener { item ->
            if (nav.currentDestination?.id != item.itemId) {
                if (item.itemId == R.id.homeFragment && nav.popBackStack(R.id.homeFragment,false)) {
                    return@setOnItemSelectedListener true
                }
                nav.navigate(item.itemId, null, NavOptions.Builder().setLaunchSingleTop(true)
                    .setPopUpTo(R.id.homeFragment,false).build())
            }
            true
        }
        bottom.setOnItemReselectedListener { }
        nav.addOnDestinationChangedListener { _, destination, args ->
            val isTopicList = destination.id == R.id.wordsFragment && args?.getString("topic") != null
            bottom.visibility = if (destination.id in tabs && !isTopicList) View.VISIBLE else View.GONE
            if (destination.id in tabs) bottom.menu.findItem(destination.id).isChecked = true
        }
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val result = tts?.setLanguage(Locale.ENGLISH)
                speechReady = result != null && result >= TextToSpeech.LANG_AVAILABLE
            }
        }
    }
    fun speak(text: String) {
        if (speechReady) {
            val result = tts?.speak(text,TextToSpeech.QUEUE_FLUSH,null,"word")
            if (result == TextToSpeech.ERROR) android.widget.Toast.makeText(this,"Không phát được âm thanh. Hãy thử lại.",android.widget.Toast.LENGTH_SHORT).show()
        }
        else android.widget.Toast.makeText(this,"Chưa có giọng đọc tiếng Anh. Hãy kiểm tra cài đặt Text-to-Speech trên máy.",android.widget.Toast.LENGTH_LONG).show()
    }
    override fun onStop() { tts?.stop(); super.onStop() }
    override fun onDestroy() { tts?.stop(); tts?.shutdown(); super.onDestroy() }
}
