package com.example.erp.app

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import android.util.Base64
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import androidx.fragment.app.FragmentActivity
import com.example.erp.core.KeyLoss
import com.example.erp.core.KeyState
import com.example.erp.core.LockRules
import java.security.GeneralSecurityException
import java.security.KeyStore
import java.security.SecureRandom
import java.security.UnrecoverableKeyException
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec

/** How one touch of the sensor ended. */
sealed interface LockResult {
    /** A match. [dataKey] is what the app's safe is locked with; it exists in memory only while the app is open. */
    class Opened(val dataKey: ByteArray) : LockResult

    /** The person closed the question. Nothing changed. */
    data object Cancelled : LockResult

    /** It did not work this time; [sentence] says why in plain words. The key is kept. */
    class Trouble(val sentence: String) : LockResult

    /** The key is gone (5 misses, or the phone's fingerprints changed). [PhoneLock.loss] says which. */
    data object Erased : LockResult

    /** A match that signed one decision ([PhoneLock.confirm]). */
    data object Confirmed : LockResult
}

/**
 * The fingerprint lock. A key is made inside the phone's secure chip and can be used only for the moment of one
 * strong fingerprint match: no PIN, no pattern. The chip destroys it when a fingerprint is added to the phone; the
 * app erases it after [LockRules.MAX_MISSES] misses in a row. That key locks a random data key, and the data key
 * is what opens the app: without a match there is nothing in the app's storage that can be read.
 */
