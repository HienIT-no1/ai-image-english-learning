package com.example.englishlearningapp.ui

import android.os.Bundle
import androidx.core.widget.doAfterTextChanged
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.materialswitch.MaterialSwitch
import androidx.lifecycle.lifecycleScope
import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.launch
import kotlinx.coroutines.ensureActive
import androidx.activity.result.contract.ActivityResultContracts
import com.example.englishlearningapp.MainActivity
import com.example.englishlearningapp.notifications.ReminderNotifier
import com.example.englishlearningapp.notifications.ReminderScheduler
class AuthFragment : ScreenFragment() {
    override fun render() {
        val registering = findNavController().currentDestination?.id == R.id.registerFragment
        space(20)
        text("◉", 68, Palette.blue, true, center = true)
        text("LENSLEARN", 13, Palette.blue, true, center = true).letterSpacing = 0.24f
        header("SEE IT. LEARN IT.", if (registering) "Bắt đầu hành trình" else "Thế giới quanh bạn,\ntừ vựng của bạn.",
            if (registering) "Tạo tài khoản để khám phá tiếng Anh mỗi ngày." else "Học tiếng Anh từ những điều nhỏ bé mỗi ngày.")

        val username = field("Tên đăng nhập", viewId = R.id.input_auth_name)
        val email = if (registering) field("Email", viewId = R.id.input_auth_email).apply {
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
        } else null
        val password = field("Mật khẩu", password = true, viewId = R.id.input_auth_password)
        notice("Tên đăng nhập 3 đến 50 ký tự • Mật khẩu tối thiểu 8 ký tự.")

        var submit: MaterialButton? = null
        submit = button(if (registering) "Tạo tài khoản  →" else "Đăng nhập  →") {
            val u = username.text.toString().trim()
            val p = password.text.toString()
            when {
                u.length !in 3..50 -> username.error = "Tên đăng nhập từ 3 đến 50 ký tự"
                email != null && !android.util.Patterns.EMAIL_ADDRESS.matcher(email.text.toString().trim()).matches() ->
                    email.error = "Nhập email hợp lệ"
                p.length !in 8..128 -> password.error = "Mật khẩu từ 8 đến 128 ký tự"
                else -> {
                    hideKeyboard()
                    submit?.isEnabled = false
                    viewLifecycleOwner.lifecycleScope.launch {
                        val result = if (email != null) {
                            auth.register(u, email.text.toString().trim(), p)
                        } else {
                            auth.login(u, p)
                        }
                        submit?.isEnabled = true
                        result.onSuccess { user ->
                            (requireActivity() as com.example.englishlearningapp.MainActivity).loadAccountData().onFailure { toast(it.message ?: "Không tải được dữ liệu học.") }
                            words.loadFromApi()
                            enter(if (user.role=="ADMIN") R.id.adminFragment else if (user.onboardingCompleted) R.id.homeFragment else R.id.onboardingFragment)
                            (requireActivity() as MainActivity).openPendingNotification()
                        }.onFailure { toast(it.message ?: "Có lỗi xảy ra") }
                    }
                }
            }
        }
        text(if (registering) "Đã có tài khoản? Đăng nhập" else "Chưa có tài khoản? Đăng ký", 14, Palette.blue, parent = content, center = true).apply {
            minHeight = dp(48)
            setOnClickListener { if (registering) findNavController().popBackStack() else go(R.id.registerFragment) }
        }
        val info = column(color = Palette.surface)
        text("✦  Mỗi hình ảnh, một khám phá", 16, bold = true, parent = info)
        text("Chụp ảnh • Lưu từ • Ôn luyện", 13, Palette.muted, parent = info)
    }

    private fun enter(destination: Int) {
        store.signedIn = destination == R.id.homeFragment || destination == R.id.adminFragment
        findNavController().navigate(destination, null, NavOptions.Builder().setPopUpTo(R.id.nav_graph, true).build())
    }
}

