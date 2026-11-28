package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.erp.core.AccessRequest
import com.example.erp.core.Approval
import com.example.erp.core.Format
import com.example.erp.core.Welcome
import com.example.erp.core.hideMiddle
import java.time.LocalDateTime

/** Every tap on a Welcome screen. All are required, so no button can be drawn without somewhere to lead. */
class WelcomeActions(
    val requestAccess: () -> Unit,
    val checkAgain: () -> Unit,
    val cancelRequest: () -> Unit,
    val requestAgain: () -> Unit,
    val makeKey: () -> Unit,
    val unlock: () -> Unit,
)

/** What the Welcome screens show besides the situation itself. */
data class WelcomeFacts(
    /** The mail address the request or key belongs to. */
    val account: String,
    val mobile: String,
    val now: LocalDateTime,
    /** False when the server could not be asked just now; [checkedAt] then says how old the status is. */
    val reachable: Boolean = true,
    val checkedAt: LocalDateTime? = null,
    /** Unlock: tries left after a miss, or null before any miss. */
    val triesLeft: Int? = null,
    /** Unlock: hours the app still opens without a connection, or null when online. */
    val offlineHours: Int? = null,
    /** Make your key: why this phone cannot protect a key fully, or null when it can. */
    val keyProblem: String? = null,
    /** Make your key and Unlock: why the last touch did not work, when the key is kept and it can be tried again. */
    val trouble: String? = null,
)

/**
 * The first screen of the app. Which one is shown is decided by [com.example.erp.core.welcomeFor], never by the
 * person. "How it works" opens from the help mark of every situation and leads back.
 */
@Composable
fun WelcomeScreen(welcome: Welcome, facts: WelcomeFacts, actions: WelcomeActions) {
    var help by rememberSaveable { mutableStateOf(false) }
    if (help) {
        BackHandler { help = false }
        HowItWorks(onBack = { help = false })
        return
    }
    val openHelp = { help = true }
    when (welcome) {
        Welcome.RequestAccess -> RequestAccess(actions, openHelp)
        is Welcome.Pending -> Pending(welcome.request, facts, actions, openHelp)
        is Welcome.Refused -> Refused(welcome.request, facts, actions, openHelp)
        is Welcome.Expired -> Expired(welcome.request, facts, actions, openHelp)
        Welcome.MakeKey -> MakeKey(facts, actions, openHelp)
        Welcome.Unlock -> Unlock(facts, actions, openHelp)
        is Welcome.KeyGone -> KeyGone(welcome, actions, openHelp)
    }
}

/**
 * The frame of every Welcome screen: the buttons sit at the bottom when there is room, and the whole page scrolls
 * when there is not (a small phone with large text), so a button is never squeezed or cut off. On a tablet it is
 * one centred column so lines stay readable.
 */
@Composable
private fun Page(content: @Composable ColumnScope.() -> Unit, buttons: @Composable ColumnScope.() -> Unit) {
    BoxWithConstraints(Modifier.fillMaxSize().padding(horizontal = 20.dp, vertical = 12.dp), contentAlignment = Alignment.TopCenter) {
        Column(
            Modifier.widthIn(max = 480.dp).fillMaxWidth().verticalScroll(rememberScrollState()).heightIn(min = maxHeight),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(13.dp), content = content)
            Column(Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp), content = buttons)
        }
    }
}

@Composable
private fun Title(text: String, centre: Boolean = false) {
    Text(text, Modifier.fillMaxWidth(), style = MaterialTheme.typography.headlineMedium, color = Look.Ink, textAlign = if (centre) TextAlign.Center else TextAlign.Start)
}

@Composable
private fun Lead(text: String, centre: Boolean = false) {
    Text(text, Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodyLarge, color = Look.Muted, textAlign = if (centre) TextAlign.Center else TextAlign.Start)
}

@Composable
private fun Small(text: String, centre: Boolean = false) {
    Text(text, Modifier.fillMaxWidth(), style = MaterialTheme.typography.bodyMedium, color = Look.Muted, textAlign = if (centre) TextAlign.Center else TextAlign.Start)
}

