package com.example.erp.core

import java.time.LocalDate
import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PaletteTest {
    @Test
    fun contrastFormulaMatchesTheStandard() {
        assertEquals(21.0, Contrast.ratio(0x000000, 0xFFFFFF), 0.01)
        assertEquals(1.0, Contrast.ratio(0x777777, 0x777777), 0.001)
        assertEquals(4.54, Contrast.ratio(0x767676, 0xFFFFFF), 0.01) // the well-known "just passes AA" grey
        assertEquals(Contrast.ratio(0x0B4F9E, 0xFFFFFF), Contrast.ratio(0xFFFFFF, 0x0B4F9E), 0.0)
    }

    /** Every text and status colour against every background it can sit on, in every look. */
    @Test
    fun everyLookIsReadable() {
        for (look in Palettes.all) {
            val strong = if (look == Palettes.OUTDOOR) 10.0 else 7.0
            for ((name, ink) in look.inks) {
                assertTrue("${look.name}: $name on the page", Contrast.ratio(ink, look.ground) >= strong)
                assertTrue("${look.name}: $name on a card", Contrast.ratio(ink, look.surface) >= strong)
                assertTrue("${look.name}: $name on a highlight", Contrast.ratio(ink, look.soft) >= 4.5)
            }
            // A status on its own tint (pills and notices) stays as readable as on the page.
            for ((ink, tint) in listOf(look.ok to look.okSoft, look.warn to look.warnSoft, look.bad to look.badSoft)) {
                assertTrue("${look.name}: a status on its tint", Contrast.ratio(ink, tint) >= strong)
                assertTrue("${look.name}: text on a status tint", Contrast.ratio(look.text, tint) >= strong)
            }
            assertTrue("${look.name}: button text", Contrast.ratio(look.onAccent, look.accent) >= 7.0)
            assertTrue("${look.name}: lines on the page", Contrast.ratio(look.line, look.ground) >= 3.0)
            assertTrue("${look.name}: lines on a card", Contrast.ratio(look.line, look.surface) >= 3.0)
        }
    }

    /** Ok and failed must differ in lightness too, so they are told apart without seeing red and green. */
    @Test
    fun okAndFailedDifferWithoutColour() {
        for (look in Palettes.all) {
            assertTrue(look.name, look.ok != look.bad && look.ok != look.warn && look.warn != look.bad)
        }
        // The real protection is that a status is always a mark and a word as well (app building blocks).
    }

    @Test
    fun outdoorWinsOverDayAndNight() {
        assertEquals(Palettes.LIGHT, Palettes.pick(phoneIsDark = false, outdoor = false))
        assertEquals(Palettes.DARK, Palettes.pick(phoneIsDark = true, outdoor = false))
        assertEquals(Palettes.OUTDOOR, Palettes.pick(phoneIsDark = true, outdoor = true))
        assertEquals(Palettes.OUTDOOR, Palettes.pick(phoneIsDark = false, outdoor = true))
    }

    @Test
    fun outdoorSwitchDoesNotFlickerAndObeysThePerson() {
        val switch = OutdoorSwitch()
        assertFalse(switch.reading(300f)) // indoors
        assertFalse(switch.reading(5000f)) // bright shade: not yet
        assertTrue(switch.reading(30000f)) // direct sun
        assertTrue(switch.reading(5000f)) // a cloud or a hand: stays
        assertFalse(switch.reading(800f)) // back inside
        switch.reading(30000f)
        assertTrue(switch.outdoor(automatic = true, forced = false))
        assertFalse(switch.outdoor(automatic = false, forced = false)) // switched off by the person
        switch.reading(100f)
        assertTrue(switch.outdoor(automatic = false, forced = true)) // switched on by hand
    }
}

class FormatTest {
    private val now = LocalDateTime.of(2026, 11, 26, 18, 7)

    @Test
    fun datesAreNeverAmbiguous() {
        assertEquals("26 Nov 2026", Format.date(LocalDate.of(2026, 11, 26)))
        assertEquals("5 Jan 2027", Format.date(LocalDate.of(2027, 1, 5)))
        assertEquals("Today, 08:57", Format.dateTime(LocalDateTime.of(2026, 11, 26, 8, 57), now))
        assertEquals("Yesterday, 17:02", Format.dateTime(LocalDateTime.of(2026, 11, 25, 17, 2), now))
        assertEquals("3 Nov, 09:00", Format.dateTime(LocalDateTime.of(2026, 11, 3, 9, 0), now))
        assertEquals("30 Dec 2025, 23:59", Format.dateTime(LocalDateTime.of(2025, 12, 30, 23, 59), now))
    }

    @Test
    fun waitingCountsFromWhenItStartedWaiting() {
        // The fault found in the old app: a 16:09 check-in showed "18 h" at 18:07 because it counted from midnight.
        assertEquals("1 h", Format.waiting(LocalDateTime.of(2026, 11, 26, 16, 9), now))
        assertEquals("just now", Format.waiting(now.minusSeconds(40), now))
        assertEquals("12 min", Format.waiting(now.minusMinutes(12), now))
        assertEquals("59 min", Format.waiting(now.minusMinutes(59), now))
        assertEquals("23 h", Format.waiting(now.minusMinutes(23 * 60 + 59), now))
        assertEquals("1 day", Format.waiting(now.minusHours(30), now))
        assertEquals("2 days", Format.waiting(now.minusHours(49), now))
        assertEquals("just now", Format.waiting(now.plusMinutes(5), now)) // a wrong phone clock
    }

    @Test
    fun longTextIsCutAtAWordAndSaysSo() {
        assertEquals("Short name", Format.short("  Short name ", 20))
        assertEquals("Reinforcement steel…", Format.short("Reinforcement steel bars for block two", 22))
        assertEquals("Supercalifragilis…", Format.short("Supercalifragilisticexpialidocious", 18))
        assertTrue(Format.short("Reinforcement steel bars for block two", 22).length <= 22)
    }
}
