package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.unit.dp
import com.example.erp.core.Conversation
import com.example.erp.core.Folder
import com.example.erp.core.Format
import com.example.erp.core.Mail
import com.example.erp.core.Mails
import com.example.erp.core.Person
import java.time.LocalDateTime

/** Every tap in mail that changes something outside the screen. All are required. */
class MailActions(
    /** A conversation was opened: its mails count as read. */
    val opened: (thread: String) -> Unit,
    val send: (to: List<String>, subject: String, body: String) -> Unit,
    /** Opens a web address in the phone's browser. Called only after the person saw the real address and agreed. */
    val openLink: (link: String) -> Unit,
)

private enum class View { LIST, FOLDERS, READ, WRITE, FILE }

/**
 * Mail. Phone: the list, then one conversation. Tablet (wide): list and conversation side by side. Every screen is
 * one scrolling page, so nothing is squeezed on a small phone or with large text.
 *
 * Built in: mail from outside the company says so; pictures from the internet are not loaded until asked for;
 * a link shows where it really leads and is opened only after a yes; a mail to someone outside says so before it
 * is sent. Attachments open inside the app; saving to the phone is a setting that is off (owner, 27 November 2026).
 */
@Composable
fun MailScreen(mails: List<Mail>, me: Person, company: Set<String>, now: LocalDateTime, actions: MailActions, asked: String? = null, onOpened: () -> Unit = {}) {
    var view by rememberSaveable { mutableStateOf(View.LIST) }
    var folder by rememberSaveable { mutableStateOf(Folder.RECEIVED) }
    var thread by rememberSaveable { mutableStateOf<String?>(null) }
    var file by remember { mutableStateOf("") }
    var title by rememberSaveable { mutableStateOf("New mail") }
    // What is being written stays in memory only. It is never put into the state Android keeps for the app outside
    // the app's own storage: that would carry mail text out of the app, and a long quoted mail would crash it.
    var to by remember { mutableStateOf("") }
    var subject by remember { mutableStateOf("") }
    var body by remember { mutableStateOf("") }

    val conversations = Mails.conversations(mails, folder)
    val open = conversations.firstOrNull { it.thread == thread }
    val write = { heading: String, toWhom: String, about: String, text: String -> title = heading; to = toWhom; subject = about; body = text; view = View.WRITE }
    val openConversation = { id: String -> thread = id; view = View.READ; actions.opened(id) }
    // An alert for one mail leads to that conversation; one that is not there leaves the list as it is.
    LaunchedEffect(asked) {
        if (asked != null) {
            if (mails.any { it.thread == asked }) openConversation(asked)
            onOpened()
        }
    }

    var wideNow by remember { mutableStateOf(false) }

    @Composable
    fun list(modifier: Modifier, selected: String?) = Page(modifier) {
        Text("Mail", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        MainButton("Write a mail", { if (!wideNow) thread = null; write("New mail", "", "", "") })
        OutlineButton("Folder: ${folder.label}", { view = View.FOLDERS })
        if (conversations.isEmpty()) Text("Nothing in ${folder.label}.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        for (conversation in conversations) ConversationRow(conversation, folder, company, now, conversation.thread == selected) { openConversation(conversation.thread) }
    }

    @Composable
    fun read(conversation: Conversation, onBack: (() -> Unit)?) = Page(Modifier.fillMaxSize()) {
        if (onBack != null) TopBar(onBack = onBack)
        Text(conversation.newest.subject, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        for (mail in conversation.mails) MailCard(mail, company, now, onFile = { file = it; view = View.FILE }, onOpenLink = actions.openLink)
        val last = conversation.newest
        MainButton("Reply", { write("Reply", last.from.address, Mails.replySubject(last.subject), Mails.quoted(last)) })
        val everyone = Mails.replyAll(last, me.address)
        if (everyone.size > 1) {
            OutlineButton("Reply to all", { write("Reply to all", everyone.joinToString(", ") { it.address }, Mails.replySubject(last.subject), Mails.quoted(last)) })
        }
        OutlineButton("Forward", { write("Forward", "", Mails.forwardSubject(last.subject), Mails.quoted(last)) })
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 840.dp
        wideNow = wide
        when {
            view == View.FOLDERS -> {
                BackHandler { view = View.LIST }
                Page(Modifier.fillMaxSize().padding(Look.Gap)) {
                    TopBar(onBack = { view = View.LIST })
                    Text("Folders", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
                    for (choice in Folder.entries) {
                        val count = Mails.conversations(mails, choice).size
                        RowCard(R.drawable.ic_mail, choice.label, if (count == 1) "1 conversation" else "$count conversations", selected = choice == folder, onClick = { folder = choice; thread = null; view = View.LIST })
                    }
                }
            }
            view == View.WRITE -> {
                val leave = { view = if (open != null) View.READ else View.LIST }
                BackHandler(onBack = leave)
                Write(title, to, subject, body, company, onTo = { to = it }, onSubject = { subject = it }, onBody = { body = it }, onLeave = leave) { recipients ->
                    actions.send(recipients, Mails.oneLine(subject), body.trim())
                    view = View.LIST
                }
            }
            view == View.FILE -> {
                BackHandler { view = View.READ }
                Page(Modifier.fillMaxSize().padding(Look.Gap)) {
                    TopBar(onBack = { view = View.READ })
                    Text(file, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
                    Notice(StatusKind.INFO, "Attachments open here, inside the app. Saving to the phone is switched off.")
                    Text("The viewer for this kind of file is not built yet.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                }
            }
            wide -> Row(Modifier.fillMaxSize().padding(Look.Gap), horizontalArrangement = Arrangement.spacedBy(Look.Gap)) {
                list(Modifier.weight(1f), open?.thread)
                Column(Modifier.weight(1.4f)) {
                    if (open != null) read(open, null)
                    else Text("Choose a mail on the left.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                }
            }
            view == View.READ && open != null -> {
                // Leaving a conversation forgets it, so a later "back" never lands in a mail read earlier.
                val close = { view = View.LIST; thread = null }
                BackHandler(onBack = close)
                Column(Modifier.fillMaxSize().padding(Look.Gap)) { read(open, close) }
            }
            else -> list(Modifier.fillMaxSize().padding(Look.Gap), null)
        }
    }
}

@Composable
private fun Page(modifier: Modifier, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp), content = content)
}

private fun names(people: List<Person>) = people.joinToString(", ") { it.name }

@Composable
private fun ConversationRow(conversation: Conversation, folder: Folder, company: Set<String>, now: LocalDateTime, selected: Boolean, onOpen: () -> Unit) {
    val mail = conversation.newest
    val outside = Mails.outside(mail.from.address, company)
    val who = if (folder == Folder.SENT || folder == Folder.DRAFTS) "To: ${names(mail.to)}" else mail.from.name
    val count = if (conversation.mails.size > 1) " (${conversation.mails.size})" else ""
    // What a pill cannot carry is said in words in the line, so nothing depends on colour or on one free slot.
    val flags = listOfNotNull("Outside".takeIf { outside && conversation.unread }, "Attachment".takeIf { conversation.mails.any { it.attachments.isNotEmpty() } })
    RowCard(
        R.drawable.ic_mail,
        who + count,
        (flags + Format.dateTime(mail.at, now) + mail.subject).joinToString(" · ") + "\n" + Mails.firstLine(mail.body),
        pill = when {
            conversation.unread -> StatusKind.INFO to "New"
            outside -> StatusKind.WARN to "Outside"
            else -> null
        },
        selected = selected,
        onClick = onOpen,
    )
}

@Composable
private fun MailCard(mail: Mail, company: Set<String>, now: LocalDateTime, onFile: (String) -> Unit, onOpenLink: (String) -> Unit) {
    var pictures by rememberSaveable(mail.id) { mutableStateOf(false) }
    var asked by remember(mail.id) { mutableStateOf<String?>(null) }
    Panel {
        Text("${mail.from.name} <${mail.from.address}>", style = MaterialTheme.typography.titleMedium)
        if (Mails.outside(mail.from.address, company)) {
            Pill(StatusKind.WARN, "Outside")
            Text("This sender is not in the company. Be careful with links and attachments.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
        val copies = if (mail.cc.isEmpty()) "" else " · Copy: ${names(mail.cc)}"
        Text("To: ${names(mail.to)}$copies · ${Format.dateTime(mail.at, now)}", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        Text(mail.body, style = MaterialTheme.typography.bodyLarge)
        if (mail.remotePictures > 0) {
            val many = if (mail.remotePictures == 1) "1 picture" else "${mail.remotePictures} pictures"
            if (pictures) {
                Text("$many from the internet shown.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            } else {
                Notice(StatusKind.INFO, "$many from the internet are not loaded, so the sender cannot see that you opened this mail.")
                OutlineButton("Show pictures", { pictures = true })
            }
        }
        for (name in mail.attachments) RowCard(R.drawable.ic_clip, name, "Opens inside the app.", onClick = { onFile(name) })
        for (link in Mails.links(mail.body)) {
            val host = Mails.realHost(link)
            if (host == null) {
                RowCard(R.drawable.ic_link, "A link the app cannot check", "The app cannot be sure where it leads, so it cannot be opened here.")
            } else {
                RowCard(R.drawable.ic_link, "Link to $host", "Tap to see the full address before it opens.", onClick = { asked = link })
            }
            if (asked == link && host != null) {
                Notice(StatusKind.WARN, "Open this in your browser? It leads to $host. Full address: $link")
                MainButton("Open $host", { asked = null; onOpenLink(link) })
                OutlineButton("Do not open", { asked = null })
            }
        }
    }
}

@Composable
private fun Field(value: String, onChange: (String) -> Unit, label: String, lines: Int) {
    OutlinedTextField(
        value,
        onChange,
        Modifier.fillMaxWidth(),
        label = { Text(label) },
        textStyle = MaterialTheme.typography.bodyLarge,
        minLines = if (lines >= 4) 4 else 1,
        singleLine = lines == 1,
        maxLines = lines,
        shape = RoundedCornerShape(Look.Corner),
    )
}

@Composable
private fun Write(
    title: String,
    to: String,
    subject: String,
    body: String,
    company: Set<String>,
    onTo: (String) -> Unit,
    onSubject: (String) -> Unit,
    onBody: (String) -> Unit,
    onLeave: () -> Unit,
    onSend: (List<String>) -> Unit,
) {
    val (usable, unusable) = Mails.addresses(to)
    val leaving = usable.filter { Mails.outside(it, company) }
    Page(Modifier.fillMaxSize().imePadding().padding(Look.Gap)) {
        TopBar(onBack = onLeave)
        Text(title, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Field(to, onTo, "To", 3)
        if (unusable.isNotEmpty()) Notice(StatusKind.BAD, "Not a mail address: ${unusable.joinToString(", ")}. Correct it to send.")
        if (leaving.isNotEmpty()) Notice(StatusKind.WARN, "This mail goes outside the company: ${leaving.joinToString(", ")}")
        Field(subject, { onSubject(it.replace(Mails.LINE_BREAK, " ")) }, "Subject", 1)
        Field(body, onBody, "Message", 12)
        // Send exists only when the mail can be sent: someone to send to, no unreadable address, and something said.
        if (usable.isNotEmpty() && unusable.isEmpty() && (subject.isNotBlank() || body.isNotBlank())) MainButton("Send", { onSend(usable) })
        OutlineButton("Discard this mail", onLeave, danger = true)
    }
}
