package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ChatTest {
    private val now = LocalDateTime.of(2026, 11, 27, 18, 0)

    private fun message(id: String, minutesAgo: Long, mine: Boolean = false, text: String = "hello", waiting: Boolean = false) =
        Message(id, "Engineer", mine, text, now.minusMinutes(minutesAgo), waiting)

    @Test
    fun noticesThenMySiteThenTheNewestFirst() {
        val rooms = listOf(
            Room("d1", "Store keeper", RoomKind.DIRECT, listOf(message("a", 1))),
            Room("t1", "Site A engineers", RoomKind.TEAM, listOf(message("b", 30))),
            Room("s1", "Site A", RoomKind.SITE, listOf(message("c", 600))),
            Room("d2", "HR", RoomKind.DIRECT),
            Room("n", "Notices", RoomKind.NOTICES, listOf(message("d", 9000))),
        )
        assertEquals(listOf("n", "s1", "d1", "t1", "d2"), Chat.ordered(rooms).map { it.id })
    }

    @Test
    fun aRoomSaysWhoWroteLastAndCountsStaySeparate() {
        assertEquals("No messages yet.", Chat.lastLine(Room("d", "HR", RoomKind.DIRECT)))
        assertEquals("Engineer: hello", Chat.lastLine(Room("s", "Site A", RoomKind.SITE, listOf(message("a", 5)))))
        assertEquals("You: two lines", Chat.lastLine(Room("s", "Site A", RoomKind.SITE, listOf(message("a", 5, mine = true, text = "two\nlines")))))
        assertEquals(5, Chat.unread(listOf(Room("a", "A", RoomKind.SITE, unread = 2), Room("b", "B", RoomKind.DIRECT, unread = 3))))
    }

    @Test
    fun onlyNoticesAreReadOnlyAndOnlyOneToOneChatsAreNotCompanyRooms() {
        assertTrue(Room("n", "Notices", RoomKind.NOTICES).readOnly)
        assertFalse(Room("s", "Site A", RoomKind.SITE).readOnly)
        assertTrue(Room("t", "Team", RoomKind.TEAM).company)
        assertFalse(Room("d", "HR", RoomKind.DIRECT).company)
    }

    @Test
    fun nothingEmptyIsSent() {
        assertNull(Chat.cleaned(""))
        assertNull(Chat.cleaned("  \n "))
        assertEquals("on my way", Chat.cleaned("  on my way\n"))
        assertEquals(Chat.MAX_LENGTH, Chat.cleaned("x".repeat(5000))!!.length)
        // A cut never leaves half an emoji behind.
        val cut = Chat.limited("x".repeat(Chat.MAX_LENGTH - 1) + "\uD83D\uDE00")
        assertEquals(Chat.MAX_LENGTH - 1, cut.length)
        assertFalse(cut.last().isSurrogate())
    }

    @Test
    fun sevenDaysStayOnThePhoneAndWhatStillWaitsIsNeverDropped() {
        val old = Message("old", "Engineer", false, "old", now.minusDays(8))
        val edge = Message("edge", "Engineer", false, "edge", now.minusDays(7))
        val unsent = Message("unsent", "You", true, "unsent", now.minusDays(20), waiting = true)
        assertEquals(listOf("edge", "unsent"), Chat.kept(listOf(old, edge, unsent), now).map { it.id })
    }
}
