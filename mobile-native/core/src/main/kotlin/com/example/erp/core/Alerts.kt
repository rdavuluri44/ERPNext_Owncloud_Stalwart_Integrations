package com.example.erp.core

import java.security.MessageDigest

/**
 * Alerts: what the phone shows for a signal (plans of 27 and 28 November 2026, finalised by the owner).
 *
 * A signal carries no content: a kind, sometimes a count, a number of hours and a reference. **Every word shown is
 * written here. Nothing shown is ever taken from the signal**, so a wrong or forged signal cannot put a name, an
 * amount or a text on a locked phone; a kind this app does not know is dropped. (This is true of every signal the
 * app handles. The server must send data-only signals: see `AlertService`.)
 */
enum class Strength {
    /** Rings: a decision waits for the person. */
    RING,

    /** The phone's normal alert sound. */
    ALERT,

    /** No sound: the alert appears or changes quietly. */
    QUIET,
}

/** One alert per slot on the phone, with its count. [id] is the phone's number for it; [lead] is where a tap goes. */
enum class Slot(val id: Int, val lead: Lead) {
    DECIDE(1, Lead.INBOX),
    REJECTED(2, Lead.INBOX),
    MESSAGE(3, Lead.CHAT),
    MAIL(4, Lead.MAIL),
    NOTICE(5, Lead.CHAT),
}

/**
 * What an approval is about, for the words on a locked phone: "Payment waiting". A kind, never a name or an
 * amount. The words are written here; the signal only chooses among them.
 */
enum class About(val code: String, val words: String) {
    ATTENDANCE("attendance", "Attendance waiting"),
    PAYMENT("payment", "Payment waiting"),
    PURCHASE("purchase", "Purchase waiting"),
    LEAVE("leave", "Leave waiting"),
    PETTY_CASH("petty_cash", "Petty cash waiting"),
    STORE("store", "Store issue waiting"),
    MACHINERY("machinery", "Machinery working waiting"),
}

sealed interface AlertAction {
    /**
     * @param item set when exactly this one thing waits: its reference, so "Approve" and "Reject" on the alert
     *   can open it. It is never shown and the app does not store it; the phone holds it inside the
     *   alert while that alert lives.
     * @param test the phone's own test: it cannot be reminded of, only stopped.
     */
    data class Show(val slot: Slot, val words: String, val strength: Strength, val item: String? = null, val test: Boolean = false) : AlertAction
    data class Remove(val slot: Slot) : AlertAction

    /** An unknown or broken signal: nothing is shown. */
    data object Ignore : AlertAction
}

/**
 * What the phone remembers between signals so it can count and remove: for each thing that waits, a short
 * fingerprint of its reference, never the reference itself. Nothing readable about the business is kept.
 */
data class AlertState(
    val deciding: Set<String> = emptySet(),
    val rejected: Set<String> = emptySet(),
    /** The chats with something unread, as fingerprints of their numbers. */
    val chats: Set<String> = emptySet(),
    val mails: Int = 0,
    val notices: Int = 0,
)

object Alerts {
    private const val MAX_COUNT = 999
    private const val MAX_HOURS = 9999

    /**
     * The most fingerprints kept per list. A "decided elsewhere" signal can get lost on the way, so a list could
     * otherwise grow without end; the real Inbox sets the lists right when it loads (not built yet).
     */
    const val MAX_MARKS = 500

    /** The fingerprint kept for one waiting thing. The same thing always gives the same fingerprint. */
    fun mark(doctype: String, docname: String): String =
        MessageDigest.getInstance("SHA-256").digest("$doctype\n$docname".toByteArray()).take(8).joinToString("") { "%02x".format(it) }

    private fun mark(data: Map<String, String>): String? {
        val doctype = data["doctype"].orEmpty()
        val docname = data["docname"].orEmpty()
        return if (doctype.isEmpty() || docname.isEmpty() || doctype.length > 200 || docname.length > 200) null else mark(doctype, docname)
    }

    private fun number(text: String?, max: Int): Int? = text?.takeIf { it.length <= 6 && it.all { c -> c in '0'..'9' } && it.isNotEmpty() }?.toInt()?.coerceIn(0, max)

