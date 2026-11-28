package com.example.erp.app

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
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
import com.example.erp.core.Chat
import com.example.erp.core.Format
import com.example.erp.core.Message
import com.example.erp.core.Room
import com.example.erp.core.RoomKind
import java.time.LocalDateTime

/** Every tap in chat that changes something. All are required: no button without somewhere to lead. */
class ChatActions(
    /** A room was opened: its messages count as read. */
    val opened: (roomId: String) -> Unit,
    val send: (roomId: String, text: String, replyTo: String?) -> Unit,
    /** Opens the one-to-one chat with a colleague, making it when there is none, and gives its room id. */
    val startWith: (colleague: String) -> String,
)

/**
 * Chat. Phone: the list of rooms, then one room. Tablet (wide): list and room side by side. Rooms are made by the
 * server; here a person can only start a one-to-one chat with a colleague.
 */
@Composable
fun ChatScreen(rooms: List<Room>, colleagues: List<String>, now: LocalDateTime, online: Boolean, actions: ChatActions, asked: String? = null, onOpened: () -> Unit = {}) {
    var openId by rememberSaveable { mutableStateOf<String?>(null) }
    var choosing by rememberSaveable { mutableStateOf(false) }
    val open = rooms.firstOrNull { it.id == openId }
    val openRoom = { id: String -> openId = id; choosing = false; actions.opened(id) }
    // An alert for one chat leads to that chat; a chat that is not there leaves the list as it is.
    LaunchedEffect(asked) {
        if (asked != null) {
            if (rooms.any { it.id == asked }) openRoom(asked)
            onOpened()
        }
    }
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 840.dp
        when {
            choosing -> {
                BackHandler { choosing = false }
                Colleagues(colleagues, onBack = { choosing = false }) { openRoom(actions.startWith(it)) }
            }
            wide -> Row(Modifier.fillMaxSize().padding(Look.Gap), horizontalArrangement = Arrangement.spacedBy(Look.Gap)) {
                RoomList(rooms, open?.id, now, online, Modifier.weight(1f), onNew = { choosing = true }, onOpen = openRoom)
                Column(Modifier.weight(1.4f)) {
                    if (open != null) RoomView(open, now, onBack = null, actions)
                    else Text("Choose a chat on the left.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                }
            }
            open != null -> {
                BackHandler { openId = null }
                Column(Modifier.fillMaxSize().padding(Look.Gap)) { RoomView(open, now, onBack = { openId = null }, actions) }
            }
            else -> RoomList(rooms, null, now, online, Modifier.fillMaxSize().padding(Look.Gap), onNew = { choosing = true }, onOpen = openRoom)
        }
    }
}

private fun icon(kind: RoomKind) = when (kind) {
    RoomKind.NOTICES -> R.drawable.ic_bell
    RoomKind.DIRECT -> R.drawable.ic_person
    else -> R.drawable.ic_chat
}

@Composable
private fun RoomList(rooms: List<Room>, selected: String?, now: LocalDateTime, online: Boolean, modifier: Modifier, onNew: () -> Unit, onOpen: (String) -> Unit) {
    Column(modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Chat", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        if (!online) {
            Notice(StatusKind.NONE, "No connection. You can read the last ${Chat.KEEP_DAYS} days and write; your messages are sent when you are back online.")
        }
        for (room in Chat.ordered(rooms)) {
            val time = room.last?.let { Format.dateTime(it.at, now) + " · " }.orEmpty()
            RowCard(
                icon(room.kind),
                room.name,
                time + Chat.lastLine(room),
                pill = if (room.unread > 0) StatusKind.INFO to "${room.unread} new" else null,
                selected = room.id == selected,
                onClick = { onOpen(room.id) },
            )
        }
        OutlineButton("New chat with a colleague", onNew)
    }
}

