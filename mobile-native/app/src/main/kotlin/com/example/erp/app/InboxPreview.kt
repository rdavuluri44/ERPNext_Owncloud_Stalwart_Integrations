package com.example.erp.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.Decided
import com.example.erp.core.Decision
import com.example.erp.core.DecisionResult
import com.example.erp.core.Delegation
import com.example.erp.core.DelegationFacts
import com.example.erp.core.Entry
import com.example.erp.core.Delegations
import com.example.erp.core.Leave
import com.example.erp.core.Receiver
import com.example.erp.core.Relation
import com.example.erp.core.Reviews
import com.example.erp.core.Inbox
import com.example.erp.core.Item
import com.example.erp.core.ItemKind
import com.example.erp.core.Line
import com.example.erp.core.Rejection
import com.example.erp.core.Sent
import com.example.erp.core.SentState
import com.example.erp.core.Step
import java.time.LocalDateTime

/**
 * Test builds only: Inbox against a stand-in, because there is no sign-in and no server answer yet. The items,
 * people and amounts are made up and live in memory only; a decision changes nothing but this list. The
 * fingerprint question is the real one. The "Signal" button plays "no connection". Two items play what can go
 * wrong: one is decided by someone else first, one changes after it was opened. One item plays "delegated to
 * me". Remove with the real Inbox
 * (cleanup list).
 *
 * @param sign the app's real fingerprint question.
 */
@Composable
fun InboxPreviewScreen(
    sign: (String, (Boolean, String?) -> Unit) -> Unit, now: LocalDateTime = LocalDateTime.now(), jump: InboxJump? = null, onJumped: () -> Unit = {},
    standIn: DelegationStandIn = remember { DelegationStandIn() }, remind: () -> Unit = {}, onCount: (Int) -> Unit = {},
) {
    var waiting by remember { mutableStateOf(sampleWaiting(now)) }
    LaunchedEffect(waiting) { onCount(Inbox.count(waiting)) }
    var decided by remember { mutableStateOf(sampleDecided(now)) }
    var sent by remember { mutableStateOf(sampleSent(now)) }
    var online by remember { mutableStateOf(true) }
    var changedOnce by remember { mutableStateOf(false) }
    val actions = InboxActions(
        sign = sign,
        decide = { id, _, decision, reason ->
            val item = waiting.first { it.id == id }
            when {
                !online -> DecisionResult.NoConnection
                id == TAKEN -> {
                    waiting = waiting.filter { it.id != id }
                    DecisionResult.Taken("Admin, P. Example", now.minusMinutes(4), Decision.APPROVED)
                }
                id == CHANGES && !changedOnce -> {
                    changedOnce = true
                    waiting = waiting.map {
                        if (it.id == id) it.copy(amount = "1275000.50", lines = it.lines + Line("Changed after you opened it", "The quantity went from 25 t to 25.5 t.", "Changed by the sender")) else it
                    }
                    DecisionResult.Changed
                }
                else -> {
                    waiting = waiting.filter { it.id != id }
                    decided = listOf(Decided(item, decision, now, reason)) + decided
                    if (decision == Decision.APPROVED) DecisionResult.Done("Approved. It moves on to the next step.")
                    else DecisionResult.Done("Rejected. ${item.from} is told.")
                }
            }
        },
        review = { id, _, approve, reject ->
            val item = waiting.first { it.id == id }
            when {
                !online -> DecisionResult.NoConnection
                id == TAKEN -> {
                    waiting = waiting.filter { it.id != id }
                    DecisionResult.Taken("Admin, P. Example", now.minusMinutes(4), Decision.APPROVED)
                }
                else -> {
                    val said = Reviews.sentence(item, approve.size, reject.size, failed = 0)
                    waiting = waiting.filter { it.id != id }
                    decided = listOf(Decided(item, if (approve.isEmpty()) Decision.REJECTED else Decision.APPROVED, now, since = said)) + decided
                    DecisionResult.Done(said)
                }
            }
        },
        remind = remind,
        delegate = { id, _, to, reason ->
            if (!online) DecisionResult.NoConnection else {
                waiting = waiting.map { if (it.id == id) it.copy(delegatedTo = to.name, delegationReason = reason) else it }
                DecisionResult.Done("Delegated to ${to.name}. You can still decide it yourself.")
            }
        },
        delegateAll = { to, until -> if (online) standIn.delegateAll(to, until, now) else DecisionResult.NoConnection },
    )
    Column(Modifier.fillMaxSize()) {
        OutlineButton(if (online) "Signal: on (stand-in)" else "Signal: off (stand-in)", { online = !online }, Modifier.padding(horizontal = Look.Gap, vertical = 8.dp))
        Box(Modifier.weight(1f)) { InboxScreen(waiting, decided, sent, now, online, actions, jump, onJumped, standIn.facts(now)) }
    }
}

