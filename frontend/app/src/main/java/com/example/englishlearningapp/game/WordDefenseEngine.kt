package com.example.englishlearningapp.game

import java.util.Locale

enum class MonsterKind { NORMAL, RUNNER, ARMORED, BOSS }
data class DefenseMonster(val index: Int, val lane: Int, var progress: Float=0f,
    var typed: Int=0, var mistakes: Int=0)
data class DefenseState(
    val roundId: Long, var next: Int=0, var spawnElapsed: Float=0f,
    val active: MutableList<DefenseMonster> = mutableListOf(),
    val outcomes: MutableList<ShooterOutcome> = mutableListOf(),
    var targetIndex: Int?=null, var energy: Int=0, var slowRemaining: Float=0f,
    var breakRemaining: Float=0f, var breakAt: Int=0, var bossProgress: Float=0f
)

/** Deterministic local rules. Server validates the deck, resolution order and score. */
class WordDefenseEngine(val words: List<ShooterWord>, val stage: Int,
    val learningMode: String, val state: DefenseState) {
    var paused=true
    val misses get()=state.outcomes.count { !it.solved }
    val combo get()=state.outcomes.asReversed().takeWhile { it.solved }.size
    val ended get()=misses>=4 || state.outcomes.size==words.size
    val target get()=state.active.firstOrNull { it.index==state.targetIndex }
    val bossStart get()=maxOf(0,words.size-3)
    fun letters(index: Int)=words[index].english.lowercase(Locale.ROOT).filter { it in 'a'..'z' }
    fun kind(index: Int)=when {
        stage%5==0 && index>=bossStart -> MonsterKind.BOSS
        letters(index).length>=8 -> MonsterKind.ARMORED
        index%3==1 && letters(index).length<=5 -> MonsterKind.RUNNER
        else -> MonsterKind.NORMAL
    }
    fun masked(monster: DefenseMonster): String {
        var n=0
        return words[monster.index].english.map { char ->
            if(char.lowercaseChar() in 'a'..'z') {
                if(n++<monster.typed) char.uppercaseChar() else '_'
            } else char
        }.joinToString("")
    }
    fun select(index: Int) { if(state.active.any { it.index==index }) state.targetIndex=index }
    private fun autoTarget() {
        if(target==null) state.targetIndex=state.active.maxByOrNull { it.progress }?.index
    }
    fun slow(): Boolean {
        if(paused || ended || state.energy<100 || state.slowRemaining>0f) return false
        state.energy=0;state.slowRemaining=6f;return true
    }
    private fun spawn() {
        if(state.next>=words.size || state.active.size>=LANE_COUNT) return
        val boss=kind(state.next)==MonsterKind.BOSS
        if(boss && state.active.isNotEmpty()) return
        val lane=if(boss) LANE_COUNT/2 else (0 until LANE_COUNT).minBy { lane ->
            state.active.filter { it.lane==lane }.maxOfOrNull { 1f-it.progress } ?: -1f
        }
        if(state.active.any { it.lane==lane && it.progress<.38f }) return
        state.active.add(DefenseMonster(state.next++,lane,if(boss) state.bossProgress else 0f))
        state.spawnElapsed=0f;autoTarget()
    }
    fun tick(seconds: Float) {
        if(paused || ended || !seconds.isFinite() || seconds<=0f) return
        var left=seconds
        while(left>0f && !ended) {
            val dt=minOf(.1f,left);left-=dt;step(dt)
        }
    }
    private fun step(dt: Float) {
        if(state.breakRemaining>0f) { state.breakRemaining=maxOf(0f,state.breakRemaining-dt);return }
        if(state.active.isEmpty() && state.next>0 && state.next<words.size && state.next%5==0 && state.breakAt!=state.next) {
            state.breakAt=state.next;state.breakRemaining=3f;return
        }
        val slowed=state.slowRemaining>0f
        state.slowRemaining=maxOf(0f,state.slowRemaining-dt)
        state.spawnElapsed+=dt
        if(state.active.isEmpty() || state.spawnElapsed>=maxOf(2.6f,4.3f-minOf(stage-1,6)*.25f)) spawn()
        for(monster in state.active.toList()) {
            if(ended) break
            val base=maxOf(15f,24f+letters(monster.index).length*1.2f-minOf(stage-1,6)*1.2f)
            val duration=base*when(kind(monster.index)) {
                MonsterKind.RUNNER -> .72f;MonsterKind.ARMORED -> 1.35f;MonsterKind.BOSS -> 1.65f;else -> 1f
            }
            monster.progress+=dt/duration*MOVEMENT_SPEED*(if(slowed) .4f else 1f)
            if(monster.progress>=1f) {
                state.outcomes.add(ShooterOutcome(words[monster.index].id,false,null,monster.mistakes))
                state.active.remove(monster)
                if(kind(monster.index)==MonsterKind.BOSS) state.bossProgress=0f
            }
        }
        autoTarget()
    }
    fun shoot(char: Char): Shot {
        if(paused || ended || char.lowercaseChar() !in 'a'..'z') return Shot.IGNORED
        autoTarget();val monster=target ?: return Shot.IGNORED
        val expected=letters(monster.index)
        if(char.lowercaseChar()!=expected[monster.typed]) { monster.mistakes++;return Shot.WRONG }
        monster.typed++
        if(monster.typed<expected.length) return Shot.CORRECT
        state.outcomes.add(ShooterOutcome(words[monster.index].id,true,words[monster.index].english,monster.mistakes))
        state.energy=minOf(100,state.energy+20)
        if(kind(monster.index)==MonsterKind.BOSS) state.bossProgress=monster.progress
        state.active.remove(monster);autoTarget();return Shot.COMPLETE
    }

    companion object {
        const val LANE_COUNT=4
        private const val MOVEMENT_SPEED=.85f
        fun valid(state: DefenseState,words: List<ShooterWord>,roundId: Long): Boolean = runCatching {
            state.roundId==roundId && state.next in 0..words.size && state.energy in 0..100 &&
            state.slowRemaining.isFinite() && state.slowRemaining in 0f..6f &&
            state.breakRemaining.isFinite() && state.breakRemaining in 0f..3f &&
            state.active.size<=LANE_COUNT && state.active.all { m -> m.index in 0 until state.next && m.lane in 0 until LANE_COUNT &&
                m.progress.isFinite() && m.progress in 0f..1.01f && m.typed in 0 until words[m.index].english.count { it.lowercaseChar() in 'a'..'z' } && m.mistakes>=0 } &&
            state.outcomes.all { result -> words.take(state.next).any { it.id==result.id } } &&
            state.outcomes.map { it.id }.distinct().size==state.outcomes.size &&
            state.active.map { it.index }.distinct().size==state.active.size &&
            state.active.none { m -> state.outcomes.any { it.id==words[m.index].id } } &&
            state.active.size+state.outcomes.size==state.next
        }.getOrDefault(false)
    }
}
