package com.example.erp.core

import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/**
 * Inbox: what waits for a person's decision (plan of 28 November 2026, decided by the developer that day).
 *
 * The app shows two decisions, Approve and Reject, and a reason is offered but not required. What a rejection does
 * is the server's to say (the owner's answer of 28 November 2026): an attendance entry goes back to be corrected
 * and presented again; other approvals have the actions their workflow defines, and in some a rejection ends the
 * document. The real connection must show the actions the server gives for the item, not assume these two. A person who does
 * not decide now has two other ways (the developer's decision of 28 November 2026): delegate it, or be reminded
 * in 2 hours. There is no "decide later" with a date of one's own: an approval needs a decision.
 */
enum class ItemKind(val heading: String, val money: Boolean = false) {
    ATTENDANCE_VERIFY("Attendance to verify"),
    ATTENDANCE_APPROVE("Attendance to approve"),
    PURCHASE("Purchases", money = true),
    PAYMENT("Payments", money = true),
    LEAVE("Leave"),
}

/** One step of an item's trail: who did what, and when. */
data class Step(val who: String, val what: String, val at: LocalDateTime, val reason: String? = null)

/** One line of evidence. [unusual] says in words what is out of the ordinary about it, when something is. */
data class Line(val title: String, val text: String, val unusual: String? = null)

/** Someone rejected what I sent; it waits for me to correct it. */
data class Rejection(val by: String, val at: LocalDateTime, val reason: String? = null)

enum class Decision(val done: String) { APPROVED("Approved"), REJECTED("Rejected") }

data class Item(
    val id: String,
    val kind: ItemKind,
    val title: String,
    /** Who sent it to me: role and name. */
    val from: String,
    val waitingSince: LocalDateTime,
    val deadline: LocalDateTime? = null,
    /** A plain decimal as the server sends it; shown the Indian way. */
    val amount: String? = null,
    val trail: List<Step> = emptyList(),
    val lines: List<Line> = emptyList(),
    /** I sent this myself, so I may not decide it. */
    val sentByMe: Boolean = false,
    val rejection: Rejection? = null,
    /** The server's mark of the version I am looking at. It goes back with a decision, so the server can refuse one made on an older version. */
    val modified: String = "",
    /** Someone delegated this to me: their role and name. I decide it; I cannot delegate it again. */
    val delegatedBy: String? = null,
    /** I delegated this to someone: their role and name. I can still decide it myself. */
    val delegatedTo: String? = null,
    val delegationReason: String? = null,
    /** The sender's number, as the server knows the person. A written name can change or repeat; this cannot. */
    val fromId: String? = null,
    /** An attendance sheet's workers, each reviewed on its own (see [Reviews]). Empty for everything else. */
    val entries: List<Entry> = emptyList(),
)

/** Something I decided, for "Decided by me". [since] says what became of it afterwards. */
data class Decided(val item: Item, val decision: Decision, val at: LocalDateTime, val reason: String? = null, val since: String? = null)

enum class SentState { WAITING, APPROVED, REJECTED }

/** Something I sent, for "Sent by me": who has it now and since when. */
data class Sent(
    val id: String,
    val title: String,
    val holder: String,
    val since: LocalDateTime,
    val state: SentState,
    val reason: String? = null,
)

/** What the server said to a decision. Nothing counts as decided until it said so. */
sealed interface DecisionResult {
    data class Done(val sentence: String) : DecisionResult

    /** Someone else decided first. */
    data class Taken(val by: String, val at: LocalDateTime, val decision: Decision) : DecisionResult

    /** The item changed since it was opened; the person looks again before deciding. */
    data object Changed : DecisionResult
    data object NotAllowed : DecisionResult
    data object NoConnection : DecisionResult
    data class Failed(val sentence: String) : DecisionResult
}

data class Section(val heading: String, val items: List<Item>)

object Inbox {
    private val CLOCK = DateTimeFormatter.ofPattern("HH:mm")
    const val MAX_REASON = 500
    private const val MAX_TITLE = 80

    /** Control characters and the invisible ones that change the direction of text. */
    private val UNSEEN = Regex("[\\p{Cc}\\p{Cf}]")


    private fun dueNow(item: Item, now: LocalDateTime) = item.deadline != null && !item.deadline.toLocalDate().isAfter(now.toLocalDate())

