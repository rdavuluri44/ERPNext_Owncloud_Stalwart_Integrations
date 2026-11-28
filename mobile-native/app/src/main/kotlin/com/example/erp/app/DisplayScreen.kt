package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.Palette
import com.example.erp.core.Palettes

/**
 * Display: the look follows the phone (day or night) and bright light (Outdoor) by itself; the person can turn
 * the automatic part off or switch Outdoor on by hand. Font size is the phone's own setting, not ours.
 */
@Composable
fun DisplayScreen(
    palette: Palette,
    hasLightSensor: Boolean,
    automatic: Boolean,
    forced: Boolean,
    lux: Float?,
    onAutomatic: (Boolean) -> Unit,
    onForced: (Boolean) -> Unit,
) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Display", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            RowCard(
                R.drawable.ic_display,
                "Showing now",
                when (palette) {
                    Palettes.OUTDOOR -> "Outdoor: strongest contrast, larger text"
                    Palettes.DARK -> "Dark: follows your phone's night mode"
                    else -> "Light: follows your phone's day mode"
                },
            )
            Panel {
                SwitchRow(
                    "Outdoor mode in bright light",
                    if (hasLightSensor) "Switches by itself in direct sun and back indoors." else "This phone has no light sensor, so this cannot work here. Use the switch below.",
                    checked = automatic && hasLightSensor,
                    onChange = { if (hasLightSensor) onAutomatic(it) },
                )
                SwitchRow("Outdoor mode now", "Keeps Outdoor mode on until you turn it off.", checked = forced, onChange = onForced)
            }
            Notice(StatusKind.INFO, "Text size and bold text follow your phone: Settings, Display, Font size. Day and night follow your phone too.")
            if (lux != null) Text("Light sensor: ${lux.toInt()} lux (test builds)", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
    }
}
