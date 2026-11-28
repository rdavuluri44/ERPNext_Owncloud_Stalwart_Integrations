package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.dp
import com.example.erp.core.Decided
import com.example.erp.core.Decision
import com.example.erp.core.DecisionResult
import com.example.erp.core.DelegationFacts
import com.example.erp.core.Delegations
import com.example.erp.core.Format
import com.example.erp.core.Inbox
import com.example.erp.core.Item
import com.example.erp.core.Receiver
import com.example.erp.core.Reviews
import com.example.erp.core.Sent
import com.example.erp.core.SentState
import com.example.erp.core.Tone
import java.time.LocalDateTime

/** Every tap in Inbox that changes something outside the screen. All are required. */
class InboxActions(
    /**
     * Asks for the fingerprint, showing [what] is being signed. [done] gets true only after a real match; otherwise
     * false, with a sentence when there is something to tell the person. A decision is never sent without it.
     */
    val sign: (what: String, done: (signed: Boolean, trouble: String?) -> Unit) -> Unit,
    /** [modified] is the version the person looked at; the server refuses a decision made on an older one. */
    val decide: (id: String, modified: String, decision: Decision, reason: String?) -> DecisionResult,
    /** An attendance sheet reviewed worker by worker: these are approved, those rejected, each with its reason. */
    val review: (id: String, modified: String, approve: List<String>, reject: Map<String, String>) -> DecisionResult,
    /** "Remind me in 2 hours": nothing is decided and nothing is sent; this phone rings again. */
    val remind: () -> Unit,
    /** One thing goes to [to]. Nothing counts as delegated until the server said so. */
    val delegate: (id: String, modified: String, to: Receiver, reason: String?) -> DecisionResult,
    /** Everything goes to [to] until [until]. The server checks the leave and who may receive. */
    val delegateAll: (to: Receiver, until: LocalDateTime) -> DecisionResult,
)

/** An alert's shortcut into Inbox: the thing to open and the screen to start on. It decides nothing. */
data class InboxJump(val id: String, val start: Start = Start.ITEM) {
    enum class Start { ITEM, REJECT, DELEGATE }
}

private enum class InboxView(val word: String, val title: String) { WAITING("Waiting", "Waiting for me"), DECIDED("Done", "Decided by me"), SENT("Sent", "Sent by me") }

private enum class Screen { LIST, ITEM, REJECT, DELEGATE, RESULT, PAST }

private fun kind(tone: Tone) = when (tone) {
    Tone.GOOD -> StatusKind.OK
    Tone.CARE -> StatusKind.WARN
    Tone.WRONG -> StatusKind.BAD
    Tone.PLAIN -> StatusKind.NONE
    Tone.WAITING -> StatusKind.WAIT
}

/**
 * Inbox: what waits for the person's decision, what they decided, and where what they sent is now.
 *
 * Built in: two decisions only, Approve and Reject, each signed with the fingerprint, and the fingerprint question
 * says what is signed; Approve is offered only after the person said they have seen the evidence; a rejection
 * has an optional reason and the sender is told of it; without a connection nothing can be decided; nothing is
 * shown as decided before the answer came. A person who does not decide now delegates or is reminded in 2 hours.
 * "Delegate" hands one thing, or everything during approved leave, to someone the server offers; it is signed too.
 */
