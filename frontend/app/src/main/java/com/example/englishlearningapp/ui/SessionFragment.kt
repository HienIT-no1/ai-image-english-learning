package com.example.englishlearningapp.ui

import android.os.Bundle
import android.view.View
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import kotlinx.coroutines.launch
import kotlinx.coroutines.ensureActive

class SessionFragment : ScreenFragment() {
    private var checking = true
    private var failure: String? = null
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState); check()
    }
    private fun check() {
        checking=true; failure=null; refresh()
        val activity=requireActivity() as com.example.englishlearningapp.MainActivity
        val owner=viewLifecycleOwner
        owner.lifecycleScope.launch {
            val result=activity.auth.restore()
            ensureActive()
            if(!isAdded || owner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            result.onSuccess { user ->
                if (user==null) { auth.logout(); enter(R.id.loginFragment) }
                else {
                    val loaded=activity.loadAccountData()
                    ensureActive()
                    if(!isAdded || owner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
                    loaded.onSuccess {
                        activity.words.loadFromApi()
                        ensureActive()
                        if(!isAdded || owner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
                        val controller=findNavController()
                        val settingsUser=arguments?.getLong("resumeSettingsUser",0L) ?: 0L
                        val resumeUser=arguments?.getLong("resumeGameUser",0L) ?: 0L
                        if(settingsUser>0 && store.userId==settingsUser && (store.onboardingCompleted || store.isAdmin)) {
                            enter(R.id.homeFragment)
                            controller.navigate(R.id.profileFragment)
                            controller.navigate(R.id.settingsFragment,arguments?.getBundle("settingsDraft"))
                        } else if (resumeUser>0 && store.userId==resumeUser && games.canResume && (store.onboardingCompleted || store.isAdmin)) {
                            // Restore only this validated user's game, after the normal account check.
                            enter(R.id.homeFragment)
                            controller.navigate(R.id.gamesFragment)
                            controller.navigate(R.id.wordShooterFragment)
                        } else {
                            enter(if(store.isAdmin) R.id.adminFragment else if(store.onboardingCompleted) R.id.homeFragment else R.id.onboardingFragment)
                        }
                        activity.openPendingNotification()
                    }.onFailure { failure=it.message; checking=false; refresh() }
                }
            }.onFailure { failure=it.message; checking=false; refresh() }
        }
    }
    private fun enter(destination: Int) {
        findNavController().navigate(destination,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
    }
    override fun render() {
        header("LENSLEARN", "Kiểm tra phiên đăng nhập")
        if (checking) notice("Đang kiểm tra tài khoản và tải bộ sưu tập…")
        else {
            notice(failure ?: "Chưa xác nhận được phiên đăng nhập.")
            button("Thử lại") { check() }
            button("Dùng tài khoản khác",outlined=true) { auth.logout(); enter(R.id.loginFragment) }
        }
    }
}
