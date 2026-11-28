package com.example.erp.core

import java.security.GeneralSecurityException
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * How the app's safe locks one value: AES-256-GCM with the data key that only a fingerprint match releases.
 * Every value gets its own random starting number, and its name is bound into it, so a value stored under one
 * name cannot be passed off under another, and any change to the stored bytes is noticed.
 */
object Seal {
    private const val IV_BYTES = 12
    private const val TAG_BITS = 128
    private const val AES_GCM = "AES/GCM/NoPadding"

    fun seal(key: ByteArray, name: String, plain: ByteArray): ByteArray {
        require(key.size == 32) { "the data key has 32 bytes" }
        require(key.any { it != 0.toByte() }) { "a wiped key seals nothing" }
        val iv = ByteArray(IV_BYTES).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance(AES_GCM)
        cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_BITS, iv))
        cipher.updateAAD(name.toByteArray())
        return iv + cipher.doFinal(plain)
    }

    /** Null when [sealed] was not locked with this key under this name, or was changed since. */
    fun open(key: ByteArray, name: String, sealed: ByteArray): ByteArray? {
        if (key.size != 32 || sealed.size < IV_BYTES + TAG_BITS / 8) return null
        return try {
            val cipher = Cipher.getInstance(AES_GCM)
            cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_BITS, sealed, 0, IV_BYTES))
            cipher.updateAAD(name.toByteArray())
            cipher.doFinal(sealed, IV_BYTES, sealed.size - IV_BYTES)
        } catch (e: GeneralSecurityException) {
            null
        }
    }
}