@Composable
fun InboxScreen(
    waiting: List<Item>, decided: List<Decided>, sent: List<Sent>, now: LocalDateTime, online: Boolean, actions: InboxActions,
    jump: InboxJump? = null, onJumped: () -> Unit = {}, delegation: DelegationFacts = DelegationFacts(),
) {
    var view by rememberSaveable { mutableStateOf(InboxView.WAITING) }
    var step by rememberSaveable { mutableStateOf(Screen.LIST) }
    var openId by rememberSaveable { mutableStateOf<String?>(null) }
    var trouble by remember(openId) { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<DecisionResult?>(null) }
    var decidedTitle by remember { mutableStateOf("") }

    val item = waiting.firstOrNull { it.id == openId }
    // "I have looked" belongs to one version of one item: a changed item must be looked at again.
    // For a sheet of workers that includes every worker's version: a corrected worker must be looked at again.
    var seen by rememberSaveable(openId, item?.modified, item?.entries?.joinToString("|") { it.modified }) { mutableStateOf(false) }
    val past = decided.firstOrNull { it.item.id == openId }
    var note by remember { mutableStateOf<String?>(null) }
    val toList = { step = Screen.LIST; openId = null; result = null }
    val open = { id: String -> openId = id; step = Screen.ITEM; note = null }

    // An alert's shortcut: that thing opens, at Reject or Delegate when asked (those screens themselves check that
    // it may be decided or delegated and that there is a connection). A thing that is not in the list leaves the list as it is.
    LaunchedEffect(jump) {
        if (jump != null) {
            if (waiting.any { it.id == jump.id }) {
                view = InboxView.WAITING
                result = null
                openId = jump.id
                step = when (jump.start) {
                    InboxJump.Start.REJECT -> Screen.REJECT
                    InboxJump.Start.DELEGATE -> Screen.DELEGATE
                    InboxJump.Start.ITEM -> Screen.ITEM
                }
            } else {
                note = "That one is already decided, or no longer waits for you."
            }
            onJumped()
        }
    }

    fun decide(target: Item, decision: Decision, reason: String?) {
        trouble = null
        actions.sign(Inbox.question(decision, target)) { signed, why ->
            if (signed) {
                decidedTitle = target.title
                result = actions.decide(target.id, target.modified, decision, reason)
                step = Screen.RESULT
            } else {
                trouble = why
            }
        }
    }

    // A sheet reviewed worker by worker is one signed step: the question says how many of each.
    fun review(target: Item, approve: List<String>, reject: Map<String, String>) {
        trouble = null
        actions.sign(Reviews.question(target, approve.size, reject.size)) { signed, why ->
            if (signed) {
                decidedTitle = target.title
                result = actions.review(target.id, target.modified, approve, reject)
                step = Screen.RESULT
            } else {
                trouble = why
            }
        }
    }

    // Delegating is signed like a decision: the fingerprint question says who receives what.
    fun delegate(target: Item?, choice: DelegateChoice) {
        trouble = null
        val what = when (choice) {
            is DelegateChoice.One -> Delegations.question(choice.to, target ?: return)
            is DelegateChoice.All -> Delegations.questionAll(choice.to, choice.from, choice.until, now)
        }
        actions.sign(what) { signed, why ->
            if (signed) {
                when (choice) {
                    is DelegateChoice.One -> {
                        decidedTitle = target?.title.orEmpty()
                        result = actions.delegate(target?.id.orEmpty(), target?.modified.orEmpty(), choice.to, choice.reason)
                    }
                    is DelegateChoice.All -> {
                        decidedTitle = "All my approvals"
                        result = actions.delegateAll(choice.to, choice.until)
                    }
                }
                step = Screen.RESULT
            } else {
                trouble = why
            }
        }
    }

    when {
        step == Screen.RESULT && result != null -> {
            BackHandler(onBack = toList)
            Result(decidedTitle, result!!, now, next = Inbox.sections(waiting, now).flatMap { it.items }.firstOrNull { Inbox.canDecide(it) && it.id != openId }, waitingCount = waiting.count { Inbox.canDecide(it) && it.id != openId },
                onLookAgain = { seen = false; result = null; step = Screen.ITEM }, onNext = { result = null; open(it) }, onList = toList)
        }
        // Without a connection these two fall back to the item, which says that nothing can be decided now.
        // A sheet of workers has no reject of the whole: its workers are rejected inside it, each with a reason.
        step == Screen.REJECT && item != null && online && Inbox.canDecide(item) && !Reviews.applies(item) -> {
            BackHandler { step = Screen.ITEM }
            Reject(item, trouble, onBack = { step = Screen.ITEM }) { reason -> decide(item, Decision.REJECTED, reason) }
        }
        step == Screen.DELEGATE && item != null && online && Delegations.canDelegate(item) -> {
            BackHandler { step = Screen.ITEM }
            DelegateChooser(item, delegation, now, trouble, onBack = { trouble = null; step = Screen.ITEM }) { choice -> delegate(item, choice) }
        }
        (step == Screen.ITEM || step == Screen.REJECT || step == Screen.DELEGATE) && item != null -> {
            BackHandler(onBack = toList)
            ItemView(
                item, now, online, seen, trouble, onSeen = { seen = it }, onBack = toList, onApprove = { decide(item, Decision.APPROVED, null) },
                onReject = { trouble = null; step = Screen.REJECT },
                onReview = { approve, reject -> review(item, approve, reject) },
                onRemind = { actions.remind(); toList(); note = "You will be reminded in 2 hours, and again every 2 hours while it waits." },
                onDelegate = if (Delegations.canDelegate(item)) ({ trouble = null; step = Screen.DELEGATE }) else null,
            )
        }
        step == Screen.PAST && past != null -> {
            BackHandler(onBack = toList)
            PastView(past, now, onBack = toList)
        }
        else -> Page {
            Text("Inbox", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            ViewSwitch(view) { view = it }
            Text(view.title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
            if (!online) Notice(StatusKind.NONE, "No connection. This is the last copy. Deciding needs a connection.")
            note?.let { Notice(StatusKind.INFO, it) }
            delegation.running?.let { Notice(StatusKind.WAIT, Delegations.runningLine(it, now) + " End it under More, Delegation.") }
            when (view) {
                InboxView.WAITING -> {
                    val sections = Inbox.sections(waiting, now)
                    if (sections.isEmpty()) Notice(StatusKind.OK, "Nothing is waiting for you.")
                    for (section in sections) {
                        Eyebrow(section.heading)
                        for (row in section.items) WaitingRow(row, now) { open(row.id) }
                    }
                }
                InboxView.DECIDED -> {
                    if (decided.isEmpty()) Text("You have not decided anything yet.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                    for (row in decided) {
                        val since = row.since?.let { " $it" }.orEmpty()
                        RowCard(
                            R.drawable.ic_inbox, row.item.title, "${row.decision.done} by you, ${Format.dateTime(row.at, now)}.$since",
                            pill = (if (row.decision == Decision.APPROVED) StatusKind.OK else StatusKind.WARN) to row.decision.done,
                            onClick = { openId = row.item.id; step = Screen.PAST },
                        )
                    }
                }
                InboxView.SENT -> {
                    if (sent.isEmpty()) Text("You have not sent anything for a decision.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                    // What was rejected is mine to correct, so it comes first.
                    for (row in sent.sortedBy { it.state != SentState.REJECTED }) {
                        val (pillKind, word) = when (row.state) {
                            SentState.WAITING -> StatusKind.WAIT to "Waiting"
                            SentState.APPROVED -> StatusKind.OK to "Approved"
                            SentState.REJECTED -> StatusKind.BAD to "Rejected"
                        }
                        RowCard(R.drawable.ic_forward, row.title, Inbox.sentLine(row, now), pill = pillKind to word)
                    }
                }
            }
        }
    }
}

/** Every Inbox screen is one scrolling page in one readable column, so nothing is squeezed at any size. */
@Composable
private fun Page(content: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
    }
}

/** The three views. Side by side when there is room; one under the other with large text. */
@Composable
private fun ViewSwitch(current: InboxView, onChoose: (InboxView) -> Unit) {
    @Composable
    fun button(view: InboxView, modifier: Modifier) {
        if (view == current) MainButton(view.word, { onChoose(view) }, modifier) else OutlineButton(view.word, { onChoose(view) }, modifier)
    }
    if (LocalDensity.current.fontScale > 1.3f) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { for (view in InboxView.entries) button(view, Modifier) }
    } else {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) { for (view in InboxView.entries) button(view, Modifier.weight(1f)) }
    }
}

