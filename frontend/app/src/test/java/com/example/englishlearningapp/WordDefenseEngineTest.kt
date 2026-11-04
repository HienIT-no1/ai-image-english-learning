package com.example.englishlearningapp

import com.example.englishlearningapp.game.*
import com.google.gson.Gson
import org.junit.Assert.*
import org.junit.Test

class WordDefenseEngineTest {
    private fun game(stage: Int=1,mode: String="RECALL",size: Int=20): WordDefenseEngine {
        val names=listOf("cat","dog","apple","banana","elephant","fish","bird","computer","book","pen",
            "table","chair","sun","moon","star","tree","flower","water","milk","bread")
        return WordDefenseEngine(names.take(size).mapIndexed { i,w -> ShooterWord(i+1L,w,"nghĩa $i") },stage,mode,DefenseState(1))
    }
    private fun ready(g: WordDefenseEngine) {
        g.paused=false
        repeat(100) { if(g.target==null && !g.ended)g.tick(.1f) }
        assertNotNull(g.target)
    }
    private fun solve(g: WordDefenseEngine) {
        ready(g);val word=g.words[g.target!!.index].english
        word.filter { it in 'a'..'z' }.forEach { g.shoot(it) }
    }
    @Test fun wrongLettersPreservePrefixComboAndEnergy() {
        val g=game();repeat(5) { solve(g) };ready(g)
        val target=g.target!!;val text=g.letters(target.index)
        g.shoot(text[0]);val typed=target.typed;val energy=g.state.energy
        assertEquals(Shot.WRONG,g.shoot(if(text[typed]=='z') 'x' else 'z'))
        assertEquals(typed,target.typed);assertEquals(5,g.combo);assertEquals(0,g.misses)
        assertEquals(energy,g.state.energy);assertEquals(1,target.mistakes)
    }
    @Test fun twentyKillsKeepAComboAndEndExactlyOnce() {
        val g=game();repeat(20) { solve(g) }
        assertTrue(g.ended);assertEquals(20,g.combo);assertEquals(20,g.state.outcomes.size)
        assertEquals(20,g.state.outcomes.map { it.id }.distinct().size)
        assertEquals(Shot.IGNORED,g.shoot('a'));g.tick(90f);assertEquals(20,g.state.outcomes.size)
    }
    @Test fun monstersUseFourLanesAndCanBeSelected() {
        val g=game();ready(g);g.tick(14f)
        assertEquals(setOf(0,1,2,3),g.state.active.map { it.lane }.toSet())
        g.tick(1f);assertEquals(4,g.state.active.size)
        val selected=g.state.active.last();g.select(selected.index);assertEquals(selected,g.target)
        assertEquals(MonsterKind.RUNNER,g.kind(1));assertEquals(MonsterKind.ARMORED,g.kind(4))
    }
    @Test fun movementIsFifteenPercentSlowerForEveryMonsterKind() {
        // Baseline crossing times before the four-lane tuning: normal, runner, armored, boss.
        val cases=listOf(
            Triple(listOf("cat"),1,27.6f),
            Triple(listOf("cat","dog"),1,19.872f),
            Triple(listOf("elephant"),1,45.36f),
            Triple(listOf("water"),5,41.58f)
        )
        for((names,stage,previousDuration) in cases) {
            val words=names.mapIndexed { i,w -> ShooterWord(i+1L,w,"nghĩa") }
            val g=WordDefenseEngine(words,stage,"RECALL",DefenseState(1))
            if(names.size==2) solve(g)
            ready(g);val target=g.target!!;val before=target.progress;g.tick(1f)
            assertEquals(.85f/previousDuration,target.progress-before,.00001f)
        }
    }
    @Test fun slowCostsFullEnergyAndReducesMovementWithoutResettingTyping() {
        val g=game();assertFalse(g.slow());repeat(5) { solve(g) };ready(g)
        val target=g.target!!;g.shoot(g.letters(target.index)[0]);val typed=target.typed
        val before=target.progress
        assertTrue(g.slow());assertEquals(0,g.state.energy);assertFalse(g.slow());g.tick(1f)
        val slowDistance=target.progress-before
        g.state.slowRemaining=0f;val next=target.progress;g.tick(1f)
        assertEquals(slowDistance*2.5f,target.progress-next,.0001f);assertEquals(typed,target.typed)
    }
    @Test fun fourthEscapeFailsAndStopsAllRemainingMonsters() {
        val g=game();ready(g);g.tick(180f)
        assertTrue(g.ended);assertEquals(4,g.misses);assertEquals(4,g.state.outcomes.size)
        val before=Gson().toJson(g.state);g.tick(100f);assertEquals(before,Gson().toJson(g.state))
    }
    @Test fun pauseAndSnapshotPreserveAllTimersAndPartialLetters() {
        val g=game();ready(g);g.tick(14f)
        g.select(g.state.active.last().index);assertEquals(3,g.target!!.lane)
        g.shoot(g.letters(g.target!!.index)[0]);g.state.energy=100;g.slow();g.tick(.7f);g.paused=true
        val json=Gson().toJson(g.state);g.tick(100f);assertEquals(json,Gson().toJson(g.state))
        val restored=Gson().fromJson(json,DefenseState::class.java)
        assertTrue(WordDefenseEngine.valid(restored,g.words,1))
        val next=WordDefenseEngine(g.words,g.stage,g.learningMode,restored)
        assertTrue(next.paused);assertEquals(g.masked(g.target!!),next.masked(next.target!!))
        assertEquals(g.state.slowRemaining,next.state.slowRemaining)
    }
    @Test fun bossHasThreeWordLayersAndKeepsItsPositionAcrossSuccessfulLayers() {
        val g=game(stage=5);repeat(17) { solve(g) };ready(g)
        assertEquals(17,g.target!!.index);assertEquals(MonsterKind.BOSS,g.kind(17));assertEquals(2,g.target!!.lane)
        g.tick(2f);val position=g.target!!.progress;solve(g);ready(g)
        assertEquals(18,g.target!!.index);assertTrue(g.target!!.progress>=position)
        solve(g);ready(g);assertEquals(19,g.target!!.index);solve(g);assertTrue(g.ended)
    }
    @Test fun wavesPauseAndSpeedHasACap() {
        val g=game();repeat(5) { solve(g) };g.tick(.1f)
        assertTrue(g.state.breakRemaining>0);assertTrue(g.state.active.isEmpty())
        val slow=game(stage=7);val late=game(stage=200);ready(slow);ready(late)
        slow.tick(1f);late.tick(1f);assertEquals(slow.target!!.progress,late.target!!.progress,.0001f)
    }
    @Test fun separatorsArePrefilledAndBothModesShareTheSameResolutionRules() {
        for(mode in listOf("TYPING","RECALL")) {
            val g=WordDefenseEngine(listOf(ShooterWord(1,"ice cream","kem")),1,mode,DefenseState(1))
            ready(g);assertEquals("___ _____",g.masked(g.target!!))
            "icecream".forEach { g.shoot(it) };assertTrue(g.ended)
            assertEquals("ice cream",g.state.outcomes.single().answer)
        }
    }
    @Test fun corruptSnapshotCannotInjectOutcomesOrInvalidPositions() {
        val g=game();val bad=DefenseState(1,next=1,active=mutableListOf(DefenseMonster(0,0,Float.NaN)))
        assertFalse(WordDefenseEngine.valid(bad,g.words,1))
        val outsideLane=DefenseState(1,next=1,active=mutableListOf(DefenseMonster(0,4)))
        assertFalse(WordDefenseEngine.valid(outsideLane,g.words,1))
        assertFalse(WordDefenseEngine.valid(DefenseState(2),g.words,1))
        val duplicate=DefenseState(1,next=1,outcomes=mutableListOf(ShooterOutcome(1,true,"cat",0),ShooterOutcome(1,true,"cat",0)))
        assertFalse(WordDefenseEngine.valid(duplicate,g.words,1))
    }
}
