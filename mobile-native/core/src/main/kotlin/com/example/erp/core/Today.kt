package com.example.erp.core

import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Today, the home screen (plan of 27 November 2026, finalised by the owner the same day). It answers three
 * questions in this order: what must I do now, what is waiting on me, what should I know.
 *
 * The rules here work from what the server says exists for this person ([TodayFacts]); they never look at a job
 * title. A card is made only when it applies, and it carries counts, never a name, an amount or a message.
 */
enum class AttendanceState { NOT_IN, IN, OUT }

data class OwnAttendance(val state: AttendanceState, val at: LocalTime? = null, val outsideSite: Boolean = false)

enum class TeamState { NOT_SENT, WITH_ENGINEER, APPROVED }

data class TeamDay(val marked: Int, val total: Int, val state: TeamState)

/** Things of one kind that wait for this person's decision. [deadline] is a day and a time, so an old copy never says "today" wrongly. */
data class Waiting(val count: Int, val sites: Int = 1, val oldestSince: LocalDateTime? = null, val deadline: LocalDateTime? = null)

/**
 * My own open request and what the server may be asked about. Both are fixed lists with the words written here:
 * nothing the server writes freely reaches Today, so a name or an amount cannot arrive inside a sentence.
 */
enum class RequestKind(val label: String) { LEAVE("Leave"), EXPENSE("Expense claim"), ADVANCE("Advance"), OTHER("Request") }

enum class RequestState(val sentence: String, val word: String, val tone: Tone) {
    WAITING("waiting for approval.", "Waiting", Tone.WAITING),
    APPROVED("approved.", "Approved", Tone.GOOD),
    RETURNED("returned to you to correct.", "Returned", Tone.WRONG),
}

data class MyRequest(val kind: RequestKind, val state: RequestState)

enum class Source(val label: String) { ATTENDANCE("attendance"), APPROVALS("approvals"), PURCHASES("purchases"), PAYMENTS("payments"), LEAVE("leave"), FACES("faces"), CHAT("chat"), MAIL("mail") }

data class SitesDay(val notSent: Int = 0, val sent: Int = 0, val verified: Int = 0, val approved: Int = 0) {
    val total: Int get() = notSent + sent + verified + approved
}

/** What the server (and the phone's own queue) say about this person's day. Null or zero: it does not apply. */
data class TodayFacts(
    val attendance: OwnAttendance? = null,
    val team: TeamDay? = null,
    val returned: Int = 0,
    val waitingToSend: Int = 0,
    val toVerify: Waiting? = null,
    val toApprove: Waiting? = null,
    val sites: SitesDay? = null,
    val faceQueue: Int = 0,
    val facesMissing: Int = 0,
    val accessRequests: Int = 0,
    val myRequest: MyRequest? = null,
    val chatUnread: Int = 0,
    /** Null: this person has no mailbox. */
    val mailUnread: Int? = null,
    val holiday: Boolean = false,
    /** False until the project manager has given this person a site. */
    val setUp: Boolean = true,
    /** What could not be asked just now. */
    val failed: List<Source> = emptyList(),
    val online: Boolean = true,
    /** When the numbers were last fetched; shown when the phone is offline. */
    val asOf: LocalDateTime? = null,
    /** Minutes the phone's clock differs from the server's. */
    val clockOffMinutes: Int = 0,
    val keyUnusedDays: Int = 0,
    val offlineHoursLeft: Int? = null,
)

enum class CardKind { MY_ATTENDANCE, MY_TEAM, RETURNED, WAITING_TO_SEND, TO_VERIFY, TO_APPROVE, FACE_QUEUE, ACCESS_REQUESTS, MY_SITES, FACES_MISSING, MY_REQUESTS, CHAT, MAIL }

/** Where a card leads. Null on a card: its screen is not built yet, so the card is not a button. */
enum class Lead { INBOX, CHAT, MAIL }

enum class Tone { GOOD, CARE, WRONG, PLAIN, WAITING }

data class Card(val kind: CardKind, val title: String, val line: String, val tone: Tone, val word: String, val lead: Lead? = null, val deadline: LocalDateTime? = null)

object Today {
    private val CLOCK = DateTimeFormatter.ofPattern("HH:mm")

    private fun many(count: Int, one: String, more: String) = if (count == 1) "1 $one" else "$count $more"

