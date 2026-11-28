package com.example.erp.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AlertsTest {
    private fun signal(kind: String, vararg more: Pair<String, String>) = mapOf("kind" to kind, *more)

    private fun approval(name: String) = signal("approval", "needs" to "decide", "doctype" to "Purchase Order", "docname" to name)

    /** Feeds signals in order and gives the last state and every action. */
    private fun run(vararg signals: Map<String, String>): Pair<AlertState, List<AlertAction>> {
        var state = AlertState()
        val actions = signals.map { signal -> Alerts.handle(signal, state).also { state = it.first }.second }
        return state to actions
    }

    @Test
    fun approvalsRingAndAreCountedOncePerThing() {
        val (state, actions) = run(approval("PO-1"), approval("PO-2"), approval("PO-1"), signal("verify", "doctype" to "Field Attendance Entry", "docname" to "FAE-9"))
        assertEquals(
            listOf("Purchase waiting", "2 approvals waiting", "2 approvals waiting", "3 approvals waiting"),
            actions.map { (it as AlertAction.Show).words },
        )
        assertTrue(actions.all { (it as AlertAction.Show).strength == Strength.RING && it.slot == Slot.DECIDE })
        assertEquals(3, state.deciding.size)
    }

    @Test
    fun removingTakesOneAwayQuietlyAndTheLastOneRemovesTheAlert() {
        val (state, actions) = run(
            approval("PO-1"), approval("PO-2"),
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-1"),
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-1"), // told twice: nothing happens the second time
            signal("remove", "doctype" to "Purchase Order", "docname" to "PO-2"),
        )
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.QUIET), actions[2])
        assertEquals(AlertAction.Ignore, actions[3])
        assertEquals(AlertAction.Remove(Slot.DECIDE), actions[4])
        assertEquals(AlertState(), state)
    }

    @Test
    fun whatCameBackToMeIsItsOwnQuieterAlert() {
        val back = signal("returned", "needs" to "decide", "doctype" to "Field Attendance Entry", "docname" to "FAE-1")
        val (state, actions) = run(back, approval("PO-1"), signal("remove", "doctype" to "Field Attendance Entry", "docname" to "FAE-1"))
        assertEquals(AlertAction.Show(Slot.REJECTED, "Rejected, to correct", Strength.ALERT), actions[0])
        assertEquals(AlertAction.Remove(Slot.REJECTED), actions[2])
        assertEquals(1, state.deciding.size) // the approval is untouched
        assertEquals("3 rejected, to correct", Alerts.rejectedWords(3))
    }

    @Test
    fun aReminderSaysThatItIsOneAndHowLong() {
        assertEquals("Reminder: an approval has been waiting for 4 hours", Alerts.reminderWords(1, 4))
        assertEquals("Reminder: an approval has been waiting for 1 hour", Alerts.reminderWords(1, 1))
        assertEquals("Reminder: 3 approvals are still waiting, the oldest for 8 hours", Alerts.reminderWords(3, 8))
        assertEquals("Reminder: an approval is still waiting", Alerts.reminderWords(1, null))
        val (state, actions) = run(signal("reminder", "count" to "3", "oldest_hours" to "8"))
        assertEquals(AlertAction.Show(Slot.DECIDE, "Reminder: 3 approvals are still waiting, the oldest for 8 hours", Strength.RING), actions.single())
        assertEquals(AlertState(), state) // a reminder counts nothing itself: the server counted
        // A reminder that says nothing waits, or says nonsense, shows nothing.
        for (bad in listOf(signal("reminder"), signal("reminder", "count" to "0"), signal("reminder", "count" to "-2"), signal("reminder", "count" to "many"), signal("reminder", "count" to "99999999999"))) {
            assertEquals(bad.toString(), AlertAction.Ignore, run(bad).second.single())
        }
        assertEquals("Reminder: 999 approvals are still waiting", (run(signal("reminder", "count" to "5000")).second.single() as AlertAction.Show).words)
    }

    @Test
    fun nothingShownIsEverTakenFromTheSignal() {
        val secret = "Payment of 1,50,000.00 to A. Example"
        val loaded = mapOf(
            "kind" to "approval", "doctype" to secret, "docname" to secret, "site" to secret, "site_label" to secret,
            "title" to secret, "body" to secret, "message" to secret, "amount" to "150000",
        )
        val (state, action) = Alerts.handle(loaded, AlertState())
        action as AlertAction.Show
        assertEquals("Approval waiting", action.words)
        // What is remembered is a short fingerprint, not the reference.
        assertFalse(state.deciding.single().contains("Example"))
        assertEquals(16, state.deciding.single().length)
        for (kind in listOf("approval", "verify", "returned", "reminder", "message", "mail", "notice", "test")) {
            val words = (Alerts.handle(loaded + ("kind" to kind) + ("count" to "2"), AlertState()).second as AlertAction.Show).words
            assertFalse("$kind: $words", words.contains("Example") || words.contains("150000") || words.contains("1,50,000"))
        }
    }

    @Test
    fun anUnknownOrBrokenSignalShowsNothingButARealApprovalIsNeverDropped() {
        for (bad in listOf(emptyMap(), signal(""), signal("APPROVAL"), signal("pay-now"), signal("remove"), signal("remove", "doctype" to "X"))) {
            val (state, action) = Alerts.handle(bad, AlertState())
            assertEquals(bad.toString(), AlertAction.Ignore, action)
            assertEquals(AlertState(), state)
        }
        // An approval without a usable reference still rings; it is just not counted or removable by name.
        val (state, action) = Alerts.handle(signal("approval"), AlertState())
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.RING), action)
        assertEquals(AlertState(), state)
        assertEquals(AlertState(), Alerts.handle(signal("approval", "doctype" to "x".repeat(500), "docname" to "y"), AlertState()).first)
    }

    @Test
    fun oneWaitingThingSaysItsKindAndCanBeOpenedSeveralCannot() {
        val (_, actions) = run(
            signal("approval", "doctype" to "Payment Entry", "docname" to "PAY-1"),
            signal("approval", "doctype" to "Leave Application", "docname" to "LV-1"),
            signal("remove", "doctype" to "Payment Entry", "docname" to "PAY-1"),
        )
        assertEquals(AlertAction.Show(Slot.DECIDE, "Payment waiting", Strength.RING, item = "PAY-1"), actions[0])
        // Two wait: the alert cannot know which one is meant, so it names neither.
        assertEquals(AlertAction.Show(Slot.DECIDE, "2 approvals waiting", Strength.RING), actions[1])
        assertEquals(AlertAction.Show(Slot.DECIDE, "Approval waiting", Strength.QUIET), actions[2])
        // The server's own short code wins over the document type; an unknown one is not shown.
        assertEquals(About.MACHINERY, Alerts.about(signal("approval", "about" to "machinery", "doctype" to "Payment Entry")))
        assertEquals(About.ATTENDANCE, Alerts.about(signal("verify", "doctype" to "Field Attendance Entry")))
        assertEquals(null, Alerts.about(signal("approval", "about" to "Pay A. Example 1,50,000.00", "doctype" to "Pay A. Example")))
        assertEquals(listOf("Attendance waiting", "Payment waiting", "Purchase waiting", "Leave waiting", "Petty cash waiting", "Store issue waiting", "Machinery working waiting"), About.entries.map { it.words })
        // A kind without a reference is said, but there is nothing to open.
        assertEquals(AlertAction.Show(Slot.DECIDE, "Leave waiting", Strength.RING), Alerts.handle(signal("approval", "about" to "leave"), AlertState()).second)
    }

    @Test
    fun theTwoHourReminderRingsWhileSomethingWaitsAndEndsWhenNothingDoes() {
        val (waiting, _) = run(approval("PO-1"), approval("PO-2"))
        assertEquals(AlertAction.Show(Slot.DECIDE, "Reminder: 2 approvals are still waiting", Strength.RING), Alerts.remind(waiting))
        val (one, _) = run(approval("PO-1"))
        assertEquals(AlertAction.Show(Slot.DECIDE, "Reminder: an approval is still waiting", Strength.RING), Alerts.remind(one))
        assertEquals(AlertAction.Ignore, Alerts.remind(AlertState()))
        // What came back to me is not a decision of mine: it does not keep the reminder going.
        assertEquals(AlertAction.Ignore, Alerts.remind(AlertState(rejected = setOf("x"))))
        // Asked for inside the app, with nothing known to the phone: it still rings, as for one thing.
        assertEquals(AlertAction.Show(Slot.DECIDE, "Reminder: an approval is still waiting", Strength.RING), Alerts.remind(AlertState(), asked = true))
    }

    @Test
    fun chatsAreCountedByChatOpenTheirChatWhenItIsOneAndClearWhenRead() {
        val direct = signal("message", "room" to "!one")
        val team = signal("message", "room" to "!two", "prio" to "normal")
        val (state, actions) = run(direct, direct, team, signal("read", "what" to "chat", "room" to "!one"), signal("read", "what" to "chat"))
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.ALERT, item = "!one"), actions[0])
        assertEquals(actions[0], actions[1]) // more messages in the same chat are still one chat
        // A busy room makes no sound, and with two chats the tap leads to the list.
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New messages in 2 chats", Strength.QUIET), actions[2])
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.QUIET), actions[3])
        assertEquals(AlertAction.Remove(Slot.MESSAGE), actions[4])
        assertEquals(AlertState(), state)
        // What is kept is a fingerprint of the room's number, never the number.
        assertFalse(Alerts.handle(direct, AlertState()).first.chats.single().contains("one"))
    }

    @Test
    fun theChatServersOwnSignalIsReadToo() {
        val (state, actions) = run(mapOf("room_id" to "!abc", "event_id" to "$1", "unread" to "3", "prio" to "high"), mapOf("unread" to "0"))
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.ALERT, item = "!abc"), actions[0])
        assertEquals(AlertAction.Remove(Slot.MESSAGE), actions[1])
        assertEquals(AlertState(), state)
        // The sender's "unread" is the person's total over all rooms; "missed_calls" may ride along and is not read.
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.QUIET, item = "!abc"), Alerts.handle(mapOf("room_id" to "!abc", "event_id" to "$2", "unread" to "5", "prio" to "normal", "missed_calls" to "1"), AlertState()).second)
        // Without a "prio", or with one the app does not know, a message is never silenced.
        for (odd in listOf(mapOf("room_id" to "!abc"), mapOf("room_id" to "!abc", "prio" to "low"), mapOf("room_id" to "!abc", "prio" to ""))) {
            assertEquals(odd.toString(), Strength.ALERT, (Alerts.handle(odd, AlertState()).second as AlertAction.Show).strength)
        }
        // Whatever else that sender puts in is never shown.
        val loaded = mapOf("room_id" to "!abc", "sender_display_name" to "A. Example", "content_body" to "Pay 1,50,000.00", "room_name" to "Site A")
        assertEquals("New message", (Alerts.handle(loaded, AlertState()).second as AlertAction.Show).words)
    }

    @Test
    fun mailAndNoticesAreCountedAndClearWhenRead() {
        val (state, actions) = run(signal("mail", "mail" to "t4"), signal("mail"), signal("mail", "count" to "7"), signal("read", "what" to "mail"), signal("notice"), signal("notice"), signal("read", "what" to "notice"))
        assertEquals(AlertAction.Show(Slot.MAIL, "New mail", Strength.QUIET, item = "t4"), actions[0])
        assertEquals(AlertAction.Show(Slot.MAIL, "2 new mails", Strength.QUIET), actions[1])
        assertEquals(AlertAction.Show(Slot.MAIL, "7 new mails", Strength.QUIET), actions[2]) // the sender's own count wins
        assertEquals(AlertAction.Remove(Slot.MAIL), actions[3])
        assertEquals(AlertAction.Show(Slot.NOTICE, "2 notices", Strength.QUIET), actions[5])
        assertEquals(AlertAction.Remove(Slot.NOTICE), actions[6])
        assertEquals(AlertState(), state)
        assertEquals(AlertAction.Remove(Slot.MAIL), Alerts.handle(signal("mail", "count" to "0"), AlertState(mails = 4)).second)
        assertEquals(AlertAction.Ignore, Alerts.handle(signal("read", "what" to "everything"), AlertState()).second)
        // Approvals are never cleared by "read": only a decision removes them.
        val waiting = run(approval("PO-1")).first
        assertEquals(waiting, Alerts.handle(signal("read", "what" to "chat"), waiting).first.copy(chats = emptySet()))
    }

    @Test
    fun chatMailAndNoticesHaveTheirOwnWordsAndStrengths() {
        assertEquals(AlertAction.Show(Slot.MESSAGE, "New message", Strength.ALERT), Alerts.handle(signal("message"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.MAIL, "New mail", Strength.QUIET), Alerts.handle(signal("mail"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.NOTICE, "Notice", Strength.QUIET), Alerts.handle(signal("notice"), AlertState()).second)
        assertEquals(AlertAction.Show(Slot.DECIDE, Alerts.TEST_WORDS, Strength.RING, test = true), Alerts.handle(signal("test"), AlertState()).second)
        assertEquals(listOf(Lead.INBOX, Lead.INBOX, Lead.CHAT, Lead.MAIL, Lead.CHAT), Slot.entries.map { it.lead })
        assertEquals(Slot.entries.size, Slot.entries.map { it.id }.toSet().size)
    }
}
