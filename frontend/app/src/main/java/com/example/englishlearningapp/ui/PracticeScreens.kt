package com.example.englishlearningapp.ui

import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.core.os.bundleOf
import androidx.navigation.NavOptions
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.Word
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.data.mapper.toWord
import androidx.lifecycle.lifecycleScope
import android.view.View
import kotlinx.coroutines.launch
import java.util.UUID
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class PracticeFragment : ScreenFragment() {
    override fun render() {
        header("MỖI NGÀY MỘT CHÚT", "Luyện tập & ghi nhớ", "Kiến thức ở lại khi bạn dành thời gian ôn luyện.")
        val hero=column(color=Palette.elevated,padding=22)
        text("▣",44,Palette.purple,parent=hero)
        text("Lật thẻ, mở trí nhớ",25,bold=true,parent=hero)
        text("${store.saved.size} từ đã lưu • Luyện theo nhịp của bạn",14,Palette.muted,parent=hero)
        button("Bắt đầu Flashcard  →",Palette.purple,hero) { go(R.id.flashcardFragment) }
        quizzes.resumeMode?.let { mode ->
            button("Tiếp tục bài Quiz đang làm",Palette.green) { go(R.id.quizFragment,"mode" to mode) }
        }
        section("Thử thách Quiz")
        tile("🍎","Nhìn ảnh chọn từ","Ghép hình minh họa với từ tiếng Anh",Palette.green) { go(R.id.quizFragment,"mode" to "image") }
        tile("▦","Nhìn từ chọn ảnh","Chọn hình minh họa đúng với từ",Palette.purple) { go(R.id.quizFragment,"mode" to "word") }
        tile("♫","Nghe chọn đáp án","Luyện nghe bằng giọng đọc trên thiết bị",Palette.blue) { go(R.id.quizFragment,"mode" to "listen") }
        tile("✎","Điền từ còn thiếu","Nhìn hình và viết lại từ tiếng Anh",Palette.orange) { go(R.id.quizFragment,"mode" to "fill") }
        button("Thử thách tổng hợp • 8 câu",Palette.green) { go(R.id.quizFragment,"mode" to "mixed") }
        notice("Câu hỏi lấy từ kho từ trên máy chủ, ưu tiên từ đã lưu. Bắt đầu dạng khác sẽ dừng bài Quiz đang làm. Hình minh họa hiện dùng biểu tượng và nghĩa tiếng Việt.")
    }
}

