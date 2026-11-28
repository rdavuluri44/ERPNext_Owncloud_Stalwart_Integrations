package com.example.erp.core

import java.math.BigDecimal
import java.math.RoundingMode

/** Money is always exact decimals, never floating point, and is shown the Indian way: 1,50,000.00. */
object Money {
    /** Reads a server amount. Refuses anything that is not a plain decimal number, so a wrong value is never shown as money. */
    fun parse(text: String): BigDecimal {
        require(Regex("-?\\d+(\\.\\d+)?").matches(text.trim())) { "not an amount: $text" }
        return BigDecimal(text.trim())
    }

    /**
     * Indian grouping: the last three digits, then groups of two (12,34,56,789.00).
     * More decimals than [decimals] are rounded half-up for display only; arithmetic keeps the exact value.
     */
    fun indian(amount: BigDecimal, decimals: Int = 2): String {
        require(decimals in 0..6)
        val shown = amount.setScale(decimals, RoundingMode.HALF_UP)
        val digits = shown.abs().toPlainString()
        val whole = digits.substringBefore('.')
        val fraction = if (decimals > 0) "." + digits.substringAfter('.') else ""
        val grouped = if (whole.length <= 3) whole else
            whole.dropLast(3).reversed().chunked(2).joinToString(",").reversed() + "," + whole.takeLast(3)
        return (if (shown.signum() < 0) "-" else "") + grouped + fraction
    }

    /** Adds amounts exactly. */
    fun total(amounts: Iterable<BigDecimal>): BigDecimal = amounts.fold(BigDecimal.ZERO, BigDecimal::add)
}
