package com.example.englishlearningapp.ui

import android.content.res.ColorStateList
import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.core.os.bundleOf
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.example.englishlearningapp.MainActivity
import com.example.englishlearningapp.R
import com.example.englishlearningapp.data.model.*
import com.example.englishlearningapp.game.*
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.gson.Gson
import kotlinx.coroutines.launch
import kotlinx.coroutines.ensureActive

class DefenseSetupFragment: ScreenFragment() {
    private var mode="RECALL"
    private var loading=true
    override fun onCreate(state: Bundle?) { super.onCreate(state);mode=state?.getString("mode") ?: "RECALL" }
    override fun onSaveInstanceState(state: Bundle) { state.putString("mode",mode);super.onSaveInstanceState(state) }
    override fun onViewCreated(view: View,state: Bundle?) {
        super.onViewCreated(view,state)
        viewLifecycleOwner.lifecycleScope.launch { words.loadTopics();loading=false;refresh() }
    }
    override fun render() {
        header("GÕ CHỮ • GIỮ THÀNH", "Phòng tuyến từ vựng", "Bảo vệ căn cứ trên 4 đường. Xoay ngang để có chiến trường rộng hơn.", true)
        val hero=column(color=Palette.elevated,padding=20)
        text("🛡  BỐN ĐƯỜNG • MỘT CĂN CỨ",18,Palette.green,true,hero)
        text("Quái thường • Chạy nhanh • Giáp • Boss 3 lớp từ",14,parent=hero)
        if((requireActivity() as MainActivity).defense.canResume) button("Tiếp tục phòng tuyến",Palette.green,hero) { go(R.id.wordDefenseFragment) }
        section("Chọn cách luyện")
        button("${if(mode=="TYPING") "✓ " else ""}Luyện gõ • Hiện từ tiếng Anh",outlined=true) { mode="TYPING";refresh() }
        button("${if(mode=="RECALL") "✓ " else ""}Luyện nhớ • Nghĩa Việt và ô trống",outlined=true) { mode="RECALL";refresh() }
        section("Chọn nguồn từ")
        button("Chơi phòng tuyến ngẫu nhiên",Palette.green) { start("RANDOM") }
        button("Phòng tuyến theo chủ đề",outlined=true) {
            if(loading) { toast("Đang tải chủ đề…");return@button }
            if(words.topics.isEmpty()) { toast("Chưa tải được chủ đề. Hãy mở lại màn này.");return@button }
            val choices=words.topics
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn chủ đề").setItems(choices.map { "${it.name} • ${it.vocabularyCount} từ" }.toTypedArray()) { _,i -> start("TOPIC",choices[i].id.toLong()) }.show()
        }
        button("Phòng tuyến từ đã lưu / từ khó",outlined=true) {
            MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn bộ từ ôn tập")
                .setItems(arrayOf("Từ đã lưu","Từ khó","Kết hợp đã lưu và khó")) { _,i -> start(listOf("SAVED","DIFFICULT","REVIEW")[i]) }.show()
        }
        notice("Chạm quái để ngắm. Mỗi chữ đúng bắn một viên đạn. Sai chữ chỉ báo hiệu ứng; chữ đúng và combo được giữ. Quái lọt căn cứ làm đứt combo; lần thứ 4 thua.")
        notice("Hạ 5 từ tích đủ một lần làm chậm 6 giây. Mỗi màn tối đa 20 từ, nghỉ giữa các đợt 5 từ. Boss xuất hiện mỗi màn thứ 5: tối đa 3 lớp từ cuối màn; một lớp lọt căn cứ tính một lượt bỏ lỡ.")
        notice("Từ đã đúng trong màn đã vượt không lặp ở màn sau. Sau 5 màn chọn tiếp tục hoặc kết thúc chặng; hết bộ từ tự hoàn thành. Kết quả cập nhật tiến độ và lịch ôn.")
    }
    private fun start(source: String,topic: Long?=null) {
        val action={ go(R.id.wordDefenseFragment,"source" to source,"topic" to topic,"learningMode" to mode) }
        if((requireActivity() as MainActivity).defense.canResume) MaterialAlertDialogBuilder(requireContext()).setTitle("Bắt đầu phòng tuyến mới?")
            .setMessage("Kết quả cũ được giữ. Nút tiếp tục sẽ trỏ đến lượt mới.").setPositiveButton("Bắt đầu") { _,_ -> action() }.setNegativeButton("Hủy",null).show()
        else action()
    }
}

