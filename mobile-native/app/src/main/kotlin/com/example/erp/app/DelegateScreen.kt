package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.DecisionResult
import com.example.erp.core.DelegationFacts
import com.example.erp.core.Delegations
import com.example.erp.core.Format
import com.example.erp.core.Inbox
import com.example.erp.core.Item
import com.example.erp.core.Receiver
import java.time.LocalDateTime

/** What the person chose on the Delegate screen. Nothing is sent before the fingerprint. */
sealed interface DelegateChoice {
    data class One(val to: Receiver, val reason: String?) : DelegateChoice
    data class All(val to: Receiver, val from: LocalDateTime, val until: LocalDateTime) : DelegateChoice
}

/**
 * Delegate: one button, two choices. "Only this one" goes to the deputy, a peer or the higher official. "All my
 * approvals until a date" goes to the deputy or a peer, only while on approved leave and inside the leave days.
 * No difference between kinds of approval (version 1). The people offered come from the server.
 *
 * @param item the thing it was opened from; null when opened from More, where only "all" can be chosen.
 */
@Composable
fun DelegateChooser(item: Item?, facts: DelegationFacts, now: LocalDateTime, trouble: String?, onBack: () -> Unit, onDelegate: (DelegateChoice) -> Unit) {
    val leave = Delegations.leaveNow(facts.leave, now)
    val whyNotAll = Delegations.whyNotAll(facts, now)
    // In memory only, like everything a person chooses or types.
    var everything by remember(item?.id) { mutableStateOf(item == null) }
    val all = everything && whyNotAll == null && leave != null
    var to by remember(item?.id, all) { mutableStateOf<Receiver?>(null) }
    var quick by remember(item?.id) { mutableStateOf<String?>(null) }
    var typed by remember(item?.id) { mutableStateOf("") }
    var until by remember(item?.id, leave) { mutableStateOf(leave?.until) }

    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (item != null) TopBar(onBack = onBack)
            Text("Delegate", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            if (item != null) {
                Text(listOfNotNull(item.title, Inbox.amount(item)).joinToString(" · "), style = MaterialTheme.typography.titleMedium, color = Look.Ink)
                Eyebrow("What")
                RowCard(R.drawable.ic_forward, "Only this one", "You can still decide it yourself.", selected = !all, onClick = { everything = false })
                RowCard(
                    R.drawable.ic_forward, "All my approvals until a date",
                    whyNotAll ?: "While you are on leave. Every kind of approval.",
                    selected = all, onClick = if (whyNotAll == null) ({ everything = true }) else null,
                )
            } else if (whyNotAll != null) {
                Notice(StatusKind.INFO, whyNotAll)
                OutlineButton("Not now", onBack)
                return@Column
            }

            val end = until
            if (all && leave != null && end != null) {
                Eyebrow("Until when")
                Text(
                    "Your approved leave: ${Format.dateTime(leave.from, now)} to ${Format.dateTime(leave.until, now)}. The delegation can end earlier, not later.",
                    style = MaterialTheme.typography.bodyMedium, color = Look.Muted,
                )
                Stepper("Ends", Format.dateTime(end, now), "1 day earlier", "1 day later", { until = Delegations.until(end.minusDays(1), leave, now) }, { until = Delegations.until(end.plusDays(1), leave, now) })
            }

            Eyebrow("To whom")
            val people = if (all) Delegations.forAll(facts.receivers) else if (item != null) Delegations.forOne(facts.receivers, item) else emptyList()
            if (people.isEmpty()) Notice(StatusKind.NONE, "Nobody can receive this now.")
            for (person in people) {
                val chosen = person == to
                RowCard(R.drawable.ic_forward, person.name, person.relation.words + if (chosen) ". Chosen." else "", selected = chosen, onClick = { to = person })
            }

            if (!all) {
                Eyebrow("Why (optional)")
                QuickReasons(Delegations.REASONS, quick) { quick = it }
                ReasonField(typed, { typed = it.take(Inbox.MAX_REASON) }, "In your own words (optional)")
            }
            if (trouble != null) Notice(StatusKind.WARN, trouble)
            // A choice counts only while that person is still offered.
            val person = to?.takeIf { it in people }
            when {
                person == null -> Text("Choose a person first.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                all && leave != null && end != null -> MainButton("Delegate with your fingerprint", { onDelegate(DelegateChoice.All(person, Delegations.start(leave, now), end)) })
                else -> MainButton("Delegate with your fingerprint", { onDelegate(DelegateChoice.One(person, Inbox.reason(quick, typed))) })
            }
            OutlineButton("Do not delegate", onBack)
        }
    }
}

/** What the server said, in one sentence, for something that is not a decision. */
fun delegationSentence(result: DecisionResult): String = when (result) {
    is DecisionResult.Done -> result.sentence
    is DecisionResult.Failed -> result.sentence
    DecisionResult.NoConnection -> "No connection. Nothing was delegated. Try again when you have signal."
    DecisionResult.NotAllowed -> "You are not allowed to delegate this. Nothing was delegated."
    else -> "Nothing was delegated."
}

/**
 * Delegation (under More): what is set, ending it, and setting it before going on leave without waiting for an
 * approval to arrive; and whose approvals are delegated to me.
 */
@Composable
fun DelegationScreen(
    facts: DelegationFacts,
    now: LocalDateTime,
    sign: (what: String, done: (signed: Boolean, trouble: String?) -> Unit) -> Unit,
    onDelegateAll: (to: Receiver, until: LocalDateTime) -> DecisionResult,
    onEnd: () -> Unit,
) {
    var choosing by remember { mutableStateOf(false) }
    var trouble by remember { mutableStateOf<String?>(null) }
    var said by remember { mutableStateOf<Pair<StatusKind, String>?>(null) }
    if (choosing) {
        DelegateChooser(null, facts, now, trouble, onBack = { choosing = false; trouble = null }) { choice ->
            if (choice is DelegateChoice.All) {
                trouble = null
                sign(Delegations.questionAll(choice.to, choice.from, choice.until, now)) { signed, why ->
                    if (signed) {
                        val result = onDelegateAll(choice.to, choice.until)
                        // What is set is shown below, so a success needs one word only.
                        said = if (result is DecisionResult.Done) StatusKind.OK to "Delegated." else StatusKind.BAD to delegationSentence(result)
                        choosing = false
                    } else {
                        trouble = why
                    }
                }
            }
        }
        return
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Delegation", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            said?.let { (kind, text) -> Notice(kind, text) }
            val running = facts.running
            if (running != null) {
                Notice(StatusKind.WAIT, Delegations.runningLine(running, now))
                OutlineButton("End it now", { said = null; onEnd() }, danger = true)
            } else {
                Text("Nothing is delegated. Your approvals come to you.", style = MaterialTheme.typography.bodyLarge, color = Look.Ink)
                Text(
                    "While you are on approved leave, all your approvals can go to your deputy or a peer, for the leave days or fewer. One single approval can be delegated at any time, from the approval itself.",
                    style = MaterialTheme.typography.bodyLarge, color = Look.Muted,
                )
                MainButton("Delegate my approvals", { said = null; choosing = true })
            }
            Eyebrow("Delegated to me")
            if (facts.toMe.isEmpty()) Text("Nobody's approvals are delegated to you.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
            for (line in facts.toMe) Panel { Text(line, style = MaterialTheme.typography.bodyLarge) }
        }
    }
}
