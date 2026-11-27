package com.example.passkeytrial

import java.math.BigInteger
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.AlgorithmParameters
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.interfaces.ECPublicKey
import java.security.spec.ECGenParameterSpec
import java.security.spec.ECParameterSpec
import java.security.spec.ECPoint
import java.security.spec.ECPublicKeySpec
import javax.crypto.Cipher
import javax.crypto.KeyAgreement
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * The phone side of the FIDO "hybrid" sign-in (CTAP 2.2, section 11.5; earlier called caBLE v2): a computer shows
 * a QR code, the phone proves over Bluetooth that it is nearby, and both talk through an encrypted tunnel.
 * Pure Kotlin, so the unit tests run on a computer. Written from the public standard, with the Apache-2.0
 * implementation in microG GmsCore (play-services-fido, hybrid) as the reference for the message layouts.
 */
object Hybrid {
    private const val HMAC = "HmacSHA256"
    private val P256: ECParameterSpec =
        AlgorithmParameters.getInstance("EC").apply { init(ECGenParameterSpec("secp256r1")) }.getParameterSpec(ECParameterSpec::class.java)
    private val PRIME = BigInteger("FFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF", 16)

    /** What the computer's QR code says: its public key for this sign-in and a one-time secret. */
    class Qr(val peerKey: ECPublicKey, val secret: ByteArray, val requestType: String?)

    // ---- QR code -------------------------------------------------------------------------------------------

    /** "FIDO:/" followed by digits: every 17 digits are 7 bytes (a little-endian number); a shorter tail holds fewer. */
    fun digitsToBytes(digits: String): ByteArray {
        val tail = intArrayOf(0, 3, 5, 8, 10, 13, 15)
        val extra = tail.indexOf(digits.length % 17)
        require(extra >= 0 && digits.all { it in '0'..'9' }) { "not a sign-in QR code" }
        val out = ByteArray(digits.length / 17 * 7 + extra)
        var at = 0
        for (chunk in digits.chunked(17)) {
            val size = if (chunk.length == 17) 7 else extra
            val bytes = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putLong(chunk.toLong()).array()
            require(bytes.drop(size).all { it == 0.toByte() }) { "QR digits out of range" }
            bytes.copyInto(out, at, 0, size)
            at += size
        }
        return out
    }

    fun parseQr(text: String): Qr {
        require(text.startsWith("FIDO:/", ignoreCase = true)) { "not a sign-in QR code" }
        val map = Cbor.decode(digitsToBytes(text.substring(6))) as? Map<*, *> ?: throw IllegalArgumentException("QR content is not a map")
        val key = map[0L] as? ByteArray ?: throw IllegalArgumentException("QR has no key")
        val secret = map[1L] as? ByteArray ?: throw IllegalArgumentException("QR has no secret")
        require(secret.size == 16) { "QR secret has the wrong size" }
        return Qr(decompress(key), secret, map[5L] as? String)
    }

    // ---- elliptic curve helpers ----------------------------------------------------------------------------

