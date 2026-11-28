package com.example.erp.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LockTest {
    @Test
    fun theFifthMissInARowErasesAndNotOneBefore() {
        for (misses in 0..4) assertFalse("$misses", LockRules.erases(misses))
        assertTrue(LockRules.erases(5))
        assertTrue(LockRules.erases(6))
        assertEquals(listOf(5, 4, 3, 2, 1, 0, 0), (0..6).map(LockRules::triesLeft))
    }

    @Test
    fun theAppLocksAfterFiveMinutesAwayAndNotBefore() {
        val left = 1_000_000L
        assertFalse("never left", LockRules.mustLock(null, left))
        assertFalse(LockRules.mustLock(left, left))
        assertFalse(LockRules.mustLock(left, left + 5 * 60_000 - 1))
        assertTrue(LockRules.mustLock(left, left + 5 * 60_000))
        assertTrue("the clock went backwards: the phone restarted", LockRules.mustLock(left, left - 1))
    }
}
