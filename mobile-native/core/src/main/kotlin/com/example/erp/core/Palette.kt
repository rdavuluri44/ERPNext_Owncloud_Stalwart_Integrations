package com.example.erp.core

import kotlin.math.pow

/**
 * Every colour the app uses, by its job, once per look. Colours are 0xRRGGBB numbers so this file has no Android
 * in it and the contrast of every pair is checked by a unit test (PaletteTest): a colour changed badly fails the build.
 */
data class Palette(
    val name: String,
    /** The page. */
    val ground: Long,
    /** Cards and panels on the page. */
    val surface: Long,
    val text: Long,
    /** Secondary text. Still fully readable. */
    val muted: Long,
    /** The one accent: main buttons, the selected place. */
    val accent: Long,
    /** Text on the accent. */
    val onAccent: Long,
    /** Borders and dividers. */
    val line: Long,
    /** A quiet highlight behind selected or grouped content. */
    val soft: Long,
    val ok: Long,
    val warn: Long,
    val bad: Long,
    /** Quiet tints behind a status pill or notice of that kind. */
    val okSoft: Long,
    val warnSoft: Long,
    val badSoft: Long,
) {
    /** The colours that carry text or a status mark. */
    val inks: Map<String, Long> get() = mapOf("text" to text, "muted" to muted, "accent" to accent, "ok" to ok, "warn" to warn, "bad" to bad)
}

object Palettes {
    /** Follows the phone in day mode: a cool white page with white cards. Sunlight-first: text contrast of 7:1 or more. */
    val LIGHT = Palette("light", 0xF4F7FB, 0xFFFFFF, 0x111827, 0x374151, 0x0B4F9E, 0xFFFFFF, 0x6B7280, 0xE8F0FA, 0x0E5A2C, 0x703C00, 0x9B1717, 0xD9F2E1, 0xFDECCB, 0xFDEBEB)

    /** Follows the phone in night mode: a near-black ground and softened colours, so it does not glare. */
    val DARK = Palette("dark", 0x0F141A, 0x18212B, 0xE8EEF3, 0xB4C0CC, 0x8FC1FF, 0x06223F, 0x7C8A99, 0x1E3350, 0x7FD9A0, 0xF3BE72, 0xFFA3A3, 0x143524, 0x3A2A10, 0x40191C)

    /** Outdoor mode, for direct sun: always light, the strongest contrast, heavy lines, no tints behind a status. */
    val OUTDOOR = Palette("outdoor", 0xFFFFFF, 0xFFFFFF, 0x000000, 0x1F2937, 0x08366E, 0xFFFFFF, 0x111827, 0xDCE9FA, 0x0A4521, 0x5C3200, 0x7A0F0F, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF)

    val all = listOf(LIGHT, DARK, OUTDOOR)

    /** Outdoor wins over the phone's day or night mode. */
    fun pick(phoneIsDark: Boolean, outdoor: Boolean): Palette = if (outdoor) OUTDOOR else if (phoneIsDark) DARK else LIGHT
}

object Contrast {
    private fun channel(value: Long): Double {
        val c = value / 255.0
        return if (c <= 0.03928) c / 12.92 else ((c + 0.055) / 1.055).pow(2.4)
    }

    private fun luminance(rgb: Long): Double =
        0.2126 * channel(rgb shr 16 and 0xFF) + 0.7152 * channel(rgb shr 8 and 0xFF) + 0.0722 * channel(rgb and 0xFF)

    /** The WCAG contrast ratio of two colours, from 1 (the same) to 21 (black on white). */
    fun ratio(a: Long, b: Long): Double {
        val (light, dark) = listOf(luminance(a), luminance(b)).sortedDescending()
        return (light + 0.05) / (dark + 0.05)
    }
}

/**
 * Decides Outdoor mode from the phone's light sensor. Two thresholds, so a cloud or a hand over the sensor does
 * not make the screen flicker between looks: on above [on] lux, off again only below [off] lux.
 * The person's own switch always wins: with [automatic] off, only [forced] counts.
 */
class OutdoorSwitch(private val on: Float = 8000f, private val off: Float = 2000f) {
    init {
        require(off < on)
    }

    var bright: Boolean = false
        private set

    /** Feeds one sensor reading; returns whether it is bright now. */
    fun reading(lux: Float): Boolean {
        if (lux >= on) bright = true else if (lux <= off) bright = false
        return bright
    }

    fun outdoor(automatic: Boolean, forced: Boolean): Boolean = forced || (automatic && bright)
}
