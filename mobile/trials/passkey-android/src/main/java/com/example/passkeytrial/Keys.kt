package com.example.passkeytrial

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec

/**
 * Keys that live in the phone's secure hardware and sign only after a strong fingerprint/face match.
 * Adding a fingerprint or face later destroys them (P82). No PIN fallback.
 */
object Keys {
    private const val STORE = "AndroidKeyStore"

    /** The phone did not give the protection we asked for; the key was deleted again. */
    class Refused(message: String) : Exception(message)

    /** [chain] describes the key's certificates: how many, and who issued the last one (the maker's or Google's root). */
    class Made(val publicKey: ECPublicKey, val certificates: List<ByteArray>, val report: String, val chain: String)

    private fun store() = KeyStore.getInstance(STORE).apply { load(null) }

    fun exists(alias: String) = store().containsAlias(alias)
    fun delete(alias: String) = store().deleteEntry(alias)

    private fun generate(alias: String, challenge: ByteArray?, strongBox: Boolean) {
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
            .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(true)
            .setInvalidatedByBiometricEnrollment(true)
        // A fresh match for every signature. From Android 11 we can name "strong biometrics only"; on 9 and 10
        // "every use" (-1) already means biometrics only, because a PIN cannot unlock a single-use key there.
        if (Build.VERSION.SDK_INT >= 30) spec.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
        else @Suppress("DEPRECATION") spec.setUserAuthenticationValidityDurationSeconds(-1)
        if (challenge != null) spec.setAttestationChallenge(challenge)
        if (strongBox) spec.setIsStrongBoxBacked(true)
        KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, STORE).apply { initialize(spec.build()) }.generateKeyPair()
    }

    /** Makes the key, then reads back what the phone really did, and refuses anything weaker than asked. */
    fun make(context: Context, alias: String, challenge: ByteArray?): Made {
        var strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        try {
            generate(alias, challenge, strongBox)
        } catch (e: StrongBoxUnavailableException) {
            strongBox = false
            generate(alias, challenge, false)
        }
        val entry = store().getEntry(alias, null) as KeyStore.PrivateKeyEntry
        val info = KeyFactory.getInstance(entry.privateKey.algorithm, STORE).getKeySpec(entry.privateKey, KeyInfo::class.java)
        @Suppress("DEPRECATION")
        val hardware = if (Build.VERSION.SDK_INT >= 31) info.securityLevel.let {
            it == KeyProperties.SECURITY_LEVEL_TRUSTED_ENVIRONMENT || it == KeyProperties.SECURITY_LEVEL_STRONGBOX
        } else info.isInsideSecureHardware
        val strongOnly = Build.VERSION.SDK_INT < 30 || info.userAuthenticationType == KeyProperties.AUTH_BIOMETRIC_STRONG
        val report = "secure hardware=$hardware strongBox=$strongBox needsMatch=${info.isUserAuthenticationRequired} " +
            "enforcedByHardware=${info.isUserAuthenticationRequirementEnforcedBySecureHardware} " +
            "destroyedOnNewFingerprint=${info.isInvalidatedByBiometricEnrollment} strongOnly=$strongOnly"
        if (!hardware || !info.isUserAuthenticationRequired || !info.isInvalidatedByBiometricEnrollment || !strongOnly ||
            !info.isUserAuthenticationRequirementEnforcedBySecureHardware
        ) {
            delete(alias)
            throw Refused("This phone did not lock the key as asked: $report")
        }
        val root = (entry.certificateChain.last() as java.security.cert.X509Certificate).subjectX500Principal.name
        val chain = "${entry.certificateChain.size} certificates, root: $root"
        return Made(entry.certificate.publicKey as ECPublicKey, entry.certificateChain.map { it.encoded }, report, chain)
    }

    /** Throws KeyPermanentlyInvalidatedException when a fingerprint or face was added since the key was made. */
    fun signer(alias: String): Signature {
        val key = store().getKey(alias, null) as? PrivateKey ?: throw IllegalStateException("no key $alias")
        return Signature.getInstance("SHA256withECDSA").apply { initSign(key) }
    }
}
