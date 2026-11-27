package com.example.passkeytrial

import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.widget.Button
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.fragment.app.FragmentActivity

/** The trial's one screen: what this phone offers, the fingerprint-lock test, and the log. */
class MainActivity : FragmentActivity() {
    private val lockAlias = "lock-test"
    private lateinit var log: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val column = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(40, 80, 40, 80) }
        fun text(value: String) = TextView(this).apply { text = value; textSize = 15f; setTextIsSelectable(true); setPadding(0, 16, 0, 16) }.also(column::addView)
        fun button(label: String, action: () -> Unit) = Button(this).apply { text = label; isAllCaps = false; setOnClickListener { action() } }.also(column::addView)

        text(phone())
        text("Fingerprint lock test")
        button("1. Make a locked key and sign") { makeAndSign() }
        button("2. Sign again (after adding a fingerprint: must say DESTROYED)") { signAgain() }
        button("Delete the test key") { Keys.delete(lockAlias); note("lock test: key deleted") }
        text("Passkeys (Android 14 and newer)")
        button("Open the phone's passkey service settings") { openProviderSettings() }
        column.addView(CheckBox(this).apply {
            text = "Send Android key attestation when a passkey is made"
            isChecked = Store.attest(this@MainActivity)
            setOnCheckedChangeListener { _, on -> Store.setAttest(this@MainActivity, on); note("attestation switch: $on") }
        })
        text("Computer sign-in by our own QR reader (all Android versions)")
        button("Scan a computer's QR code") { startActivity(Intent(this, HybridActivity::class.java)) }
        button("Delete all trial passkeys") { Store.clear(this); note("passkeys deleted") }
        button("Clear the log") { Store.clearLog(this); refresh() }
        log = text("")
        setContentView(ScrollView(this).apply { addView(column) })
        Store.fetchBrowsers(this)
        Store.log(this, phone().replace("\n", " | "))
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        log.text = "Passkeys held: " + Store.passkeys(this).joinToString { "${it.userName} @ ${it.rpId}" }.ifEmpty { "none" } + "\n\n" + Store.logText(this)
    }

    private fun note(line: String) {
        Store.log(this, line)
        refresh()
    }

    private fun phone(): String {
        val manager = BiometricManager.from(this)
        fun state(code: Int) = when (code) {
            BiometricManager.BIOMETRIC_SUCCESS -> "ready"
            BiometricManager.BIOMETRIC_ERROR_NONE_ENROLLED -> "none enrolled"
            BiometricManager.BIOMETRIC_ERROR_NO_HARDWARE -> "no sensor"
            else -> "not usable ($code)"
        }
        val play = runCatching { packageManager.getPackageInfo("com.google.android.gms", 0).versionName }.getOrNull() ?: "absent"
        return "${Build.MANUFACTURER} ${Build.MODEL}, Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})\n" +
            "Strong fingerprint/face: ${state(manager.canAuthenticate(BIOMETRIC_STRONG))}\n" +
            "Weak face/fingerprint: ${state(manager.canAuthenticate(BIOMETRIC_WEAK))}\n" +
            "StrongBox chip: ${packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)}\n" +
            "Passkey service possible: ${Build.VERSION.SDK_INT >= 34}\n" +
            "Google Play services: $play"
    }

    private fun makeAndSign() {
        if (Keys.exists(lockAlias)) return note("lock test: a key exists already; use button 2 or delete it")
        val made = try {
            Keys.make(this, lockAlias, null)
        } catch (e: Exception) {
            return note("lock test: REFUSED $e")
        }
        note("lock test: key made, ${made.report}")
        signAgain()
    }

    private fun signAgain() {
        if (!Keys.exists(lockAlias)) return note("lock test: no key; use button 1")
        Biometric.sign(this, lockAlias, "trial".toByteArray(), "Confirm with your fingerprint") { signed ->
            signed.onSuccess { note("lock test: SIGNED (${it.size} bytes)") }.onFailure {
                note(if (it is KeyPermanentlyInvalidatedException) "lock test: KEY DESTROYED after a fingerprint/face change (correct)" else "lock test: not signed: $it")
            }
        }
    }

    private fun openProviderSettings() {
        if (Build.VERSION.SDK_INT < 34) return note("this Android has no passkey services (needs Android 14)")
        runCatching { startActivity(Intent(Settings.ACTION_CREDENTIAL_PROVIDER, Uri.parse("package:$packageName"))) }
            .onFailure { note("the phone has no passkey service settings: $it") }
    }
}
