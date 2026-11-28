package com.example.erp.app

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** The shared building blocks. Screens are made only from these, so every screen keeps the same rules. */

enum class StatusKind(val mark: String, val word: String) {
    OK("✓", "OK"),
    WARN("!", "Check"),
    BAD("✕", "Failed"),
    NONE("–", "Not reached"),
    INFO("i", "Note"),
    WAIT("…", "Waiting"),
}

@Composable
private fun StatusKind.color(): Color = when (this) {
    StatusKind.OK -> Look.Ok
    StatusKind.WARN, StatusKind.WAIT -> Look.Warn
    StatusKind.BAD -> Look.Bad
    StatusKind.NONE -> Look.Muted
    StatusKind.INFO -> Look.Accent
}

/** The quiet colour behind a pill or notice of this kind. */
@Composable
private fun StatusKind.tint(): Color = when (this) {
    StatusKind.OK -> Look.OkSoft
    StatusKind.WARN, StatusKind.WAIT -> Look.WarnSoft
    StatusKind.BAD -> Look.BadSoft
    StatusKind.NONE, StatusKind.INFO -> Look.Soft
}

/**
 * A plain status line: a mark, the text, and colour. It is never tappable, so its text must never name an
 * action ("open", "tap", "see"). A message that needs the person to act is an [ActionMessage].
 */
@Composable
fun Status(kind: StatusKind, text: String, modifier: Modifier = Modifier) {
    Row(modifier, horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
        Text(kind.mark, color = kind.color(), fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyLarge)
        Text(text, color = kind.color(), fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyLarge)
    }
}

