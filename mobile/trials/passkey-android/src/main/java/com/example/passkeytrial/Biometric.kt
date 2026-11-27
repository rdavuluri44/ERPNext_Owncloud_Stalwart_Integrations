package com.example.passkeytrial

import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity

object Biometric {
    /** Asks for a strong fingerprint/face match and signs [data] with the key; the match unlocks this one signature only. */
    fun sign(activity: FragmentActivity, alias: String, data: ByteArray, title: String, done: (Result<ByteArray>) -> Unit) {
        val signature = try {
            Keys.signer(alias)
        } catch (e: Exception) {
            done(Result.failure(e))
            return
        }
        val prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    done(runCatching { result.cryptoObject!!.signature!!.run { update(data); sign() } })
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    done(Result.failure(IllegalStateException("fingerprint/face error $errorCode: $errString")))
                }
            },
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .setNegativeButtonText("Cancel")
            .setAllowedAuthenticators(BIOMETRIC_STRONG)
            .build()
        prompt.authenticate(info, BiometricPrompt.CryptoObject(signature))
    }
}