    /**
     * "Waiting for me", in order: what was rejected back to me (I am holding someone up), what is due today or
     * already missed, then each kind with its oldest first, then what I delegated (someone else has it, I still
     * can decide it).
     */
    fun sections(items: List<Item>, now: LocalDateTime): List<Section> {
        val rejected = items.filter { it.rejection != null }.sortedBy { it.waitingSince }
        val rest = items.filter { it.rejection == null }
        val passed = rest.filter { it.delegatedTo != null }.sortedBy { it.waitingSince }
        val open = rest.filter { it.delegatedTo == null }
        val due = open.filter { dueNow(it, now) }.sortedBy { it.deadline }
        val byKind = ItemKind.entries.map { kind -> Section(kind.heading, open.filter { it.kind == kind && !dueNow(it, now) }.sortedBy { it.waitingSince }) }
        return (listOf(Section("Rejected, to correct", rejected), Section("Due today", due)) + byKind + Section("Delegated by you", passed))
            .filter { it.items.isNotEmpty() }
            .map { it.copy(heading = "${it.heading} (${it.items.size})") }
    }

    /** The number on Inbox: what I must decide myself, and what came back to me to correct. */
    fun count(items: List<Item>): Int = items.count { it.rejection != null || (canDecide(it) && it.delegatedTo == null) }

    /** I never decide what I sent myself, and what was rejected back to me is mine to correct, not to decide. */
    fun canDecide(item: Item): Boolean = !item.sentByMe && item.rejection == null && !amountUnreadable(item) && !workersMissing(item)

    /** An attendance sheet without its workers: there is nothing to look at, so nothing is decided as a whole. */
    fun workersMissing(item: Item): Boolean = item.entries.isEmpty() && (item.kind == ItemKind.ATTENDANCE_VERIFY || item.kind == ItemKind.ATTENDANCE_APPROVE)

    fun amount(item: Item): String? = item.amount?.let { runCatching { Money.indian(Money.parse(it)) }.getOrNull() }

    /**
     * The server sent an amount this app cannot read, or none for a payment or a purchase. Nobody signs an amount
     * they cannot see, and a title must not be able to stand in for a missing one.
     */
    fun amountUnreadable(item: Item): Boolean = if (item.amount == null) item.kind.money else amount(item) == null

    /**
     * What the fingerprint question says: the touch signs exactly this. The amount comes first and the title is one
     * short line, because the sender wrote the title: it must not be able to push the amount away or imitate one.
     */
    fun question(decision: Decision, item: Item): String =
        (if (decision == Decision.APPROVED) "Approve" else "Reject") + amount(item)?.let { " $it" }.orEmpty() + ": " + short(item.title)

    /** A text someone else wrote, made safe for the fingerprint question: one short line, no invisible characters. */
    fun short(text: String): String = Mails.oneLine(text.replace(UNSEEN, " ")).take(MAX_TITLE)

    fun rowLine(item: Item, now: LocalDateTime): String =
        listOfNotNull("From ${item.from}", "waiting ${Format.waiting(item.waitingSince, now)}", amount(item)).joinToString(" · ")

    /** The deadline in words, with how urgent it is; null when the item has none. */
    fun deadline(item: Item, now: LocalDateTime): Pair<Tone, String>? {
        val deadline = item.deadline ?: return null
        return when {
            now.isAfter(deadline) -> Tone.WRONG to "Was due ${Format.dateTime(deadline, now)}"
            deadline.toLocalDate() == now.toLocalDate() -> Tone.CARE to "Due ${deadline.format(CLOCK)}"
            else -> Tone.PLAIN to "Due ${Format.dateTime(deadline, now)}"
        }
    }

    fun rejectionLine(rejection: Rejection, now: LocalDateTime): String =
        "Rejected by ${rejection.by}, ${Format.dateTime(rejection.at, now)}. " + (rejection.reason ?: "No reason given.")

    fun sentLine(sent: Sent, now: LocalDateTime): String = when (sent.state) {
        SentState.WAITING -> "With ${sent.holder} for ${Format.waiting(sent.since, now)}."
        SentState.APPROVED -> "Approved by ${sent.holder}, ${Format.dateTime(sent.since, now)}."
        SentState.REJECTED -> "Rejected by ${sent.holder}, ${Format.dateTime(sent.since, now)}. " + (sent.reason ?: "No reason given.")
    }

    /** The reason as it is sent: the quick choice, the person's own words, both, or nothing. One line, limited length. */
    fun reason(quick: String?, typed: String): String? =
        Mails.oneLine(listOfNotNull(quick, typed.trim().ifEmpty { null }).joinToString(": ")).take(MAX_REASON).ifEmpty { null }
}