/** A short status word in a rounded tint, always with its mark, so it never depends on colour alone. */
@Composable
fun Pill(kind: StatusKind, word: String, modifier: Modifier = Modifier) {
    Surface(modifier, shape = RoundedCornerShape(50), color = kind.tint(), border = BorderStroke(Look.LineWidth, kind.color()), contentColor = kind.color()) {
        Row(Modifier.padding(horizontal = 10.dp, vertical = 4.dp), horizontalArrangement = Arrangement.spacedBy(5.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(kind.mark, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.labelMedium)
            Text(word, style = MaterialTheme.typography.labelMedium)
        }
    }
}

/**
 * A tinted card that tells the person something: amber for "do this first", blue for "good to know", red for a
 * fault. Like [Status] it is never tappable, so its text must never name a tap.
 */
@Composable
fun Notice(kind: StatusKind, text: String, modifier: Modifier = Modifier) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(Look.Corner), color = kind.tint(), border = BorderStroke(Look.LineWidth, kind.color()), contentColor = Look.Ink) {
        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
            Text(kind.mark, color = kind.color(), fontWeight = FontWeight.Bold, style = MaterialTheme.typography.bodyLarge)
            Text(text, fontWeight = FontWeight.Medium, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

/**
 * The row card: an icon in a tinted square, a title on its own line and under it one line of text with, when
 * the card has a state, a pill at the right. With large text on the phone the pill moves under the text, so
 * nothing is squeezed. With [onClick] the whole card is one tap target.
 */
@Composable
fun RowCard(
    icon: Int,
    title: String,
    text: String,
    modifier: Modifier = Modifier,
    pill: Pair<StatusKind, String>? = null,
    selected: Boolean = false,
    onClick: (() -> Unit)? = null,
) {
    val pillBelow = LocalDensity.current.fontScale > 1.3f
    val shape = RoundedCornerShape(Look.Corner)
    val border = BorderStroke(if (selected) 2.dp else Look.LineWidth, if (selected) Look.Accent else Look.Line)
    val color = if (selected) Look.Soft else Look.Surface
    val inside = @Composable {
        Row(Modifier.padding(14.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(46.dp).background(if (selected) Look.Surface else Look.Soft, RoundedCornerShape(13.dp)), contentAlignment = Alignment.Center) {
                Icon(painterResource(icon), contentDescription = null, tint = Look.Accent)
            }
            // The title keeps the card's full width; the pill shares the smaller second line.
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                if (pill == null || pillBelow) {
                    if (text.isNotEmpty()) Text(text, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                    if (pill != null) Pill(pill.first, pill.second)
                } else {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                        Text(text, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
                        Pill(pill.first, pill.second)
                    }
                }
            }
        }
    }
    val size = modifier.fillMaxWidth().heightIn(min = Look.Touch)
    if (onClick != null) Surface(onClick, size, shape = shape, border = border, color = color, contentColor = Look.Ink, content = inside)
    else Surface(size, shape = shape, border = border, color = color, contentColor = Look.Ink, content = inside)
}

/**
 * A message the person must act on. It cannot be built without the action: [onAct] is required, so a message
 * that says "open" always opens something (the "no dead ends" rule).
 */
@Composable
fun ActionMessage(kind: StatusKind, text: String, actionLabel: String, onAct: () -> Unit, modifier: Modifier = Modifier) {
    Panel(modifier) {
        Status(kind, text)
        MainButton(actionLabel, onAct)
    }
}

@Composable
fun Panel(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Surface(modifier.fillMaxWidth(), shape = RoundedCornerShape(Look.Corner), border = BorderStroke(Look.LineWidth, Look.Line), color = Look.Surface, contentColor = Look.Ink) {
        Column(Modifier.padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
    }
}

/** The one main button of a screen. [forward] adds the arrow of a step that leads on. */
@Composable
fun MainButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier, forward: Boolean = false) {
    Button(onClick, modifier.fillMaxWidth().heightIn(min = Look.Touch), shape = RoundedCornerShape(Look.Corner)) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        if (forward) Icon(painterResource(R.drawable.ic_forward), contentDescription = null, modifier = Modifier.padding(start = 10.dp))
    }
}

/** A second, quieter button. [danger] is for an action that takes something away; it never sits beside the main button. */
@Composable
fun OutlineButton(label: String, onClick: () -> Unit, modifier: Modifier = Modifier, danger: Boolean = false) {
    val ink = if (danger) Look.Bad else Look.Accent
    OutlinedButton(
        onClick,
        modifier.fillMaxWidth().heightIn(min = Look.Touch),
        shape = RoundedCornerShape(Look.Corner),
        border = BorderStroke(2.dp, ink),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = ink),
    ) {
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

/**
 * The bar at the top of a step: back at the left, the step chip in the middle, help at the right, always in the
 * same places. A part is drawn only when it has somewhere to lead.
 */
@Composable
fun TopBar(modifier: Modifier = Modifier, step: Pair<Int, Int>? = null, onBack: (() -> Unit)? = null, onHelp: (() -> Unit)? = null) {
    Row(modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(48.dp)) {
            if (onBack != null) IconButton(onBack, Modifier.size(48.dp)) { Icon(painterResource(R.drawable.ic_back), contentDescription = "Back", tint = Look.Ink) }
        }
        Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
            if (step != null) {
                Surface(shape = RoundedCornerShape(50), color = Look.Soft, contentColor = Look.Ink) {
                    Text("STEP ${step.first} OF ${step.second}", Modifier.padding(horizontal = 14.dp, vertical = 6.dp), style = MaterialTheme.typography.labelMedium)
                }
            }
        }
        Box(Modifier.size(48.dp)) {
            if (onHelp != null) IconButton(onHelp, Modifier.size(48.dp)) { Icon(painterResource(R.drawable.ic_help), contentDescription = "Help", tint = Look.Ink) }
        }
    }
}

/** The small label in capitals above a title. */
@Composable
fun Eyebrow(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), modifier, color = Look.Accent, style = MaterialTheme.typography.labelMedium, letterSpacing = 1.sp)
}

/** The large fingerprint mark in soft rings. A picture only: the phone shows its own fingerprint box. */
@Composable
fun FingerprintMark(modifier: Modifier = Modifier) {
    Box(modifier.size(196.dp).background(Look.Soft.copy(alpha = 0.45f), CircleShape), contentAlignment = Alignment.Center) {
        Box(Modifier.size(150.dp).background(Look.Soft, CircleShape), contentAlignment = Alignment.Center) {
            Icon(painterResource(R.drawable.ic_fingerprint), contentDescription = null, modifier = Modifier.size(92.dp), tint = Look.Accent)
        }
    }
}

/** A setting with its explanation. The whole row is the switch, so it is easy to hit and is read out as one thing. */
@Composable
fun SwitchRow(title: String, explanation: String, checked: Boolean, onChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier.fillMaxWidth().heightIn(min = Look.Touch).toggleable(checked, role = Role.Switch, onValueChange = onChange),
        horizontalArrangement = Arrangement.spacedBy(Look.Gap),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = Look.Ink)
            Text(explanation, style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
        Switch(checked, onCheckedChange = null)
    }
}