class OnboardingFragment : ScreenFragment() {
    private var saving=false
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
        button(if(saving) "Đang lưu hồ sơ…" else "Bắt đầu khám phá  →") {
            if (saving) return@button
            saving=true;refresh()
            viewLifecycleOwner.lifecycleScope.launch {
                auth.updateProfile(store.name,selectedLevel,selectedGoal,store.reminders).onSuccess {
                    learning.load()
                    findNavController().navigate(R.id.homeFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
                    (requireActivity() as MainActivity).openPendingNotification()
                }.onFailure { toast(it.message ?: "Chưa lưu được hồ sơ.") }
                saving=false;refresh()
            }
        }.isEnabled=!saving
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
        tile("♧", "Thông báo", "Nhắc học và các từ đến hạn") { go(R.id.notificationsFragment) }
        tile("⚙", "Cài đặt", "Tên, trình độ & mục tiêu học tập") { go(R.id.settingsFragment) }
        if (store.isAdmin) tile("▦", "Quản trị hệ thống", "Quản lý người dùng, chủ đề và từ vựng", Palette.purple) { go(R.id.adminFragment) }
        button("Đăng xuất", Palette.orange, outlined = true) {
            MaterialAlertDialogBuilder(requireContext()).setTitle("Đăng xuất tài khoản?")
                .setMessage("Bộ sưu tập và tiến độ trên máy chủ được giữ lại.")
                .setNegativeButton("Ở lại",null).setPositiveButton("Đăng xuất") { _, _ ->
                    auth.logout()
                    findNavController().navigate(R.id.loginFragment,null,NavOptions.Builder().setPopUpTo(R.id.nav_graph,true).build())
                }.show()
        }
        notice("LensLearn • Phiên bản giao diện 1.0")
    }
}