    private fun due(deadline: LocalDateTime?, now: LocalDateTime): String = when {
        deadline == null -> ""
        now.isAfter(deadline) -> " Was due ${Format.dateTime(deadline, now)}."
        deadline.toLocalDate() == now.toLocalDate() -> " Due today, ${deadline.format(CLOCK)}."
        else -> " Due ${Format.dateTime(deadline, now)}."
    }

    /**
     * The cards for today, in order: anything with a deadline today first (the nearest first), then my own work,
     * then what waits for my decision, then what I should know. Nothing is listed that does not apply.
     */
    fun cards(facts: TodayFacts, now: LocalDateTime): List<Card> {
        val cards = mutableListOf<Card>()
        val own = facts.attendance
        if (own != null && !facts.holiday) {
            val time = own.at?.format(CLOCK)
            val outside = if (own.outsideSite && own.state != AttendanceState.OUT) " You are outside the site." else ""
            cards += when (own.state) {
                AttendanceState.NOT_IN -> Card(CardKind.MY_ATTENDANCE, "My attendance", "Not checked in yet.$outside", Tone.CARE, "Not checked in")
                AttendanceState.IN -> Card(CardKind.MY_ATTENDANCE, "My attendance", "Checked in${time?.let { " at $it" }.orEmpty()}.$outside", Tone.GOOD, "Checked in")
                AttendanceState.OUT -> Card(CardKind.MY_ATTENDANCE, "My attendance", "Checked out${time?.let { " at $it" }.orEmpty()}.", Tone.PLAIN, "Done")
            }
        }
        // A team without people, or more marked than there are people, is not a day the app can describe: no card.
        facts.team?.takeIf { !facts.holiday && it.total > 0 && it.marked in 0..it.total }?.let { team ->
            val (state, tone, word) = when (team.state) {
                TeamState.NOT_SENT -> Triple("Not sent yet.", Tone.CARE, "Not sent")
                TeamState.WITH_ENGINEER -> Triple("Sent, with the engineer.", Tone.WAITING, "Sent")
                TeamState.APPROVED -> Triple("Approved.", Tone.GOOD, "Approved")
            }
            cards += Card(CardKind.MY_TEAM, "My team today", "Marked ${team.marked} of ${team.total}. $state", tone, word)
        }
        if (facts.returned > 0) {
            cards += Card(CardKind.RETURNED, "Returned to me", many(facts.returned, "entry was", "entries were") + " sent back to correct.", Tone.WRONG, "${facts.returned}")
        }
        if (facts.waitingToSend > 0) {
            cards += Card(CardKind.WAITING_TO_SEND, "Waiting to send", many(facts.waitingToSend, "thing is", "things are") + " saved on this phone and not sent yet.", Tone.WAITING, "${facts.waitingToSend}")
        }
        facts.toVerify?.takeIf { it.count > 0 }?.let {
            cards += Card(CardKind.TO_VERIFY, "To verify", many(it.count, "entry", "entries") + (if (it.sites > 0) " at " + many(it.sites, "site", "sites") else "") + "." + due(it.deadline, now), Tone.CARE, "${it.count}", Lead.INBOX, it.deadline)
        }
        facts.toApprove?.takeIf { it.count > 0 }?.let {
            val oldest = it.oldestSince?.let { since -> ", the oldest for ${Format.waiting(since, now)}" }.orEmpty()
            cards += Card(CardKind.TO_APPROVE, "To approve", "${it.count} waiting$oldest." + due(it.deadline, now), Tone.CARE, "${it.count}", Lead.INBOX, it.deadline)
        }
        if (facts.faceQueue > 0) cards += Card(CardKind.FACE_QUEUE, "Face queue", many(facts.faceQueue, "photo", "photos") + " to settle.", Tone.CARE, "${facts.faceQueue}", Lead.INBOX)
        if (facts.accessRequests > 0) {
            cards += Card(CardKind.ACCESS_REQUESTS, "Access requests", many(facts.accessRequests, "person waits", "people wait") + " for you.", Tone.CARE, "${facts.accessRequests}", Lead.INBOX)
        }
        facts.sites?.takeIf { it.total > 0 && !facts.holiday }?.let { sites ->
            val parts = listOfNotNull(
                "${sites.approved} approved".takeIf { sites.approved > 0 },
                "${sites.verified} verified".takeIf { sites.verified > 0 },
                "${sites.sent} sent".takeIf { sites.sent > 0 },
                "${sites.notSent} not sent yet".takeIf { sites.notSent > 0 },
            )
            val done = sites.approved == sites.total
            cards += Card(CardKind.MY_SITES, "My sites today", many(sites.total, "site", "sites") + ": " + parts.joinToString(", ") + ".", if (done) Tone.GOOD else Tone.PLAIN, if (done) "All approved" else "In progress")
        }
        if (facts.facesMissing > 0) {
            cards += Card(CardKind.FACES_MISSING, "Faces missing", many(facts.facesMissing, "worker has", "workers have") + " no face enrolled.", Tone.PLAIN, "${facts.facesMissing}")
        }
        facts.myRequest?.let { cards += Card(CardKind.MY_REQUESTS, "My requests", "${it.kind.label}: ${it.state.sentence}", it.state.tone, it.state.word) }
        if (facts.chatUnread > 0) cards += Card(CardKind.CHAT, "Chat", "${facts.chatUnread} unread.", Tone.PLAIN, "${facts.chatUnread}", Lead.CHAT)
        if ((facts.mailUnread ?: 0) > 0) cards += Card(CardKind.MAIL, "Mail", "${facts.mailUnread} unread.", Tone.PLAIN, "${facts.mailUnread}", Lead.MAIL)
        // A deadline today (or one already missed) goes first, the nearest first; everything else, also a deadline
        // on a later day, keeps the order above.
        fun urgent(card: Card) = card.deadline != null && !card.deadline.toLocalDate().isAfter(now.toLocalDate())
        return cards.sortedWith(compareBy<Card> { !urgent(it) }.thenBy { if (urgent(it)) it.deadline else null })
    }

