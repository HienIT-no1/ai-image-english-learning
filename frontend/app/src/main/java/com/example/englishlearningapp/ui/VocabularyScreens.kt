package com.example.englishlearningapp.ui

import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import androidx.core.widget.doAfterTextChanged
import com.example.englishlearningapp.R

class WordsFragment : ScreenFragment() {
    private var query = ""
    private var filter = "saved"
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        query = state?.getString("query") ?: ""
        filter = state?.getString("filter") ?: arguments?.getString("topic") ?: "saved"
    }
    override fun onSaveInstanceState(state: Bundle) { super.onSaveInstanceState(state); state.putString("query",query); state.putString("filter",filter) }
    override fun render() {
        val topic = words.topics.firstOrNull { it.id == filter }
        header("BỘ SƯU TẬP CỦA BẠN",topic?.name ?: "Từ vựng", "Gom những khám phá nhỏ thành vốn từ của bạn.",topic != null)
        val search = field("Tìm từ tiếng Anh hoặc nghĩa tiếng Việt",query,viewId=R.id.input_word_search)
        val chips = com.google.android.material.chip.ChipGroup(requireContext()).apply { isSingleSelection = true; isSelectionRequired = true }
        content.addView(chips)
        val options = listOf("saved" to "Đã lưu","all" to "Tất cả") + words.topics.map { it.id to it.name }
        options.forEach { (id,label) ->
            val chip = com.google.android.material.chip.Chip(requireContext()).apply {
                text=label; isCheckable=true; isChecked=filter==id
                setTextColor(Palette.white); chipBackgroundColor=android.content.res.ColorStateList.valueOf(if(filter==id) Palette.elevated else Palette.surface)
                setOnClickListener { if (filter != id) { filter=id; hideKeyboard(); refresh() } }
            }
            chips.addView(chip)
        }
        space(14)
        val list = column()
        fun showList() {
            list.removeAllViews()
            val matches = words.search(query,filter,store.saved)
            text("${matches.size} từ vựng",12,Palette.muted,parent=list)
            if(matches.isEmpty()) {
                text("Chưa có từ phù hợp",22,bold=true,parent=list)
                text("Thử từ khóa khác hoặc khám phá chủ đề để lưu thêm từ.",14,Palette.muted,parent=list)
                button("Khám phá chủ đề",parent=list) { go(R.id.topicsFragment) }
            } else matches.forEach { wordRow(it,list) }
        }
        showList()
        search.doAfterTextChanged { query=it.toString(); showList() }
        button("Khám phá theo chủ đề",outlined=true) { go(R.id.topicsFragment) }
    }
}

class TopicsFragment : ScreenFragment() {
    override fun render() {
        header("KHÁM PHÁ", "Chủ đề từ vựng", "Bắt đầu với những điều quen thuộc quanh bạn.",true)
        words.topics.forEach { topic ->
            val topicWords=words.words.filter { it.topic==topic.id }
            tile(topic.symbol,topic.name,"${topicWords.size} từ • ${topicWords.count { it.id in store.saved }} đã lưu") { go(R.id.wordsFragment,"topic" to topic.id) }
        }
        val tip=column(color=Palette.elevated)
        text("✦  Học ít, nhớ lâu",18,Palette.purple,true,tip)
        text("Chọn một chủ đề mỗi ngày. Lưu những từ mới và ôn lại bằng Flashcard.",14,Palette.muted,parent=tip)
    }
}

class WordDetailFragment : ScreenFragment() {
    override fun render() {
        header("KHÁM PHÁ TỪ MỚI", "Chi tiết từ vựng", back=true)
        val word=words.find(arguments?.getString("wordId"))
        if (word == null) {
            text("Không tìm thấy từ vựng",22,bold=true)
            notice("Từ này không còn trong danh sách. Hãy chọn một từ khác.")
            button("Khám phá chủ đề") { go(R.id.topicsFragment) }
            return
        }
        val hero=column(color=Palette.elevated,padding=24)
        text(word.symbol,86,parent=hero,center=true)
        text(word.english,36,bold=true,parent=hero,center=true)
        text(word.ipa,18,Palette.blue,parent=hero,center=true)
        text(word.meaning,21,parent=hero,center=true)
        button("♫  Nghe phát âm",outlined=true,parent=hero) { speak(word.english) }
        val examples=column(color=Palette.surface)
        text("SỬ DỤNG TRONG CÂU",11,Palette.purple,true,examples)
        text(word.example,19,bold=true,parent=examples)
        text(word.translation,14,Palette.muted,parent=examples)
        button("♫  Nghe câu ví dụ",outlined=true,parent=examples) { speak(word.example) }
        button(if(word.id in store.saved) "★  Đã lưu • Bấm để bỏ lưu" else "＋  Lưu vào bộ sưu tập",Palette.blue) { store.toggleSave(word.id); refresh() }
        button("Luyện tập bằng Flashcard",Palette.purple,outlined=true) { go(R.id.flashcardFragment,"wordId" to word.id) }
        section("Cùng chủ đề")
        words.words.filter { it.topic==word.topic && it.id!=word.id }.forEach { wordRow(it) }
    }
}

class HistoryFragment : ScreenFragment() {
    override fun render() {
        header("NHỮNG KHÁM PHÁ", "Lịch sử nhận diện", "Các phiên dùng thử với kết quả nhận diện mẫu.",true)
        if(store.history.isEmpty()) {
            text("◷",64,Palette.blue,center=true)
            text("Chưa có khám phá nào",22,bold=true,center=true)
            text("Chọn một ảnh và thử luồng nhận diện đầu tiên.",14,Palette.muted,center=true)
            button("Khám phá ngay") { go(R.id.cameraFragment) }
        } else {
            store.history.asReversed().forEachIndexed { index, entry ->
                val parts=entry.split("|",limit=2)
                val word=words.find(parts[0]) ?: return@forEachIndexed
                tile(word.symbol,"Lần ${store.history.size-index} • ${word.english}","${parts.getOrElse(1) { "" }} • Kết quả mẫu") { go(R.id.wordDetailFragment,"wordId" to word.id) }
            }
            button("Xóa lịch sử",Palette.orange,outlined=true) {
                com.google.android.material.dialog.MaterialAlertDialogBuilder(requireContext()).setTitle("Xóa lịch sử trên máy?")
                    .setNegativeButton("Hủy",null).setPositiveButton("Xóa") { _, _ -> store.history=emptyList(); refresh() }.show()
            }
        }
    }
}
