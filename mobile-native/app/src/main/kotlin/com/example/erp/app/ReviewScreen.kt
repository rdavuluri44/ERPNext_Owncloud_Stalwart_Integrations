package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.Entry
import com.example.erp.core.Inbox
import com.example.erp.core.Item
import com.example.erp.core.Reviews

/**
 * An attendance approval, worker by worker: every worker is a card; all are approved unless marked "Reject", and a
 * rejected worker needs a reason. One button counts both sides and one fingerprint signs them. Rejecting all at
 * once is the same step with one reason for all, and it too covers only the entries that are the person's to
 * review. Put inside the item's own scrolling page.
 *
 * @param onReview the entries to approve, and the entries to reject each with its reason.
 */
@Composable
fun ReviewPart(
    item: Item,
    seen: Boolean,
    trouble: String?,
    onSeen: (Boolean) -> Unit,
    onReview: (approve: List<String>, reject: Map<String, String>) -> Unit,
    onDelegate: (() -> Unit)?,
    onRemind: () -> Unit,
) {
    val entries = Reviews.entries(item)
    // In memory only, and only for the version of the sheet and of its workers that is on the screen.
    val version = listOf(item.id, item.modified) + entries.map { it.modified }
    var marked by remember(version) { mutableStateOf(mapOf<String, String?>()) }
    var notes by remember(version) { mutableStateOf(mapOf<String, String>()) }
    var allOut by remember(version) { mutableStateOf(false) }
    var allReason by remember(version) { mutableStateOf<String?>(null) }
    var allNote by remember(version) { mutableStateOf("") }
    var photo by remember(item.id) { mutableStateOf<String?>(null) }
    val unusual = entries.count { it.unusual != null }
    var narrowed by remember(item.id) { mutableStateOf(false) }
    // Nothing unusual left (the sheet changed): the narrowed list would be empty and without a way back.
    val closely = narrowed && unusual > 0
    val mine = Reviews.mine(item).map { it.id }
    val reasons = Reviews.reasons(item.kind)
    Eyebrow("The workers")
    if (unusual > 0) {
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val all = "All (${entries.size})"
            val some = "To look at closely ($unusual)"
            if (closely) OutlineButton(all, { narrowed = false }, Modifier.weight(1f)) else MainButton(all, { narrowed = false }, Modifier.weight(1f))
            // Narrowing the list takes back "I have looked": what is hidden has not been looked at.
            if (closely) MainButton(some, { narrowed = true }, Modifier.weight(1f)) else OutlineButton(some, { narrowed = true; onSeen(false) }, Modifier.weight(1f))
        }
    }
    for (entry in entries.filter { !closely || it.unusual != null }) {
        WorkerCard(
            entry, reasons, canMark = !allOut,
            rejected = entry.id in marked, reason = marked[entry.id], note = notes[entry.id].orEmpty(), photoOpen = photo == entry.id,
            onReject = { reject -> marked = if (reject) marked + (entry.id to null) else marked - entry.id },
            onReason = { marked = marked + (entry.id to it) },
            onNote = { notes = notes + (entry.id to it.take(Inbox.MAX_REASON)) },
            onPhoto = { photo = if (photo == entry.id) null else entry.id },
        )
    }

    if (trouble != null) Notice(StatusKind.WARN, trouble)
    val (approve, reject) = Reviews.counts(item, marked.keys)
    when {
        mine.isEmpty() -> Notice(StatusKind.INFO, "None of these is yours to review.")
        // Nothing is signed from a narrowed list: the button would cover workers that are not on the screen.
        closely -> Notice(StatusKind.INFO, "Showing $unusual of ${entries.size}. Go back to All to approve or reject.")
        allOut -> {
            Panel {
                Text("Reject all ${mine.size}", style = MaterialTheme.typography.titleMedium, color = Look.Ink)
                Text("One reason for all of them (needed). They go back to be corrected.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                QuickReasons(reasons, allReason) { allReason = it }
                ReasonField(allNote, { allNote = it.take(Inbox.MAX_REASON) }, "More in your own words (optional)")
            }
            val reason = allReason
            if (reason == null) Text("Choose why.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
            else MainButton(Reviews.words(item, 0, mine.size) + " with your fingerprint", { onReview(emptyList(), mine.associateWith { Inbox.reason(reason, allNote).orEmpty() }) })
            OutlineButton("Do not reject all", { allOut = false; allReason = null; allNote = "" })
        }
        else -> {
            // Approving is offered only after the person says they have seen what they sign.
            if (approve > 0) SwitchRow("I have looked at everything above", "Needed before you can approve.", seen, onSeen)
            when {
                !Reviews.ready(item, marked) -> Text("Choose why for each worker you reject.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                approve > 0 && !seen -> Unit
                else -> MainButton(Reviews.words(item, approve, reject) + " with your fingerprint", {
                    onReview(
                        mine.filter { it !in marked },
                        // The reason sent is the chosen one, with the person's own words after it when they wrote some.
                        mine.filter { it in marked }.associateWith { Inbox.reason(marked[it], notes[it].orEmpty()).orEmpty() },
                    )
                })
            }
            OutlineButton("Reject all ${mine.size} with one reason", { allOut = true; marked = emptyMap() }, danger = true)
        }
    }
    if (onDelegate != null) OutlineButton("Delegate", onDelegate)
    OutlineButton("Remind me in 2 hours", onRemind)
}

@Composable
private fun WorkerCard(
    entry: Entry,
    reasons: List<String>,
    canMark: Boolean,
    rejected: Boolean,
    reason: String?,
    note: String,
    photoOpen: Boolean,
    onReject: (Boolean) -> Unit,
    onReason: (String?) -> Unit,
    onNote: (String) -> Unit,
    onPhoto: () -> Unit,
) = Panel {
    Text(entry.name, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
    Text(entry.text, style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
    if (entry.unusual != null) Status(StatusKind.WARN, entry.unusual!!)
    OutlineButton(if (photoOpen) "Hide the photo of ${entry.name}" else "Show the photo of ${entry.name}", onPhoto)
    // ponytail: the made-up data has no photos; the real one is loaded from the server and shown here, large.
    if (photoOpen) Notice(StatusKind.NONE, "No photo in the made-up data. The real photo shows here, large.")
    val notMine = entry.notMine
    when {
        notMine != null -> Notice(StatusKind.INFO, notMine)
        !canMark -> Unit
        else -> {
            SwitchRow("Reject ${entry.name}", if (rejected) "Goes back to be corrected." else "Will be approved.", rejected, onReject)
            if (rejected) {
                Text("Why (needed)", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                QuickReasons(reasons, reason, onReason)
                ReasonField(note, onNote, "More in your own words (optional)")
            }
        }
    }
}
