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

class GamesFragment : ScreenFragment() {
    private var loading=true
    private var failure: String?=null
    override fun onViewCreated(view: View,savedInstanceState: Bundle?) {
        super.onViewCreated(view,savedInstanceState);loadTopics()
    }
    private fun loadTopics() {
        loading=true;failure=null;refresh()
        viewLifecycleOwner.lifecycleScope.launch {
            words.loadTopics().onFailure { failure=it.message }
            loading=false;refresh()
        }
    }
    override fun render() {
        header("CHƠI ĐỂ NHỚ","Trò chơi","Chọn trò chơi và bộ từ bạn muốn chinh phục.",true)
        val hero=column(color=Palette.elevated,padding=22)
        text("✦  BẮN CHỮ",24,Palette.orange,true,hero)
        text("Nhìn nghĩa, nhớ từ, bắn từng chữ cái!",16,parent=hero)
        text("20 từ mỗi màn • Combo từ 5 từ liên tiếp • Được bỏ lỡ 3 từ",13,Palette.muted,parent=hero)
        if(games.canResume) button("Tiếp tục / xem kết quả lượt trước",Palette.green,hero) { go(R.id.wordShooterFragment) }
        section("Chọn nguồn từ")
        tile("✧","Chơi ngẫu nhiên","Từ phù hợp trình độ • Một chặng tối đa 5 màn",Palette.blue) { start("RANDOM") }
        tile("▦","Chơi theo chủ đề","Chọn một chủ đề và đi đến khi hết từ",Palette.purple) { topics() }
        tile("↻","Ôn từ của bạn","Từ đã lưu, từ khó hoặc kết hợp cả hai",Palette.green) { review() }
        failure?.let { notice(it);button("Tải lại chủ đề",outlined=true) { loadTopics() } }
        notice("Hoàn thành từ để nối combo. Gõ sai chữ chỉ có hiệu ứng báo sai, không trừ lượt và không mất combo. Từ chạm đáy mới làm đứt chuỗi; lần chạm đáy thứ 4 sẽ thua màn.")
        notice("Nguồn ít hơn 20 từ sẽ có màn ngắn hơn. Từ đã đúng không lặp lại ở màn kế tiếp trong cùng lượt chơi.")
    }
    private fun topics() {
        if(loading) { toast("Đang tải chủ đề…");return }
        if(words.topics.isEmpty()) { toast("Chưa có chủ đề. Hãy tải lại.");return }
        val choices=words.topics
        MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn chủ đề")
            .setItems(choices.map { "${it.name} • ${it.vocabularyCount} từ" }.toTypedArray()) { _,index -> start("TOPIC",choices[index].id.toLong()) }
            .setNegativeButton("Đóng",null).show()
    }
    private fun review() {
        val sources=listOf("SAVED","DIFFICULT","REVIEW")
        MaterialAlertDialogBuilder(requireContext()).setTitle("Chọn bộ từ ôn tập")
            .setItems(arrayOf("Từ đã lưu","Từ khó • lần gần nhất trả lời sai","Kết hợp từ đã lưu và từ khó")) { _,index -> start(sources[index]) }
            .setNegativeButton("Đóng",null).show()
    }
    private fun start(source: String,topic: Long?=null) {
        val action={ go(R.id.wordShooterFragment,"source" to source,"topic" to topic) }
        if(games.canResume) MaterialAlertDialogBuilder(requireContext()).setTitle("Bắt đầu lượt chơi mới?")
            .setMessage("Lượt mới dùng bộ từ mới. Kết quả các màn đã gửi vẫn được lưu; nút tiếp tục sẽ chuyển sang lượt mới.")
            .setPositiveButton("Bắt đầu") { _,_ -> action() }.setNegativeButton("Hủy",null).show()
        else action()
    }
}