@Composable
private fun Colleagues(colleagues: List<String>, onBack: () -> Unit, onChoose: (String) -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        TopBar(onBack = onBack)
        Text("New chat", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        Text("Choose a colleague. Rooms for sites and teams are made for you.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
        for (name in colleagues) RowCard(R.drawable.ic_person, name, "Opens your chat with them.", onClick = { onChoose(name) })
    }
}

@Composable
private fun RoomView(room: Room, now: LocalDateTime, onBack: (() -> Unit)?, actions: ChatActions) {
    // In memory only: what is being typed is never handed to the state Android keeps outside the app.
    var draft by remember(room.id) { mutableStateOf("") }
    var replyTo by rememberSaveable(room.id) { mutableStateOf<String?>(null) }
    val answered = room.messages.firstOrNull { it.id == replyTo }
    val messagesScroll = rememberScrollState()
    val pageScroll = rememberScrollState()
    // The newest message is in view when the room opens and after each new one.
    LaunchedEffect(room.id, room.messages.size) {
        messagesScroll.scrollTo(messagesScroll.maxValue)
        pageScroll.scrollTo(pageScroll.maxValue)
    }
    BoxWithConstraints(Modifier.fillMaxSize()) {
    // Normally the writing box stays at the bottom and only the messages scroll. On a small screen or with large
    // text there is no room for that, so the whole room scrolls as one page and nothing is squeezed or cut off.
    // Measured without the keyboard, so opening it never switches the layout under the person's fingers.
    val tight = LocalDensity.current.fontScale > 1.3f || maxHeight < 520.dp
    Column(Modifier.fillMaxSize().imePadding().then(if (tight) Modifier.verticalScroll(pageScroll) else Modifier), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        if (onBack != null) TopBar(onBack = onBack)
        Text(room.name, style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
        if (room.company) Text("Company room. Messages here are kept by the company.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        Column(if (tight) Modifier.fillMaxWidth() else Modifier.weight(1f).fillMaxWidth().verticalScroll(messagesScroll), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (room.messages.isEmpty()) Text("No messages yet.", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
            for (message in room.messages) {
                MessageRow(message, room.messages.firstOrNull { it.id == message.replyTo }, now, onReply = if (room.readOnly) null else ({ replyTo = message.id }))
            }
        }
        if (room.readOnly) {
            Notice(StatusKind.NONE, "Only notices are posted here. Nobody can write in this room.")
        } else {
            if (answered != null) {
                Text("Replying to ${name(answered)}: ${Format.short(answered.text, 60)}", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                OutlineButton("Do not reply to it", { replyTo = null })
            }
            OutlinedTextField(
                draft,
                { draft = Chat.limited(it) },
                Modifier.fillMaxWidth(),
                label = { Text("Message") },
                textStyle = MaterialTheme.typography.bodyLarge,
                maxLines = 5,
                shape = RoundedCornerShape(Look.Corner),
            )
            if (draft.length >= Chat.MAX_LENGTH) Text("A message holds ${Chat.MAX_LENGTH} characters at most. Send this one and go on in the next.", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
            val text = Chat.cleaned(draft)
            if (text != null) {
                MainButton("Send", {
                    actions.send(room.id, text, replyTo)
                    draft = ""
                    replyTo = null
                })
            }
        }
    }
    }
}

private fun name(message: Message) = if (message.mine) "You" else message.sender

/**
 * One message, built for sunlight: the sender's name in bold, a strong line around it, and the person's own set to
 * the right with a tint and the word "You", so it is never told apart by colour alone. A tap starts a reply.
 */
@Composable
private fun MessageRow(message: Message, answered: Message?, now: LocalDateTime, onReply: (() -> Unit)?) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (message.mine) Arrangement.End else Arrangement.Start) {
        val inside = @Composable {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("${name(message)} · ${Format.dateTime(message.at, now)}", style = MaterialTheme.typography.titleMedium)
                if (answered != null) Text("Reply to ${name(answered)}: ${Format.short(answered.text, 60)}", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                Text(message.text, style = MaterialTheme.typography.bodyLarge)
                if (message.waiting) Status(StatusKind.WAIT, "Waiting to send")
            }
        }
        val size = Modifier.fillMaxWidth(0.9f).heightIn(min = Look.Touch)
        val shape = RoundedCornerShape(Look.Corner)
        val border = BorderStroke(Look.LineWidth, Look.Line)
        val color = if (message.mine) Look.Soft else Look.Surface
        if (onReply != null) Surface(onReply, size, shape = shape, border = border, color = color, contentColor = Look.Ink, content = inside)
        else Surface(size, shape = shape, border = border, color = color, contentColor = Look.Ink, content = inside)
    }
}
