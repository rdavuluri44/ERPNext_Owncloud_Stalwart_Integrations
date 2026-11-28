package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class InboxTest {
    private val now = LocalDateTime.of(2026, 11, 28, 9, 15)

    private fun item(id: String, kind: ItemKind = ItemKind.LEAVE, hoursWaiting: Long = 1) =
        Item(id, kind, "Item $id", "Engineer, A. Example", now.minusHours(hoursWaiting))

    @Test
    fun whatHoldsSomeoneUpComesFirstThenDeadlinesThenEachKindOldestFirst() {
        val items = listOf(
            item("leave-new", hoursWaiting = 1),
            item("leave-old", hoursWaiting = 30),
            item("pay", ItemKind.PAYMENT).copy(amount = "150000"),
            item("due", ItemKind.ATTENDANCE_APPROVE).copy(deadline = now.withHour(10).withMinute(0)),
            item("missed", ItemKind.ATTENDANCE_VERIFY).copy(deadline = now.minusHours(1)),
            item("next-week", ItemKind.PURCHASE).copy(deadline = now.plusDays(6)),
            item("back", ItemKind.PURCHASE).copy(rejection = Rejection("Management, R. Example", now.minusHours(2))),
        )
        val sections = Inbox.sections(items, now)
        assertEquals(
            listOf("Rejected, to correct (1)", "Due today (2)", "Purchases (1)", "Payments (1)", "Leave (2)"),
            sections.map { it.heading },
        )
        assertEquals(listOf("back"), sections[0].items.map { it.id })
        assertEquals(listOf("missed", "due"), sections[1].items.map { it.id }) // the missed one first
        // A deadline on a later day waits its turn among its kind.
        assertEquals(listOf("next-week"), sections[2].items.map { it.id })
        assertEquals(listOf("leave-old", "leave-new"), sections[4].items.map { it.id })
        assertEquals(emptyList<Section>(), Inbox.sections(emptyList(), now))
    }

    @Test
    fun iNeverDecideWhatISentOrWhatCameBackToMe() {
        assertTrue(Inbox.canDecide(item("a")))
        assertFalse(Inbox.canDecide(item("a").copy(sentByMe = true)))
        assertFalse(Inbox.canDecide(item("a").copy(rejection = Rejection("Management", now))))
    }

    @Test
    fun theFingerprintQuestionSaysExactlyWhatIsSigned() {
        val payment = item("p", ItemKind.PAYMENT).copy(title = "Payment to a supplier", amount = "150000")
        assertEquals("Approve 1,50,000.00: Payment to a supplier", Inbox.question(Decision.APPROVED, payment))
        assertEquals("Reject 1,50,000.00: Payment to a supplier", Inbox.question(Decision.REJECTED, payment))
        // The sender writes the title: it cannot push the amount away, and it is cut to one short line.
        assertEquals("Approve 1,50,000.00: " + "T".repeat(80), Inbox.question(Decision.APPROVED, payment.copy(title = "T".repeat(300))))
        // An amount this app cannot read is never signed.
        assertNull(Inbox.amount(payment.copy(amount = "12x")))
        assertFalse(Inbox.canDecide(payment.copy(amount = "12x")))
        // A payment without any amount is not signed either: its title could name one.
        assertFalse(Inbox.canDecide(payment.copy(amount = null)))
        assertTrue(Inbox.canDecide(item("leave")))
        // Line breaks and invisible direction marks never reach the question.
        assertEquals("Approve 1,50,000.00: Tea 00.005", Inbox.question(Decision.APPROVED, payment.copy(title = "Tea\n\u202E00.005")))
        assertEquals(null, LockRules.missWords(0))
        assertEquals("Not signed. 1 try left. After 5 misses in a row the key is erased.", LockRules.missWords(4))
        assertEquals("Approve: Item a", Inbox.question(Decision.APPROVED, item("a")))
        assertEquals("1,25,00,000.50", Inbox.amount(payment.copy(amount = "12500000.5")))
        assertEquals("From Engineer, A. Example · waiting 1 h · 1,50,000.00", Inbox.rowLine(payment, now))
    }

    @Test
    fun aDeadlineSaysHowUrgentItIs() {
        assertNull(Inbox.deadline(item("a"), now))
        assertEquals(Tone.CARE to "Due 10:00", Inbox.deadline(item("a").copy(deadline = now.withHour(10).withMinute(0)), now))
        assertEquals(Tone.WRONG to "Was due Today, 08:15", Inbox.deadline(item("a").copy(deadline = now.minusHours(1)), now))
        assertEquals(Tone.PLAIN to "Due 4 Dec, 09:15", Inbox.deadline(item("a").copy(deadline = now.plusDays(6)), now))
    }

    @Test
    fun aRejectionAlwaysGoesBackAndItsReasonIsOptional() {
        assertEquals("Rejected by Management, R. Example, Today, 07:15. No reason given.", Inbox.rejectionLine(Rejection("Management, R. Example", now.minusHours(2)), now))
        assertEquals("Rejected by Management, Today, 07:15. Photo not clear", Inbox.rejectionLine(Rejection("Management", now.minusHours(2), "Photo not clear"), now))
        assertNull(Inbox.reason(null, "   "))
        assertEquals("Photo not clear", Inbox.reason("Photo not clear", ""))
        assertEquals("Worker 7 is marked twice", Inbox.reason(null, " Worker 7 is\nmarked twice "))
        assertEquals("Wrong time: off by one hour", Inbox.reason("Wrong time", "off by one hour"))
        assertEquals(Inbox.MAX_REASON, Inbox.reason(null, "x".repeat(900))!!.length)
        // There are two decisions and no third, final one.
        assertEquals(listOf("Approved", "Rejected"), Decision.entries.map { it.done })
    }

    @Test
    fun whatISentSaysWhoHasItAndSinceWhen() {
        val sent = Sent("s", "Purchase request", "Project manager, V. Example", now.minusHours(26), SentState.WAITING)
        assertEquals("With Project manager, V. Example for 1 day.", Inbox.sentLine(sent, now))
        assertEquals("Approved by Project manager, V. Example, Yesterday, 07:15.", Inbox.sentLine(sent.copy(state = SentState.APPROVED), now))
        assertEquals("Rejected by Project manager, V. Example, Yesterday, 07:15. No reason given.", Inbox.sentLine(sent.copy(state = SentState.REJECTED), now))
    }
}