@Composable
private fun WaitingRow(item: Item, now: LocalDateTime, onOpen: () -> Unit) {
    val deadline = Inbox.deadline(item, now)
    val extra = listOfNotNull(
        "You sent this.".takeIf { item.sentByMe },
        item.delegatedBy?.let { "Delegated to you by $it." }, item.delegatedTo?.let { "With $it." },
    ).joinToString(" ")
    RowCard(
        R.drawable.ic_inbox,
        item.title,
        Inbox.rowLine(item, now) + (if (extra.isEmpty()) "" else "\n$extra"),
        pill = when {
            item.rejection != null -> StatusKind.BAD to "Rejected"
            deadline != null && deadline.first != Tone.PLAIN -> kind(deadline.first) to deadline.second
            else -> null
        },
        onClick = onOpen,
    )
}

@Composable
private fun Trail(item: Item, now: LocalDateTime) {
    if (item.trail.isEmpty()) return
    Eyebrow("What happened so far")
    Panel {
        for (step in item.trail) {
            Text("${step.what} by ${step.who}, ${Format.dateTime(step.at, now)}", style = MaterialTheme.typography.bodyLarge)
            if (step.reason != null) Text(step.reason!!, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
        Text("Waiting for you since ${Format.dateTime(item.waitingSince, now)}", style = MaterialTheme.typography.bodyLarge)
    }
}

@Composable
private fun Evidence(item: Item) {
    if (item.lines.isEmpty()) return
    val unusual = item.lines.count { it.unusual != null }
    Eyebrow(if (unusual == 0) "What it is about" else "What it is about ($unusual to look at closely)")
    Panel {
        for (line in item.lines) {
            Text(line.title, style = MaterialTheme.typography.titleMedium)
            Text(line.text, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            if (line.unusual != null) Status(StatusKind.WARN, line.unusual!!)
        }
    }
}

@Composable
private fun ItemHead(item: Item, now: LocalDateTime, onBack: () -> Unit) {
    TopBar(onBack = onBack)
    Text(item.title, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
    Inbox.amount(item)?.let { Text(it, style = MaterialTheme.typography.headlineMedium, color = Look.Ink) }
    Text("From ${item.from}", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
    Inbox.deadline(item, now)?.let { (tone, words) -> Status(kind(tone), words) }
}

@Composable
private fun ItemView(
    item: Item,
    now: LocalDateTime,
    online: Boolean,
    seen: Boolean,
    trouble: String?,
    onSeen: (Boolean) -> Unit,
    onBack: () -> Unit,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onReview: (approve: List<String>, reject: Map<String, String>) -> Unit,
    onRemind: () -> Unit,
    onDelegate: (() -> Unit)?,
) = Page {
    ItemHead(item, now, onBack)
    Delegations.itemLine(item)?.let { Notice(StatusKind.INFO, it) }
    Trail(item, now)
    Evidence(item)
    val rejection = item.rejection
    when {
        rejection != null -> {
            Notice(StatusKind.BAD, Inbox.rejectionLine(rejection, now))
            Text("Correct it where you made it. Where its kind allows, it can be presented again.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        }
        item.sentByMe -> Notice(StatusKind.INFO, "You sent this. Someone else must decide it.")
        Inbox.amountUnreadable(item) -> Notice(StatusKind.BAD, "The amount is missing or cannot be read on this phone, so nothing can be decided here. Open it on the web.")
        Inbox.workersMissing(item) -> Notice(StatusKind.BAD, "The workers of this sheet are not here, so nothing can be decided. Open it on the web.")
        !online -> Notice(StatusKind.NONE, "Needs a connection. Nothing can be decided now.")
        // An attendance sheet is reviewed worker by worker.
        Reviews.applies(item) -> ReviewPart(item, seen, trouble, onSeen, onReview, onDelegate = onDelegate, onRemind = onRemind)
        else -> {
            if (trouble != null) Notice(StatusKind.WARN, trouble)
            // Approve is offered only after the person says they have seen what they sign.
            SwitchRow("I have looked at everything above", "Needed before you can approve.", seen, onSeen)
            if (seen) MainButton("Approve with your fingerprint", onApprove)
            OutlineButton("Reject", onReject, danger = true)
            // Not on what was delegated to me, and not twice: one step only.
            if (onDelegate != null) OutlineButton("Delegate", onDelegate)
            OutlineButton("Remind me in 2 hours", onRemind)
        }
    }
}

@Composable
internal fun ReasonField(value: String, onChange: (String) -> Unit, label: String) {
    OutlinedTextField(value, onChange, Modifier.fillMaxWidth(), label = { Text(label) }, textStyle = MaterialTheme.typography.bodyLarge, minLines = 2, maxLines = 5, shape = RoundedCornerShape(Look.Corner))
}

/** One of the quick reasons, or none. A second tap on the chosen one takes it away again. */
@Composable
internal fun QuickReasons(choices: List<String>, chosen: String?, onChoose: (String?) -> Unit) {
    for (choice in choices) RowCard(R.drawable.ic_forward, choice, if (choice == chosen) "Chosen. Tap again to take it away." else "", selected = choice == chosen, onClick = { onChoose(if (choice == chosen) null else choice) })
}

@Composable
private fun Reject(item: Item, trouble: String?, onBack: () -> Unit, onReject: (reason: String?) -> Unit) {
    // In memory only, like everything a person types.
    var quick by remember(item.id) { mutableStateOf<String?>(null) }
    var typed by remember(item.id) { mutableStateOf("") }
    Page {
        TopBar(onBack = onBack)
        Text("Reject", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Text(item.title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
        Notice(StatusKind.INFO, "${item.from} is told. A reason is not required, but it tells them why.")
        QuickReasons(Reviews.reasons(item.kind), quick) { quick = it }
        ReasonField(typed, { typed = it.take(Inbox.MAX_REASON) }, "In your own words (optional)")
        if (trouble != null) Notice(StatusKind.WARN, trouble)
        MainButton("Reject with your fingerprint", { onReject(Inbox.reason(quick, typed)) })
        OutlineButton("Do not reject", onBack)
    }
}

/** A day and a time, chosen with large plus and minus buttons that work with gloves. No limit on how far ahead. */
@Composable
internal fun Stepper(label: String, value: String, less: String, more: String, onLess: () -> Unit, onMore: () -> Unit) {
    Text(label, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlineButton(less, onLess, Modifier.weight(1f))
        OutlineButton(more, onMore, Modifier.weight(1f))
    }
    Text(value, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
}

@Composable
private fun Result(title: String, result: DecisionResult, now: LocalDateTime, next: Item?, waitingCount: Int, onLookAgain: () -> Unit, onNext: (String) -> Unit, onList: () -> Unit) = Page {
    Text(title, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
    when (result) {
        is DecisionResult.Done -> Notice(StatusKind.OK, result.sentence)
        is DecisionResult.Taken -> Notice(StatusKind.INFO, "Already ${result.decision.done.lowercase()} by ${result.by}, ${Format.dateTime(result.at, now)}. Nothing was decided by you.")
        DecisionResult.Changed -> {
            Notice(StatusKind.WARN, "This was changed after you opened it. Nothing was decided. Look at it again.")
            MainButton("Look at it again", onLookAgain)
        }
        DecisionResult.NotAllowed -> Notice(StatusKind.BAD, "You are not allowed to decide this. Nothing was decided.")
        DecisionResult.NoConnection -> Notice(StatusKind.NONE, "No connection. Nothing was decided. Try again when you have signal.")
        is DecisionResult.Failed -> Notice(StatusKind.BAD, result.sentence)
    }
    if (result !is DecisionResult.Changed && next != null) {
        MainButton(if (waitingCount == 1) "Open the next one" else "Open the next one ($waitingCount more)", { onNext(next.id) }, forward = true)
    }
    OutlineButton("Back to the list", onList)
}

@Composable
private fun PastView(past: Decided, now: LocalDateTime, onBack: () -> Unit) = Page {
    ItemHead(past.item, now, onBack)
    Notice(if (past.decision == Decision.APPROVED) StatusKind.OK else StatusKind.WARN, "${past.decision.done} by you, ${Format.dateTime(past.at, now)}." + past.reason?.let { " Reason: $it" }.orEmpty())
    past.since?.let { Text(it, style = MaterialTheme.typography.bodyLarge, color = Look.Ink) }
    Evidence(past.item)
    Text("A decision cannot be undone here. If it was a mistake, the document is cancelled or amended on the web by the people allowed to.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
}
