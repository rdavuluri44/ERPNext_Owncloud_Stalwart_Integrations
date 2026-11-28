package com.example.erp.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import com.example.erp.core.Chat
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.Message
import com.example.erp.core.Room
import com.example.erp.core.RoomKind
import java.time.LocalDateTime

/**
 * Test builds only: the chat screens against a stand-in, because the chat server and sign-in do not exist yet.
 * The rooms, people and messages are made up, live in memory only, and nothing is sent anywhere. The "Signal"
 * button plays "no connection", so waiting messages can be seen. Remove with the real chat (cleanup list).
 */
@Composable
fun ChatPreviewScreen(now: LocalDateTime = LocalDateTime.now(), open: String? = null, onOpened: () -> Unit = {}, onCount: (Int) -> Unit = {}) {
    var rooms by remember { mutableStateOf(sampleRooms(now)) }
    LaunchedEffect(rooms) { onCount(Chat.unread(rooms)) }
    var online by remember { mutableStateOf(true) }
    var count by remember { mutableStateOf(0) }
    val actions = ChatActions(
        opened = { id -> rooms = rooms.map { if (it.id == id) it.copy(unread = 0) else it } },
        send = { id, text, replyTo ->
            count += 1
            val message = Message("mine-$count", "You", mine = true, text = text, at = now, waiting = !online, replyTo = replyTo)
            rooms = rooms.map { if (it.id == id) it.copy(messages = it.messages + message) else it }
        },
        startWith = { colleague ->
            val existing = rooms.firstOrNull { it.kind == RoomKind.DIRECT && it.name == colleague }
            existing?.id ?: "direct-$colleague".also { rooms = rooms + Room(it, colleague, RoomKind.DIRECT) }
        },
    )
    Column(Modifier.fillMaxSize()) {
        OutlineButton(
            if (online) "Signal: on (stand-in)" else "Signal: off (stand-in)",
            {
                online = !online
                // Back online: what was waiting is sent.
                if (online) rooms = rooms.map { room -> room.copy(messages = room.messages.map { it.copy(waiting = false) }) }
            },
            Modifier.padding(horizontal = Look.Gap, vertical = 8.dp),
        )
        Box(Modifier.weight(1f)) { ChatScreen(rooms, listOf("Engineer", "HR", "Project manager", "Store keeper"), now, online, actions, open, onOpened) }
    }
}

/** The number the bar shows for Chat before the stand-in was opened. */
internal fun standInUnreadChats(now: LocalDateTime): Int = Chat.unread(sampleRooms(now))

private fun sampleRooms(now: LocalDateTime): List<Room> {
    fun from(id: String, who: String, text: String, minutesAgo: Long) = Message(id, who, mine = false, text = text, at = now.minusMinutes(minutesAgo))
    return listOf(
        Room(
            "notices", "Notices", RoomKind.NOTICES,
            listOf(
                from("n1", "System", "The attendance window for today closes at 10:00.", 600),
                from("n2", "System", "A new version of the app is ready. It installs the next time you open the app.", 95),
            ),
            unread = 1,
        ),
        Room(
            "site-a", "Site A", RoomKind.SITE,
            listOf(
                from("s1", "Site supervisor", "Good morning. The concrete arrives at 11:00, keep the east gate free.", 180),
                from("s2", "Engineer", "Noted. Shuttering on the second floor is checked and ready.", 150),
                from("s3", "Store keeper", "Two more vibrators are needed. Who has the spare one?", 20),
            ),
            unread = 2,
        ),
        Room("site-a-engineers", "Site A engineers", RoomKind.TEAM, listOf(from("t1", "Project manager", "Please send the pour checklist before the lorry is unloaded.", 60))),
        Room("direct-Project manager", "Project manager", RoomKind.DIRECT, listOf(from("d1", "Project manager", "Can you be at the site office at 16:00?", 1500))),
    )
}
