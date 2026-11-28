package com.example.erp.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.erp.core.AccessRequest
import com.example.erp.core.Approval
import com.example.erp.core.KeyLoss
import com.example.erp.core.KeyState
import com.example.erp.core.welcomeFor
import java.time.LocalDateTime

/**
 * Test builds only: the Welcome screens against a stand-in, because the server part for access requests does not
 * exist yet. Every situation can be chosen, and every button leads to the situation it would lead to for real.
 * No key is made and nothing is sent. Remove with the real onboarding (cleanup list).
 */
enum class Situation(val label: String) {
    NEW("new here"),
    WAITING("waiting, manager"),
    HALF("waiting, admin"),
    OFFLINE("waiting, offline"),
    REFUSED("refused"),
    EXPIRED("ran out"),
    APPROVED("approved"),
    WEAK_PHONE("weak phone"),
    UNLOCK("has a key"),
    MISS("after a miss"),
    UNLOCK_OFFLINE("key, offline"),
    GONE("key gone"),
}

@Composable
fun WelcomePreviewScreen(now: LocalDateTime = LocalDateTime.now()) {
    var situation by rememberSaveable { mutableStateOf(Situation.NEW) }
    val sent = now.minusMinutes(42)
    val waiting = AccessRequest(sent)
    val half = waiting.copy(projectManager = Approval.CONFIRMED, projectManagerAt = now.minusMinutes(30))
    val approved = half.copy(admin = Approval.CONFIRMED, adminAt = now.minusMinutes(5))
    val request = when (situation) {
        Situation.WAITING, Situation.OFFLINE -> waiting
        Situation.HALF -> half
        Situation.REFUSED -> half.copy(admin = Approval.REFUSED, refusedBecause = "The mobile number does not match our records.")
        Situation.EXPIRED -> waiting.copy(expired = true)
        Situation.APPROVED, Situation.WEAK_PHONE -> approved
        else -> null
    }
    val key = when (situation) {
        Situation.UNLOCK, Situation.MISS, Situation.UNLOCK_OFFLINE -> KeyState.PRESENT
        Situation.GONE -> KeyState.LOST
        else -> KeyState.NONE
    }
    val facts = WelcomeFacts(
        account = "name@example.com",
        mobile = "+91 90000 00000",
        now = now,
        reachable = situation != Situation.OFFLINE,
        checkedAt = now.minusMinutes(12),
        triesLeft = if (situation == Situation.MISS) 3 else null,
        offlineHours = if (situation == Situation.UNLOCK_OFFLINE) 8 else null,
        keyProblem = if (situation == Situation.WEAK_PHONE) "it has no fingerprint sensor of the strong kind." else null,
    )
    val actions = WelcomeActions(
        requestAccess = { situation = Situation.WAITING },
        checkAgain = {
            situation = when (situation) {
                Situation.WAITING -> Situation.HALF
                Situation.HALF -> Situation.APPROVED
                else -> Situation.WAITING
            }
        },
        cancelRequest = { situation = Situation.NEW },
        requestAgain = { situation = Situation.NEW },
        makeKey = { situation = Situation.UNLOCK },
        unlock = { situation = if (situation == Situation.MISS) Situation.GONE else Situation.MISS },
    )
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.padding(horizontal = Look.Gap, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Welcome preview", style = MaterialTheme.typography.bodyMedium, color = Look.Ink)
            OutlineButton(
                "Situation: ${situation.label}",
                { situation = Situation.entries[(situation.ordinal + 1) % Situation.entries.size] },
            )
        }
        Box(Modifier.weight(1f)) { WelcomeScreen(welcomeFor(key, KeyLoss.MISSES, request), facts, actions) }
    }
}