    /** The kind of thing, from the server's short code, or from a document type this app knows; null otherwise. */
    fun about(data: Map<String, String>): About? {
        About.entries.find { it.code == data["about"] }?.let { return it }
        val doctype = data["doctype"].orEmpty()
        return when {
            doctype.length > 200 -> null
            "Attendance" in doctype -> About.ATTENDANCE
            doctype == "Payment Entry" -> About.PAYMENT
            doctype in setOf("Purchase Order", "Purchase Invoice", "Material Request") -> About.PURCHASE
            doctype == "Leave Application" -> About.LEAVE
            doctype == "Expense Claim" -> About.PETTY_CASH
            doctype == "Stock Entry" -> About.STORE
            else -> null
        }
    }

    /**
     * "Remind me in 2 hours" has come due (the developer's decision of 28 November 2026: fixed at 2 hours, at every
     * hour of the day, repeating until nothing waits). Nothing waiting any more: nothing is shown and the repeat ends.
     */
    fun remind(state: AlertState, asked: Boolean = false): AlertAction = when {
        state.deciding.isNotEmpty() -> AlertAction.Show(Slot.DECIDE, reminderWords(state.deciding.size, null), Strength.RING)
        // Asked for inside the app, on something the phone had no alert for: reminded of all the same.
        asked -> AlertAction.Show(Slot.DECIDE, reminderWords(1, null), Strength.RING)
        else -> AlertAction.Ignore
    }

    fun chatWords(chats: Int): String = if (chats <= 1) "New message" else "New messages in $chats chats"

    fun mailWords(count: Int): String = if (count <= 1) "New mail" else "$count new mails"

    fun noticeWords(count: Int): String = if (count <= 1) "Notice" else "$count notices"

    /** A short opaque number of a chat or a mail, as the signal carries it; null when missing or absurd. */
    private fun reference(text: String?): String? = text?.takeIf { it.isNotEmpty() && it.length <= 200 }

    fun waitingWords(count: Int): String = if (count <= 1) "Approval waiting" else "$count approvals waiting"

    fun rejectedWords(count: Int): String = if (count <= 1) "Rejected, to correct" else "$count rejected, to correct"

    fun reminderWords(count: Int, hours: Int?): String {
        val since = hours?.takeIf { it > 0 }?.let { if (it == 1) "1 hour" else "$it hours" }
        return when {
            count <= 1 -> "Reminder: an approval " + (since?.let { "has been waiting for $it" } ?: "is still waiting")
            else -> "Reminder: $count approvals are still waiting" + since?.let { ", the oldest for $it" }.orEmpty()
        }
    }

    /** What a test shows; it says that it is one. */
    const val TEST_WORDS = "Test alert. This is how an approval rings."

