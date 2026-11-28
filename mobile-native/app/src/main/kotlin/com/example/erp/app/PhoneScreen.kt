package com.example.erp.app

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
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

/** What the app needs from this phone, checked for real. The same check opens onboarding later (screen A2). */
class PhoneLine(val kind: StatusKind, val icon: Int, val title: String, val text: String)

class PhoneCheck(val lines: List<PhoneLine>, val usable: Boolean)

fun checkPhone(context: Context): PhoneCheck {
    val strong = BiometricManager.from(context).canAuthenticate(BIOMETRIC_STRONG)
    val (kind, text) = when (strong) {
        BiometricManager.BIOMETRIC_SUCCESS -> StatusKind.OK to "Ready to use."
        BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> StatusKind.WARN to "No fingerprint saved yet. Add yours in the phone's Settings."
        BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> StatusKind.BAD to "This phone has none. The app cannot keep a key here."
        else -> StatusKind.BAD to "Not usable right now (code $strong)."
    }
    val strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
    val lines = listOf(
        PhoneLine(kind, R.drawable.ic_fingerprint, "Fingerprint sensor", text),
        PhoneLine(StatusKind.OK, R.drawable.ic_chip, "Secure chip", if (strongBox) "A separate chip (StrongBox)." else "Built into the processor."),
        // The app cannot be installed below Android 9, so a running app is always on a supported version.
        PhoneLine(StatusKind.OK, R.drawable.ic_phone, "Android ${Build.VERSION.RELEASE}", "Supported."),
    )
    return PhoneCheck(lines, usable = strong == BiometricManager.BIOMETRIC_SUCCESS)
}

@Composable
fun PhoneScreen(check: PhoneCheck, model: String, version: String, safeNote: String? = null, onSafeNote: (() -> Unit)? = null) {
    // One centred column, so text lines stay readable on a tablet.
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(Look.Gap), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Column(Modifier.widthIn(max = 640.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("This phone", style = MaterialTheme.typography.headlineMedium, color = Look.Ink)
            Text(model, style = MaterialTheme.typography.bodyLarge, color = Look.Ink)
            for (line in check.lines) RowCard(line.icon, line.title, line.text, pill = line.kind to line.kind.word)
            Notice(
                if (check.usable) StatusKind.OK else StatusKind.WARN,
                if (check.usable) "This phone can keep a fingerprint-locked key." else "This phone cannot keep a fingerprint-locked key yet.",
            )
            if (onSafeNote != null) {
                RowCard(R.drawable.ic_lock, "Safe (test builds)", safeNote ?: "Empty.")
                OutlineButton("Save a test note in the safe", onSafeNote)
            }
            Text("App version $version", style = MaterialTheme.typography.bodyMedium, color = Look.Muted)
        }
    }
}
