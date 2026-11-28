package com.example.erp.core

import java.math.BigDecimal
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class MoneyTest {
    @Test
    fun indianGrouping() {
        assertEquals("0.00", Money.indian(BigDecimal("0")))
        assertEquals("999.00", Money.indian(BigDecimal("999")))
        assertEquals("1,000.00", Money.indian(BigDecimal("1000")))
        assertEquals("1,50,000.00", Money.indian(BigDecimal("150000")))
        assertEquals("12,34,56,789.50", Money.indian(BigDecimal("123456789.5")))
        assertEquals("-1,50,000.25", Money.indian(BigDecimal("-150000.25")))
        assertEquals("1,00,000", Money.indian(BigDecimal("100000"), decimals = 0))
    }

    @Test
    fun roundsOnlyForDisplayAndNeverShowsMinusZero() {
        assertEquals("0.13", Money.indian(BigDecimal("0.125")))
        assertEquals("1,00,000.00", Money.indian(BigDecimal("99999.995")))
        assertEquals("0.00", Money.indian(BigDecimal("-0.001")))
    }

    @Test
    fun totalsAreExactWhereFloatingPointIsNot() {
        assertEquals(BigDecimal("0.3"), Money.total(listOf(BigDecimal("0.1"), BigDecimal("0.2"))))
        assertFalse(0.1 + 0.2 == 0.3) // the fault this rule exists to avoid
    }

    @Test
    fun refusesWhatIsNotAnAmount() {
        assertEquals(BigDecimal("150000.50"), Money.parse(" 150000.50 "))
        for (bad in listOf("", "1,50,000", "1e5", "NaN", "12.", ".5", "abc")) {
            assertThrows(bad, IllegalArgumentException::class.java) { Money.parse(bad) }
        }
    }
}

class TraceTest {
    private val id = "req_0123456789abcdef"

    @Test
    fun aTraceNamesTheFirstPointThatFailed() {
        var now = 1000L
        val tracer = Tracer(clock = { now++ })
        tracer.start(id, "Check-out")
        tracer.mark(id, Point.SCREEN, true)
        tracer.mark(id, Point.PHONE_STORE, true)
        tracer.mark(id, Point.NETWORK, true, tookMs = 420)
        tracer.mark(id, Point.GATEWAY, true)
        val trace = tracer.mark(id, Point.SERVER, false, "Refused: outside the site", detail = "distance_m=180")!!
        assertEquals(Point.SERVER, trace.fault?.point)
        assertFalse(trace.complete)
        assertEquals(5, trace.marks.size)
    }

    @Test
    fun completeOnlyWhenSavedAndReadBackTheSame() {
        val tracer = Tracer()
        tracer.start(id, "Check-in")
        tracer.mark(id, Point.SERVER, true)
        assertFalse(tracer.find(id)!!.complete)
        tracer.mark(id, Point.READ_BACK, true, "matches")
        assertTrue(tracer.find(id)!!.complete)
        tracer.mark(id, Point.DISPLAY, false, "differs in check_in_time")
        assertFalse(tracer.find(id)!!.complete)
    }

    @Test
    fun theReportLeavesValuesOutUnlessAsked() {
        val tracer = Tracer()
        tracer.start(id, "Check-out")
        tracer.mark(id, Point.NETWORK, true, tookMs = 420)
        tracer.mark(id, Point.SERVER, false, "Refused: outside the site", detail = "distance_m=180")
        val safe = tracer.find(id)!!.report()
        assertTrue(safe.contains("3. Network: ok (420 ms)"))
        assertTrue(safe.contains("5. Server function: FAILED - Refused: outside the site"))
        assertTrue(safe.contains("6. Read-back: not reached"))
        assertFalse(safe.contains("distance_m"))
        assertTrue(tracer.find(id)!!.report(withValues = true).contains("distance_m=180"))
    }

    @Test
    fun keepsOnlyTheNewestAndWipesOnSignOut() {
        val tracer = Tracer(limit = 2)
        val ids = listOf("a", "b", "c").map { it.repeat(16) }
        ids.forEach { tracer.start(it, "Action") }
        assertEquals(listOf(ids[2], ids[1]), tracer.all().map { it.id })
        assertNull(tracer.mark(ids[0], Point.SCREEN, true)) // pushed out: the mark is dropped, nothing crashes
        tracer.clear()
        assertTrue(tracer.all().isEmpty())
    }

    @Test
    fun refusesATrackingNumberTheServerWouldRefuse() {
        val tracer = Tracer()
        for (bad in listOf("short", "has space 0123456789", "x".repeat(81))) {
            assertThrows(IllegalArgumentException::class.java) { tracer.start(bad, "Action") }
        }
    }

    @Test
    fun marksFromManyThreadsAreAllKept() {
        val tracer = Tracer()
        tracer.start(id, "Busy")
        val threads = List(8) { Thread { repeat(100) { tracer.mark(id, Point.NETWORK, true) } } }
        threads.forEach(Thread::start)
        threads.forEach(Thread::join)
        assertEquals(800, tracer.find(id)!!.marks.size)
    }
}

class ReadBackTest {
    private val kinds = mapOf(
        "site" to ReadBack.Kind.TEXT,
        "amount" to ReadBack.Kind.DECIMAL,
        "check_in_time" to ReadBack.Kind.DATETIME,
        "revision" to ReadBack.Kind.WHOLE,
        "captured_offline" to ReadBack.Kind.YES_NO,
    )
    private val sent = mapOf("site" to "SITE-0001", "amount" to "150000.5", "check_in_time" to "2026-11-26 08:57:00", "revision" to "1", "captured_offline" to "0")

    @Test
    fun sameValuesInDifferentWritingMatch() {
        val stored = mapOf("site" to "SITE-0001", "amount" to "150000.500000", "check_in_time" to "2026-11-26 08:57:00.000000", "revision" to "1", "captured_offline" to "false", "owner" to "added by the server")
        assertTrue(ReadBack.differences(sent, stored, kinds).isEmpty())
        assertEquals("matches", ReadBack.note(emptyList()))
    }

    @Test
    fun aTimeZoneShiftIsNamedAsOne() {
        val stored = sent + ("check_in_time" to "2026-11-26 03:27:00")
        val found = ReadBack.differences(sent, stored, kinds).single()
        assertEquals("check_in_time", found.field)
        assertEquals("time shifted by -5.5 hours: a time zone fault", found.why)
    }

    @Test
    fun wrongMissingAndUnreadableValuesAreAllCaught() {
        val stored = mapOf("site" to "SITE-0002", "amount" to "150000.49", "check_in_time" to "yesterday", "captured_offline" to "0")
        val found = ReadBack.differences(sent, stored, kinds).associateBy { it.field }
        assertEquals(setOf("site", "amount", "check_in_time", "revision"), found.keys)
        assertEquals("missing on the server", found.getValue("revision").why)
        assertEquals("cannot be read as datetime", found.getValue("check_in_time").why)
    }

    @Test
    fun theNoteNamesFieldsButNeverValues() {
        val note = ReadBack.note(ReadBack.differences(sent, sent + ("site" to "SITE-0002"), kinds))
        assertEquals("differs in site (different value)", note)
        assertFalse(note.contains("SITE-0002"))
    }
}
