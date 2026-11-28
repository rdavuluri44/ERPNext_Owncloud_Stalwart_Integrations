package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DelegationTest {
    private val now = LocalDateTime.of(2026, 11, 28, 9, 15)
    private val deputy = Receiver("d", "Deputy manager, D. Example", Relation.DEPUTY)
    private val peer = Receiver("p", "Project manager, P. Example", Relation.PEER)
    private val peerAway = Receiver("v", "Project manager, V. Example", Relation.PEER, onLeave = true)
    private val higher = Receiver("r", "Director, R. Example", Relation.HIGHER)
    private val all = listOf(higher, peerAway, peer, deputy)
    private val leave = Leave(now.minusHours(1), now.plusDays(4))

    private fun item(from: String = "Engineer, A. Example") = Item("a", ItemKind.LEAVE, "Leave, 3 days", from, now.minusHours(1))

    @Test
    fun oneThingCanGoToTheDeputyAPeerOrTheHigherOfficialButNeverToItsSender() {
        assertEquals(listOf(deputy, peerAway, peer, higher), Delegations.forOne(all, item()))
        assertEquals(listOf(deputy, peerAway, higher), Delegations.forOne(all, item(from = peer.name)))
        // By the person's number too: a name written differently does not let the sender through.
        assertEquals(listOf(deputy, peerAway, higher), Delegations.forOne(all, item(from = "Site manager, P. Example").copy(fromId = peer.id)))
    }

    @Test
    fun everythingGoesOnlyToTheDeputyOrAPeerWhoIsNotOnLeave() {
        assertEquals(listOf(deputy, peer), Delegations.forAll(all))
        assertEquals(emptyList<Receiver>(), Delegations.forAll(listOf(higher, peerAway)))
    }

    @Test
    fun everythingNeedsApprovedLeaveThatHasNotEndedAndNoDelegationAlreadySet() {
        assertNull(Delegations.whyNotAll(DelegationFacts(all, leave), now))
        assertEquals(Delegations.NO_LEAVE, Delegations.whyNotAll(DelegationFacts(all, leave = null), now))
        // Leave that is over, or about to be, is no leave.
        assertEquals(Delegations.NO_LEAVE, Delegations.whyNotAll(DelegationFacts(all, Leave(now.minusDays(3), now.minusHours(1))), now))
        assertEquals(Delegations.NO_LEAVE, Delegations.whyNotAll(DelegationFacts(all, Leave(now.minusDays(3), now.plusMinutes(10))), now))
        // Leave that has not begun counts: the person sets it before going.
        assertNull(Delegations.whyNotAll(DelegationFacts(all, Leave(now.plusDays(2), now.plusDays(5))), now))
        assertEquals(Delegations.ALREADY, Delegations.whyNotAll(DelegationFacts(all, leave, running = Delegation(deputy, now, leave.until)), now))
    }

    @Test
    fun thePeriodStaysInsideTheLeaveItCanEndEarlierNeverLater() {
        assertEquals(now, Delegations.start(leave, now)) // the leave has begun
        val ahead = Leave(now.plusDays(2), now.plusDays(5))
        assertEquals(ahead.from, Delegations.start(ahead, now))
        assertEquals(leave.until, Delegations.until(now.plusDays(30), leave, now))
        assertEquals(now.plusDays(2), Delegations.until(now.plusDays(2), leave, now))
        assertEquals(now.plusMinutes(15), Delegations.until(now.minusDays(1), leave, now))
        assertEquals(ahead.from.plusMinutes(15), Delegations.until(now, ahead, now))
    }

    @Test
    fun oneStepOnlyAndOnlyWhatICouldDecideMyself() {
        assertTrue(Delegations.canDelegate(item()))
        assertFalse(Delegations.canDelegate(item().copy(delegatedBy = peer.name))) // came to me by delegation
        assertFalse(Delegations.canDelegate(item().copy(delegatedTo = deputy.name))) // I delegated it already
        assertFalse(Delegations.canDelegate(item().copy(sentByMe = true)))
        assertFalse(Delegations.canDelegate(item().copy(rejection = Rejection("Management", now))))
        // I can still decide what I delegated; the receiver decides what came to them.
        assertTrue(Inbox.canDecide(item().copy(delegatedTo = deputy.name)))
        assertTrue(Inbox.canDecide(item().copy(delegatedBy = peer.name)))
    }

    @Test
    fun theFingerprintQuestionSaysWhoReceivesWhat() {
        assertEquals("Delegate to Deputy manager, D. Example: Leave, 3 days", Delegations.question(deputy, item()))
        assertEquals("Delegate all approvals until 2 Dec, 09:15 to Deputy manager, D. Example", Delegations.questionAll(deputy, now, leave.until, now))
        // A delegation set before the leave says when it starts; one for money says how much.
        assertEquals("Delegate all approvals from 30 Nov, 09:15 until 2 Dec, 09:15 to Deputy manager, D. Example", Delegations.questionAll(deputy, now.plusDays(2), leave.until, now))
        assertEquals("Delegate 1,50,000.00 to Deputy manager, D. Example: Payment", Delegations.question(deputy, Item("p", ItemKind.PAYMENT, "Payment", "Accounts", now, amount = "150000")))
        // Names and titles are one short line each, without invisible characters.
        val odd = Delegations.question(deputy.copy(name = "D.\nExample\u202E"), item().copy(title = "T".repeat(300)))
        assertEquals("Delegate to D. Example: " + "T".repeat(80), odd)
    }

    @Test
    fun theLinesSayWhereThingsAreNow() {
        assertEquals("Your approvals go to Deputy manager, D. Example until 2 Dec, 09:15. You can still decide them yourself.", Delegations.runningLine(Delegation(deputy, now, leave.until), now))
        assertEquals("From 30 Nov, 09:15 until 2 Dec, 09:15 your approvals go to Deputy manager, D. Example.", Delegations.runningLine(Delegation(deputy, now.plusDays(2), leave.until), now))
        assertEquals("Delegated to you by Project manager, P. Example. Travelling. You decide it with your own fingerprint.", Delegations.itemLine(item().copy(delegatedBy = peer.name, delegationReason = "Travelling")))
        assertEquals("You delegated this to Deputy manager, D. Example. You can still decide it yourself.", Delegations.itemLine(item().copy(delegatedTo = deputy.name)))
        assertNull(Delegations.itemLine(item()))
        // What I delegated has its own place in the list, after the kinds.
        val sections = Inbox.sections(listOf(item(), item().copy(id = "b", delegatedTo = deputy.name)), now)
        assertEquals(listOf("Leave (1)", "Delegated by you (1)"), sections.map { it.heading })
    }
}