    /**
     * One signal in, the new state and what to do out. The server's kinds (owner's note of 28 November 2026):
     * `approval`, `verify` (something waits for a decision), `returned` (something came back to its sender, shown
     * as "rejected"), `reminder`, `remove`. `message` and `mail` are for the chat and mail senders. `notice` is
     * not used: the owner said on 28 November 2026 that no notice signal comes from the server; a notice arrives
     * as a chat alert for the Notices room.
     * `test` is the phone's own. `read` (with `what`: chat, mail or notice) says that something was read elsewhere.
     * The chat server's own sender does not use these kinds: it names a room (`room_id`) and gives the unread count
     * (`unread`), so that shape is read too.
     */
    fun handle(data: Map<String, String>, state: AlertState): Pair<AlertState, AlertAction> {
        val kind = data["kind"] ?: when {
            data["unread"] == "0" -> "read-chat"
            "room_id" in data || "event_id" in data -> "message"
            else -> null
        }
        when (kind) {
            "approval", "verify" -> {
                val mark = mark(data)
                val deciding = if (mark == null || state.deciding.size >= MAX_MARKS) state.deciding else state.deciding + mark
                // A signal without a usable reference still rings: a real approval is never dropped for a missing field.
                // When this is the only thing waiting, the alert says its kind and can lead straight to it.
                val only = mark != null && deciding == setOf(mark)
                val words = if (only || deciding.isEmpty()) about(data)?.words ?: waitingWords(1) else waitingWords(deciding.size)
                return state.copy(deciding = deciding) to AlertAction.Show(Slot.DECIDE, words, Strength.RING, item = data["docname"].takeIf { only })
            }
            "returned" -> {
                val mark = mark(data)
                val rejected = if (mark == null || state.rejected.size >= MAX_MARKS) state.rejected else state.rejected + mark
                return state.copy(rejected = rejected) to AlertAction.Show(Slot.REJECTED, rejectedWords(rejected.size), Strength.ALERT)
            }
            "reminder" -> {
                val count = number(data["count"], MAX_COUNT) ?: return state to AlertAction.Ignore
                if (count == 0) return state to AlertAction.Ignore
                return state to AlertAction.Show(Slot.DECIDE, reminderWords(count, number(data["oldest_hours"], MAX_HOURS)), Strength.RING)
            }
            "remove" -> {
                val mark = mark(data) ?: return state to AlertAction.Ignore
                return when (mark) {
                    in state.deciding -> {
                        val left = state.deciding - mark
                        state.copy(deciding = left) to if (left.isEmpty()) AlertAction.Remove(Slot.DECIDE) else AlertAction.Show(Slot.DECIDE, waitingWords(left.size), Strength.QUIET)
                    }
                    in state.rejected -> {
                        val left = state.rejected - mark
                        state.copy(rejected = left) to if (left.isEmpty()) AlertAction.Remove(Slot.REJECTED) else AlertAction.Show(Slot.REJECTED, rejectedWords(left.size), Strength.QUIET)
                    }
                    else -> state to AlertAction.Ignore
                }
            }
            "message" -> {
                val room = reference(data["room"] ?: data["room_id"])
                // One alert for all chats, counting the chats, not the messages. A chat without a number counts once.
                val chats = if (state.chats.size >= MAX_MARKS) state.chats else state.chats + (room?.let { mark("room", it) } ?: "?")
                // A message in a busy room makes no sound; one to me alone, or one that names me, does.
                // The chat sender marks it itself: `prio` is "high" for those and "normal" for a busy room.
                val strength = if (data["prio"] == "normal") Strength.QUIET else Strength.ALERT
                return state.copy(chats = chats) to AlertAction.Show(Slot.MESSAGE, chatWords(chats.size), strength, item = room.takeIf { chats.size == 1 })
            }
            "mail" -> {
                // The sender's own count wins; without one, each signal is one more.
                val count = number(data["count"], MAX_COUNT) ?: (state.mails + 1).coerceAtMost(MAX_COUNT)
                if (count == 0) return state.copy(mails = 0) to AlertAction.Remove(Slot.MAIL)
                return state.copy(mails = count) to AlertAction.Show(Slot.MAIL, mailWords(count), Strength.QUIET, item = reference(data["mail"]).takeIf { count == 1 })
            }
            "notice" -> {
                val count = number(data["count"], MAX_COUNT) ?: (state.notices + 1).coerceAtMost(MAX_COUNT)
                if (count == 0) return state.copy(notices = 0) to AlertAction.Remove(Slot.NOTICE)
                return state.copy(notices = count) to AlertAction.Show(Slot.NOTICE, noticeWords(count), Strength.QUIET)
            }
            // Read here or on another device: the alert goes, or its count goes down without a sound.
            "read", "read-chat" -> when (if (kind == "read-chat") "chat" else data["what"]) {
                "chat" -> {
                    val room = reference(data["room"])
                    val left = if (room == null) emptySet() else state.chats - mark("room", room)
                    return state.copy(chats = left) to if (left.isEmpty()) AlertAction.Remove(Slot.MESSAGE) else AlertAction.Show(Slot.MESSAGE, chatWords(left.size), Strength.QUIET)
                }
                "mail" -> return state.copy(mails = 0) to AlertAction.Remove(Slot.MAIL)
                "notice" -> return state.copy(notices = 0) to AlertAction.Remove(Slot.NOTICE)
                else -> return state to AlertAction.Ignore
            }
            "test" -> return state to AlertAction.Show(Slot.DECIDE, TEST_WORDS, Strength.RING, test = true)
            else -> return state to AlertAction.Ignore
        }
    }
}
