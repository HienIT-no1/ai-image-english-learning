package com.example.englishlearningapp

import com.example.englishlearningapp.game.*
import org.junit.Assert.*
import org.junit.Test

class WordShooterEngineTest {
    private fun game(count: Int=20): WordShooterEngine = WordShooterEngine(
        (1..count).map { ShooterWord(it.toLong(),"cat","con mèo") },1,ShooterState(1)
    )
    private fun solveNext(game: WordShooterEngine) {
        game.tick(0.01f)
        game.state.active.maxByOrNull { it.progress }?.let { game.select(it.index) }
        "cat".forEach { game.shoot(it) }
    }
    @Test fun wrongLettersPreserveProgressAndCombo() {
        val game=game();game.paused=false
        repeat(5) { solveNext(game) }
        assertEquals(5,game.combo)
        game.tick(0.01f)
        assertEquals(Shot.CORRECT,game.shoot('C'))
        assertEquals(Shot.WRONG,game.shoot('x'))
        assertEquals("C__",game.masked(game.target!!))
        assertEquals(5,game.combo);assertEquals(0,game.misses)
        assertEquals(Shot.CORRECT,game.shoot('a'));assertEquals(Shot.COMPLETE,game.shoot('t'))
        assertEquals(6,game.combo);assertEquals(1,game.state.outcomes.last().mistakes)
    }
    @Test fun fourthMissFailsButThreeAreAllowed() {
        val game=game();game.paused=false
        repeat(3) { game.tick(30f) }
        assertEquals(3,game.misses);assertFalse(game.ended)
        game.tick(30f)
        assertEquals(4,game.misses);assertTrue(game.ended)
        val previous=game.state.outcomes.size;game.tick(100f)
        assertEquals(previous,game.state.outcomes.size)
    }
    @Test fun pauseAndResumePreserveTimersAndLetters() {
        val game=game();game.paused=false;game.tick(1f);game.shoot('c')
        val position=game.target!!.progress
        game.paused=true;game.tick(30f)
        assertEquals(position,game.target!!.progress)
        assertEquals(Shot.IGNORED,game.shoot('a'))
        val restored=WordShooterEngine(game.words,1,game.state)
        assertTrue(restored.paused);assertEquals("C__",restored.masked(restored.target!!))
        restored.paused=false;restored.shoot('a');restored.shoot('t');assertEquals(1,restored.correct)
    }
    @Test fun twentyWordsCanKeepOneComboToTheEnd() {
        val game=game();game.paused=false
        repeat(20) { solveNext(game) }
        assertTrue(game.ended);assertEquals(20,game.combo);assertEquals(20,game.maxCombo)
        assertEquals(0,game.misses)
    }
    @Test fun onlyMissBreaksComboAndTargetsCanSwitch() {
        val game=game();game.paused=false
        repeat(7) { solveNext(game) }
        game.tick(0.1f);game.tick(6f)
        assertEquals(2,game.state.active.size)
        val second=game.state.active.last();game.select(second.index);game.shoot('c')
        assertEquals(1,second.typed)
        game.state.active.first().progress=0.999f;game.tick(0.1f)
        assertEquals(0,game.combo);assertEquals(7,game.maxCombo)
        assertEquals(1,game.misses);assertEquals(1,second.typed)
    }
    @Test fun separatorsArePrefilledRatherThanUntypeable() {
        val game=WordShooterEngine(listOf(ShooterWord(1,"ice cream","kem")),1,ShooterState(1))
        game.paused=false;game.tick(0.1f)
        assertEquals("___ _____",game.masked(game.target!!))
        "icecream".forEach { game.shoot(it) }
        assertTrue(game.ended);assertEquals("ice cream",game.state.outcomes.single().answer)
    }
}