class PhoneLock(context: Context) {
    private val app = context.applicationContext
    private val prefs = context.getSharedPreferences("lock", Context.MODE_PRIVATE)
    private val hasStrongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)

    private fun store() = KeyStore.getInstance(STORE).apply { load(null) }

    val misses: Int get() = prefs.getInt(MISSES, 0)

    val loss: KeyLoss? get() = prefs.getString(LOSS, null)?.let { name -> KeyLoss.entries.find { it.name == name } }

    fun state(): KeyState {
        // The locked data key is here but the chip no longer has its key: the phone removed it.
        // Erased only when the phone clearly says so; a key store that fails to answer leaves the key alone.
        if (prefs.contains(WRAPPED) && runCatching { !store().containsAlias(ALIAS) }.getOrDefault(false)) erase(KeyLoss.NEW_FINGERPRINT)
        return when {
            prefs.contains(WRAPPED) -> KeyState.PRESENT
            loss != null -> KeyState.LOST
            else -> KeyState.NONE
        }
    }

    /** The person has read why the key is gone and asks for a new one. */
    fun forgetLoss() = prefs.edit(commit = true) { remove(LOSS) }

    private fun erase(why: KeyLoss) {
        runCatching { store().deleteEntry(ALIAS) }
        Safe.wipe(app) // what the lost key protected can never be opened again
        Session.lock() // also when the key went while the app was open
        val first = loss ?: why // a later look at the empty store must not replace the real reason
        prefs.edit(commit = true) { clear(); putString(LOSS, first.name) }
        // After the key is marked gone, so a signal arriving now is refused: no alert stays behind for a key that is gone.
        AlertCenter.clear(app)
    }

    private fun generate(strongBox: Boolean) {
        val spec = KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
        // A fresh match for every use. From Android 11 we can name "strong biometrics only"; on 9 and 10 "every
        // use" (-1) already means biometrics only, because a PIN cannot unlock a single-use key there.
        if (Build.VERSION.SDK_INT >= 30) spec.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
        else @Suppress("DEPRECATION") spec.setUserAuthenticationValidityDurationSeconds(-1)
        if (strongBox) spec.setIsStrongBoxBacked(true)
        KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, STORE).apply { init(spec.build()) }.generateKey()
    }

    /** Makes the chip's key, then reads back what the phone really did. Anything weaker than asked is deleted. */
    private fun makeChipKey(): SecretKey {
        try {
            generate(hasStrongBox)
        } catch (e: StrongBoxUnavailableException) {
            generate(false)
        }
        val key = store().getKey(ALIAS, null) as SecretKey
        val info = SecretKeyFactory.getInstance(key.algorithm, STORE).getKeySpec(key, KeyInfo::class.java) as KeyInfo
        @Suppress("DEPRECATION")
        val inChip = if (Build.VERSION.SDK_INT >= 31) info.securityLevel.let {
            it == KeyProperties.SECURITY_LEVEL_TRUSTED_ENVIRONMENT || it == KeyProperties.SECURITY_LEVEL_STRONGBOX
        } else info.isInsideSecureHardware
        val strongOnly = Build.VERSION.SDK_INT < 30 || info.userAuthenticationType == KeyProperties.AUTH_BIOMETRIC_STRONG
        @Suppress("DEPRECATION")
        val everyUse = info.userAuthenticationValidityDurationSeconds <= 0
        if (!inChip || !strongOnly || !everyUse || !info.isUserAuthenticationRequired || !info.isInvalidatedByBiometricEnrollment ||
            !info.isUserAuthenticationRequirementEnforcedBySecureHardware
        ) {
            store().deleteEntry(ALIAS)
            throw GeneralSecurityException("the phone did not lock the key as asked")
        }
        return key
    }

    /** One touch makes the key. Cancelled or failed: no key is left behind. */
    fun make(activity: FragmentActivity, done: (LockResult) -> Unit) {
        val cipher = try {
            Cipher.getInstance(AES_GCM).apply { init(Cipher.ENCRYPT_MODE, makeChipKey()) }
        } catch (e: Exception) { // the phone's own key store throws more kinds than it documents
            runCatching { store().deleteEntry(ALIAS) }
            done(LockResult.Trouble("This phone could not lock a key to your fingerprint, so no key was made. Check that your fingerprint is saved in the phone's Settings."))
            return
        }
        ask(activity, "Make your key", cipher, countMisses = false, done = { result ->
            if (result !is LockResult.Opened) runCatching { store().deleteEntry(ALIAS) }
            done(result)
        }) { matched ->
            val dataKey = ByteArray(32).also { SecureRandom().nextBytes(it) }
            val locked = matched.iv + matched.doFinal(dataKey)
            Safe.wipe(app) // a new key starts with an empty safe
            prefs.edit(commit = true) { clear(); putString(WRAPPED, Base64.encodeToString(locked, Base64.NO_WRAP)) }
            LockResult.Opened(dataKey)
        }
    }

    /** One touch opens the app. A miss is counted and kept; the fifth in a row erases the key. */
    fun open(activity: FragmentActivity, done: (LockResult) -> Unit) =
        unlock(activity, "Open with your fingerprint", null, done) { LockResult.Opened(it) }

    /**
     * One touch signs one decision. The question shows [what] is signed. It is the same proof as opening the app:
     * the chip releases the key only for a real match, and here the released data key is thrown away at once.
     * Misses count exactly as at the door, so a stranger with the open phone gets no free tries.
     */
    fun confirm(activity: FragmentActivity, what: String, done: (LockResult) -> Unit) =
        unlock(activity, "Confirm with your fingerprint", what, done) {
            it.fill(0)
            LockResult.Confirmed
        }

    private fun unlock(activity: FragmentActivity, title: String, what: String?, done: (LockResult) -> Unit, result: (ByteArray) -> LockResult) {
        val locked = prefs.getString(WRAPPED, null)?.let { runCatching { Base64.decode(it, Base64.NO_WRAP) }.getOrNull() }
        val key = try {
            store().getKey(ALIAS, null) as? SecretKey
        } catch (e: UnrecoverableKeyException) {
            null // some phones report a destroyed key this way
        } catch (e: Exception) {
            done(LockResult.Trouble("The phone's secure chip did not answer. Restart the phone and try again."))
            return
        }
        if (locked == null || locked.size <= IV_BYTES || key == null) {
            erase(KeyLoss.NEW_FINGERPRINT)
            done(LockResult.Erased)
            return
        }
        val cipher = try {
            Cipher.getInstance(AES_GCM).apply { init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, locked, 0, IV_BYTES)) }
        } catch (e: KeyPermanentlyInvalidatedException) {
            // The chip destroyed the key: a fingerprint was added, or the screen lock was removed.
            erase(KeyLoss.NEW_FINGERPRINT)
            done(LockResult.Erased)
            return
        } catch (e: Exception) {
            // Not a destroyed key. Keep it: erasing here would take a working key away for a passing fault.
            done(LockResult.Trouble("The phone's secure chip did not answer. Restart the phone and try again."))
            return
        }
        ask(activity, title, cipher, countMisses = true, done = done, what = what) { matched ->
            val dataKey = matched.doFinal(locked, IV_BYTES, locked.size - IV_BYTES)
            prefs.edit(commit = true) { remove(MISSES) }
            result(dataKey)
        }
    }

    private fun ask(
        activity: FragmentActivity,
        title: String,
        cipher: Cipher,
        countMisses: Boolean,
        done: (LockResult) -> Unit,
        what: String? = null,
        onMatch: (Cipher) -> LockResult,
    ) {
        var finished = false
        var missedHere = false
        fun finish(result: LockResult) {
            if (!finished) {
                finished = true
                done(result)
            }
        }

        /** Written at once, so closing the app after a miss does not give the tries back. True when it erased. */
        fun countMiss(): Boolean {
            val now = misses + 1
            prefs.edit(commit = true) { putInt(MISSES, now) }
            if (LockRules.erases(now)) erase(KeyLoss.MISSES)
            return LockRules.erases(now)
        }
        lateinit var prompt: BiometricPrompt
        prompt = BiometricPrompt(
            activity,
            ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    finish(
                        runCatching { onMatch(result.cryptoObject!!.cipher!!) }
                            .getOrElse { LockResult.Trouble("The phone's secure chip did not answer. Try again.") },
                    )
                }

                override fun onAuthenticationFailed() {
                    if (!countMisses || finished) return
                    missedHere = true
                    if (countMiss()) {
                        finish(LockResult.Erased)
                        prompt.cancelAuthentication()
                    }
                }

                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    // Older Android versions report the miss that makes the phone lock its sensor only as a
                    // lockout, never as a miss. After a miss in this same question it is counted as one.
                    val lockout = errorCode == BiometricPrompt.ERROR_LOCKOUT || errorCode == BiometricPrompt.ERROR_LOCKOUT_PERMANENT
                    if (lockout && countMisses && missedHere && !finished && countMiss()) {
                        finish(LockResult.Erased)
                        return
                    }
                    finish(
                        when (errorCode) {
                            BiometricPrompt.ERROR_USER_CANCELED, BiometricPrompt.ERROR_NEGATIVE_BUTTON, BiometricPrompt.ERROR_CANCELED ->
                                LockResult.Cancelled
                            BiometricPrompt.ERROR_LOCKOUT ->
                                LockResult.Trouble("Too many tries on this phone. Wait half a minute, then try again.")
                            BiometricPrompt.ERROR_LOCKOUT_PERMANENT ->
                                LockResult.Trouble("The phone has locked its fingerprint sensor. Unlock the phone once with its PIN or pattern, then try again.")
                            BiometricPrompt.ERROR_NO_BIOMETRICS ->
                                LockResult.Trouble("No fingerprint is saved on this phone. Add yours in the phone's Settings.")
                            else -> LockResult.Trouble("The fingerprint sensor did not answer (code $errorCode). Try again.")
                        },
                    )
                }
            },
        )
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(title)
            .apply { if (what != null) setDescription(what) }
            .setNegativeButtonText("Cancel")
            .setAllowedAuthenticators(BIOMETRIC_STRONG)
            .build()
        prompt.authenticate(info, BiometricPrompt.CryptoObject(cipher))
    }

    companion object {
        /** Whether this phone has its key, read without touching the key itself. For code that runs while the app is closed. */
        fun hasKey(context: Context): Boolean = context.getSharedPreferences("lock", Context.MODE_PRIVATE).contains(WRAPPED)
        const val STORE = "AndroidKeyStore"
        const val ALIAS = "app-lock"
        const val AES_GCM = "AES/GCM/NoPadding"
        const val IV_BYTES = 12
        const val WRAPPED = "wrapped"
        const val MISSES = "misses"
        const val LOSS = "loss"
    }
}

