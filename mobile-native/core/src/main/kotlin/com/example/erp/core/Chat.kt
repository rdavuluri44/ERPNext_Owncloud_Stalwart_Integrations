package com.example.erp.core

import java.time.LocalDateTime

/** The rules of chat that do not depend on a server or a screen (screen plan of 27 November 2026, points 8 to 13). */
enum class RoomKind {
    /** System messages that only inform. Nobody writes here. */
    NOTICES,

    /** The room of the person's own site. */
    SITE,
    TEAM,

    /** One colleague. */
    DIRECT,
}

data class Message(
    val id: String,
    val sender: String,
    val mine: Boolean,
    val text: String,
    val at: LocalDateTime,
    /** Written without a connection; it is sent when the phone is back online. */
    val waiting: Boolean = false,
    /** The id of the message this one answers. */
    val replyTo: String? = null,
)

data class Room(val id: String, val name: String, val kind: RoomKind, val messages: List<Message> = emptyList(), val unread: Int = 0) {
    /** Company rooms are kept by the company and say so; a one-to-one chat is not a company room. */
    val company: Boolean get() = kind != RoomKind.DIRECT
    val readOnly: Boolean get() = kind == RoomKind.NOTICES
    val last: Message? get() = messages.lastOrNull()
}

object Chat {
    /** Days of each room kept on the phone for reading without signal: the same as photos (owner, 27 November 2026). */
    const val KEEP_DAYS = 7L
    const val MAX_LENGTH = 4000

    /** Notices first, then the person's site, then everything else with the newest message on top. */
    fun ordered(rooms: List<Room>): List<Room> = rooms.sortedWith(
        compareBy<Room> {
            when (it.kind) {
                RoomKind.NOTICES -> 0
                RoomKind.SITE -> 1
                else -> 2
            }
        }.thenByDescending { it.last?.at ?: LocalDateTime.MIN },
    )

    fun unread(rooms: List<Room>): Int = rooms.sumOf { it.unread }

    /** The line under a room's name: who wrote last and how it starts. */
    fun lastLine(room: Room): String {
        val last = room.last ?: return "No messages yet."
        return (if (last.mine) "You" else last.sender) + ": " + Format.short(last.text.replace('\n', ' '), 60)
    }

    /** What is really sent for what was typed, or null when there is nothing to send. */
    fun cleaned(typed: String): String? = limited(typed.trim()).ifEmpty { null }

    /** At most [MAX_LENGTH] characters, and never half of a character that is stored in two parts (many emoji). */
    fun limited(text: String): String = text.take(MAX_LENGTH).let { if (it.isNotEmpty() && it.last().isHighSurrogate()) it.dropLast(1) else it }

    /** What stays on the phone: the last [KEEP_DAYS] days, and anything still waiting to be sent. */
    fun kept(messages: List<Message>, now: LocalDateTime): List<Message> = messages.filter { it.waiting || !it.at.isBefore(now.minusDays(KEEP_DAYS)) }
}
