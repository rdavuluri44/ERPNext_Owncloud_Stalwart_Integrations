package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class WelcomeTest {
    private val sent = LocalDateTime.of(2026, 11, 27, 9, 30)
    private val waiting = AccessRequest(sent)

    @Test
    fun aNewPhoneAsksForAccess() {
        assertEquals(Welcome.RequestAccess, welcomeFor(KeyState.NONE, null, null))
    }

    @Test
    fun aKeyOnThePhoneAlwaysWins() {
        // Also over a stale request of any kind: a working person is never put back into onboarding.
        for (request in listOf(null, waiting, waiting.copy(admin = Approval.REFUSED), waiting.copy(expired = true))) {
            assertEquals(Welcome.Unlock, welcomeFor(KeyState.PRESENT, null, request))
        }
    }

    @Test
    fun approvedNeedsBothApproversInAnyOrder() {
        assertEquals(Welcome.Pending(waiting), welcomeFor(KeyState.NONE, null, waiting))
        val onlyManager = waiting.copy(projectManager = Approval.CONFIRMED)
        assertEquals(Welcome.Pending(onlyManager), welcomeFor(KeyState.NONE, null, onlyManager))
        // The admin's yes alone is not enough, even if it arrives first.
        val onlyAdmin = waiting.copy(admin = Approval.CONFIRMED)
        assertEquals(Welcome.Pending(onlyAdmin), welcomeFor(KeyState.NONE, null, onlyAdmin))
        val both = onlyManager.copy(admin = Approval.CONFIRMED)
        assertEquals(Welcome.MakeKey, welcomeFor(KeyState.NONE, null, both))
    }

    @Test
    fun aRefusalIsToldBeforeAnExpiryAndNeverBecomesApproved() {
        val refused = waiting.copy(projectManager = Approval.CONFIRMED, admin = Approval.REFUSED, refusedBecause = "Wrong site", expired = true)
        assertEquals(Welcome.Refused(refused), welcomeFor(KeyState.NONE, null, refused))
        assertFalse(refused.approved)
        val expired = waiting.copy(expired = true)
        assertEquals(Welcome.Expired(expired), welcomeFor(KeyState.NONE, null, expired))
        // Both said yes but the days ran out before the key was made: it has run out.
        val late = waiting.copy(projectManager = Approval.CONFIRMED, admin = Approval.CONFIRMED, expired = true)
        assertEquals(Welcome.Expired(late), welcomeFor(KeyState.NONE, null, late))
    }

    @Test
    fun aLostKeySaysWhyUntilANewRequestExists() {
        assertEquals(Welcome.KeyGone(KeyLoss.MISSES), welcomeFor(KeyState.LOST, KeyLoss.MISSES, null))
        assertEquals(Welcome.KeyGone(KeyLoss.REMOVED), welcomeFor(KeyState.LOST, null, null))
        assertEquals(Welcome.Pending(waiting), welcomeFor(KeyState.LOST, KeyLoss.MISSES, waiting))
        val both = waiting.copy(projectManager = Approval.CONFIRMED, admin = Approval.CONFIRMED)
        assertEquals(Welcome.MakeKey, welcomeFor(KeyState.LOST, KeyLoss.NEW_FINGERPRINT, both))
    }

    @Test
    fun aNumberIsShownBackWithItsMiddleHidden() {
        assertEquals("+91 90••• ••000", hideMiddle("+91 90000 00000"))
        assertEquals("90••• ••000", hideMiddle("9000000000"))
        assertEquals("•••••", hideMiddle("12345"))
        assertFalse(hideMiddle("+91 98765 43210").contains("8765"))
    }
}
