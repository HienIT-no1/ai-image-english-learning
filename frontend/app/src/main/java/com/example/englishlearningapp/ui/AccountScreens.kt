package com.example.englishlearningapp.ui

import android.os.Bundle
import androidx.core.widget.doAfterTextChanged
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.materialswitch.MaterialSwitch

class AuthFragment : ScreenFragment() {
    override fun render() {
        val registering = findNavController().currentDestination?.id == R.id.registerFragment
        space(20)
        text("◉", 68, Palette.blue, true, center = true)
        text("LENSLEARN", 13, Palette.blue, true, center = true).letterSpacing = 0.24f
        header("SEE IT. LEARN IT.", if (registering) "Bắt đầu hành trình" else "Thế giới quanh bạn,\ntừ vựng của bạn.",
            if (registering) "Tạo hồ sơ để khám phá tiếng Anh mỗi ngày." else "Học tiếng Anh từ những điều nhỏ bé mỗi ngày.")
        val name = if (registering) field("Tên của bạn",viewId=R.id.input_auth_name) else null
        val email = field("Email",viewId=R.id.input_auth_email).apply { inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS }
        val password = field("Mật khẩu", password = true,viewId=R.id.input_auth_password)
        notice("Bản trải nghiệm giao diện • Không xác thực tài khoản thật. Email và mật khẩu không được lưu hoặc gửi đi.")
        button(if (registering) "Tạo hồ sơ mẫu  →" else "Đăng nhập trải nghiệm  →") {
            when {
                name != null && name.text.toString().trim().isEmpty() -> name.error = "Nhập tên của bạn"
                !android.util.Patterns.EMAIL_ADDRESS.matcher(email.text.toString().trim()).matches() -> email.error = "Nhập email hợp lệ"
                password.text.toString().length < 6 -> password.error = "Nhập ít nhất 6 ký tự để thử giao diện"
                else -> {
                    store.name = name?.text?.toString()?.trim() ?: email.text.toString().trim().substringBefore('@')
                    enter(if (registering) R.id.onboardingFragment else R.id.homeFragment)
                }
            }
        }
        button("Khám phá bằng hồ sơ mẫu", outlined = true) { store.name = "Bạn học"; enter(R.id.onboardingFragment) }
        text(if (registering) "Đã có hồ sơ? Đăng nhập" else "Chưa có hồ sơ? Đăng ký", 14, Palette.blue, parent = content, center = true).apply {
            minHeight = dp(48)
            setOnClickListener { if (registering) findNavController().popBackStack() else go(R.id.registerFragment) }
        }
        val info = column(color = Palette.surface)
        text("✦  Mỗi hình ảnh, một khám phá", 16, bold = true, parent = info)
        text("Chụp ảnh • Lưu từ • Ôn luyện", 13, Palette.muted, parent = info)
    }
    private fun enter(destination: Int) {
        store.signedIn = destination == R.id.homeFragment
        findNavController().navigate(destination,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
    }
}

class OnboardingFragment : ScreenFragment() {
    private var selectedLevel = ""
    private var selectedGoal = 10
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        selectedLevel = state?.getString("level") ?: store.level
        selectedGoal = state?.getInt("goal") ?: store.goal
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state)
        state.putString("level",selectedLevel); state.putInt("goal",selectedGoal)
    }
    override fun render() {
        header("HỒ SƠ HỌC TẬP", "Học theo nhịp của bạn", "Chọn trình độ và mục tiêu phù hợp. Bạn có thể đổi sau.")
        section("Trình độ hiện tại")
        listOf("A1 • Mới bắt đầu","A2 • Cơ bản","B1 • Trung cấp","B2 • Khá").forEach { level ->
            button((if (selectedLevel == level) "✓  " else "") + level, outlined = true) { selectedLevel = level; refresh() }
        }
        section("Mục tiêu mỗi ngày")
        listOf(5,10,15,20).forEach { goal ->
            button("${if (goal == selectedGoal) "✓  " else ""}$goal lượt luyện tập / ngày", Palette.purple, outlined = true) { selectedGoal = goal; refresh() }
        }
        button("Bắt đầu khám phá  →") {
            store.saveProfile(store.name,selectedLevel,selectedGoal,store.reminders)
            store.signedIn = true
            findNavController().navigate(R.id.homeFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
        }
    }
}