/**
 * The open app: the data key, in memory only. It is gone when the app's process ends, when the app was left for
 * [LockRules.AWAY_MS], and it is overwritten before it is dropped.
 */
object Session {
    private val handler = Handler(Looper.getMainLooper())
    private val lockLater = Runnable { lock() }
    private var leftAt: Long? = null

    var dataKey: ByteArray? by mutableStateOf(null)
        private set

    /** Ask for the fingerprint by itself when the person arrives; after they closed the question, only on a tap. */
    var askOnArrival = true

    val isOpen: Boolean get() = dataKey != null

    @Synchronized
    fun open(key: ByteArray) {
        dataKey = key
    }

    /**
     * The only way to use the data key. It cannot be wiped in the middle of [use], from any thread, so nothing is
     * ever sealed with a key that is half or fully zeroed. Null when the app is locked.
     */
    @Synchronized
    fun <T> withKey(use: (ByteArray) -> T): T? = dataKey?.let(use)

    @Synchronized
    fun lock() {
        dataKey?.fill(0)
        dataKey = null
        askOnArrival = true
    }

    /**
     * The app went out of sight. The timer drops the key while the app stays away and the phone is awake; a
     * sleeping phone pauses it, and [back] then decides by the clock that keeps running.
     */
    fun left() {
        leftAt = SystemClock.elapsedRealtime()
        handler.removeCallbacks(lockLater)
        handler.postDelayed(lockLater, LockRules.AWAY_MS)
    }

    fun back() {
        handler.removeCallbacks(lockLater)
        if (LockRules.mustLock(leftAt, SystemClock.elapsedRealtime())) lock()
        leftAt = null
    }
}
