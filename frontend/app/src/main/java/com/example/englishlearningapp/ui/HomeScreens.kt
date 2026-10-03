package com.example.englishlearningapp.ui

import com.example.englishlearningapp.R
import java.util.Calendar
import java.util.Locale

class HomeFragment : ScreenFragment() {
    override fun render() {
        val greeting = row()
        text("◉  LensLearn",20,Palette.blue,true,greeting).layoutParams = android.widget.LinearLayout.LayoutParams(0,-2,1f)
        text("🔥 ${store.streak}",16,Palette.orange,true,greeting).layoutParams = android.widget.LinearLayout.LayoutParams(-2,-2)
        space(8)
        header("XIN CHÀO, ${store.name}", "Hôm nay, bạn sẽ\nkhám phá điều gì?", "Biến thế giới quanh bạn thành bài học tiếng Anh.")
        val hero = column(color = Palette.elevated, padding = 22)
        hero.background = android.graphics.drawable.GradientDrawable(android.graphics.drawable.GradientDrawable.Orientation.TL_BR,
            intArrayOf(0xFF243D68.toInt(),Palette.elevated,0xFF38305A.toInt())).apply { cornerRadius=dp(24).toFloat() }
        text("✦  HỌC TỪ CUỘC SỐNG",11,Palette.blue,true,hero)
        text("Nhìn thấy.\nGhi nhớ.\nSử dụng.",28,bold=true,parent=hero)
        text("🍎   📚   🌿",42,parent=hero,center=true)
        text("Một bức ảnh mở ra cả thế giới từ vựng.",13,Palette.muted,parent=hero)
        button("Mở camera khám phá  →", parent=hero) { go(R.id.cameraFragment) }
        space(8)
        section("Nhịp học của bạn", "Chi tiết") { go(R.id.progressFragment) }
        stats(store.saved.size.toString() to "Từ đã lưu",store.mastered.size.toString() to "Đã ghi nhớ",store.streak.toString() to "Ngày liên tiếp")
        val goal = column(color=Palette.surface)
        text("Mục tiêu hôm nay",16,bold=true,parent=goal)
        text("${store.todayCount} / ${store.goal} lượt luyện tập",13,Palette.muted,parent=goal)
        progress(store.todayCount,store.goal,goal,Palette.green)
        button("Ôn tập ngay",Palette.purple,goal) { go(R.id.flashcardFragment) }
        section("Từ vựng hôm nay", "Khám phá") { go(R.id.topicsFragment) }
        if (words.words.isNotEmpty()) wordRow(words.words[Calendar.getInstance().get(Calendar.DAY_OF_YEAR) % words.words.size])
        section("Một bước nhỏ mỗi ngày")
        tile("✦","Thử thách Quiz","4 cách luyện tập, một mục tiêu ghi nhớ",Palette.green) { go(R.id.practiceFragment) }
    }
}

class ProgressFragment : ScreenFragment() {
    override fun render() {
        header("HÀNH TRÌNH CỦA BẠN","Tiến độ học tập","Mỗi lần ôn luyện là một bước tiến.",true)
        stats(store.saved.size.toString() to "Từ đã lưu",store.mastered.size.toString() to "Đã nhớ",store.reviews.toString() to "Lượt học")
        val card = column(color=Palette.elevated)
        text("🔥  ${store.streak} ngày liên tiếp",23,Palette.orange,true,card)
        text("Duy trì nhịp học, xây dựng thói quen.",13,Palette.muted,parent=card)
        section("7 ngày gần đây")
        val week=row()
        val calendar=Calendar.getInstance().apply { add(Calendar.DAY_OF_YEAR,-6) }
        repeat(7) {
            val active=store.dateFormat().format(calendar.time) in store.studyDays
            val cell=android.widget.LinearLayout(requireContext()).apply { orientation=android.widget.LinearLayout.VERTICAL }
            week.addView(cell,android.widget.LinearLayout.LayoutParams(0,-2,1f))
            text(calendar.getDisplayName(Calendar.DAY_OF_WEEK,Calendar.SHORT,Locale.forLanguageTag("vi")) ?: "",10,Palette.muted,parent=cell,center=true)
            text(if(active) "●" else "○",25,if(active) Palette.green else Palette.line,parent=cell,center=true)
            text(calendar.get(Calendar.DAY_OF_MONTH).toString(),12,Palette.muted,parent=cell,center=true)
            calendar.add(Calendar.DAY_OF_YEAR,1)
        }
        val target=column(color=Palette.surface)
        text("Mục tiêu hôm nay",18,bold=true,parent=target)
        text("${store.todayCount} / ${store.goal} lượt luyện tập",14,Palette.blue,parent=target)
        progress(store.todayCount,store.goal,target,Palette.green)
        section("Kết quả Quiz")
        val accuracy=if(store.quizTotal==0) "—" else "${store.quizCorrect*100/store.quizTotal}%"
        stats(store.quizRuns.toString() to "Bài hoàn thành",accuracy to "Độ chính xác")
        section("Trạng thái từ vựng")
        text("${store.saved.count { it !in store.mastered }} từ đã lưu cần ôn tập",16,Palette.blue)
        notice("Đây là thống kê luyện tập cục bộ. Lịch ôn SRS sẽ được bổ sung khi có nghiệp vụ phía server.")
        button("Tiếp tục ôn tập",Palette.purple) { go(R.id.flashcardFragment) }
    }
}