@Composable
private fun RequestAccess(actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Box(Modifier.align(Alignment.CenterHorizontally).size(72.dp).background(Look.Accent, RoundedCornerShape(20.dp)), contentAlignment = Alignment.Center) {
                Icon(painterResource(R.drawable.ic_key), contentDescription = null, modifier = Modifier.size(38.dp), tint = Look.Ground)
            }
            Title("ERP Mobile", centre = true)
            Lead("Your phone becomes your key.", centre = true)
            RowCard(R.drawable.ic_fingerprint, "Opens with your fingerprint", "No password to remember or share.")
            RowCard(R.drawable.ic_offline, "Works at site without signal", "What you record is kept safe and sent later.")
            RowCard(R.drawable.ic_computer, "Opens your computer too", "Scan a code on the screen with this phone.")
            Notice(StatusKind.INFO, "To start you need: this phone, your ID, and a meeting with your project manager.")
        },
        buttons = {
            MainButton("Request access", actions.requestAccess, forward = true)
            Small("Had access on another phone? Request access here too. Your old phone's key is then removed.", centre = true)
        },
    )
}

@Composable
private fun RequestDetails(request: AccessRequest, facts: WelcomeFacts) {
    Small("${facts.account} · ${hideMiddle(facts.mobile)} · sent ${Format.dateTime(request.sentAt, facts.now)}")
}

@Composable
private fun Pending(request: AccessRequest, facts: WelcomeFacts, actions: WelcomeActions, onHelp: () -> Unit) {
    var confirmCancel by rememberSaveable { mutableStateOf(false) }
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Eyebrow("Access request")
            Title("Request sent")
            Lead("Two people must approve before your key is made.")
            val managerDone = request.projectManager == Approval.CONFIRMED
            RowCard(
                R.drawable.ic_person,
                "Project manager",
                if (managerDone) request.projectManagerAt?.let { Format.dateTime(it, facts.now) }.orEmpty() else "Meet them with this phone and your ID.",
                pill = if (managerDone) StatusKind.OK to "Confirmed" else StatusKind.WAIT to "Waiting",
            )
            RowCard(
                R.drawable.ic_shield,
                "Admin",
                when {
                    request.admin == Approval.CONFIRMED -> request.adminAt?.let { Format.dateTime(it, facts.now) }.orEmpty()
                    managerDone -> "Checks your request next."
                    else -> "Checks after the project manager."
                },
                pill = when {
                    request.admin == Approval.CONFIRMED -> StatusKind.OK to "Confirmed"
                    managerDone -> StatusKind.WAIT to "Waiting"
                    else -> StatusKind.NONE to "Not yet"
                },
            )
            if (facts.reachable) {
                Notice(StatusKind.INFO, "You get an alert on this phone when it is done. You can close the app.")
            } else {
                val last = facts.checkedAt?.let { " Last checked ${Format.dateTime(it, facts.now)}." }.orEmpty()
                Notice(StatusKind.NONE, "Cannot check right now: no connection.$last")
            }
            RequestDetails(request, facts)
        },
        buttons = {
            if (confirmCancel) {
                Notice(StatusKind.WARN, "Cancel this request? To get access you would have to send a new one and be approved again.")
                OutlineButton("Yes, cancel my request", { confirmCancel = false; actions.cancelRequest() }, danger = true)
                MainButton("Keep my request", { confirmCancel = false })
            } else {
                MainButton("Check again", actions.checkAgain)
                OutlineButton("Cancel my request", { confirmCancel = true }, danger = true)
            }
        },
    )
}

@Composable
private fun Refused(request: AccessRequest, facts: WelcomeFacts, actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Eyebrow("Access request")
            Title("Request refused")
            val who = if (request.projectManager == Approval.REFUSED) "The project manager" else "The admin"
            Notice(StatusKind.BAD, "$who refused this request. Reason given: ${request.refusedBecause?.takeIf { it.isNotBlank() } ?: "none"}")
            Lead("If the reason can be put right, send a new request.")
            RequestDetails(request, facts)
        },
        buttons = { MainButton("Request again", actions.requestAgain, forward = true) },
    )
}

