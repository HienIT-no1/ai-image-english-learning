package com.example.englishlearningapp.ui

import android.os.Bundle
import android.view.View
import androidx.lifecycle.lifecycleScope
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import kotlinx.coroutines.launch

class SessionFragment : ScreenFragment() {
    private var checking = true
    private var failure: String? = null
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState); check()
    }
    private fun check() {
        checking=true; failure=null; refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            val result=auth.restore()
            result.onSuccess { user ->
                if (user==null) { auth.logout(); enter(R.id.loginFragment) }
                else {
                    val loaded=(requireActivity() as com.example.englishlearningapp.MainActivity).loadAccountData()
                    loaded.onSuccess {
                        words.loadFromApi()
                        enter(if(store.onboardingCompleted) R.id.homeFragment else R.id.onboardingFragment)
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
