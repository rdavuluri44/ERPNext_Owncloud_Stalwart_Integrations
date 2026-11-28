package com.example.erp.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.AttendanceState
import com.example.erp.core.Lead
import com.example.erp.core.MyRequest
import com.example.erp.core.OwnAttendance
import com.example.erp.core.RequestKind
import com.example.erp.core.RequestState
import com.example.erp.core.SitesDay
import com.example.erp.core.Source
import com.example.erp.core.TeamDay
import com.example.erp.core.TeamState
import com.example.erp.core.TodayFacts
import com.example.erp.core.Waiting
import java.time.LocalDateTime
import java.time.LocalTime

/**
 * Test builds only: Today against a stand-in, because there is no sign-in and no server answer yet. Each choice
 * is one made-up day: the seven roles of the plan, and the situations every screen must handle. The numbers are
 * invented and nothing is asked from any server. Remove with the real Today (cleanup list).
 */
enum class Day(val label: String, val who: String) {
    SUPERVISOR("Site supervisor", "Site supervisor · Site A"),
    ENGINEER("Engineer", "Engineer · Site A, Site B"),
    PROJECT_MANAGER("Project manager", "Project manager · 3 sites"),
    HR("HR", "HR · Office"),
    ADMIN("Admin", "Admin · Office"),
    MANAGEMENT("Management", "Management"),
    STAFF("Staff", "Staff · Site A"),
    EVENING("Supervisor, evening", "Site supervisor · Site A"),
    NEW_PERSON("New person", "New here"),
    HOLIDAY("Holiday", "Site supervisor · Site A"),
    OFFLINE("No connection", "Site supervisor · Site A"),
    FAILED("A check failed", "Project manager · 3 sites"),
    QUIET("Nothing waiting", "Staff · Site A"),
}

private fun facts(day: Day, now: LocalDateTime): TodayFacts {
    val checkedIn = OwnAttendance(AttendanceState.IN, LocalTime.of(8, 57))
    val supervisor = TodayFacts(attendance = checkedIn, team = TeamDay(18, 24, TeamState.NOT_SENT), returned = 2, facesMissing = 3, chatUnread = 3)
    val manager = TodayFacts(
        attendance = checkedIn, toApprove = Waiting(8, oldestSince = now.minusHours(2)), faceQueue = 4, accessRequests = 1,
        sites = SitesDay(notSent = 1, verified = 1, approved = 1), facesMissing = 6, chatUnread = 5, mailUnread = 12,
    )
    return when (day) {
        Day.SUPERVISOR -> supervisor
        Day.ENGINEER -> TodayFacts(
            attendance = checkedIn, toVerify = Waiting(12, sites = 2, deadline = now.toLocalDate().atTime(23, 30)), sites = SitesDay(notSent = 1, sent = 1), facesMissing = 2, chatUnread = 1, mailUnread = 2,
        )
        Day.PROJECT_MANAGER -> manager
        Day.HR -> TodayFacts(attendance = checkedIn, toApprove = Waiting(3, oldestSince = now.minusHours(26)), facesMissing = 14, mailUnread = 7)
        Day.ADMIN -> TodayFacts(attendance = checkedIn, accessRequests = 2, sites = SitesDay(notSent = 2, sent = 1, verified = 1, approved = 3), mailUnread = 4)
        Day.MANAGEMENT -> TodayFacts(toApprove = Waiting(5, oldestSince = now.minusHours(5)), sites = SitesDay(notSent = 2, sent = 1, verified = 1, approved = 3), chatUnread = 2, mailUnread = 9)
        Day.STAFF -> TodayFacts(attendance = OwnAttendance(AttendanceState.NOT_IN, outsideSite = true), myRequest = MyRequest(RequestKind.LEAVE, RequestState.WAITING), chatUnread = 2)
        Day.EVENING -> TodayFacts(attendance = OwnAttendance(AttendanceState.OUT, LocalTime.of(17, 32)), team = TeamDay(24, 24, TeamState.APPROVED))
        Day.NEW_PERSON -> TodayFacts(setUp = false)
        Day.HOLIDAY -> supervisor.copy(holiday = true, returned = 0, facesMissing = 0, chatUnread = 0)
        Day.OFFLINE -> supervisor.copy(online = false, waitingToSend = 3, asOf = now.minusMinutes(18), offlineHoursLeft = 3, team = TeamDay(21, 24, TeamState.NOT_SENT))
        Day.FAILED -> manager.copy(failed = listOf(Source.PURCHASES, Source.LEAVE), keyUnusedDays = 5)
        Day.QUIET -> TodayFacts(attendance = null, clockOffMinutes = -12)
    }
}

@Composable
fun TodayPreviewScreen(onOpen: (Lead) -> Unit, now: LocalDateTime = LocalDateTime.now()) {
    var day by rememberSaveable { mutableStateOf(Day.SUPERVISOR) }
    var retried by rememberSaveable { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        OutlineButton(
            "Role: ${day.label}",
            { day = Day.entries[(day.ordinal + 1) % Day.entries.size]; retried = false },
            Modifier.padding(horizontal = Look.Gap, vertical = 8.dp),
        )
        // "Try again" asks no server here: the stand-in shows the same made-up day with every check answered.
        val shown = facts(day, now).let { if (retried) it.copy(failed = emptyList()) else it }
        Box(Modifier.weight(1f)) { TodayScreen(day.who, shown, now, onOpen, onRefresh = { retried = true }) }
    }
}
