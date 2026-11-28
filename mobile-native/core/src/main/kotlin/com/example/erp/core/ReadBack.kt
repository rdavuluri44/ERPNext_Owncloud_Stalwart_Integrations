package com.example.erp.core

import java.math.BigDecimal
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

/**
 * Read-back: after a save, the app reads the record again and compares it field by field with what it sent.
 * Each field is compared by its kind, so "150000.0" and "150000.00" are the same money, and a time that came back
 * shifted by the time zone is caught.
 */
object ReadBack {
    enum class Kind { TEXT, WHOLE, DECIMAL, DATETIME, YES_NO }

    /** One field that came back different. [sent] and [stored] are values: for test builds only. */
    data class Difference(val field: String, val sent: String?, val stored: String?, val why: String)

    private val SERVER_TIME: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

    private fun time(text: String): LocalDateTime = LocalDateTime.parse(text.trim().substringBefore('.'), SERVER_TIME)

    private fun same(kind: Kind, sent: String, stored: String): Boolean = when (kind) {
        Kind.TEXT -> sent == stored
        Kind.WHOLE -> sent.trim().toLong() == stored.trim().toLong()
        Kind.DECIMAL -> BigDecimal(sent.trim()).compareTo(BigDecimal(stored.trim())) == 0
        Kind.DATETIME -> time(sent) == time(stored)
        Kind.YES_NO -> yes(sent) == yes(stored)
    }

    private fun yes(text: String): Boolean = when (text.trim().lowercase()) {
        "1", "true", "yes" -> true
        "0", "false", "no", "" -> false
        else -> throw IllegalArgumentException("not yes or no: $text")
    }

    /**
     * Compares every field named in [kinds]. A field missing on either side is a difference; so is a value that
     * cannot be read as its kind. Fields the server adds on its own (not in [kinds]) are ignored.
     */
    fun differences(sent: Map<String, String?>, stored: Map<String, String?>, kinds: Map<String, Kind>): List<Difference> =
        kinds.mapNotNull { (field, kind) ->
            val a = sent[field]
            val b = stored[field]
            when {
                a == null && b == null -> null
                a == null || b == null -> Difference(field, a, b, if (b == null) "missing on the server" else "not sent, but stored")
                else -> try {
                    if (same(kind, a, b)) null else Difference(field, a, b, explain(kind, a, b))
                } catch (e: RuntimeException) {
                    Difference(field, a, b, "cannot be read as ${kind.name.lowercase().replace('_', ' ')}")
                }
            }
        }

    private fun explain(kind: Kind, sent: String, stored: String): String {
        if (kind == Kind.DATETIME) {
            val minutes = ChronoUnit.MINUTES.between(time(sent), time(stored))
            // Whole and half hours are how time zones differ; this is the usual cause.
            if (minutes != 0L && minutes % 30 == 0L) return "time shifted by ${minutes / 60.0} hours: a time zone fault"
        }
        return "different value"
    }

    /** The safe sentence for a trace note: field names only, no values. */
    fun note(differences: List<Difference>): String =
        if (differences.isEmpty()) "matches" else "differs in " + differences.joinToString { "${it.field} (${it.why})" }
}