class SettingsFragment : ScreenFragment() {
    private var saving=false
    private var draftName=""
    private var draftLevel=""
    private var draftGoal=10
    private var draftReminders=false
    private var draftMinutes=1200
    private var previewAfterPermission=false
    private val notificationPermission=registerForActivityResult(ActivityResultContracts.RequestPermission()) { allowed ->
        if(isAdded && view!=null) {
            if(allowed && previewAfterPermission) ReminderScheduler.preview(requireContext())
            if(!allowed) toast("Chưa được cấp quyền. Bạn có thể mở cài đặt thông báo của điện thoại.")
            ReminderScheduler.sync(requireContext());refresh()
        }
        previewAfterPermission=false
    }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val draft=state ?: arguments
        draftName=draft?.getString("name") ?: store.name
        draftLevel=draft?.getString("level") ?: store.level
        draftGoal=draft?.getInt("goal",store.goal) ?: store.goal
        draftReminders=draft?.getBoolean("reminders",store.reminders) ?: store.reminders
        draftMinutes=draft?.getInt("minutes",store.reminderMinutes) ?: store.reminderMinutes
    }
    fun snapshot()=Bundle().apply {
        putString("name",draftName);putString("level",draftLevel);putInt("goal",draftGoal)
        putBoolean("reminders",draftReminders);putInt("minutes",draftMinutes)
    }
    override fun onSaveInstanceState(state: Bundle) { state.putAll(snapshot());super.onSaveInstanceState(state) }
    override fun render() {
        header("CÁ NHÂN HÓA","Cài đặt học tập","Điều chỉnh để việc học trở nên thoải mái hơn.",true)
        section("Màu giao diện")
        button("${if(!Palette.light) "✓  " else ""}Tối • Xanh tím",Palette.purple,outlined=!Palette.light) {
            hideKeyboard();(requireActivity() as MainActivity).changeTheme(false,snapshot())
        }.id=R.id.theme_dark
        button("${if(Palette.light) "✓  " else ""}Sáng • Trắng xanh dịu",Palette.blue,outlined=Palette.light) {
            hideKeyboard();(requireActivity() as MainActivity).changeTheme(true,snapshot())
        }.id=R.id.theme_light
        notice("Màu đổi ngay và được nhớ trên điện thoại này.")
        section("Hồ sơ học tập")
        val name=field("Tên hiển thị",draftName,viewId=R.id.input_settings_name)
        name.doAfterTextChanged { draftName=it.toString() }
        button(draftLevel,outlined=true) {
            val levels=arrayOf("A1 • Mới bắt đầu","A2 • Cơ bản","B1 • Trung cấp","B2 • Khá")
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn trình độ").setItems(levels) { _,i -> draftLevel=levels[i];hideKeyboard();refresh() }.show()
        }
        button("Mục tiêu: $draftGoal lượt mỗi ngày",Palette.purple,outlined=true) {
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn mục tiêu").setItems(arrayOf("5 lượt","10 lượt","15 lượt","20 lượt")) { _,i ->
                draftGoal=listOf(5,10,15,20)[i];hideKeyboard();refresh()
            }.show()
        }
        section("Nhắc nhở ôn tập")
        val toggle=MaterialSwitch(requireContext()).apply {
            id=R.id.reminder_toggle;text="Nhắc ôn tập hằng ngày";isChecked=draftReminders;setTextColor(Palette.white)
            setOnCheckedChangeListener { _,checked ->
                draftReminders=checked
                if(checked && android.os.Build.VERSION.SDK_INT>=33 && !ReminderNotifier.allowed(requireContext())) requestPermission(false)
            }
        }
        content.addView(toggle)
        button("Giờ nhắc: %02d:%02d".format(draftMinutes/60,draftMinutes%60),outlined=true) {
            android.app.TimePickerDialog(requireContext(),{ _,hour,minute -> draftMinutes=hour*60+minute;hideKeyboard();refresh() },draftMinutes/60,draftMinutes%60,true).show()
        }.id=R.id.reminder_time
        val allowed=ReminderNotifier.allowed(requireContext())
        notice(if(allowed) "Điện thoại đã cho phép thông báo." else "Thông báo đang bị chặn trên điện thoại. Hãy cấp quyền để nhận lời nhắc.")
        if(!allowed) {
            button("Cho phép thông báo",outlined=true) { requestPermission(false) }
            button("Mở cài đặt thông báo",outlined=true) {
                startActivity(android.content.Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                    .putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,requireContext().packageName))
            }
        }
        button("Gửi thử thông báo",Palette.green,outlined=true) {
            if(ReminderNotifier.allowed(requireContext())) {
                ReminderScheduler.preview(requireContext());toast("Đã gửi yêu cầu thông báo thử. Kéo thanh thông báo xuống để xem.")
            } else requestPermission(true)
        }.id=R.id.reminder_preview
        notice("Giờ nhắc theo điện thoại. Android có thể gửi trễ khi tiết kiệm pin. Không nhắc nếu bạn đã đạt mục tiêu và không còn từ đến hạn.")
        button("Xem thông báo trong app",outlined=true) { go(R.id.notificationsFragment) }
        notice("Bấm Lưu thay đổi để lưu hồ sơ, giờ nhắc và bật/tắt nhắc học lên máy chủ.")
        button(if(saving) "Đang lưu…" else "Lưu thay đổi") {
            if(saving) return@button
            if(draftName.trim().isEmpty()) { name.error="Tên không được để trống";return@button }
            hideKeyboard();saving=true;refresh()
            val activity=requireActivity() as MainActivity
            viewLifecycleOwner.lifecycleScope.launch {
                val result=activity.auth.updateProfile(draftName.trim(),draftLevel,draftGoal,draftReminders,draftMinutes)
                kotlinx.coroutines.currentCoroutineContext().ensureActive()
                if(!isAdded || view==null) return@launch
                result.onSuccess {
                    activity.learning.load()
                    if(isAdded && view!=null) { toast("Đã lưu cài đặt và cập nhật lịch nhắc");findNavController().popBackStack() }
                }.onFailure { toast(it.message ?: "Chưa lưu được cài đặt.") }
                saving=false;refresh()
            }
        }.apply { id=R.id.settings_save;isEnabled=!saving }
    }
    private fun requestPermission(preview: Boolean) {
        previewAfterPermission=preview
        if(android.os.Build.VERSION.SDK_INT>=33) notificationPermission.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        else {
            toast("Hãy bật thông báo trong cài đặt điện thoại.")
            startActivity(android.content.Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                .putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,requireContext().packageName))
        }
    }
}
