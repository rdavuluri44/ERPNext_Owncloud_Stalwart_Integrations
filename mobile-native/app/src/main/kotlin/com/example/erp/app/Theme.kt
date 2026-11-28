package com.example.erp.app

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.erp.core.Palette
import com.example.erp.core.Palettes

private val LocalPalette = staticCompositionLocalOf { Palettes.LIGHT }

private val Long.color: Color get() = Color(0xFF000000L or this)

/**
 * The colours of the look in use. Screens name a colour only by its job, so they follow the phone's day or night
 * mode and Outdoor mode without knowing about them. The values and their contrast are tested in the rules module.
 * Status is always a mark and a word as well as a colour (see [Status]).
 */
object Look {
    val Ground: Color @Composable get() = LocalPalette.current.ground.color
    val Surface: Color @Composable get() = LocalPalette.current.surface.color
    val Ink: Color @Composable get() = LocalPalette.current.text.color
    val Muted: Color @Composable get() = LocalPalette.current.muted.color
    val Accent: Color @Composable get() = LocalPalette.current.accent.color
    val Line: Color @Composable get() = LocalPalette.current.line.color
    val Soft: Color @Composable get() = LocalPalette.current.soft.color
    val Ok: Color @Composable get() = LocalPalette.current.ok.color
    val Warn: Color @Composable get() = LocalPalette.current.warn.color
    val Bad: Color @Composable get() = LocalPalette.current.bad.color
    val OkSoft: Color @Composable get() = LocalPalette.current.okSoft.color
    val WarnSoft: Color @Composable get() = LocalPalette.current.warnSoft.color
    val BadSoft: Color @Composable get() = LocalPalette.current.badSoft.color

    /** Thin lines; heavy ones in Outdoor mode. */
    val LineWidth: Dp @Composable get() = if (LocalPalette.current == Palettes.OUTDOOR) 2.dp else 1.dp
    val Corner = 16.dp

    /** Touch targets are at least this tall (gloves, one hand). */
    val Touch = 56.dp
    val Gap = 16.dp
}

/** Sizes in sp, so every text also follows the font size the person set on the phone. Outdoor is a step larger and heavier. */
private fun type(outdoor: Boolean): Typography {
    val more = if (outdoor) 2 else 0
    val body = if (outdoor) FontWeight.Medium else FontWeight.Normal
    return Typography(
        headlineMedium = TextStyle(fontSize = (30 + more).sp, lineHeight = (36 + more).sp, fontWeight = FontWeight.ExtraBold),
        titleMedium = TextStyle(fontSize = (19 + more).sp, lineHeight = (26 + more).sp, fontWeight = FontWeight.SemiBold),
        bodyLarge = TextStyle(fontSize = (17 + more).sp, lineHeight = (25 + more).sp, fontWeight = body),
        bodyMedium = TextStyle(fontSize = (15 + more).sp, lineHeight = (22 + more).sp, fontWeight = body),
        labelLarge = TextStyle(fontSize = (18 + more).sp, lineHeight = (24 + more).sp, fontWeight = FontWeight.SemiBold),
        labelMedium = TextStyle(fontSize = (15 + more).sp, lineHeight = (20 + more).sp, fontWeight = FontWeight.SemiBold),
    )
}

/** Wallpaper colours are deliberately not used: a status colour must mean the same, with the same contrast, on every phone. */
@Composable
fun ErpTheme(palette: Palette, content: @Composable () -> Unit) {
    val scheme = (if (palette == Palettes.DARK) darkColorScheme() else lightColorScheme()).copy(
        primary = palette.accent.color,
        onPrimary = palette.onAccent.color,
        secondaryContainer = palette.soft.color,
        onSecondaryContainer = palette.text.color,
        background = palette.ground.color,
        onBackground = palette.text.color,
        surface = palette.ground.color,
        onSurface = palette.text.color,
        surfaceVariant = palette.surface.color,
        onSurfaceVariant = palette.muted.color,
        surfaceContainer = palette.surface.color,
        outline = palette.line.color,
        error = palette.bad.color,
        onError = palette.ground.color,
    )
    CompositionLocalProvider(LocalPalette provides palette) {
        MaterialTheme(colorScheme = scheme, typography = type(palette == Palettes.OUTDOOR), content = content)
    }
}
