package com.example.englishlearningapp.ui

import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.core.os.bundleOf
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.Word
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class PracticeFragment : ScreenFragment() {
    override fun render() {
        header("MỖI NGÀY MỘT CHÚT", "Luyện tập & ghi nhớ", "Kiến thức ở lại khi bạn dành thời gian ôn luyện.")
        val hero=column(color=Palette.elevated,padding=22)
        text("▣",44,Palette.purple,parent=hero)
        text("Lật thẻ, mở trí nhớ",25,bold=true,parent=hero)
        text("${store.saved.size} từ đã lưu • Luyện theo nhịp của bạn",14,Palette.muted,parent=hero)
        button("Bắt đầu Flashcard  →",Palette.purple,hero) { go(R.id.flashcardFragment) }
        section("Thử thách Quiz")
        tile("🍎","Nhìn ảnh chọn từ","Ghép hình minh họa với từ tiếng Anh",Palette.green) { go(R.id.quizFragment,"mode" to "image") }
        tile("▦","Nhìn từ chọn ảnh","Chọn hình minh họa đúng với từ",Palette.purple) { go(R.id.quizFragment,"mode" to "word") }
        tile("♫","Nghe chọn đáp án","Luyện nghe bằng giọng đọc trên thiết bị",Palette.blue) { go(R.id.quizFragment,"mode" to "listen") }
        tile("✎","Điền từ còn thiếu","Nhìn hình và viết lại từ tiếng Anh",Palette.orange) { go(R.id.quizFragment,"mode" to "fill") }
        button("Thử thách tổng hợp • 8 câu",Palette.green) { go(R.id.quizFragment,"mode" to "mixed") }
        notice("Quiz ưu tiên từ đã lưu, bổ sung từ mẫu khi chưa đủ 8 từ. Mỗi lần bắt đầu sẽ có thứ tự câu hỏi mới.")
    }
}

class FlashcardFragment : ScreenFragment() {
    private var ids=emptyList<String>()
    private var index=0
    private var flipped=false
    private var remembered=0
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        ids=state?.getStringArrayList("ids") ?: arrayListOf<String>().apply {
            addAll(arguments?.getStringArrayList("wordIds") ?: emptyList())
            arguments?.getString("wordId")?.let { add(it) }
            if (isEmpty()) addAll(store.saved.sorted())
        }
        ids=ids.distinct().filter { words.find(it)!=null }
        index=state?.getInt("index") ?: 0; flipped=state?.getBoolean("flipped") ?: false; remembered=state?.getInt("remembered") ?: 0
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state); state.putStringArrayList("ids",ArrayList(ids)); state.putInt("index",index)
        state.putBoolean("flipped",flipped); state.putInt("remembered",remembered)
    }
    override fun render() {
        // Returning from Topics can populate a previously empty deck.
        if (ids.isEmpty()) ids=store.saved.sorted().filter { words.find(it)!=null }
        header("ÔN TẬP TỪ VỰNG", "Flashcard", "Chạm vào thẻ để khám phá mặt còn lại.",true)
        if(ids.isEmpty()) {
            text("📚",68,center=true)
            text("Lưu từ đầu tiên của bạn",24,bold=true,center=true)
            notice("Bộ thẻ sẽ được tạo từ những từ bạn lưu trong bộ sưu tập.")
            button("Khám phá từ vựng") { go(R.id.topicsFragment) }
            return
        }
        if(index>=ids.size) {
            text("✦",74,Palette.green,center=true)
            text("Một bước tiến thật tốt!",25,bold=true,center=true)
            stats("$remembered / ${ids.size}" to "Thẻ đã nhớ",(ids.size-remembered).toString() to "Cần luyện lại")
            button("Ôn lại bộ thẻ",Palette.purple) { index=0; remembered=0; flipped=false; refresh() }
            button("Xem tiến độ",outlined=true) { go(R.id.progressFragment) }
            return
        }
        val word=words.find(ids[index]) ?: return
        text("THẺ ${index+1} / ${ids.size}",12,Palette.blue,true)
        progress(index,ids.size,color=Palette.purple)
        val card=column(color=Palette.elevated,padding=26)
        card.minimumHeight=dp(310)
        text(word.symbol,86,parent=card,center=true)
        if(flipped) {
            text(word.meaning,30,bold=true,parent=card,center=true)
            text(word.english+"  "+word.ipa,17,Palette.blue,parent=card,center=true)
            text(word.example,16,Palette.muted,parent=card,center=true)
        } else {
            text(word.english,34,bold=true,parent=card,center=true)
            text(word.ipa,18,Palette.blue,parent=card,center=true)
            text("Chạm để xem nghĩa  ↻",13,Palette.muted,parent=card,center=true)
        }
        card.isFocusable=true; card.contentDescription="Thẻ ${word.english}. Chạm để lật thẻ"
        card.setOnClickListener { flipped=!flipped; refresh() }
        button("♫  Nghe phát âm",outlined=true) { speak(word.english) }
        if(flipped) {
            button("✓  Đã nhớ",Palette.green) { answer(word,true) }
            button("↻  Cần ôn lại",Palette.orange,outlined=true) { answer(word,false) }
        } else button("Lật thẻ",Palette.purple) { flipped=true; refresh() }
        notice("Hãy tự đánh giá sau khi xem nghĩa. Các thẻ cần ôn sẽ tiếp tục ở trạng thái đang học.")
    }
    private fun answer(word: Word,known: Boolean) {
        store.practice(word.id,known); if(known) remembered++; index++; flipped=false; refresh(keepScrollPosition=false)
    }
}

