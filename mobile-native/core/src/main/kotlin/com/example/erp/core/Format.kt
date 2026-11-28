package com.example.erp.core

import java.time.Duration
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * The app's fixed ways of writing dates and waiting times, the same on every phone whatever its language or
 * region setting, so the app and the web always read the same and a date is never ambiguous (no 11/12).
 */
object Format {
    private val DAY: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.ENGLISH)
    private val DAY_SHORT: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM", Locale.ENGLISH)
    private val TIME: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm", Locale.ENGLISH)

    /** 26 Nov 2026 */
    fun date(day: LocalDate): String = DAY.format(day)

    /** "Today, 08:57", "Yesterday, 17:02", "26 Nov, 08:57", and with the year when it is not this year. */
    fun dateTime(moment: LocalDateTime, now: LocalDateTime): String {
        val day = moment.toLocalDate()
        val prefix = when {
            day == now.toLocalDate() -> "Today"
            day == now.toLocalDate().minusDays(1) -> "Yesterday"
            day.year == now.year -> DAY_SHORT.format(day)
            else -> DAY.format(day)
        }
        return "$prefix, ${TIME.format(moment)}"
    }

    /**
     * How long something has waited, counted from when it started waiting: "just now", "12 min", "3 h", "2 days".
     * A start in the future (a phone clock that is wrong) reads "just now" rather than a negative time.
     */
    fun waiting(since: LocalDateTime, now: LocalDateTime): String {
        val minutes = Duration.between(since, now).toMinutes()
        return when {
            minutes < 1 -> "just now"
            minutes < 60 -> "$minutes min"
            minutes < 24 * 60 -> "${minutes / 60} h"
            minutes < 48 * 60 -> "1 day"
            else -> "${minutes / (24 * 60)} days"
        }
    }

    /** Cuts long text at a word where it can, and always shows that it was cut. */
    fun short(text: String, max: Int): String {
        require(max >= 2)
        val clean = text.trim()
        if (clean.length <= max) return clean
        val cut = clean.take(max - 1)
        val atWord = cut.substringBeforeLast(' ', cut)
        return (if (atWord.length >= max / 2) atWord else cut).trimEnd() + "…"
    }
}
