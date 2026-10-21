package com.example.englishlearningapp.game

import java.util.Locale

/** Frame-independent game rules, independent of Android Views and the network. */
data class ShooterWord(val id: Long,val english: String,val meaning: String)
data class FallingWord(val index: Int,var progress: Float=0f,var typed: Int=0,var mistakes: Int=0,val lane: Int=0)
data class ShooterOutcome(val id: Long,val solved: Boolean,val answer: String?,val mistakes: Int)
data class ShooterState(
    val roundId: Long,
    var next: Int=0,
    var spawnElapsed: Float=0f,
    val active: MutableList<FallingWord> = mutableListOf(),
    val outcomes: MutableList<ShooterOutcome> = mutableListOf(),
    var targetIndex: Int?=null
)
enum class Shot { CORRECT, WRONG, COMPLETE, IGNORED }

class WordShooterEngine(val words: List<ShooterWord>,val stage: Int,val state: ShooterState) {
    var paused=true
    val misses get()=state.outcomes.count { !it.solved }
    val correct get()=state.outcomes.count { it.solved }
    val combo get()=state.outcomes.asReversed().takeWhile { it.solved }.size
    val maxCombo get(): Int {
        var current=0;var best=0
        state.outcomes.forEach { current=if(it.solved) current+1 else 0;best=maxOf(best,current) }
        return best
    }
    val ended get()=misses>=4 || state.outcomes.size==words.size
    val target get()=state.active.firstOrNull { it.index==state.targetIndex }
    fun letters(index: Int)=words[index].english.lowercase(Locale.ROOT).filter { it in 'a'..'z' }
    fun masked(item: FallingWord): String {
        var letter=0
        return words[item.index].english.map { c ->
            if(c.lowercaseChar() in 'a'..'z') {
                if(letter++<item.typed) c.uppercaseChar() else '_'
            } else c
        }.joinToString("")
    }
    fun select(index: Int) { if(state.active.any { it.index==index }) state.targetIndex=index }
    private fun autoTarget() {
        if(target==null) state.targetIndex=state.active.maxByOrNull { it.progress }?.index
    }
    private fun spawn() {
        if(state.next>=words.size || state.active.size>=3) return
        val lane=state.next%2
        if(state.active.any { it.lane==lane && it.progress<0.36f }) return
        state.active.add(FallingWord(state.next++,lane=lane));state.spawnElapsed=0f;autoTarget()
    }
    fun tick(seconds: Float): List<ShooterOutcome> {
        if(paused || ended || seconds<=0f) return emptyList()
        val newlyMissed=mutableListOf<ShooterOutcome>()
        state.spawnElapsed+=seconds
        if(state.active.isEmpty() || state.spawnElapsed>=maxOf(3.4f,5.2f-minOf(stage-1,5)*0.25f)) spawn()
        state.active.toList().forEach { item ->
            if(ended) return@forEach
            val duration=maxOf(14f,20f+letters(item.index).length*1.2f-minOf(stage-1,5)*1.3f)
            item.progress+=seconds/duration
            if(item.progress>=1f) {
                val outcome=ShooterOutcome(words[item.index].id,false,null,item.mistakes)
                state.outcomes.add(outcome);newlyMissed.add(outcome);state.active.remove(item)
            }
        }
        autoTarget();return newlyMissed
    }
    fun shoot(char: Char): Shot {
        if(paused || ended) return Shot.IGNORED
        autoTarget()
        val item=target ?: return Shot.IGNORED
        val expected=letters(item.index)
        if(char.lowercaseChar()!=expected[item.typed]) { item.mistakes++;return Shot.WRONG }
        item.typed++
        if(item.typed<expected.length) return Shot.CORRECT
        state.outcomes.add(ShooterOutcome(words[item.index].id,true,words[item.index].english,item.mistakes))
        state.active.remove(item);autoTarget();return Shot.COMPLETE
    }
}