class WordDefenseFragment : Fragment() {
    private val host get()=requireActivity() as MainActivity
    private val gson=Gson()
    private var layout: LinearLayout?=null
    private var run: GameRunDto?=null
    private var engine: WordDefenseEngine?=null
    private var arena: WordDefenseView?=null
    private var hud: TextView?=null
    private var focus: TextView?=null
    private var pauseButton: MaterialButton?=null
    private var busy=false
    private var startIssued=false
    private var ownerToken: String?=null
    override fun onCreate(state: Bundle?) {
        super.onCreate(state);startIssued=state?.getBoolean("startIssued") ?: false
    }
    override fun onCreateView(inflater: LayoutInflater,parent: ViewGroup?,state: Bundle?): View = LinearLayout(requireContext()).also {
        it.orientation=LinearLayout.VERTICAL;it.setPadding(dp(10),dp(6),dp(10),dp(6));it.setBackgroundColor(Palette.background)
        layout=it
    }
    override fun onViewCreated(view: View,state: Bundle?) {
        ownerToken=host.store.token
        requireActivity().onBackPressedDispatcher.addCallback(viewLifecycleOwner,object: OnBackPressedCallback(true) {
            override fun handleOnBackPressed() { exit() }
        })
        load()
    }
    override fun onSaveInstanceState(state: Bundle) {
        save();state.putBoolean("startIssued",startIssued);super.onSaveInstanceState(state)
    }
    private fun load() {
        if(busy) return
        busy=true;message("Đang lấy bộ từ từ máy chủ…")
        val activity=host
        val currentOwner=viewLifecycleOwner
        val previous=activity.store.activeDefense
        currentOwner.lifecycleScope.launch {
            val source=if(startIssued) null else arguments?.getString("source")
            val topic=arguments?.getLong("topic",0)?.takeIf { it>0 }
            val result=activity.defense.start(source,topic,arguments?.getString("learningMode") ?: "RECALL")
            ensureActive()
            if(!isAdded || layout==null || currentOwner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            if(activity.store.activeDefense!=previous) startIssued=true
            busy=false
            result.onSuccess { startIssued=true;accept(it) }.onFailure { error(it.message ?: "Không tải được màn chơi.") { load() } }
        }
    }
    private fun accept(data: GameRunDto) {
        run=data
        if(data.round.status!="PLAYING") { engine=null;showResult(data);return }
        val words=data.round.words.map { ShooterWord(it.vocabularyId,it.word,it.meanings.firstOrNull()?.meaningVi.orEmpty()) }
        val restored=runCatching { host.store.localDefenseState?.let { gson.fromJson(it,DefenseState::class.java) } }.getOrNull()
            ?.takeIf { WordDefenseEngine.valid(it,words,data.round.roundId) }
        engine=WordDefenseEngine(words,data.round.stage,data.learningMode,restored ?: DefenseState(data.round.roundId))
        save()
        if(engine!!.ended) submit() else showPlay()
    }
    private var slowButton: MaterialButton?=null
    private fun showPlay() {
        val box=layout ?: return;box.removeAllViews()
        val game=engine ?: return
        val top=LinearLayout(requireContext()).apply { orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL }
        box.addView(top,LinearLayout.LayoutParams(-1,dp(48)))
        action("‹",top) { exit() }.apply {
            contentDescription="Rời phòng tuyến";layoutParams=LinearLayout.LayoutParams(dp(42),dp(44));minWidth=0;minimumWidth=0;setPadding(0,0,0,0)
        }
        hud=label("",12,Palette.white,top).apply { layoutParams=LinearLayout.LayoutParams(0,-2,1f) }
        slowButton=action("❄",top) {
            if(game.slow()) { save();updateHud();arena?.invalidate();arena?.requestFocus() }
        }.apply { id=R.id.defense_slow;layoutParams=LinearLayout.LayoutParams(dp(128),dp(44));textSize=11f;setPadding(0,0,0,0) }
        pauseButton=action("Tiếp tục",top) { togglePause() }.apply {
            id=R.id.defense_pause;layoutParams=LinearLayout.LayoutParams(dp(94),dp(44));textSize=11f;setPadding(0,0,0,0)
        }
        val landscape=resources.configuration.orientation==android.content.res.Configuration.ORIENTATION_LANDSCAPE
        val play=LinearLayout(requireContext()).apply { orientation=if(landscape) LinearLayout.HORIZONTAL else LinearLayout.VERTICAL }
        box.addView(play,LinearLayout.LayoutParams(-1,0,1f))
        val keysPanel=LinearLayout(requireContext()).apply { orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER_VERTICAL }
        arena=WordDefenseView(requireContext(),game).also { surface ->
            surface.id=R.id.defense_arena
            surface.onChanged={ save();updateHud() };surface.onFinished={ submit() };surface.onSpoken={ host.speak(it) }
            play.addView(surface,if(landscape) LinearLayout.LayoutParams(0,-1,1.5f) else LinearLayout.LayoutParams(-1,0,1f))
        }
        play.addView(keysPanel,if(landscape) LinearLayout.LayoutParams(0,-1,1f) else LinearLayout.LayoutParams(-1,-2))
        focus=label("",12,Palette.blue,keysPanel).apply { minHeight=dp(48);maxLines=3;gravity=Gravity.CENTER_VERTICAL }
        listOf("QWERTYUIOP","ASDFGHJKL","ZXCVBNM").forEach { letters ->
            val row=LinearLayout(requireContext()).apply { orientation=LinearLayout.HORIZONTAL }
            keysPanel.addView(row,LinearLayout.LayoutParams(-1,dp(42)))
            letters.forEach { char ->
                val key=MaterialButton(requireContext()).apply {
                    id=resources.getIdentifier("game_key_${char.lowercaseChar()}","id",requireContext().packageName)
                    text=char.toString();textSize=14f;isAllCaps=false;cornerRadius=dp(7);minWidth=0;minimumWidth=0
                    insetTop=dp(1);insetBottom=dp(1);setPadding(0,0,0,0)
                    setTextColor(Palette.white);backgroundTintList=ColorStateList.valueOf(Palette.elevated)
                    contentDescription="Bắn chữ $char";setOnClickListener { arena?.fire(char) }
                }
                row.addView(key,LinearLayout.LayoutParams(0,-1,1f).apply { setMargins(dp(1),0,dp(1),0) })
            }
        }
        label("Chạm quái để ngắm • Sai chữ giữ combo • Hạ 5 từ tích đủ làm chậm",10,Palette.muted,box).gravity=Gravity.CENTER
        updateHud();arena?.requestFocus()
    }
    private fun updateHud() {
        val game=engine ?: return
        hud?.text="Màn ${game.stage} • ${game.state.outcomes.size}/${game.words.size} từ • ${if(game.learningMode=="TYPING") "Gõ" else "Nhớ"}\nCombo ${game.combo} • Lọt ${game.misses}/3"
        val target=game.target
        focus?.text=if(target==null) "4 đường • Chọn mục tiêu" else "Đang ngắm: ${game.words[target.index].meaning}\n${if(game.learningMode=="TYPING") game.words[target.index].english.uppercase()+" • " else ""}${game.masked(target)}"
        arena?.contentDescription=focus?.text.toString()+". Combo ${game.combo}. Lọt ${game.misses}."
        pauseButton?.text=if(game.paused) "Tiếp tục" else "Tạm dừng"
        slowButton?.text=if(game.state.slowRemaining>0f) "❄ Đang làm chậm" else "❄ Làm chậm ${game.state.energy}%"
        slowButton?.isEnabled=!game.paused && game.state.energy==100 && game.state.slowRemaining<=0f
    }
    private fun togglePause() {
        val game=engine ?: return
        game.paused=!game.paused;save();updateHud();arena?.invalidate();arena?.requestFocus()
    }
    private fun pause() { engine?.paused=true;save();updateHud();arena?.invalidate() }
    private fun save() {
        if(!isAdded || host.store.token!=ownerToken) return
        engine?.let { host.store.localDefenseState=gson.toJson(it.state) }
    }
    private fun submit() {
        if(busy || !isAdded || view==null || layout==null) return
        val data=run ?: return;val game=engine ?: return
        if(!game.ended) return
        pause();busy=true;message("Đang lưu kết quả màn chơi…")
        val request=GameFinishRequest(game.state.outcomes.map { GameOutcomeDto(it.id,if(it.solved) "SOLVED" else "MISSED",it.answer,it.mistakes) })
        val activity=host
        val currentOwner=viewLifecycleOwner
        currentOwner.lifecycleScope.launch {
            val result=activity.defense.finish(data,request)
            ensureActive()
            if(!isAdded || layout==null || currentOwner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            result.onSuccess { busy=false;accept(it) }
                .onFailure { busy=false;error(it.message ?: "Chưa lưu được kết quả.") { submit() } }
        }
    }
    private fun next() {
        if(busy) return
        val data=run ?: return
        busy=true;message("Đang chuẩn bị màn tiếp theo…")
        val activity=host
        val currentOwner=viewLifecycleOwner
        currentOwner.lifecycleScope.launch {
            val result=activity.defense.next(data)
            ensureActive()
            if(!isAdded || layout==null || currentOwner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            result.onSuccess { busy=false;accept(it) }
                .onFailure { busy=false;error(it.message ?: "Chưa chuyển được màn.") { next() } }
        }
    }
    private fun complete() {
        val data=run ?: return
        if(busy)return
        busy=true;message("Đang kết thúc chặng…")
        val activity=host
        viewLifecycleOwner.lifecycleScope.launch {
            val result=activity.defense.complete(data);ensureActive()
            if(!isAdded || layout==null)return@launch
            busy=false;result.onSuccess { accept(it) }.onFailure { error(it.message ?: "Chưa kết thúc được chặng") { complete() } }
        }
    }
    private fun showResult(data: GameRunDto) {
        val root=layout ?: return;root.removeAllViews();arena=null
        val scroll=ScrollView(requireContext());root.addView(scroll,LinearLayout.LayoutParams(-1,-1))
        val box=LinearLayout(requireContext()).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(16),dp(10),dp(16)) };scroll.addView(box)
        val stage=data.round;val passed=stage.status=="PASSED"
        label(if(data.completed) "CHẶNG CHƠI HOÀN THÀNH" else "KẾT QUẢ MÀN ${stage.stage}",12,Palette.blue,box)
        label(if(passed && stage.maxCombo==20) "HOÀN HẢO!" else if(passed) "Vượt màn!" else "Thử lại nhé!",30,if(passed) Palette.green else Palette.orange,box)
        label("${stage.correctCount}/${stage.words.size} từ đúng • ${stage.missedCount} từ lọt căn cứ",16,Palette.white,box)
        label("Combo cao nhất: ${stage.maxCombo} • Điểm màn: ${stage.score}\nTổng điểm lượt chơi: ${data.totalScore}",16,Palette.purple,box)
        label("Kết quả đã lưu trên máy chủ.",13,Palette.muted,box)
        val missed=stage.results.filter { it.outcome=="MISSED" }
        if(missed.isNotEmpty()) {
            label("Những từ cần ôn lại",20,Palette.white,box)
            missed.forEach { result ->
                val word=stage.words.first { it.vocabularyId==result.vocabularyId }
                action("♫  ${word.word} • ${word.meanings.firstOrNull()?.meaningVi.orEmpty()}",box,Palette.elevated) { host.speak(word.word) }
            }
        }
        if(!data.completed) {
            label(if(passed) "Màn sau giữ từ bỏ lỡ, thêm từ mới và loại từ đã đúng." else "Chơi lại cùng bộ từ của màn này. Các màn đã vượt vẫn được giữ.",14,Palette.muted,box)
            if(data.checkpoint) {
                label("ĐIỂM NGHỈ • Đã vượt 5 màn. Bạn có thể tiếp tục hoặc kết thúc chặng tại đây.",15,Palette.orange,box)
                action("Kết thúc chặng",box,Palette.purple) { complete() }
            }
            action(if(passed) "Màn tiếp theo →" else "Chơi lại màn ${stage.stage}",box,Palette.green) { next() }
        } else {
            label(if(data.remainingCount==0) "Bạn đã hoàn thành toàn bộ bộ từ!" else "Chặng đã kết thúc tại điểm nghỉ. Bạn có thể chọn nguồn từ cho lượt mới.",15,Palette.muted,box)
        }
        action("Về phòng tuyến",box) { returnToGames() }
    }
    private fun message(value: String) {
        layout?.removeAllViews();arena=null
        layout?.let { label(value,17,Palette.white,it) }
    }
    private fun error(value: String,retry: () -> Unit) {
        message(value)
        layout?.let { action("Thử lại",it) { retry() };action("Về phòng tuyến",it) { returnToGames() } }
    }
    private fun exit() {
        if(engine==null || run?.round?.status!="PLAYING") { returnToGames();return }
        pause()
        MaterialAlertDialogBuilder(requireContext()).setTitle("Màn chơi đã tạm dừng")
            .setMessage("Bạn có thể tiếp tục ngay hoặc quay lại sau. Tiến độ trên máy này được giữ lại.")
            .setPositiveButton("Tiếp tục") { _,_ -> if(engine?.paused==true) togglePause() }
            .setNegativeButton("Về trò chơi") { _,_ -> returnToGames() }.show()
    }
    private fun returnToGames() {
        pause()
        if(!findNavController().popBackStack(R.id.defenseSetupFragment,false)) findNavController().navigate(R.id.defenseSetupFragment)
    }
    private fun label(value: String,size: Int,color: Int,parent: LinearLayout): TextView=TextView(requireContext()).apply {
        text=value;textSize=size.toFloat();setTextColor(color);setPadding(dp(4),dp(6),dp(4),dp(6))
        parent.addView(this,LinearLayout.LayoutParams(-1,-2))
    }
    private fun action(value: String,parent: LinearLayout,color: Int=Palette.blue,click: () -> Unit): MaterialButton=MaterialButton(requireContext()).apply {
        text=value;isAllCaps=false;cornerRadius=dp(12);textSize=14f;setTextColor(if(color==Palette.elevated) Palette.white else Palette.onAccent)
        backgroundTintList=ColorStateList.valueOf(color);minHeight=dp(48)
        parent.addView(this,LinearLayout.LayoutParams(-1,-2));setOnClickListener { click() }
    }
    private fun dp(v: Int)=requireContext().dp(v)
    override fun onPause() { pause();super.onPause() }
    override fun onDestroyView() { save();busy=false;layout=null;arena=null;hud=null;focus=null;pauseButton=null;slowButton=null;super.onDestroyView() }
}
