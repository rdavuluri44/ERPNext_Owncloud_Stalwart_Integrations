package com.example.passkeytrial

import java.io.ByteArrayOutputStream
import java.math.BigInteger
import java.nio.ByteBuffer
import java.security.MessageDigest
import java.util.Base64

/** The few CBOR types WebAuthn needs: whole numbers, bytes, text, lists and maps (kept in the given order). */
object Cbor {
    fun encode(value: Any): ByteArray = ByteArrayOutputStream().also { write(it, value) }.toByteArray()

    private fun head(out: ByteArrayOutputStream, major: Int, n: Long) {
        val m = major shl 5
        when {
            n < 24 -> out.write(m or n.toInt())
            n < 0x100 -> { out.write(m or 24); out.write(n.toInt()) }
            n < 0x10000 -> { out.write(m or 25); out.write(ByteBuffer.allocate(2).putShort(n.toShort()).array()) }
            n < 0x100000000 -> { out.write(m or 26); out.write(ByteBuffer.allocate(4).putInt(n.toInt()).array()) }
            else -> { out.write(m or 27); out.write(ByteBuffer.allocate(8).putLong(n).array()) }
        }
    }

    private fun write(out: ByteArrayOutputStream, value: Any?) {
        when (value) {
            is Int -> write(out, value.toLong())
            is Long -> if (value >= 0) head(out, 0, value) else head(out, 1, -1 - value)
            is ByteArray -> { head(out, 2, value.size.toLong()); out.write(value) }
            is String -> value.toByteArray().let { head(out, 3, it.size.toLong()); out.write(it) }
            is List<*> -> { head(out, 4, value.size.toLong()); value.forEach { write(out, it) } }
            is Map<*, *> -> { head(out, 5, value.size.toLong()); value.forEach { (k, v) -> write(out, k); write(out, v) } }
            is Boolean -> out.write(if (value) 0xf5 else 0xf4)
            else -> throw IllegalArgumentException("CBOR: unsupported value $value")
        }
    }

    /** Reads one value: numbers as Long, bytes, text, lists, maps, true/false and null. Anything else is refused. */
    fun decode(bytes: ByteArray): Any? = Reader(bytes).run { value(0).also { require(at == bytes.size) { "CBOR: extra bytes" } } }

    private class Reader(val bytes: ByteArray) {
        var at = 0

        private fun take(n: Int): ByteArray {
            require(n >= 0 && at + n <= bytes.size) { "CBOR: cut short" }
            return bytes.copyOfRange(at, at + n).also { at += n }
        }

        private fun length(low: Int): Long = when {
            low < 24 -> low.toLong()
            low == 24 -> take(1)[0].toLong() and 0xff
            low == 25 -> ByteBuffer.wrap(take(2)).short.toLong() and 0xffff
            low == 26 -> ByteBuffer.wrap(take(4)).int.toLong() and 0xffffffffL
            low == 27 -> ByteBuffer.wrap(take(8)).long.also { require(it >= 0) { "CBOR: number too large" } }
            else -> throw IllegalArgumentException("CBOR: unsupported length")
        }

        fun value(depth: Int): Any? {
            require(depth < 8) { "CBOR: nested too deep" }
            val first = take(1)[0].toInt() and 0xff
            val low = first and 31
            return when (first shr 5) {
                0 -> length(low)
                1 -> -1 - length(low)
                2 -> take(count(low))
                3 -> String(take(count(low)))
                4 -> List(count(low)) { value(depth + 1) }
                5 -> LinkedHashMap<Any?, Any?>().apply {
                    repeat(count(low)) {
                        val key = value(depth + 1)
                        require(key is Long || key is String) { "CBOR: unsupported map key" }
                        require(!containsKey(key)) { "CBOR: duplicate map key" }
                        put(key, value(depth + 1))
                    }
                }
                else -> when (first) {
                    0xf4 -> false
                    0xf5 -> true
                    0xf6 -> null
                    else -> throw IllegalArgumentException("CBOR: unsupported type")
                }
            }
        }

