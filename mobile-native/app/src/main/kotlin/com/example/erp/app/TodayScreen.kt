package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import com.example.erp.core.Card
import com.example.erp.core.CardKind
import com.example.erp.core.Format
import com.example.erp.core.Lead
import com.example.erp.core.Today
import com.example.erp.core.TodayFacts
import com.example.erp.core.Tone
import java.time.LocalDateTime

private fun kind(tone: Tone) = when (tone) {
    Tone.GOOD -> StatusKind.OK
    Tone.CARE -> StatusKind.WARN
    Tone.WRONG -> StatusKind.BAD
    Tone.PLAIN -> StatusKind.NONE
    Tone.WAITING -> StatusKind.WAIT
}

private fun icon(kind: CardKind) = when (kind) {
    CardKind.MY_ATTENDANCE -> R.drawable.ic_fingerprint
    CardKind.MY_TEAM, CardKind.FACES_MISSING, CardKind.FACE_QUEUE -> R.drawable.ic_person
    CardKind.RETURNED -> R.drawable.ic_back
    CardKind.WAITING_TO_SEND -> R.drawable.ic_offline
    CardKind.TO_VERIFY, CardKind.TO_APPROVE -> R.drawable.ic_inbox
    CardKind.ACCESS_REQUESTS -> R.drawable.ic_key
    CardKind.MY_SITES, CardKind.MY_REQUESTS -> R.drawable.ic_today
    CardKind.CHAT -> R.drawable.ic_chat
    CardKind.MAIL -> R.drawable.ic_mail
}

/**
 * Today, the home screen. What is shown is decided by [Today.cards] from what the server says exists for this
 * person. A card is one tap to one place; a card whose screen is not built yet is shown but is not a button.
 * Phone: one column. Tablet: two.
 *
 * @param who the person's name and site, shown under the date.
 */
@Composable
fun TodayScreen(who: String, facts: TodayFacts, now: LocalDateTime, onOpen: (Lead) -> Unit, onRefresh: () -> Unit) {
    val cards = Today.cards(facts, now)
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 840.dp
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Today", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
                Text("${Format.date(now.toLocalDate())} · $who", style = MaterialTheme.typography.bodyLarge, color = Look.Muted)
                val (tone, line) = Today.status(facts, now)
                Status(kind(tone), line)
                for (warning in Today.warnings(facts)) Notice(StatusKind.WARN, warning)
                Today.failedLine(facts)?.let { ActionMessage(StatusKind.BAD, it, "Try again", onRefresh) }
                if (cards.isEmpty()) Today.emptyLine(facts)?.let { Notice(StatusKind.OK, it) }
            }
            if (wide) {
                Row(horizontalArrangement = Arrangement.spacedBy(Look.Gap)) {
                    for (half in 0..1) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                            cards.filterIndexed { index, _ -> index % 2 == half }.forEach { TodayCard(it, onOpen) }
                        }
                    }
                }
            } else {
                for (card in cards) TodayCard(card, onOpen)
            }
        }
    }
}

@Composable
private fun TodayCard(card: Card, onOpen: (Lead) -> Unit) {
    val lead = card.lead
    RowCard(icon(card.kind), card.title, card.line, pill = kind(card.tone) to card.word, onClick = if (lead != null) ({ onOpen(lead) }) else null)
}