class QuizFragment : ScreenFragment() {
    private var index=0
    private var correct=0
    private var selected: String?=null
    private var draft=""
    private var recorded=false
    private var ids=emptyList<String>()
    private var sessionId=""
    private var wrongIds=mutableListOf<String>()
    private val mode get()=arguments?.getString("mode") ?: "mixed"
    private val total get()=ids.size
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        ids=state?.getStringArrayList("ids") ?: quizzes.createSession(store.saved)
        sessionId=state?.getString("sessionId") ?: java.util.UUID.randomUUID().toString()
        wrongIds=(state?.getStringArrayList("wrongIds") ?: arrayListOf()).toMutableList()
        index=state?.getInt("index") ?: 0; correct=state?.getInt("correct") ?: 0
        selected=state?.getString("selected"); draft=state?.getString("draft") ?: ""; recorded=state?.getBoolean("recorded") ?: false
        requireActivity().onBackPressedDispatcher.addCallback(this,object: OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { confirmExit() }
        })
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state); state.putStringArrayList("ids",ArrayList(ids)); state.putInt("index",index)
        state.putInt("correct",correct); state.putString("selected",selected); state.putString("draft",draft); state.putBoolean("recorded",recorded)
        state.putString("sessionId",sessionId); state.putStringArrayList("wrongIds",ArrayList(wrongIds))
    }
    override fun render() {
        if (ids.isEmpty() || index !in ids.indices || words.find(ids[index])==null) {
            header("LUYỆN TẬP","Chưa có câu hỏi",back=true)
            notice("Hãy quay lại và bắt đầu bài luyện mới.")
            return
        }
        header("THỬ THÁCH NHỎ", "Quiz từ vựng", "Câu ${index+1} / $total")
        text("‹  Thoát bài luyện",14,Palette.blue).apply { minHeight=dp(48); setOnClickListener { confirmExit() } }
        progress(index,total,color=Palette.green)
        val word=words.find(ids[index]) ?: return
        val kind=if(mode=="mixed") listOf("image","word","listen","fill")[index%4] else mode
        val prompt=column(color=Palette.elevated,padding=24)
        prompt.id=R.id.quiz_prompt
        prompt.tag=word.id
        text(when(kind) { "image" -> "Hình này là gì trong tiếng Anh?"; "word" -> "Chọn hình tương ứng với từ"; "listen" -> "Nghe và chọn từ bạn nghe được"; else -> "Viết từ tiếng Anh cho hình này" },18,bold=true,parent=prompt,center=true)
        when(kind) {
            "word" -> text(word.english,36,Palette.blue,true,prompt,true)
            "listen" -> button("♫  Bấm để nghe",parent=prompt) { speak(word.english) }
            else -> text(word.symbol,78,parent=prompt,center=true)
        }
        if(kind=="fill") {
            val input=field("Nhập từ tiếng Anh",draft,viewId=R.id.input_quiz_answer)
            // The model owns this draft so an old question's view state cannot overwrite it.
            input.isSaveEnabled=false
            input.isEnabled=selected==null
            input.addTextChangedListener(object: android.text.TextWatcher {
                override fun beforeTextChanged(s: CharSequence?,start: Int,count: Int,after: Int) {}
                override fun onTextChanged(s: CharSequence?,start: Int,before: Int,count: Int) { draft=s.toString() }
                override fun afterTextChanged(s: android.text.Editable?) {}
            })
            if(selected==null) button("Kiểm tra đáp án",Palette.green) {
                if(draft.trim().isEmpty()) input.error="Hãy nhập đáp án" else check(word,draft.trim())
            }
        } else {
            val choices=quizzes.question(word.id,index).optionIds.mapNotNull { words.find(it) }
            choices.forEach { option ->
                val label=if(kind=="word") option.symbol else option.english
                val answered = selected != null
                val isCorrectOption = option.id == word.id
                val isSelectedWrong = answered && selected == option.english && !isCorrectOption
                val color=when {
                    answered && isCorrectOption -> Palette.green
                    isSelectedWrong -> Palette.red
                    else -> Palette.blue
                }
                val highlighted = answered && (isCorrectOption || isSelectedWrong)
                button(label,color,outlined=!highlighted) { if(selected==null) check(word,option.english) }.apply {
                    if(kind=="word") { textSize=30f; contentDescription="Hình ${option.meaning}" }
                    if (answered && isCorrectOption) contentDescription = "$label. Đáp án đúng"
                    if (isSelectedWrong) contentDescription = "$label. Bạn đã chọn sai"
                    if(selected!=null) isClickable=false
                }
            }
        }
        if(selected!=null) {
            val right=selected.equals(word.english,true)
            val feedback=column(color=Palette.surface)
            text(if(right) "✓  Chính xác!" else "✕  Chưa chính xác",19,if(right) Palette.green else Palette.red,true,feedback)
            text("${word.english} • ${word.meaning}",16,parent=feedback)
            text(word.example,13,Palette.muted,parent=feedback)
            button(if(index+1==total) "Xem kết quả  →" else "Câu tiếp theo  →",Palette.green) {
                if(index+1==total) finish() else { index++; selected=null; draft=""; refresh(keepScrollPosition=false) }
            }
        }
    }
    private fun check(word: Word,answer: String) {
        if(selected!=null) return
        selected=answer
        val right=answer.equals(word.english,true)
        if(right) correct++ else wrongIds.add(word.id)
        hideKeyboard()
        // Quiz is practice; only explicit Flashcard self-assessment changes mastery.
        val previous=word.id in store.mastered
        store.practice(word.id,previous)
        refresh()
    }
    private fun finish() {
        if (findNavController().currentDestination?.id != R.id.quizFragment) return
        if(!recorded) {
            store.recordQuiz(sessionId,correct,total); recorded=true
        }
        findNavController().navigate(R.id.quizResultFragment,bundleOf("correct" to correct,"total" to total,"mode" to mode,"wrongIds" to ArrayList(wrongIds)),
            NavOptions.Builder().setPopUpTo(R.id.quizFragment,true).build())
    }
    private fun confirmExit() {
        MaterialAlertDialogBuilder(requireContext()).setTitle("Dừng bài Quiz?").setMessage("Kết quả bài chưa hoàn thành sẽ không được lưu. Các lượt luyện đã làm vẫn được tính.")
            .setNegativeButton("Tiếp tục",null).setPositiveButton("Dừng") { _, _ -> findNavController().popBackStack() }.show()
    }
}