        /** A length or item count can never exceed the bytes that are left; checked before it is narrowed to Int. */
        private fun count(low: Int): Int = length(low).also { require(it <= bytes.size - at) { "CBOR: impossible length" } }.toInt()
    }
}

/** The byte formats of a passkey (W3C WebAuthn level 3). Pure Kotlin, so the unit tests run on a computer. */
object WebAuthn {
    /** This trial app's own identity as a passkey holder (random, trial only). */
    val AAGUID: ByteArray = hex("8bd4e8e34c274d33bb487358c2819c52")

    /** Person present (0x01) and verified by fingerprint/face (0x04). Never "can be backed up": the key stays in one phone. */
    const val GET_FLAGS = 0x05

    /** As above, plus "new key attached" (0x40). */
    const val CREATE_FLAGS = 0x45

    fun b64(bytes: ByteArray): String = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    fun unb64(text: String): ByteArray = Base64.getUrlDecoder().decode(text)
    fun sha256(bytes: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(bytes)
    fun hex(text: String): ByteArray = ByteArray(text.length / 2) { text.substring(it * 2, it * 2 + 2).toInt(16).toByte() }

    /** A curve coordinate as exactly 32 bytes (BigInteger adds a sign byte or drops leading zeros). */
    fun fixed32(n: BigInteger): ByteArray {
        val raw = n.toByteArray().dropWhile { it == 0.toByte() }
        require(raw.size <= 32) { "coordinate too long" }
        return ByteArray(32 - raw.size) + raw
    }

    /** The public key in COSE form: EC2 key (1: 2), ES256 (3: -7), curve P-256 (-1: 1), x, y. */
    fun coseKey(x: BigInteger, y: BigInteger): ByteArray =
        Cbor.encode(linkedMapOf(1 to 2, 3 to -7, -1 to 1, -2 to fixed32(x), -3 to fixed32(y)))

    /** Authenticator data: site hash, flags, counter (always 0: no counter), and for a new key its ID and public key. */
    fun authData(rpId: String, flags: Int, credentialId: ByteArray? = null, coseKey: ByteArray? = null): ByteArray {
        val out = ByteArrayOutputStream()
        out.write(sha256(rpId.toByteArray()))
        out.write(flags)
        out.write(ByteArray(4))
        if (credentialId != null && coseKey != null) {
            out.write(AAGUID)
            out.write(ByteBuffer.allocate(2).putShort(credentialId.size.toShort()).array())
            out.write(credentialId)
            out.write(coseKey)
        }
        return out.toByteArray()
    }

    /** Without a signature: format "none". With one: Android key attestation (signature plus the key's certificates). */
    fun attestationObject(authData: ByteArray, signature: ByteArray? = null, certificates: List<ByteArray> = emptyList()): ByteArray =
        Cbor.encode(
            if (signature == null) linkedMapOf("fmt" to "none", "attStmt" to emptyMap<String, Any>(), "authData" to authData)
            else linkedMapOf(
                "fmt" to "android-key",
                "attStmt" to linkedMapOf("alg" to -7, "sig" to signature, "x5c" to certificates),
                "authData" to authData,
            ),
        )

    /**
     * A website may use a key only for its own host or a parent of it: login.example.org may use example.org.
     * A name without a dot (a bare ending such as "com") is never a site. Two-part public endings such as "co.uk"
     * are not known here: the verified browser has already refused them before it calls (it holds the full list).
     */
    fun siteMayUse(host: String, rpId: String): Boolean =
        rpId.contains('.') && !rpId.startsWith(".") && !rpId.endsWith(".") && (host == rpId || host.endsWith(".$rpId"))

    /**
     * Who may ask for a key or a signature:
     * - a caller whose website claim Android verified against the list of real browsers (this includes Google
     *   Play services on the QR route); only such a caller's client-data hash is ever signed;
     * - our own app, which names no website and whose client data we write ourselves.
     * A caller that claims a website without being verified, and every other app, is refused.
     */
    fun callerAllowed(verifiedOrigin: String?, statesWebsite: Boolean, ownApp: Boolean): Boolean =
        verifiedOrigin != null || (!statesWebsite && ownApp)
}