class ProfileFragment : ScreenFragment() {
    override fun render() {
        header("GÓC CỦA BẠN", "Hồ sơ học tập", "Một chút mỗi ngày, tiến xa hơn mỗi tuần.")
        val profile = column(color = Palette.elevated)
        text(store.name.take(1).uppercase(), 40, Palette.purple, true, profile, true)
        text(store.name, 23, bold = true, parent = profile, center = true)
        text(store.level, 13, Palette.muted, parent = profile, center = true)
        stats(store.saved.size.toString() to "Từ đã lưu", store.streak.toString() to "Ngày liên tiếp", store.mastered.size.toString() to "Đã nhớ")
        tile("↗", "Tiến độ học tập", "Thống kê & mục tiêu mỗi ngày") { go(R.id.progressFragment) }
        tile("◷", "Lịch sử nhận diện", "Các lần thử nhận diện bằng ảnh") { go(R.id.historyFragment) }
        tile("⚙", "Cài đặt", "Tên, trình độ & mục tiêu học tập") { go(R.id.settingsFragment) }
        tile("▦", "Khu quản trị mẫu", "Khám phá giao diện dành cho Admin", Palette.purple) { go(R.id.adminFragment) }
        button("Đăng xuất", Palette.orange, outlined = true) {
            MaterialAlertDialogBuilder(requireContext()).setTitle("Đăng xuất hồ sơ mẫu?")
                .setMessage("Từ đã lưu và tiến độ trên máy vẫn được giữ lại.")
                .setNegativeButton("Ở lại",null).setPositiveButton("Đăng xuất") { _, _ ->
                    store.signedIn = false
                    findNavController().navigate(R.id.loginFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
                }.show()
        }
        notice("LensLearn • Phiên bản giao diện 1.0")
    }
}

class SettingsFragment : ScreenFragment() {
    private var draftName = ""
    private var draftLevel = ""
    private var draftGoal = 10
    private var draftReminders = false
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        draftName = state?.getString("name") ?: store.name
        draftLevel = state?.getString("level") ?: store.level
        draftGoal = state?.getInt("goal") ?: store.goal
        draftReminders = state?.getBoolean("reminders") ?: store.reminders
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state)
        state.putString("name",draftName); state.putString("level",draftLevel)
        state.putInt("goal",draftGoal); state.putBoolean("reminders",draftReminders)
    }
    override fun render() {
        header("CÁ NHÂN HÓA", "Cài đặt học tập", "Điều chỉnh để việc học trở nên thoải mái hơn.", true)
        val name = field("Tên hiển thị",draftName,viewId=R.id.input_settings_name)
        name.doAfterTextChanged { draftName=it.toString() }
        section("Trình độ")
        button(draftLevel, outlined = true) {
            val levels = arrayOf("A1 • Mới bắt đầu","A2 • Cơ bản","B1 • Trung cấp","B2 • Khá")
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn trình độ").setItems(levels) { _, i ->
                draftLevel = levels[i]; hideKeyboard(); refresh()
            }.show()
        }
        section("Mục tiêu mỗi ngày")
        button("$draftGoal lượt luyện tập", Palette.purple, outlined = true) {
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn mục tiêu").setItems(arrayOf("5 lượt","10 lượt","15 lượt","20 lượt")) { _, i ->
                draftGoal = listOf(5,10,15,20)[i]; hideKeyboard(); refresh()
            }.show()
        }
        val toggle = MaterialSwitch(requireContext()).apply {
            text = "Nhắc ôn tập (tùy chọn mẫu)"; isChecked = draftReminders; setTextColor(Palette.white)
            setOnCheckedChangeListener { _, checked -> draftReminders = checked }
        }
        content.addView(toggle)
        notice("Bấm Lưu thay đổi để áp dụng. Thông báo theo lịch sẽ được triển khai ở giai đoạn sau.")
        button("Lưu thay đổi") {
            if (name.text.toString().trim().isEmpty()) name.error = "Tên không được để trống"
            else {
                store.saveProfile(draftName.trim(),draftLevel,draftGoal,draftReminders)
                hideKeyboard(); toast("Đã lưu cài đặt"); findNavController().popBackStack()
            }
        }
    }
}
