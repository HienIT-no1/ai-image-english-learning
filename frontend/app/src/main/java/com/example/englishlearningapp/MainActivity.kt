package com.example.englishlearningapp

import android.os.Bundle
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import androidx.core.view.WindowCompat
import com.example.englishlearningapp.ui.Palette
import com.example.englishlearningapp.data.local.AppAppearance
import com.example.englishlearningapp.data.repository.NotificationRepository
import com.example.englishlearningapp.notifications.ReminderScheduler
import com.example.englishlearningapp.notifications.ReminderNotifier
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
import com.example.englishlearningapp.data.repository.AiRepository
import com.example.englishlearningapp.data.repository.AdminRepository
import com.example.englishlearningapp.data.repository.AuthRepository
import com.example.englishlearningapp.data.repository.CollectionRepository
import com.example.englishlearningapp.data.repository.LearningRepository
import com.example.englishlearningapp.data.remote.apiResult
import com.example.englishlearningapp.data.repository.GameRepository
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
    lateinit var games: GameRepository
        private set
    lateinit var notifications: NotificationRepository
        private set
    private var themeDraft: Bundle?=null
    lateinit var admin: AdminRepository
        private set
    lateinit var ai: AiRepository
        private set
    private var tts: TextToSpeech? = null
    private var speechReady = false
    private var checkingSession = false
    private val nav get() = (supportFragmentManager.findFragmentById(R.id.nav_host) as NavHostFragment).navController

    override fun onCreate(savedInstanceState: Bundle?) {
        store = LearningStore(this)
        Palette.light=AppAppearance(this).light
        setTheme(if(Palette.light) R.style.Theme_EnglishLearningApp_Light else R.style.Theme_EnglishLearningApp)
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
        admin = AdminRepository(api,store)
        ai = AiRepository(api)
        words = WordRepository(api)
        collections = CollectionRepository(api,store,words)
        learning = LearningRepository(api,store)
        quizzes = QuizRepository(api,store,words,learning)
        games = GameRepository(api,store,learning)
        notifications = NotificationRepository(api,store,words)
        auth = AuthRepository(api,store) { collections.reset(); learning.reset() }
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        WindowCompat.getInsetsController(window,window.decorView).apply {
            isAppearanceLightStatusBars=Palette.light;isAppearanceLightNavigationBars=Palette.light
        }
        ReminderScheduler.sync(this)
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
            val resume=Bundle().apply {
                val draft=savedInstanceState.getBundle("themeDraft")
                if(draft!=null && savedInstanceState.getLong("themeUser",0)==store.userId) {
                    putLong("resumeSettingsUser",store.userId ?: 0L);putBundle("settingsDraft",draft)
                }
                if (nav.currentDestination?.id==R.id.wordShooterFragment && games.canResume) {
                    putLong("resumeGameUser",store.userId ?: 0L)
                }
            }
            nav.navigate(R.id.sessionFragment,resume,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
        tts = TextToSpeech(this) { status ->
            if (status==TextToSpeech.SUCCESS) speechReady=(tts?.setLanguage(Locale.ENGLISH) ?: -1)>=TextToSpeech.LANG_AVAILABLE
        }
    }
    suspend fun loadAccountData(): Result<Unit> = apiResult {
        collections.load().getOrThrow()
        quizzes.syncPending().getOrThrow()
        games.syncPending().getOrThrow()
        learning.load().getOrThrow()
        notifications.syncPending()
    }
    fun changeTheme(light: Boolean,draft: Bundle) {
        if(AppAppearance(this).light==light) return
        themeDraft=draft
        AppAppearance(this).light=light
        recreate()
    }
    override fun onSaveInstanceState(state: Bundle) {
        val current=(supportFragmentManager.findFragmentById(R.id.nav_host) as? NavHostFragment)
            ?.childFragmentManager?.primaryNavigationFragment
        val draft=themeDraft ?: (current as? com.example.englishlearningapp.ui.SettingsFragment)?.snapshot()
        if(draft!=null) { state.putBundle("themeDraft",draft);state.putLong("themeUser",store.userId ?: 0L) }
        super.onSaveInstanceState(state)
    }
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent);setIntent(intent)
        if(intent.hasExtra("notification_user")) {
            nav.navigate(R.id.sessionFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
    }
    fun openPendingNotification(): Boolean {
        val user=intent.getLongExtra("notification_user",0L)
        if(user<=0 || !store.signedIn || (!store.onboardingCompleted && !store.isAdmin)) return false
        val id=intent.getLongExtra("notification_id",0L)
        val date=intent.getStringExtra("notification_date")
        intent.removeExtra("notification_user");intent.removeExtra("notification_id");intent.removeExtra("notification_date")
        if(store.userId!=user) return false
        NotificationManagerCompat.from(this).cancel(ReminderNotifier.ID)
        NotificationManagerCompat.from(this).cancel(ReminderNotifier.ID+1)
        if(id>0) lifecycleScope.launch { notifications.read(id) }
        else if(date!=null) lifecycleScope.launch {
            notifications.inbox().onSuccess { page ->
                page.items.firstOrNull { it.occurrenceDate==date }?.let { notifications.read(it.notificationId) }
            }
        }
        nav.navigate(R.id.dueReviewFragment,null,NavOptions.Builder().setLaunchSingleTop(true).build())
        return true
    }
    fun openLogin() {
        if (nav.currentDestination?.id != R.id.loginFragment) {
            nav.navigate(R.id.loginFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
    }
    fun logout() { auth.logout(); openLogin() }
    override fun onResume() {
        super.onResume()
        ReminderScheduler.sync(this)
        if (!store.signedIn || store.token.isNullOrBlank() || nav.currentDestination?.id==R.id.sessionFragment || checkingSession) return
        checkingSession=true
        lifecycleScope.launch {
            try {
                val result=auth.restore()
                result.onSuccess { user ->
                    if (user != null) {
                        if (!store.isAdmin && nav.currentDestination?.id in setOf(R.id.adminFragment,R.id.adminListFragment)) {
                            nav.navigate(R.id.homeFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
                        }
                        loadAccountData()
                    }
                }
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
