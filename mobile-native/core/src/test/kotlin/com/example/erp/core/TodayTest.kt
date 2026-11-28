package com.example.erp.core

import java.time.LocalDateTime
import java.time.LocalTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TodayTest {
    private val now = LocalDateTime.of(2026, 11, 27, 9, 15)

    private fun kinds(facts: TodayFacts) = Today.cards(facts, now).map { it.kind }

    @Test
    fun onlyWhatAppliesIsShown() {
        assertEquals(emptyList<CardKind>(), kinds(TodayFacts()))
        assertEquals(listOf(CardKind.MY_ATTENDANCE), kinds(TodayFacts(attendance = OwnAttendance(AttendanceState.NOT_IN), chatUnread = 0, mailUnread = 0)))
        // Zero of something is no card, and a person without a mailbox has no Mail card.
        val nothing = TodayFacts(returned = 0, toVerify = Waiting(0), toApprove = Waiting(0), sites = SitesDay(), faceQueue = 0, mailUnread = null)
        assertEquals(emptyList<CardKind>(), kinds(nothing))
    }

    @Test
    fun aDeadlineTodayComesFirstThenMyOwnWorkThenWhatWaitsThenWhatIShouldKnow() {
        val engineer = TodayFacts(
            attendance = OwnAttendance(AttendanceState.IN, LocalTime.of(8, 57)),
            toVerify = Waiting(12, sites = 2, deadline = now.withHour(10).withMinute(0)),
            sites = SitesDay(notSent = 1, sent = 1),
            chatUnread = 3,
            mailUnread = 5,
        )
        assertEquals(listOf(CardKind.TO_VERIFY, CardKind.MY_ATTENDANCE, CardKind.MY_SITES, CardKind.CHAT, CardKind.MAIL), kinds(engineer))
        val first = Today.cards(engineer, now).first()
        assertEquals("12 entries at 2 sites. Due today, 10:00.", first.line)
        assertEquals(Lead.INBOX, first.lead)
        // Two deadlines: the nearer one first. A missed one says so.
        val both = TodayFacts(toVerify = Waiting(2, deadline = now.withHour(10).withMinute(0)), toApprove = Waiting(4, deadline = now.withHour(9).withMinute(0)))
        assertEquals(listOf(CardKind.TO_APPROVE, CardKind.TO_VERIFY), kinds(both))
        assertEquals("4 waiting. Was due Today, 09:00.", Today.cards(both, now).first().line)
        // A deadline on a later day does not jump the queue: my own work for today stays first.
        val later = TodayFacts(attendance = OwnAttendance(AttendanceState.NOT_IN), toVerify = Waiting(2, deadline = now.plusDays(4)))
        assertEquals(listOf(CardKind.MY_ATTENDANCE, CardKind.TO_VERIFY), kinds(later))
        // A deadline on another day never says "today", and no site count is invented.
        assertEquals("2 entries. Due 28 Nov, 10:00.", Today.cards(TodayFacts(toVerify = Waiting(2, sites = 0, deadline = now.plusDays(1).withHour(10).withMinute(0))), now).single().line)
    }

    @Test
    fun theSupervisorSeesTheTeamAndWhatCameBack() {
        val facts = TodayFacts(
            attendance = OwnAttendance(AttendanceState.NOT_IN, outsideSite = true),
            team = TeamDay(18, 24, TeamState.NOT_SENT),
            returned = 2,
            waitingToSend = 1,
            facesMissing = 6,
        )
        val cards = Today.cards(facts, now)
        assertEquals(listOf(CardKind.MY_ATTENDANCE, CardKind.MY_TEAM, CardKind.RETURNED, CardKind.WAITING_TO_SEND, CardKind.FACES_MISSING), cards.map { it.kind })
        assertEquals("Not checked in yet. You are outside the site.", cards[0].line)
        assertEquals("Marked 18 of 24. Not sent yet.", cards[1].line)
        assertEquals("2 entries were sent back to correct.", cards[2].line)
        assertEquals("1 thing is saved on this phone and not sent yet.", cards[3].line)
        // A check-in without a time says no time; a team the app cannot describe gets no card.
        assertEquals("Checked in.", Today.cards(TodayFacts(attendance = OwnAttendance(AttendanceState.IN)), now).single().line)
        assertEquals("Checked out.", Today.cards(TodayFacts(attendance = OwnAttendance(AttendanceState.OUT)), now).single().line)
        assertEquals(emptyList<CardKind>(), kinds(TodayFacts(team = TeamDay(0, 0, TeamState.NOT_SENT))))
        assertEquals(emptyList<CardKind>(), kinds(TodayFacts(team = TeamDay(30, 24, TeamState.NOT_SENT))))
        // Cards whose screens are not built lead nowhere, so they are not buttons.
        assertTrue(cards.all { it.lead == null })
    }

    @Test
    fun theProjectManagerSeesWhatWaitsAndHowTheSitesStand() {
        val facts = TodayFacts(
            toApprove = Waiting(8, oldestSince = now.minusHours(2)),
            faceQueue = 4,
            accessRequests = 1,
            sites = SitesDay(notSent = 1, verified = 1, approved = 1),
        )
        val cards = Today.cards(facts, now)
        assertEquals(listOf(CardKind.TO_APPROVE, CardKind.FACE_QUEUE, CardKind.ACCESS_REQUESTS, CardKind.MY_SITES), cards.map { it.kind })
        assertEquals("8 waiting, the oldest for 2 h.", cards[0].line)
        assertEquals("1 person waits for you.", cards[2].line)
        assertEquals("3 sites: 1 approved, 1 verified, 1 not sent yet.", cards[3].line)
        assertEquals("All approved", Today.cards(TodayFacts(sites = SitesDay(approved = 2)), now).single().word)
    }

    @Test
    fun countsOnlyNeverAnAmountOrAName() {
        val full = TodayFacts(
            attendance = OwnAttendance(AttendanceState.OUT, LocalTime.of(17, 32)), team = TeamDay(24, 24, TeamState.APPROVED), returned = 1, waitingToSend = 3,
            toVerify = Waiting(1), toApprove = Waiting(1), faceQueue = 1, accessRequests = 2, sites = SitesDay(sent = 1), facesMissing = 1,
            myRequest = MyRequest(RequestKind.LEAVE, RequestState.WAITING), chatUnread = 1, mailUnread = 1,
        )
        val cards = Today.cards(full, now)
        assertEquals(CardKind.entries.toSet(), cards.map { it.kind }.toSet())
        for (card in cards) {
            assertFalse(card.line, Regex("\\d[\\d,]*\\.\\d\\d|₹|Rs").containsMatchIn(card.line)) // nothing that looks like money
        }
        // My own request is said in the app's fixed words, and its word is a state, never an action like "Open".
        val request = cards.single { it.kind == CardKind.MY_REQUESTS }
        assertEquals("Leave: waiting for approval." to "Waiting", request.line to request.word)
        assertEquals("Advance: returned to you to correct.", Today.cards(TodayFacts(myRequest = MyRequest(RequestKind.ADVANCE, RequestState.RETURNED)), now).single().line)
    }

    @Test
    fun aHolidayANewPersonAndAFailedCheckAreSaidPlainly() {
        val holiday = TodayFacts(attendance = OwnAttendance(AttendanceState.NOT_IN), team = TeamDay(0, 24, TeamState.NOT_SENT), holiday = true)
        assertEquals(emptyList<CardKind>(), kinds(holiday))
        assertEquals("Today is a holiday for your site. Nothing is waiting for you.", Today.emptyLine(holiday))
        assertEquals("You are set up. Your site and your team appear here when the project manager adds you.", Today.emptyLine(TodayFacts(setUp = false)))
        assertEquals("Nothing is waiting for you today.", Today.emptyLine(TodayFacts()))
        // "Nothing is waiting" is never said when something could not be checked.
        val failed = TodayFacts(failed = listOf(Source.PURCHASES, Source.LEAVE))
        assertNull(Today.emptyLine(failed))
        assertEquals("Could not check: purchases, leave. What is shown may be incomplete.", Today.failedLine(failed))
        assertNull(Today.failedLine(TodayFacts()))
        // Nor without a connection: the app cannot know, so it claims nothing. Also when nothing was ever fetched.
        assertNull(Today.emptyLine(TodayFacts(online = false, asOf = now.minusHours(3))))
        assertNull(Today.emptyLine(TodayFacts(online = false)))
        assertNull(Today.emptyLine(TodayFacts(online = false, holiday = true)))
    }

    @Test
    fun theStatusLineAndTheWarnings() {
        assertEquals(Tone.GOOD to "Up to date.", Today.status(TodayFacts(), now))
        assertEquals(Tone.GOOD to "Up to date.", Today.status(TodayFacts(clockOffMinutes = 4), now))
        assertEquals(Tone.CARE to "Your phone's clock is 12 minutes behind. Attendance uses the server's time.", Today.status(TodayFacts(clockOffMinutes = -12), now))
        val offline = TodayFacts(online = false, waitingToSend = 3, asOf = now.minusMinutes(18), offlineHoursLeft = 3)
        assertEquals(Tone.PLAIN to "No connection: 3 things wait to be sent. The numbers are as of Today, 08:57.", Today.status(offline, now))
        assertEquals(listOf("Without a connection the app opens for 3 more hours."), Today.warnings(offline))
        assertEquals(listOf("Your key was not used for 5 days. Open the app again within 2 days, or the key is removed."), Today.warnings(TodayFacts(keyUnusedDays = 5)))
        assertEquals(emptyList<String>(), Today.warnings(TodayFacts(keyUnusedDays = 2, offlineHoursLeft = 8)))
        assertEquals(listOf("Your key was not used for 9 days and can be removed at any moment. Use the app with a connection today."), Today.warnings(TodayFacts(keyUnusedDays = 9)))
        assertEquals(listOf("Without a connection the app will not open again. Connect before you close it."), Today.warnings(TodayFacts(online = false, offlineHoursLeft = 0)))
    }
}
