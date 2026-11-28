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
import com.example.erp.core.Folder
import com.example.erp.core.Mail
import com.example.erp.core.Mails
import com.example.erp.core.Person
import java.time.LocalDateTime

/**
 * Test builds only: the mail screens against a stand-in, because the mail sign-in does not exist yet. The mails
 * and people are made up, live in memory only, and nothing is sent anywhere. "Open" on a link opens nothing here;
 * the line at the top says which address the browser would have been given. Remove with the real mail client
 * (cleanup list).
 */
@Composable
fun MailPreviewScreen(now: LocalDateTime = LocalDateTime.now(), open: String? = null, onOpened: () -> Unit = {}, onCount: (Int) -> Unit = {}) {
    val me = Person("You", "you@example.com")
    var mails by remember { mutableStateOf(sampleMails(now, me)) }
    LaunchedEffect(mails) { onCount(mails.count { it.unread }) }
    var note by remember { mutableStateOf("Stand-in: nothing is sent.") }
    var count by remember { mutableStateOf(0) }
    val actions = MailActions(
        opened = { thread -> mails = mails.map { if (it.thread == thread) it.copy(unread = false) else it } },
        send = { to, subject, body ->
            count += 1
            mails = mails + Mail("sent-$count", "sent-$count", Folder.SENT, me, to.map { Person(it, it) }, subject = subject.ifEmpty { "(no subject)" }, body = body, at = now)
            note = "Stand-in: put in Sent, not sent."
        },
        openLink = { link -> note = "Stand-in: the browser would open ${Mails.realHost(link)}." },
    )
    Column(Modifier.fillMaxSize()) {
        Notice(StatusKind.NONE, note, Modifier.padding(horizontal = Look.Gap, vertical = 8.dp))
        Box(Modifier.weight(1f)) { MailScreen(mails, me, setOf("example.com"), now, actions, open, onOpened) }
    }
}

private fun web(rest: String) = "https" + "://" + rest

/** The number the bar shows for Mail before the stand-in was opened. */
internal fun standInUnreadMails(now: LocalDateTime): Int = sampleMails(now, Person("You", "you@example.com")).count { it.unread }

private fun sampleMails(now: LocalDateTime, me: Person): List<Mail> {
    val manager = Person("Project manager", "pm@example.com")
    val engineer = Person("Engineer", "engineer@example.com")
    val hr = Person("HR", "hr@example.com")
    return listOf(
        Mail(
            "m1", "t1", Folder.RECEIVED, manager, listOf(me), listOf(engineer), "Pour checklist for Friday",
            "Please go through the attached checklist before the lorry is unloaded.\n\nSend it back signed by the site supervisor.",
            now.minusMinutes(35), unread = true, attachments = listOf("pour-checklist.pdf"),
        ),
        Mail(
            "m2", "t2", Folder.RECEIVED, Person("Supplier accounts", "accounts@supplier-example.net"), listOf(me), subject = "Your statement for November is ready",
            body = "Dear customer,\n\nyour statement is ready. See it here: ${web("portal.supplier-example.net/statements/november")}\n\nRegards, Accounts",
            at = now.minusMinutes(190), unread = true, remotePictures = 2,
        ),
        Mail(
            "m3", "t3", Folder.RECEIVED, Person("IT Support", "support@example.com.account-check.net"), listOf(me), subject = "Your mailbox is almost full",
            body = "Your mailbox will be closed today. Confirm your account now: ${web("example.com.account-check.net/login")}",
            at = now.minusMinutes(400),
        ),
        Mail("m4", "t4", Folder.RECEIVED, hr, listOf(me), subject = "Leave plan for December", body = "Please send your leave dates for December by Monday.", at = now.minusMinutes(2900)),
        Mail("m5", "t4", Folder.RECEIVED, hr, listOf(me), subject = "Re: Leave plan for December", body = "A reminder: the leave dates are due tomorrow.", at = now.minusMinutes(1500)),
        Mail("m6", "t5", Folder.SENT, me, listOf(engineer), subject = "Shuttering on the second floor", body = "Is the second floor ready for inspection tomorrow morning?", at = now.minusMinutes(800)),
    )
}