/**
 * Test builds only: the made-up people, leave and delegation, in memory, shared by Inbox and More. The real ones
 * come from the server, which also checks them (cleanup list).
 */
class DelegationStandIn {
    var running by mutableStateOf<Delegation?>(null)
    var onLeave by mutableStateOf(true)

    fun facts(now: LocalDateTime) = DelegationFacts(
        receivers = listOf(
            Receiver("higher", "Management, R. Example", Relation.HIGHER),
            Receiver("peer-1", "Project manager, P. Example", Relation.PEER),
            Receiver("peer-2", "Project manager, V. Example", Relation.PEER, onLeave = true),
            Receiver("deputy", "Deputy manager, D. Example", Relation.DEPUTY),
        ),
        leave = if (onLeave) Leave(now.toLocalDate().atStartOfDay(), now.toLocalDate().plusDays(4).atTime(18, 0)) else null,
        running = running,
        toMe = listOf("Project manager, P. Example delegated one approval to you. It is in Inbox."),
    )

    fun delegateAll(to: Receiver, until: LocalDateTime, now: LocalDateTime): DecisionResult {
        val leave = Delegations.leaveNow(facts(now).leave, now) ?: return DecisionResult.NotAllowed
        val set = Delegation(to, Delegations.start(leave, now), Delegations.until(until, leave, now))
        running = set
        return DecisionResult.Done("Delegated. " + Delegations.runningLine(set, now))
    }
}

/** Test builds only: Delegation (under More) against the stand-in, with a switch that plays "no approved leave". */
@Composable
fun DelegationPreviewScreen(standIn: DelegationStandIn, sign: (String, (Boolean, String?) -> Unit) -> Unit, now: LocalDateTime = LocalDateTime.now()) {
    Column(Modifier.fillMaxSize()) {
        OutlineButton(if (standIn.onLeave) "Leave: approved (stand-in)" else "Leave: none (stand-in)", { standIn.onLeave = !standIn.onLeave }, Modifier.padding(horizontal = Look.Gap, vertical = 8.dp))
        Box(Modifier.weight(1f)) {
            DelegationScreen(standIn.facts(now), now, sign, onDelegateAll = { to, until -> standIn.delegateAll(to, until, now) }, onEnd = { standIn.running = null })
        }
    }
}

private const val TAKEN = "attendance-b"
private const val CHANGES = "purchase-steel"

/** The number the bar shows for Inbox before the stand-in was opened. */
internal fun standInWaiting(now: LocalDateTime): Int = Inbox.count(sampleWaiting(now))