class FlashcardFragment : ScreenFragment() {
    private var ids=emptyList<String>()
    private var keys=emptyList<String>()
    private var index=0
    private var flipped=false
    private var remembered=0
    private var loading=true
    private var sending=false
    private var failure: String?=null
    private var pendingAnswer: Boolean?=null
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        ids=state?.getStringArrayList("ids") ?: arguments?.getStringArrayList("wordIds")
            ?: arguments?.getString("wordId")?.let { listOf(it) } ?: emptyList()
        keys=state?.getStringArrayList("keys") ?: emptyList()
        index=state?.getInt("index") ?: 0;flipped=state?.getBoolean("flipped") ?: false
        remembered=state?.getInt("remembered") ?: 0
        if (state?.containsKey("pending")==true) pendingAnswer=state.getBoolean("pending")
    }
    override fun onSaveInstanceState(state: Bundle) {
        super.onSaveInstanceState(state)
        state.putStringArrayList("ids",ArrayList(ids));state.putStringArrayList("keys",ArrayList(keys))
        state.putInt("index",index);state.putBoolean("flipped",flipped);state.putInt("remembered",remembered)
        pendingAnswer?.let { state.putBoolean("pending",it) }
    }
    override fun onViewCreated(view: View,savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState);load()
    }
    private fun load() {
        loading=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            val result=collections.load()
            result.onSuccess {
                words.loadFromApi()
                learning.load().onSuccess {
                    if (ids.isEmpty()) ids=store.saved.sorted()
                    ids=ids.distinct().filter { words.find(it)!=null }
                    if (keys.size!=ids.size) keys=ids.map { UUID.randomUUID().toString() }
                }.onFailure { failure=it.message }
            }.onFailure { failure=it.message }
            loading=false;refresh()
        }
    }
    override fun render() {
        header("HỌC ÍT, NHỚ LÂU","Flashcard",back=true)
        if (loading) { notice("Đang tải bộ thẻ và tiến độ…");return }
        if (failure!=null && pendingAnswer==null) { notice(failure!!);button("Thử lại") { load() };return }
        if (ids.isEmpty()) { notice("Lưu từ vào bộ sưu tập để bắt đầu học.");button("Khám phá từ vựng") { go(R.id.topicsFragment) };return }
        if (index>=ids.size) {
            text("Một bước tiến thật tốt!",25,bold=true)
            stats("$remembered / ${ids.size}" to "Thẻ đã nhớ")
            notice("Kết quả học đã được lưu.")
            button("Ôn lại bộ thẻ") { index=0;remembered=0;flipped=false;keys=ids.map { UUID.randomUUID().toString() };refresh() }
            button("Xem tiến độ",outlined=true) { go(R.id.progressFragment) };return
        }
        val word=words.find(ids[index]) ?: return
        text("THẺ ${index+1} / ${ids.size}",12,Palette.blue,true)
        progress(index,ids.size,color=Palette.purple)
        val card=column(color=Palette.elevated,padding=26)
        text(word.symbol,76,parent=card,center=true)
        text(if (flipped) word.meaning else word.english,30,bold=true,parent=card,center=true)
        text(if (flipped) word.english+"  "+word.ipa else word.ipa,17,Palette.blue,parent=card,center=true)
        if (flipped) text(word.example,16,parent=card,center=true)
        card.setOnClickListener { if (!sending && pendingAnswer==null) { flipped=!flipped;refresh() } }
        button("♫  Nghe phát âm",outlined=true) { speak(word.english) }
        if (sending) notice("Đang lưu kết quả…")
        else if (pendingAnswer!=null) {
            notice(failure ?: "Chưa xác nhận được kết quả học.")
            button("Thử lưu lại") { answer(word,pendingAnswer!!) }
        } else if (flipped) {
            button("✓  Đã nhớ",Palette.green) { answer(word,true) }
            button("↻  Cần ôn lại",Palette.orange,outlined=true) { answer(word,false) }
        } else button("Lật thẻ") { flipped=true;refresh() }
    }
    private fun answer(word: Word,known: Boolean) {
        if (sending) return
        sending=true;failure=null;pendingAnswer=known;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            learning.review(ReviewRequest(word.id.toLong(),known,keys[index])).onSuccess {
                if (known) remembered++
                index++;flipped=false;pendingAnswer=null
            }.onFailure { failure=it.message }
            sending=false;refresh(false)
        }
    }
}