@Composable
private fun Expired(request: AccessRequest, facts: WelcomeFacts, actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Eyebrow("Access request")
            Title("Request ran out")
            Notice(StatusKind.WARN, "This request was not approved in the allowed time, so it is closed.")
            Lead("Send it again, and meet your project manager with this phone and your ID.")
            RequestDetails(request, facts)
        },
        buttons = { MainButton("Request again", actions.requestAgain, forward = true) },
    )
}

@Composable
private fun MakeKey(facts: WelcomeFacts, actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(step = 5 to 5, onHelp = onHelp)
            Eyebrow("Approved")
            Title("Approved. Make your key")
            Lead("Touch the fingerprint sensor once. The key is made in this phone's secure chip and never leaves it.")
            FingerprintMark(Modifier.align(Alignment.CenterHorizontally).padding(vertical = 8.dp))
            RowCard(R.drawable.ic_lock, "Stays in this phone", "It cannot be copied, backed up or moved.")
            if (facts.keyProblem != null) Notice(StatusKind.BAD, "This phone cannot protect a key: ${facts.keyProblem} No key was made.")
            else if (facts.trouble != null) Notice(StatusKind.WARN, facts.trouble)
        },
        buttons = { if (facts.keyProblem == null) MainButton("Make my key", actions.makeKey, forward = true) },
    )
}

@Composable
private fun Unlock(facts: WelcomeFacts, actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Title("Welcome back", centre = true)
            Lead("Open the app with your fingerprint.", centre = true)
            FingerprintMark(Modifier.align(Alignment.CenterHorizontally).padding(vertical = 16.dp))
            if (facts.triesLeft != null) {
                val tries = if (facts.triesLeft == 1) "1 try left" else "${facts.triesLeft} tries left"
                Notice(StatusKind.WARN, "Not recognised. $tries. Dry your finger and the sensor. After 5 misses in a row the key is erased.")
            }
            if (facts.trouble != null) Notice(StatusKind.WARN, facts.trouble)
            if (facts.offlineHours != null) {
                Notice(StatusKind.NONE, "No connection. You can work; it is sent when you are back online. The app opens without a connection for ${facts.offlineHours} more hours.")
            }
        },
        buttons = {
            MainButton("Open with fingerprint", actions.unlock)
            if (facts.account.isNotBlank()) Small("Not you? This phone's key belongs to ${facts.account}.", centre = true)
        },
    )
}

@Composable
private fun KeyGone(gone: Welcome.KeyGone, actions: WelcomeActions, onHelp: () -> Unit) {
    Page(
        content = {
            TopBar(onHelp = onHelp)
            Eyebrow("This phone")
            Title("Your key is gone")
            Notice(StatusKind.BAD, gone.why.sentence)
            Lead("What you already sent is safe on the server. To use the app on this phone again, ask for a new key.")
        },
        buttons = { MainButton("Request a new key", actions.requestAgain, forward = true) },
    )
}

@Composable
private fun HowItWorks(onBack: () -> Unit) {
    Page(
        content = {
            TopBar(onBack = onBack)
            Title("How it works")
            Lead("Five steps, once per phone.")
            RowCard(R.drawable.ic_phone, "1. Phone check", "The app checks the fingerprint sensor and the secure chip.")
            RowCard(R.drawable.ic_fingerprint, "2. Only your fingerprints", "Nobody else's fingerprint may be saved on this phone.")
            RowCard(R.drawable.ic_person, "3. Request access", "You send your mail address and mobile number.")
            RowCard(R.drawable.ic_shield, "4. Two approvals", "Your project manager meets you with your ID, then the admin approves.")
            RowCard(R.drawable.ic_key, "5. Your key", "One touch of the sensor makes the key in this phone.")
            Notice(StatusKind.INFO, "Keeping the key: use the app at least once every 7 days. 5 misses in a row erase the key. Adding a new fingerprint to the phone destroys it.")
        },
        buttons = { MainButton("Back", onBack) },
    )
}