class QuizResultFragment : ScreenFragment() {
    override fun render() {
        val correct=arguments?.getInt("correct") ?: 0
        val total=arguments?.getInt("total") ?: 8
        header("THỬ THÁCH HOÀN THÀNH", "Bạn vừa tiến bộ thêm!",back=true)
        val card=column(color=Palette.elevated,padding=28)
        text("🏆",76,parent=card,center=true)
        text("$correct / $total",46,Palette.green,true,card,true)
        text("câu trả lời chính xác",15,Palette.muted,parent=card,center=true)
        progress(correct,total,card,Palette.green)
        text(if(correct==total) "Tuyệt vời, bạn đã nhớ rất tốt." else "Ôn lại một chút, lần sau sẽ tốt hơn.",16,parent=card,center=true)
        stats("${correct*100/total.coerceAtLeast(1)}%" to "Độ chính xác",store.streak.toString() to "Ngày liên tiếp")
        button("Làm lại Quiz",Palette.green) {
            findNavController().navigate(R.id.quizFragment,bundleOf("mode" to (arguments?.getString("mode") ?: "mixed")),
                NavOptions.Builder().setPopUpTo(R.id.quizResultFragment,true).build())
        }
        button("Ôn tập bằng Flashcard",Palette.purple,outlined=true) { go(R.id.flashcardFragment) }
        button("Xem tiến độ học tập",outlined=true) { go(R.id.progressFragment) }
        val mistakes=arguments?.getStringArrayList("wrongIds")?.distinct() ?: emptyList()
        if (mistakes.isNotEmpty()) {
            section("Từ cần ôn lại")
            notice("Lưu từ vào bộ sưu tập để học lại sau. Bỏ lưu chỉ thay đổi bộ sưu tập, không xóa từ khỏi kết quả Quiz.")
            button("Ôn các từ trả lời sai",Palette.purple) { go(R.id.flashcardFragment,"wordIds" to ArrayList(mistakes)) }
            mistakes.mapNotNull { words.find(it) }.forEach { wordRow(it,showSaveLabel=true) }
        }
    }
}