class QuizFragment : ScreenFragment() {
    private var attempt: QuizAttemptDto?=null
    private var index=0
    private var feedback: QuizFeedbackDto?=null
    private var draft=""
    private var pendingAnswer: String?=null
    private var loading=true
    private var sending=false
    private var failure: String?=null
    private val mode get()=arguments?.getString("mode") ?: "mixed"
    override fun onViewCreated(view: View,savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState)
        requireActivity().onBackPressedDispatcher.addCallback(viewLifecycleOwner,object: OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { confirmExit() }
        })
        load()
    }
    private fun load() {
        loading=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            quizzes.start(mode).onSuccess {
                attempt=it;index=it.answeredCount;feedback=null;pendingAnswer=null
                if (it.completed) showResult(it)
            }.onFailure { failure=it.message }
            loading=false;refresh()
        }
    }
    override fun render() {
        val data=attempt
        header("THỬ THÁCH NHỎ","Quiz từ vựng",if(data!=null) "Câu ${minOf(index+1,data.totalQuestions)} / ${data.totalQuestions}" else "")
        if (loading) { notice("Đang tải bài Quiz…");return }
        if (data==null) { notice(failure ?: "Chưa tải được bài Quiz.");button("Thử lại") { load() };return }
        text("‹  Thoát bài luyện",14,Palette.blue).apply { minHeight=dp(48);setOnClickListener { confirmExit() } }
        if (index>=data.totalQuestions) {
            failure?.let { notice(it) }
            button(if(sending) "Đang lưu kết quả…" else "Xem kết quả  →",Palette.green) { finish() }.isEnabled=!sending
            return
        }
        val question=data.questions[index]
        val word=question.word.toWord()
        val kind=question.questionType
        progress(index,data.totalQuestions,color=Palette.green)
        val prompt=column(color=Palette.elevated,padding=24)
        prompt.id=R.id.quiz_prompt;prompt.tag=question.questionId
        text(when(kind) {
            "WORD_TO_IMAGE"->"Chọn biểu tượng và nghĩa tương ứng"
            "LISTENING"->"Nghe và chọn từ bạn nghe được"
            "FILL_BLANK"->"Viết từ tiếng Anh tương ứng"
            else->"Chọn từ tiếng Anh tương ứng"
        },18,bold=true,parent=prompt,center=true)
        when(kind) {
            "WORD_TO_IMAGE" -> text(word.english,34,Palette.blue,true,prompt,true)
            "LISTENING" -> button("♫  Bấm để nghe",parent=prompt) { speak(word.english) }
            else -> { text(word.symbol,76,parent=prompt,center=true);text(word.meaning,16,parent=prompt,center=true) }
        }
        if (kind=="FILL_BLANK") {
            val input=field("Nhập từ tiếng Anh",draft,viewId=R.id.input_quiz_answer)
            input.isSaveEnabled=false;input.isEnabled=feedback==null && !sending && pendingAnswer==null
            input.addTextChangedListener(object: android.text.TextWatcher {
                override fun beforeTextChanged(s: CharSequence?,start: Int,count: Int,after: Int) {}
                override fun onTextChanged(s: CharSequence?,start: Int,before: Int,count: Int) { draft=s.toString() }
                override fun afterTextChanged(s: android.text.Editable?) {}
            })
            if (feedback==null && pendingAnswer==null) button("Kiểm tra đáp án",Palette.green) {
                if (draft.trim().isEmpty()) input.error="Hãy nhập đáp án" else answer(draft.trim())
            }.isEnabled=!sending
        } else question.options.forEach { dto ->
            val option=dto.toWord()
            val label=if(kind=="WORD_TO_IMAGE") "${option.symbol} ${option.meaning}" else option.english
            val correct=feedback?.correctChoiceKey==option.id
            val wrong=feedback!=null && feedback?.userAnswer==option.id && !correct
            button(label,if(correct) Palette.green else if(wrong) Palette.red else Palette.blue,outlined=feedback==null) {
                answer(option.id)
            }.apply { isEnabled=feedback==null && !sending && pendingAnswer==null }
        }
        if (sending) notice("Đang gửi đáp án…")
        if (failure!=null) notice(failure!!)
        if (pendingAnswer!=null && !sending && feedback==null) button("Thử gửi lại đáp án") { answer(pendingAnswer!!) }
        feedback?.let { result ->
            val info=column(color=Palette.surface)
            text(if(result.isCorrect) "✓  Chính xác!" else "✕  Chưa chính xác",19,if(result.isCorrect) Palette.green else Palette.red,true,info)
            text("${result.correctAnswer} • ${word.meaning}",16,parent=info)
            text(word.example,13,Palette.muted,parent=info)
            button(if(index+1==data.totalQuestions) "Xem kết quả  →" else "Câu tiếp theo  →",Palette.green) {
                if (index+1==data.totalQuestions) finish() else { index++;feedback=null;draft="";failure=null;refresh(false) }
            }.isEnabled=!sending
        }
    }
    private fun answer(value: String) {
        if (sending || feedback!=null) return
        val data=attempt ?: return
        val question=data.questions[index]
        pendingAnswer=value;sending=true;failure=null;hideKeyboard();refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            quizzes.answer(data.attemptId,question.questionId,value).onSuccess {
                feedback=it.feedback;pendingAnswer=null
                attempt=data.copy(answeredCount=data.answeredCount+1,
                    correctAnswers=data.correctAnswers+if(it.feedback.isCorrect) 1 else 0,answers=data.answers+it.feedback)
            }.onFailure { failure=it.message }
            sending=false;refresh()
        }
    }
    private fun finish() {
        if (sending) return
        val data=attempt ?: return
        sending=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            quizzes.complete(data.attemptId).onSuccess { showResult(it) }.onFailure { failure=it.message }
            sending=false;refresh()
        }
    }
    private fun showResult(data: QuizAttemptDto) {
        if (findNavController().currentDestination?.id!=R.id.quizFragment) return
        val wrong=data.answers.filter { !it.isCorrect }.map { it.word.vocabularyId.toString() }.distinct()
        findNavController().navigate(R.id.quizResultFragment,bundleOf("correct" to data.correctAnswers,"total" to data.totalQuestions,
            "mode" to mode,"wrongIds" to ArrayList(wrong)),NavOptions.Builder().setPopUpTo(R.id.quizFragment,true).build())
    }
    private fun confirmExit() {
        MaterialAlertDialogBuilder(requireContext()).setTitle("Rời bài Quiz?")
            .setMessage("Các câu đã gửi được lưu. Bạn có thể tiếp tục bài này trong mục Luyện tập.")
            .setNegativeButton("Tiếp tục",null).setPositiveButton("Rời bài") { _,_ -> findNavController().popBackStack() }.show()
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