    /** A 33-byte compressed P-256 point back to a public key: y = sqrt(x^3 - 3x + b), sign chosen by the first byte. */
    fun decompress(point: ByteArray): ECPublicKey {
        require(point.size == 33 && (point[0] == 2.toByte() || point[0] == 3.toByte())) { "not a compressed P-256 point" }
        val x = BigInteger(1, point.copyOfRange(1, 33))
        require(x < PRIME) { "point is not on the curve" }
        val square = x.modPow(BigInteger.valueOf(3), PRIME).subtract(x.multiply(BigInteger.valueOf(3))).add(P256.curve.b).mod(PRIME)
        var y = square.modPow(PRIME.add(BigInteger.ONE).shiftRight(2), PRIME)
        require(y.modPow(BigInteger.TWO, PRIME) == square) { "point is not on the curve" }
        if (y.testBit(0) != (point[0] == 3.toByte())) y = PRIME.subtract(y)
        require(onCurve(x, y)) { "point is not on the curve" }
        return KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(ECPoint(x, y), P256)) as ECPublicKey
    }

    /** True only for a real point of P-256: both numbers below the prime and y^2 = x^3 - 3x + b. Never left to the platform. */
    fun onCurve(x: BigInteger, y: BigInteger): Boolean =
        x.signum() >= 0 && y.signum() >= 0 && x < PRIME && y < PRIME &&
            y.modPow(BigInteger.TWO, PRIME) == x.modPow(BigInteger.valueOf(3), PRIME).subtract(x.multiply(BigInteger.valueOf(3))).add(P256.curve.b).mod(PRIME)

    /** The 65-byte form 04 | x | y. */
    fun uncompressed(key: ECPublicKey): ByteArray = byteArrayOf(4) + WebAuthn.fixed32(key.w.affineX) + WebAuthn.fixed32(key.w.affineY)

    fun fromUncompressed(bytes: ByteArray): ECPublicKey {
        require(bytes.size == 65 && bytes[0] == 4.toByte()) { "not an uncompressed P-256 point" }
        val point = ECPoint(BigInteger(1, bytes.copyOfRange(1, 33)), BigInteger(1, bytes.copyOfRange(33, 65)))
        require(onCurve(point.affineX, point.affineY)) { "point is not on the curve" }
        return KeyFactory.getInstance("EC").generatePublic(ECPublicKeySpec(point, P256)) as ECPublicKey
    }

    fun newKeyPair(): KeyPair = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()

    fun sharedSecret(mine: PrivateKey, theirs: ECPublicKey): ByteArray =
        KeyAgreement.getInstance("ECDH").apply { init(mine); doPhase(theirs, true) }.generateSecret()

    // ---- key derivation ------------------------------------------------------------------------------------

    private fun hmac(key: ByteArray, vararg parts: ByteArray): ByteArray =
        Mac.getInstance(HMAC).apply { init(SecretKeySpec(key, HMAC)); parts.forEach(::update) }.doFinal()

    /** HKDF-SHA256 (RFC 5869). */
    fun hkdf(secret: ByteArray, salt: ByteArray, info: ByteArray, length: Int): ByteArray {
        val prk = hmac(if (salt.isEmpty()) ByteArray(32) else salt, secret)
        var block = ByteArray(0)
        var out = ByteArray(0)
        var counter = 1
        while (out.size < length) {
            block = hmac(prk, block, info, byteArrayOf(counter++.toByte()))
            out += block
        }
        return out.copyOf(length)
    }

    /** Keys derived from the QR secret; the purpose number is written as 4 little-endian bytes. */
    private fun derive(secret: ByteArray, salt: ByteArray, purpose: Int, length: Int) = hkdf(secret, salt, byteArrayOf(purpose.toByte(), 0, 0, 0), length)

    fun eidKey(qrSecret: ByteArray) = derive(qrSecret, ByteArray(0), 1, 64)
    fun tunnelId(qrSecret: ByteArray) = derive(qrSecret, ByteArray(0), 2, 16)
    fun psk(qrSecret: ByteArray, advertPlaintext: ByteArray) = derive(qrSecret, advertPlaintext, 3, 32)

    // ---- Bluetooth advert ----------------------------------------------------------------------------------

    /** The 16 bytes hidden in the advert: 0, a 10-byte random nonce, the tunnel's 3-byte routing ID, the relay's number. */
    fun advertPlaintext(nonce: ByteArray, routingId: ByteArray, relayId: Int): ByteArray {
        require(nonce.size == 10 && routingId.size == 3 && relayId in 0..0xffff)
        return byteArrayOf(0) + nonce + routingId + byteArrayOf(relayId.toByte(), (relayId shr 8).toByte())
    }

    /** 20 advertised bytes: the plaintext as one AES-256 block, plus 4 bytes of HMAC so the computer can spot its own. */
    fun advert(eidKey: ByteArray, plaintext: ByteArray): ByteArray {
        require(eidKey.size == 64 && plaintext.size == 16)
        val block = Cipher.getInstance("AES/CBC/NoPadding")
            .apply { init(Cipher.ENCRYPT_MODE, SecretKeySpec(eidKey.copyOf(32), "AES"), IvParameterSpec(ByteArray(16))) }
            .doFinal(plaintext)
        return block + hmac(eidKey.copyOfRange(32, 64), block).copyOf(4)
    }

    /** What the computer does with an advert it hears (used by the tests): null when it is not for this QR code. */
    fun readAdvert(eidKey: ByteArray, advert: ByteArray): ByteArray? {
        if (advert.size != 20) return null
        val block = advert.copyOf(16)
        if (!MessageDigest.isEqual(hmac(eidKey.copyOfRange(32, 64), block).copyOf(4), advert.copyOfRange(16, 20))) return null
        return Cipher.getInstance("AES/CBC/NoPadding")
            .apply { init(Cipher.DECRYPT_MODE, SecretKeySpec(eidKey.copyOf(32), "AES"), IvParameterSpec(ByteArray(16))) }
            .doFinal(block).takeIf { it[0] == 0.toByte() }
    }

    // ---- relay (tunnel) server -----------------------------------------------------------------------------

    /** Relay 0 and 1 are fixed by the standard; 256 and up are names computed from the number, to be registered by whoever runs one. */
    fun relayDomain(id: Int): String {
        if (id == 0) return "cable.ua5v.com"
        if (id == 1) return "cable.auth.com"
        require(id in 256..0xffff) { "unknown relay number $id" }
        val input = "caBLEv2 tunnel server domain".toByteArray() + byteArrayOf(id.toByte(), (id shr 8).toByte(), 0)
        var value = ByteBuffer.wrap(WebAuthn.sha256(input), 0, 8).order(ByteOrder.LITTLE_ENDIAN).long
        val ending = arrayOf(".com", ".org", ".net", ".info")[(value and 3).toInt()]
        val name = StringBuilder("cable.")
        value = value ushr 2
        while (value != 0L) {
            name.append("abcdefghijklmnopqrstuvwxyz234567"[(value and 31).toInt()])
            value = value ushr 5
        }
        return name.append(ending).toString()
    }

    // ---- encrypted channel ---------------------------------------------------------------------------------

    /**
     * Noise handshake KNpsk0 with P-256, AES-256-GCM and SHA-256. The computer starts (its key is in the QR
     * code); the phone answers. The shared secret from the advert (psk) ties the channel to this QR code and
     * to the phone that was nearby.
     */
    class Noise(peerStatic: ECPublicKey, psk: ByteArray) {
        private var hash: ByteArray = "Noise_KNpsk0_P256_AESGCM_SHA256".toByteArray().copyOf(32)
        private var chain: ByteArray = hash.clone()
        private var key = ByteArray(32)

        init {
            mixHash(byteArrayOf(1)) // prologue: "the QR code holder starts"
            mixHash(uncompressed(peerStatic))
            val (c, h, k) = expand(psk, 3)
            chain = c; mixHash(h); key = k
        }

        private fun mixHash(data: ByteArray) { hash = WebAuthn.sha256(hash + data) }

        private fun expand(material: ByteArray, count: Int): List<ByteArray> {
            val prk = hmac(chain, material)
            var block = ByteArray(0)
            return (1..count).map { n -> hmac(prk, block, byteArrayOf(n.toByte())).also { block = it } }
        }

        private fun mixKey(material: ByteArray) { expand(material, 2).let { chain = it[0]; key = it[1] } }

        private fun gcm(mode: Int, data: ByteArray): ByteArray =
            Cipher.getInstance("AES/GCM/NoPadding").apply {
                init(mode, SecretKeySpec(key, "AES"), GCMParameterSpec(128, ByteArray(12)))
                updateAAD(hash)
            }.doFinal(data)

        /** Reads the computer's first message and writes the phone's answer. Returns (answer, channel). */
        fun respond(message: ByteArray, peerStatic: ECPublicKey, phone: KeyPair = newKeyPair()): Pair<ByteArray, Channel> {
            require(message.size >= 65 + 16) { "handshake message too short" }
            val theirs = message.copyOf(65)
            mixHash(theirs); mixKey(theirs)
            val sealed = message.copyOfRange(65, message.size)
            gcm(Cipher.DECRYPT_MODE, sealed) // throws when the computer does not know the QR secret and the advert
            mixHash(sealed)

            val mine = uncompressed(phone.public as ECPublicKey)
            mixHash(mine); mixKey(mine)
            mixKey(sharedSecret(phone.private, fromUncompressed(theirs)))
            mixKey(sharedSecret(phone.private, peerStatic))
            val answer = gcm(Cipher.ENCRYPT_MODE, ByteArray(0))
            mixHash(answer)
            val keys = expand(ByteArray(0), 2)
            return (mine + answer) to Channel(read = keys[0], write = keys[1])
        }

        /** The computer's side, for the tests only: first message, then reading the phone's answer. */
        fun start(computer: KeyPair): ByteArray {
            val mine = uncompressed(computer.public as ECPublicKey)
            mixHash(mine); mixKey(mine)
            val sealed = gcm(Cipher.ENCRYPT_MODE, ByteArray(0))
            mixHash(sealed)
            return mine + sealed
        }

        fun finish(answer: ByteArray, computer: KeyPair, computerStatic: PrivateKey): Channel {
            val theirs = answer.copyOf(65)
            mixHash(theirs); mixKey(theirs)
            mixKey(sharedSecret(computer.private, fromUncompressed(theirs)))
            mixKey(sharedSecret(computerStatic, fromUncompressed(theirs)))
            gcm(Cipher.DECRYPT_MODE, answer.copyOfRange(65, answer.size))
            val keys = expand(ByteArray(0), 2)
            return Channel(read = keys[1], write = keys[0])
        }
    }

    /** After the handshake: every message is padded to a multiple of 32 bytes and sealed with a counting nonce. */
    class Channel(private val read: ByteArray, private val write: ByteArray) {
        private var readCount = 0
        private var writeCount = 0

        private fun cipher(mode: Int, key: ByteArray, count: Int) = Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(mode, SecretKeySpec(key, "AES"), GCMParameterSpec(128, ByteBuffer.allocate(12).putInt(8, count).array()))
        }

        /** Locked: replies come from two threads, and a counter used twice would repeat an AES-GCM nonce. */
        @Synchronized
        fun seal(message: ByteArray): ByteArray {
            check(writeCount < MAX_MESSAGES) { "channel used up" }
            val padding = 32 - message.size % 32
            val padded = message.copyOf(message.size + padding).also { it[it.lastIndex] = (padding - 1).toByte() }
            return cipher(Cipher.ENCRYPT_MODE, write, writeCount++).doFinal(padded)
        }

        @Synchronized
        fun open(sealed: ByteArray): ByteArray {
            check(readCount < MAX_MESSAGES) { "channel used up" }
            val padded = cipher(Cipher.DECRYPT_MODE, read, readCount++).doFinal(sealed)
            val padding = (padded.last().toInt() and 0xff) + 1
            require(padding <= padded.size) { "bad padding" }
            return padded.copyOf(padded.size - padding)
        }
    }

    /** A sign-in needs a handful of messages; far below the point where a counter could wrap. */
    const val MAX_MESSAGES = 1 shl 16

    // ---- the requests inside the channel (CTAP2) -----------------------------------------------------------

    const val FRAME_SHUTDOWN = 0
    const val FRAME_CTAP = 1
    const val CMD_MAKE_CREDENTIAL = 1
    const val CMD_GET_ASSERTION = 2
    const val CMD_GET_INFO = 4
    const val STATUS_OK = 0
    const val STATUS_INVALID_COMMAND = 0x01
    const val STATUS_CREDENTIAL_EXCLUDED = 0x19
    const val STATUS_OPERATION_DENIED = 0x27
    const val STATUS_NO_CREDENTIALS = 0x2e

    /** "Who are you": a phone that verifies the person itself and holds sign-in keys on the device. */
    fun info(): ByteArray = Cbor.encode(
        linkedMapOf(
            1 to listOf("FIDO_2_0", "FIDO_2_1"),
            3 to WebAuthn.AAGUID,
            4 to linkedMapOf("rk" to true, "up" to true, "uv" to true),
            9 to listOf("internal", "hybrid"),
        ),
    )

    /** The first message after the handshake carries the phone's description. */
    fun greeting(): ByteArray = Cbor.encode(linkedMapOf(1 to info()))

    class SignIn(val rpId: String, val clientDataHash: ByteArray, val allowed: List<ByteArray>)

    fun parseSignIn(parameters: ByteArray): SignIn {
        val map = Cbor.decode(parameters) as? Map<*, *> ?: throw IllegalArgumentException("request is not a map")
        val allowed = (map[3L] as? List<*>).orEmpty().mapNotNull { (it as? Map<*, *>)?.get("id") as? ByteArray }
        return SignIn(map[1L] as String, map[2L] as ByteArray, allowed)
    }

    class Create(
        val clientDataHash: ByteArray,
        val rpId: String,
        val userId: ByteArray,
        val userName: String,
        val algorithms: List<Long>,
        val excluded: List<ByteArray>,
    )

    fun parseCreate(parameters: ByteArray): Create {
        val map = Cbor.decode(parameters) as? Map<*, *> ?: throw IllegalArgumentException("request is not a map")
        val user = map[3L] as Map<*, *>
        val algorithms = (map[4L] as? List<*>).orEmpty().mapNotNull { (it as? Map<*, *>)?.get("alg") as? Long }
        val excluded = (map[5L] as? List<*>).orEmpty().mapNotNull { (it as? Map<*, *>)?.get("id") as? ByteArray }
        return Create(map[1L] as ByteArray, (map[2L] as Map<*, *>)["id"] as String, user["id"] as ByteArray, user["name"] as? String ?: "user", algorithms, excluded)
    }

    /** A new key's answer: without a signature no attestation ("none"), with one Android key attestation. */
    fun createAnswer(authData: ByteArray, signature: ByteArray? = null, certificates: List<ByteArray> = emptyList()): ByteArray =
        byteArrayOf(STATUS_OK.toByte()) + Cbor.encode(
            if (signature == null) linkedMapOf(1 to "none", 2 to authData, 3 to emptyMap<String, Any>())
            else linkedMapOf(1 to "android-key", 2 to authData, 3 to linkedMapOf("alg" to -7, "sig" to signature, "x5c" to certificates)),
        )

    fun signInAnswer(credentialId: ByteArray, authData: ByteArray, signature: ByteArray, userHandle: ByteArray): ByteArray =
        byteArrayOf(STATUS_OK.toByte()) + Cbor.encode(
            linkedMapOf(
                1 to linkedMapOf("id" to credentialId, "type" to "public-key"),
                2 to authData,
                3 to signature,
                4 to linkedMapOf("id" to userHandle),
            ),
        )
}
