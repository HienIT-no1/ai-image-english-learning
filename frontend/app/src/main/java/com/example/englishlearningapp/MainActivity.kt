package com.example.englishlearningapp

import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.View
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavOptions
import androidx.navigation.fragment.NavHostFragment
import com.example.englishlearningapp.data.local.LearningStore
import com.example.englishlearningapp.data.remote.RetrofitClient
import com.example.englishlearningapp.data.repository.AuthRepository
import com.example.englishlearningapp.data.repository.CollectionRepository
import com.example.englishlearningapp.data.repository.LearningRepository
import com.example.englishlearningapp.data.remote.apiResult
import com.example.englishlearningapp.data.repository.QuizRepository
import com.example.englishlearningapp.data.repository.WordRepository
import com.google.android.material.bottomnavigation.BottomNavigationView
import kotlinx.coroutines.launch
import java.util.Locale

class MainActivity : AppCompatActivity() {
    lateinit var store: LearningStore
        private set
    lateinit var words: WordRepository
        private set
    lateinit var collections: CollectionRepository
        private set
    lateinit var auth: AuthRepository
        private set
    lateinit var learning: LearningRepository
        private set
    lateinit var quizzes: QuizRepository
        private set
    private var tts: TextToSpeech? = null
    private var speechReady = false
    private var checkingSession = false
    private val nav get() = (supportFragmentManager.findFragmentById(R.id.nav_host) as NavHostFragment).navController

    override fun onCreate(savedInstanceState: Bundle?) {
        store = LearningStore(this)
        super.onCreate(savedInstanceState)
        val api = RetrofitClient.create(store) { rejectedToken ->
            runOnUiThread {
                // A late response from account A must never sign account B out.
                if (store.token == rejectedToken) {
                    auth.logout()
                    Toast.makeText(this@MainActivity,"Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại.",Toast.LENGTH_LONG).show()
                    openLogin()
                }
            }
        }
        words = WordRepository(api)
        collections = CollectionRepository(api,store,words)
        learning = LearningRepository(api,store)
        quizzes = QuizRepository(api,store,words,learning)
        auth = AuthRepository(api,store) { collections.reset(); learning.reset() }
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.ime())
            view.setPadding(bars.left,bars.top,bars.right,bars.bottom); insets
        }
        val bottom = findViewById<BottomNavigationView>(R.id.bottom_nav)
        val tabs = setOf(R.id.homeFragment,R.id.cameraFragment,R.id.wordsFragment,R.id.practiceFragment,R.id.profileFragment)
        bottom.setOnItemSelectedListener { item ->
            if (!store.signedIn || store.token.isNullOrBlank()) { openLogin(); false }
            else {
                if (nav.currentDestination?.id != item.itemId) {
                    if (item.itemId != R.id.homeFragment || !nav.popBackStack(R.id.homeFragment,false)) {
                        nav.navigate(item.itemId,null,NavOptions.Builder().setLaunchSingleTop(true)
                            .setPopUpTo(R.id.homeFragment,false).build())
                    }
                }; true
            }
        }
        bottom.setOnItemReselectedListener { }
        nav.addOnDestinationChangedListener { _, destination, args ->
            val topicList = destination.id==R.id.wordsFragment && args?.getString("topic")!=null
            bottom.visibility = if (destination.id in tabs && !topicList) View.VISIBLE else View.GONE
            if (destination.id in tabs) bottom.menu.findItem(destination.id).isChecked=true
        }
        // A restored navigation stack also passes through the session check before showing account data.
        if (savedInstanceState != null) {
            nav.navigate(R.id.sessionFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
        tts = TextToSpeech(this) { status ->
            if (status==TextToSpeech.SUCCESS) speechReady=(tts?.setLanguage(Locale.ENGLISH) ?: -1)>=TextToSpeech.LANG_AVAILABLE
        }
    }
    suspend fun loadAccountData(): Result<Unit> = apiResult {
        collections.load().getOrThrow()
        quizzes.syncPending().getOrThrow()
        learning.load().getOrThrow()
    }
    fun openLogin() {
        if (nav.currentDestination?.id != R.id.loginFragment) {
            nav.navigate(R.id.loginFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
    }
    fun logout() { auth.logout(); openLogin() }
    override fun onResume() {
        super.onResume()
        if (!store.signedIn || store.token.isNullOrBlank() || nav.currentDestination?.id==R.id.sessionFragment || checkingSession) return
        checkingSession=true
        lifecycleScope.launch {
            try {
                val result=auth.restore()
                result.onSuccess { if (it != null) loadAccountData() }
                    .onFailure { Toast.makeText(this@MainActivity,it.message,Toast.LENGTH_LONG).show() }
            } finally { checkingSession=false }
        }
    }
    fun speak(text: String) {
        if (speechReady) {
            if (tts?.speak(text,TextToSpeech.QUEUE_FLUSH,null,"word")==TextToSpeech.ERROR)
                Toast.makeText(this@MainActivity,"Không phát được âm thanh. Hãy thử lại.",Toast.LENGTH_SHORT).show()
        } else Toast.makeText(this@MainActivity,"Chưa có giọng đọc tiếng Anh. Hãy kiểm tra cài đặt Text-to-Speech trên máy.",Toast.LENGTH_LONG).show()
    }
    override fun onStop() { tts?.stop(); super.onStop() }
    override fun onDestroy() { tts?.stop(); tts?.shutdown(); super.onDestroy() }
}
