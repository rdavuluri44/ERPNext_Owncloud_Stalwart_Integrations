package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp

/** Every tap on the Alerts screen. All are required. */
class AlertActions(
    /** Does the one thing that unblocks alerts: asks the phone's permission, or opens the right phone setting. */
    val fix: (Fix) -> Unit,
    /** Opens the phone's own switch for one kind of alert. */
    val openKind: (AlertKind) -> Unit,
    /** Makes a signal on the phone itself after a short wait, so the phone can be locked first. */
    val signal: (data: Map<String, String>) -> Unit,
    val removeAll: () -> Unit,
    /** "Remind me in 2 hours", asked for inside the app. */
    val remind: () -> Unit,
    /** The person is looking at a place ("chat", "notice", "mail"): its alert has done its work and goes. */
    val seen: (what: String) -> Unit,
)

/** How long a test waits before it shows, so the person can lock the phone or close the app first. */
const val TEST_WAIT_SECONDS = 10

/**
 * Alerts (under More): whether alerts can reach this phone and why not, the kinds with the phone's own switch for
 * each, and a test every person can run on their own phone. Test builds add one button per kind of signal and the
 * phone's delivery address.
 */
@Composable
fun AlertsScreen(view: AlertsView, testBuild: Boolean, actions: AlertActions) {
    val clipboard = LocalClipboardManager.current
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Alerts", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            val fix = view.fix
            if (view.blocked != null && fix != null) ActionMessage(StatusKind.BAD, "Alerts are blocked: ${view.blocked}", fix.label, { actions.fix(fix) })
            else Notice(StatusKind.OK, "Alerts can show on this phone.")
            if (view.blocked == null && !view.fullPage) {
                ActionMessage(StatusKind.WARN, "The full page over a locked screen is not allowed on this phone yet. Approvals still ring, as a banner.", Fix.FULL_PAGE.label, { actions.fix(Fix.FULL_PAGE) })
            }
            // While the phone is in use the phone itself shows only a banner; the full page there is the person's choice.
            if (view.blocked == null) when (view.onTop) {
                false -> ActionMessage(StatusKind.NONE, "While you use the phone, an approval comes as a banner at the top. To get the full page then too, allow this app to show over other apps: find this app in the list that opens and switch it on.", Fix.ON_TOP.label, { actions.fix(Fix.ON_TOP) })
                null -> Notice(StatusKind.NONE, "While you use this phone, an approval comes as a banner at the top. This phone cannot show the full page then.")
                true -> Notice(StatusKind.OK, "Allowed: the full page can also show while you use the phone. Not during a call.")
            }
            if (!view.connected) Notice(StatusKind.NONE, "This build is not connected to the alert service, so nothing arrives by itself. The test below still works.")
            Text(
                "Approvals ring at any time, unless your phone is on silent or on Do not disturb. Reminders come every 4 hours between 07:00 and 21:00. An alert never shows a name or an amount; you see those after your fingerprint.",
                style = MaterialTheme.typography.bodyLarge, color = Look.Muted,
            )
            MainButton("Test my alerts", { actions.signal(mapOf("kind" to "test")) })
            Text("It rings in about $TEST_WAIT_SECONDS seconds; the phone may take up to a minute. Lock the phone now, or close the app, to see the full page a real approval shows. \"Remind me in 2 hours\" on a real approval brings it back every 2 hours, at any hour, until nothing waits.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)

            Eyebrow("The kinds")
            for (kind in AlertKind.entries) RowCard(R.drawable.ic_bell, kind.title, kind.text + " Tap for the phone's own switch.", onClick = { actions.openKind(kind) })

            if (testBuild) {
                Eyebrow("Test signals (test builds)")
                Text("Each arrives after about $TEST_WAIT_SECONDS seconds (the phone may take up to a minute), also when the app is closed.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                Text("While the app is open and unlocked, an approval shows a line at the top instead of the full page, and chat and mail make no banner. Leave the app or lock the phone to see the alert itself.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                Text("In test builds \"Remind me in 2 hours\" comes back after 2 minutes. The two approvals below name things of the made-up Inbox, so Approve and Reject on the alert open them.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                fun approval(doctype: String, name: String) = mapOf("kind" to "approval", "needs" to "decide", "doctype" to doctype, "docname" to name)
                OutlineButton("Signal: an approval", { actions.signal(approval("Payment Entry", "payment")) })
                OutlineButton("Signal: a second approval", { actions.signal(approval("Leave Application", "leave")) })
                OutlineButton("Signal: reminder, 3 waiting, 8 hours", { actions.signal(mapOf("kind" to "reminder", "count" to "3", "oldest_hours" to "8")) })
                OutlineButton("Signal: the second approval was decided", { actions.signal(mapOf("kind" to "remove", "doctype" to "Leave Application", "docname" to "leave")) })
                OutlineButton("Signal: the first approval was decided", { actions.signal(mapOf("kind" to "remove", "doctype" to "Payment Entry", "docname" to "payment")) })
                OutlineButton("Signal: rejected, to correct", { actions.signal(mapOf("kind" to "returned", "doctype" to "Test", "docname" to "back")) })
                OutlineButton("Signal: a chat message to me", { actions.signal(mapOf("kind" to "message", "room" to "direct-Project manager")) })
                OutlineButton("Signal: a message in a team room", { actions.signal(mapOf("kind" to "message", "room" to "site-a-engineers", "prio" to "normal")) })
                OutlineButton("Signal: the chats were read elsewhere", { actions.signal(mapOf("kind" to "read", "what" to "chat")) })
                OutlineButton("Signal: mail", { actions.signal(mapOf("kind" to "mail", "mail" to "t4")) })
                OutlineButton("Signal: the mail was read elsewhere", { actions.signal(mapOf("kind" to "read", "what" to "mail")) })
                OutlineButton("Signal: with a name and an amount in it", { actions.signal(mapOf("kind" to "approval", "doctype" to "Test", "docname" to "three", "title" to "Pay A. Example 1,50,000.00", "body" to "Pay A. Example 1,50,000.00")) })
                OutlineButton("Remove every alert now", actions.removeAll, danger = true)

                Eyebrow("Delivery address (test builds)")
                val address = view.address
                if (address == null) {
                    Text(if (view.connected) "Google has not given this phone an address yet. Come back to this screen in a moment." else "None: this build is not connected to the alert service.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                } else {
                    Text("With this address the owner can send this one phone a test signal. It lets nobody read anything or sign in. Send it privately.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                    Panel { Text(address, style = MaterialTheme.typography.bodyMedium) }
                    OutlineButton("Copy the delivery address", { clipboard.setText(AnnotatedString(address)) })
                }
            }
        }
    }
}