private fun sampleWaiting(now: LocalDateTime): List<Item> {
    val engineer = "Engineer, A. Example"
    val supervisor = "Site supervisor, K. Example"
    fun worker(n: Int, time: String, unusual: String? = null, notMine: String? = null) = Entry("w$n", "Worker $n", "Checked in $time", unusual, notMine)
    return listOf(
        Item(
            "attendance-a", ItemKind.ATTENDANCE_APPROVE, "Attendance, Site A, 6 workers", engineer, now.minusMinutes(95), deadline = now.toLocalDate().atTime(23, 30),
            trail = listOf(Step(supervisor, "Sent", now.minusHours(3)), Step(engineer, "Verified", now.minusMinutes(95))),
            entries = listOf(
                worker(1, "08:52"), worker(2, "08:55"), worker(3, "08:57", "Outside the site by 140 m"), worker(4, "09:01"), worker(5, "09:20", "Time changed by hand"),
                worker(6, "08:49", notMine = "You marked this worker yourself, so someone else reviews this one."),
            ),
        ),
        Item(
            TAKEN, ItemKind.ATTENDANCE_APPROVE, "Attendance, Site B, 3 workers", engineer, now.minusHours(3),
            trail = listOf(Step(supervisor, "Sent", now.minusHours(5)), Step(engineer, "Verified", now.minusHours(3))),
            entries = listOf(worker(1, "08:40"), worker(2, "08:44"), worker(3, "08:51")),
        ),
        Item(
            "payment", ItemKind.PAYMENT, "Payment to a supplier", "Accounts, S. Example", now.minusHours(6), amount = "150000",
            trail = listOf(Step("Accounts, S. Example", "Prepared", now.minusHours(6))),
            lines = listOf(Line("For", "Cement, delivered to Site A on 24 Nov."), Line("Invoice", "Attached, 1 page."), Line("Purchase order", "Approved on 20 Nov.")),
        ),
        Item(
            CHANGES, ItemKind.PURCHASE, "Purchase request: steel", "Store keeper, M. Example", now.minusHours(28), amount = "1250000.50",
            trail = listOf(Step("Store keeper, M. Example", "Asked", now.minusHours(28))),
            lines = listOf(Line("What", "Steel bars, 25 t, for Site B."), Line("Needed by", "5 Dec.")),
        ),
        Item(
            "machinery", ItemKind.PURCHASE, "Machinery working, Site B, 2 days", supervisor, now.minusHours(4), amount = "64000",
            delegatedBy = "Project manager, P. Example", delegationReason = "Travelling",
            lines = listOf(Line("What", "Excavator, 2 days, 16 hours."), Line("Log", "Signed by the operator.")),
        ),
        Item("leave", ItemKind.LEAVE, "Leave, 3 days", supervisor, now.minusHours(20), lines = listOf(Line("Days", "2 to 4 December."), Line("Who covers", "The second supervisor of Site A."))),
        Item(
            "advance", ItemKind.PAYMENT, "Advance for site expenses", "You", now.minusHours(2), amount = "20000", sentByMe = true,
            lines = listOf(Line("For", "Small purchases at Site A in December.")),
        ),
        Item(
            "cement", ItemKind.PURCHASE, "Purchase request: cement", "You", now.minusHours(50), amount = "480000",
            rejection = Rejection("Management, R. Example", now.minusHours(2), "Amount or quantity is wrong: more than the estimate for this month"),
            lines = listOf(Line("What", "Cement, 1,200 bags, for Site A.")),
        ),
    )
}

private fun sampleDecided(now: LocalDateTime): List<Decided> = listOf(
    Decided(Item("old-1", ItemKind.ATTENDANCE_APPROVE, "Attendance, Site A, 24 workers", "Engineer, A. Example", now.minusDays(1)), Decision.APPROVED, now.minusDays(1).plusHours(1), since = "Now with HR for the month's pay."),
    Decided(
        Item("old-2", ItemKind.PURCHASE, "Purchase request: sand", "Store keeper, M. Example", now.minusDays(3), amount = "96000"),
        Decision.REJECTED, now.minusDays(3).plusHours(2), reason = "A document is missing", since = "Corrected and presented again; approved by you 2 days ago.",
    ),
)

private fun sampleSent(now: LocalDateTime): List<Sent> = listOf(
    Sent("s1", "Advance for site expenses", "Management, R. Example", now.minusHours(2), SentState.WAITING),
    Sent("s2", "Purchase request: cement", "Management, R. Example", now.minusHours(2), SentState.REJECTED, "Amount or quantity is wrong: more than the estimate for this month"),
    Sent("s3", "Leave, 1 day", "Management, R. Example", now.minusHours(30), SentState.WAITING),
    Sent("s4", "Purchase request: tools", "Management, R. Example", now.minusDays(4), SentState.APPROVED),
)