/** Full-height game view avoids putting falling targets inside a scrolling screen. */
class WordShooterFragment : Fragment() {
    private val host get()=requireActivity() as MainActivity
    private val gson=Gson()
    private var layout: LinearLayout?=null
    private var run: GameRunDto?=null
    private var engine: WordShooterEngine?=null
    private var arena: WordShooterView?=null
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
        val previous=activity.store.activeGame
        currentOwner.lifecycleScope.launch {
            val source=if(startIssued) null else arguments?.getString("source")
            val topic=arguments?.getLong("topic",0)?.takeIf { it>0 }
            val result=activity.games.start(source,topic)
            ensureActive()
            if(!isAdded || layout==null || currentOwner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            if(activity.store.activeGame!=previous) startIssued=true
            busy=false
            result.onSuccess { startIssued=true;accept(it) }.onFailure { error(it.message ?: "Không tải được màn chơi.") { load() } }
        }
    }
    private fun accept(data: GameRunDto) {
        run=data
        if(data.round.status!="PLAYING") { engine=null;showResult(data);return }
        val words=data.round.words.map { ShooterWord(it.vocabularyId,it.word,it.meanings.firstOrNull()?.meaningVi.orEmpty()) }
        val restored=runCatching { host.store.localGameState?.let { gson.fromJson(it,ShooterState::class.java) } }.getOrNull()
            ?.takeIf { it.roundId==data.round.roundId && it.next in 0..words.size &&
                it.active.all { f -> f.index in words.indices && f.typed in 0..words[f.index].english.count { c -> c in 'a'..'z' } } }
        engine=WordShooterEngine(words,data.round.stage,restored ?: ShooterState(data.round.roundId))
        if(engine!!.ended) submit() else showPlay()
    }
    private fun showPlay() {
        val box=layout ?: return;box.removeAllViews()
        val game=engine ?: return
        val row=LinearLayout(requireContext()).apply { orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL }
        box.addView(row,LinearLayout.LayoutParams(-1,-2))
        val back=action("‹",row) { exit() }
        back.contentDescription="Rời màn chơi"
        back.apply {
            layoutParams=LinearLayout.LayoutParams(dp(44),dp(46))
            minWidth=0;minimumWidth=0;setPadding(0,0,0,0)
            insetTop=0;insetBottom=0;maxLines=1
        }
        hud=label("",14,Palette.white,row).apply { layoutParams=LinearLayout.LayoutParams(0,-2,1f) }
        pauseButton=action("Bắt đầu",row) { togglePause() }.apply {
            layoutParams=LinearLayout.LayoutParams(dp(104),dp(46))
            setPadding(dp(6),0,dp(6),0);insetTop=0;insetBottom=0
            maxLines=1;ellipsize=android.text.TextUtils.TruncateAt.END
        }
        focus=label("",12,Palette.blue,box).apply { minHeight=dp(32);gravity=Gravity.CENTER_VERTICAL }
        val landscape=resources.configuration.orientation==android.content.res.Configuration.ORIENTATION_LANDSCAPE
        val playArea=if(landscape) LinearLayout(requireContext()).apply {
            orientation=LinearLayout.HORIZONTAL
            box.addView(this,LinearLayout.LayoutParams(-1,0,1f))
        } else box
        val keyboard=if(landscape) LinearLayout(requireContext()).apply {
            orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER_VERTICAL
        } else box
        arena=WordShooterView(requireContext(),game).also { surface ->
            surface.id=R.id.game_arena
            surface.onChanged={ save();updateHud() }
            surface.onFinished={ submit() }
            surface.onSpoken={ host.speak(it) }
            playArea.addView(surface,(if(landscape) LinearLayout.LayoutParams(0,-1,1.2f) else LinearLayout.LayoutParams(-1,0,1f)).apply { topMargin=dp(4);bottomMargin=dp(6) })
        }
        if(landscape) playArea.addView(keyboard,LinearLayout.LayoutParams(0,-1,1f).apply { marginStart=dp(8) })
        listOf("QWERTYUIOP","ASDFGHJKL","ZXCVBNM").forEach { letters ->
            val keys=LinearLayout(requireContext()).apply { orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER }
            keyboard.addView(keys,LinearLayout.LayoutParams(-1,dp(48)))
            letters.forEach { char ->
                val key=MaterialButton(requireContext()).apply {
                    id=resources.getIdentifier("game_key_${char.lowercaseChar()}","id",requireContext().packageName)
                    text=char.toString();textSize=17f;isAllCaps=false;cornerRadius=dp(8)
                    insetTop=dp(2);insetBottom=dp(2);minWidth=0;minimumWidth=0
                    setPadding(0,0,0,0);setTextColor(Palette.white);backgroundTintList=ColorStateList.valueOf(Palette.elevated)
                    contentDescription="Bắn chữ $char";setOnClickListener { arena?.fire(char) }
                }
                keys.addView(key,LinearLayout.LayoutParams(0,-1,1f).apply { setMargins(dp(1),0,dp(1),0) })
            }
        }
        label("Chạm để ngắm • Sai chữ không mất combo",11,Palette.muted,box).gravity=Gravity.CENTER
        updateHud();arena?.requestFocus()
    }
    private fun updateHud() {
        val game=engine ?: return
        hud?.text="Màn ${game.stage} • ${game.state.outcomes.size}/${game.words.size} từ\nChuỗi ${game.combo} • Bỏ lỡ ${game.misses}/3"
        val target=game.target
        focus?.text=if(target==null) "${game.words.size} từ • Combo bắt đầu từ 5 từ liên tiếp" else "Đang ngắm: ${game.words[target.index].meaning} • ${game.masked(target)}"
        arena?.contentDescription=focus?.text.toString()+". Chuỗi ${game.combo}. Bỏ lỡ ${game.misses}."
        pauseButton?.text=if(game.paused) "Tiếp tục" else "Tạm dừng"
    }
    private fun togglePause() {
        val game=engine ?: return
        game.paused=!game.paused;save();updateHud();arena?.invalidate();arena?.requestFocus()
    }
    private fun pause() { engine?.paused=true;save();updateHud();arena?.invalidate() }
    private fun save() {
        if(!isAdded || host.store.token!=ownerToken) return
        engine?.let { host.store.localGameState=gson.toJson(it.state) }
    }
    private fun submit() {
        if(busy) return
        val data=run ?: return;val game=engine ?: return
        if(!game.ended) return
        pause();busy=true;message("Đang lưu kết quả màn chơi…")
        val request=GameFinishRequest(game.state.outcomes.map { GameOutcomeDto(it.id,if(it.solved) "SOLVED" else "MISSED",it.answer,it.mistakes) })
        val activity=host
        val currentOwner=viewLifecycleOwner
        currentOwner.lifecycleScope.launch {
            val result=activity.games.finish(data,request)
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
            val result=activity.games.next(data)
            ensureActive()
            if(!isAdded || layout==null || currentOwner.lifecycle.currentState==androidx.lifecycle.Lifecycle.State.DESTROYED) return@launch
            result.onSuccess { busy=false;accept(it) }
                .onFailure { busy=false;error(it.message ?: "Chưa chuyển được màn.") { next() } }
        }
    }
    private fun showResult(data: GameRunDto) {
        val root=layout ?: return;root.removeAllViews();arena=null
        val scroll=ScrollView(requireContext());root.addView(scroll,LinearLayout.LayoutParams(-1,-1))
        val box=LinearLayout(requireContext()).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(10),dp(16),dp(10),dp(16)) };scroll.addView(box)
        val stage=data.round;val passed=stage.status=="PASSED"
        label(if(data.completed) "CHẶNG CHƠI HOÀN THÀNH" else "KẾT QUẢ MÀN ${stage.stage}",12,Palette.blue,box)
        label(if(passed && stage.maxCombo==20) "HOÀN HẢO!" else if(passed) "Vượt màn!" else "Thử lại nhé!",30,if(passed) Palette.green else Palette.orange,box)
        label("${stage.correctCount}/${stage.words.size} từ đúng • ${stage.missedCount} từ chạm đáy",16,Palette.white,box)
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
            action(if(passed) "Màn tiếp theo →" else "Chơi lại màn ${stage.stage}",box,Palette.green) { next() }
        } else {
            label(if(data.remainingCount==0) "Bạn đã hoàn thành toàn bộ bộ từ!" else "Đã xong 5 màn. Bạn có thể mở lượt mới hoặc ôn các từ còn khó.",15,Palette.muted,box)
        }
        action("Về màn Trò chơi",box) { returnToGames() }
    }
    private fun message(value: String) {
        layout?.removeAllViews();arena=null
        layout?.let { label(value,17,Palette.white,it) }
    }
    private fun error(value: String,retry: () -> Unit) {
        message(value)
        layout?.let { action("Thử lại",it) { retry() };action("Về màn Trò chơi",it) { returnToGames() } }
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
        if(!findNavController().popBackStack(R.id.gamesFragment,false)) findNavController().navigate(R.id.gamesFragment)
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
    override fun onDestroyView() { save();busy=false;layout=null;arena=null;hud=null;focus=null;pauseButton=null;super.onDestroyView() }
}