    /** The one status line under the date. */
    fun status(facts: TodayFacts, now: LocalDateTime): Pair<Tone, String> = when {
        !facts.online -> {
            val waiting = if (facts.waitingToSend > 0) ": " + many(facts.waitingToSend, "thing waits", "things wait") + " to be sent" else ""
            val age = facts.asOf?.let { ". The numbers are as of ${Format.dateTime(it, now)}" }.orEmpty()
            Tone.PLAIN to "No connection$waiting$age."
        }
        kotlin.math.abs(facts.clockOffMinutes) >= 5 ->
            Tone.CARE to "Your phone's clock is ${kotlin.math.abs(facts.clockOffMinutes)} minutes ${if (facts.clockOffMinutes > 0) "ahead" else "behind"}. Attendance uses the server's time."
        else -> Tone.GOOD to "Up to date."
    }

    /** Things that cost access if ignored. */
    fun warnings(facts: TodayFacts): List<String> = listOfNotNull(
        "Your key was not used for ${facts.keyUnusedDays} days. Open the app again within ${many(7 - facts.keyUnusedDays, "day", "days")}, or the key is removed.".takeIf { facts.keyUnusedDays in 5..6 },
        "Your key was not used for ${facts.keyUnusedDays} days and can be removed at any moment. Use the app with a connection today.".takeIf { facts.keyUnusedDays >= 7 },
        facts.offlineHoursLeft?.takeIf { !facts.online && it > 0 }?.let { "Without a connection the app opens for ${many(it, "more hour", "more hours")}." },
        "Without a connection the app will not open again. Connect before you close it.".takeIf { !facts.online && facts.offlineHoursLeft != null && facts.offlineHoursLeft <= 0 },
    )

    /**
     * What is said when there is no card. "Nothing is waiting" is said only when everything could be checked just
     * now: a source that failed is named instead ([TodayFacts.failed]), and without a connection nothing is
     * claimed at all (the status line says "No connection"). Never an all-clear the app cannot stand behind.
     */
    fun emptyLine(facts: TodayFacts): String? = when {
        !facts.setUp -> "You are set up. Your site and your team appear here when the project manager adds you."
        facts.failed.isNotEmpty() -> null
        !facts.online -> null
        facts.holiday -> "Today is a holiday for your site. Nothing is waiting for you."
        else -> "Nothing is waiting for you today."
    }

    fun failedLine(facts: TodayFacts): String? = facts.failed.takeIf { it.isNotEmpty() }?.let { failed -> "Could not check: ${failed.joinToString(", ") { it.label }}. What is shown may be incomplete." }
}
