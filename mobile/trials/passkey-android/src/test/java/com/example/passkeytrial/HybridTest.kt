package com.example.passkeytrial

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.interfaces.ECPublicKey
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class HybridTest {
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }

    /** The computer's side of the QR encoding, written independently of the decoder under test. */
    private fun bytesToDigits(data: ByteArray): String {
        val tail = intArrayOf(0, 3, 5, 8, 10, 13, 15)
        return data.toList().chunked(7).joinToString("") { chunk ->
            val number = ByteBuffer.wrap((chunk + List(8 - chunk.size) { 0.toByte() }).toByteArray()).order(ByteOrder.LITTLE_ENDIAN).long
            number.toString().padStart(if (chunk.size == 7) 17 else tail[chunk.size], '0')
        }
    }

    private fun compressed(key: ECPublicKey) =
        byteArrayOf(if (key.w.affineY.testBit(0)) 3 else 2) + WebAuthn.fixed32(key.w.affineX)

    @Test
    fun hkdfMatchesTheStandardExample() { // RFC 5869, test case 1
        val out = Hybrid.hkdf(ByteArray(22) { 0x0b }, WebAuthn.hex("000102030405060708090a0b0c"), WebAuthn.hex("f0f1f2f3f4f5f6f7f8f9"), 42)
        assertEquals("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865", hex(out))
    }

    @Test
    fun cborReaderRoundTripsAndRefusesBrokenInput() {
        val value = linkedMapOf<Any?, Any?>(0L to byteArrayOf(1, 2), 1L to "text", 2L to listOf(1L, -7L, 300L), 4L to false, 5L to true)
        val back = Cbor.decode(Cbor.encode(value)) as Map<*, *>
        assertArrayEquals(byteArrayOf(1, 2), back[0L] as ByteArray)
        assertEquals("text", back[1L])
        assertEquals(listOf(1L, -7L, 300L), back[2L])
        assertEquals(false, back[4L])
        assertEquals(true, back[5L])
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("4401")) } // 4 bytes promised, 1 given
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("0000")) } // extra bytes
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("9b7fffffffffffffff")) } // impossible list size
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(ByteArray(20) { 0x81.toByte() }) } // nested too deep
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("5b0000000100000001" + "00")) } // length above 2^31 must not shrink to 1
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("a2" + "0101" + "0102")) } // the same key twice
        assertThrows(IllegalArgumentException::class.java) { Cbor.decode(WebAuthn.hex("a1" + "4100" + "01")) } // bytes as a map key
    }

    @Test
    fun qrCodeIsReadBackExactly() {
        val computer = Hybrid.newKeyPair().public as ECPublicKey
        val secret = ByteArray(16) { (it * 7).toByte() }
        val content = Cbor.encode(linkedMapOf(0 to compressed(computer), 1 to secret, 2 to 2, 3 to 1790000000, 4 to false, 5 to "ga"))
        val qr = Hybrid.parseQr("FIDO:/" + bytesToDigits(content))
        assertEquals(computer.w, qr.peerKey.w) // both y signs are covered over repeated runs; x and y must match
        assertArrayEquals(secret, qr.secret)
        assertEquals("ga", qr.requestType)
        assertThrows(IllegalArgumentException::class.java) { Hybrid.parseQr("https://example.org") }
        assertThrows(IllegalArgumentException::class.java) { Hybrid.parseQr("FIDO:/12") }
        assertThrows(IllegalArgumentException::class.java) { Hybrid.parseQr("FIDO:/99999999999999999") } // more than 7 bytes
    }

    @Test
    fun digitsCoverEveryTailLength() {
        for (size in 0..20) {
            val data = ByteArray(size) { (200 + it).toByte() }
            assertArrayEquals(data, Hybrid.digitsToBytes(bytesToDigits(data)))
        }
    }

    @Test
    fun bothPointFormsGiveTheSameKey() {
        repeat(8) {
            val key = Hybrid.newKeyPair().public as ECPublicKey
            assertEquals(key.w, Hybrid.decompress(compressed(key)).w)
            assertEquals(key.w, Hybrid.fromUncompressed(Hybrid.uncompressed(key)).w)
        }
        assertThrows(IllegalArgumentException::class.java) { Hybrid.decompress(ByteArray(33)) }
    }

    @Test
    fun pointsThatAreNotOnTheCurveAreRefused() {
        val good = Hybrid.uncompressed(Hybrid.newKeyPair().public as ECPublicKey)
        Hybrid.fromUncompressed(good)
        val bad = good.clone().also { it[64] = (it[64].toInt() xor 1).toByte() } // y changed by one bit
        assertThrows(IllegalArgumentException::class.java) { Hybrid.fromUncompressed(bad) }
        val tooBig = byteArrayOf(4) + ByteArray(64) { 0xff.toByte() } // both numbers above the prime
        assertThrows(IllegalArgumentException::class.java) { Hybrid.fromUncompressed(tooBig) }
        assertThrows(IllegalArgumentException::class.java) { Hybrid.fromUncompressed(byteArrayOf(4) + ByteArray(64)) } // (0, 0)
        assertThrows(IllegalArgumentException::class.java) { Hybrid.decompress(byteArrayOf(2) + ByteArray(32) { 0xff.toByte() }) }
    }

    @Test
    fun channelGivesEveryMessageItsOwnNonceAlsoFromManyThreads() {
        val a = Hybrid.Channel(read = ByteArray(32) { 1 }, write = ByteArray(32) { 2 })
        val sealed = java.util.Collections.synchronizedList(mutableListOf<ByteArray>())
        val threads = List(8) { Thread { repeat(200) { sealed += a.seal(ByteArray(0)) } } }
        threads.forEach(Thread::start)
        threads.forEach(Thread::join)
        // The same empty message under the same key: equal bytes would mean a nonce was used twice.
        assertEquals(1600, sealed.map { it.joinToString("") { b -> "%02x".format(b) } }.toSet().size)
    }

    @Test
    fun advertIsOnlyReadableWithTheQrSecret() {
        val key = Hybrid.eidKey(ByteArray(16) { 1 })
        val plain = Hybrid.advertPlaintext(ByteArray(10) { 9 }, byteArrayOf(0xa, 0xb, 0xc), 0)
        assertEquals(16, plain.size)
        assertEquals("0a0b0c0000", hex(plain.copyOfRange(11, 16)))
        val advert = Hybrid.advert(key, plain)
        assertEquals(20, advert.size)
        assertArrayEquals(plain, Hybrid.readAdvert(key, advert))
        assertNull(Hybrid.readAdvert(Hybrid.eidKey(ByteArray(16) { 2 }), advert))
        assertEquals("0001", hex(Hybrid.advertPlaintext(ByteArray(10), ByteArray(3), 256).copyOfRange(14, 16)))
    }

    @Test
    fun relayNamesFollowTheStandard() {
        assertEquals("cable.ua5v.com", Hybrid.relayDomain(0))
        assertEquals("cable.auth.com", Hybrid.relayDomain(1))
        assertEquals("cable.wufkweyy3uaxb.com", Hybrid.relayDomain(266)) // the value Chromium's own test expects
        assertThrows(IllegalArgumentException::class.java) { Hybrid.relayDomain(2) }
    }

    @Test
    fun handshakeGivesBothSidesTheSameChannelAndRejectsAStranger() {
        val computerStatic = Hybrid.newKeyPair()
        val secret = ByteArray(16) { 5 }
        val plain = Hybrid.advertPlaintext(ByteArray(10) { 3 }, ByteArray(3) { 1 }, 0)
        val psk = Hybrid.psk(secret, plain)
        val staticKey = computerStatic.public as ECPublicKey

        val computer = Hybrid.Noise(staticKey, psk)
        val computerEphemeral = Hybrid.newKeyPair()
        val hello = computer.start(computerEphemeral)
        val (answer, phoneChannel) = Hybrid.Noise(staticKey, psk).respond(hello, staticKey)
        val computerChannel = computer.finish(answer, computerEphemeral, computerStatic.private)

        val request = byteArrayOf(1, 2) + ByteArray(40) { it.toByte() }
        assertArrayEquals(request, phoneChannel.open(computerChannel.seal(request)))
        assertArrayEquals(byteArrayOf(7), computerChannel.open(phoneChannel.seal(byteArrayOf(7))))
        val full = computerChannel.seal(ByteArray(32))
        assertEquals(64 + 16, full.size) // a full block still gets padding, plus the 16-byte tag
        assertEquals(32, phoneChannel.open(full).size)
        assertArrayEquals(ByteArray(0), phoneChannel.open(computerChannel.seal(ByteArray(0))))

        // A computer that saw the QR code but did not hear this phone's advert has the wrong shared secret.
        val stranger = Hybrid.Noise(staticKey, Hybrid.psk(secret, Hybrid.advertPlaintext(ByteArray(10), ByteArray(3), 0)))
        val strangerHello = stranger.start(Hybrid.newKeyPair())
        assertThrows(javax.crypto.AEADBadTagException::class.java) { Hybrid.Noise(staticKey, psk).respond(strangerHello, staticKey) }
        // A replayed message does not open twice (the counter moved on).
        val once = computerChannel.seal(byteArrayOf(1))
        phoneChannel.open(once)
        assertThrows(javax.crypto.AEADBadTagException::class.java) { phoneChannel.open(once) }
    }

    @Test
    fun signInRequestAndAnswerUseTheCtapLayout() {
        val id = ByteArray(16) { 4 }
        val request = Cbor.encode(
            linkedMapOf(1 to "example.org", 2 to ByteArray(32) { 8 }, 3 to listOf(linkedMapOf("id" to id, "type" to "public-key")), 5 to linkedMapOf("uv" to true)),
        )
        val parsed = Hybrid.parseSignIn(request)
        assertEquals("example.org", parsed.rpId)
        assertEquals(32, parsed.clientDataHash.size)
        assertArrayEquals(id, parsed.allowed.single())
        assertTrue(Hybrid.parseSignIn(Cbor.encode(linkedMapOf(1 to "example.org", 2 to ByteArray(32)))).allowed.isEmpty())

        val answer = Hybrid.signInAnswer(id, ByteArray(37), byteArrayOf(1), byteArrayOf(2))
        assertEquals(0, answer[0].toInt())
        val map = Cbor.decode(answer.copyOfRange(1, answer.size)) as Map<*, *>
        assertArrayEquals(id, (map[1L] as Map<*, *>)["id"] as ByteArray)
        assertEquals(37, (map[2L] as ByteArray).size)
        assertNotNull(map[3L])
        assertArrayEquals(byteArrayOf(2), (map[4L] as Map<*, *>)["id"] as ByteArray)

        val create = Hybrid.parseCreate(
            Cbor.encode(
                linkedMapOf(
                    1 to ByteArray(32) { 6 },
                    2 to linkedMapOf("id" to "example.org", "name" to "Example"),
                    3 to linkedMapOf("id" to byteArrayOf(5, 5), "name" to "trial-user"),
                    4 to listOf(linkedMapOf("alg" to -7, "type" to "public-key"), linkedMapOf("alg" to -257, "type" to "public-key")),
                    5 to listOf(linkedMapOf("id" to id, "type" to "public-key")),
                ),
            ),
        )
        assertEquals("example.org", create.rpId)
        assertEquals("trial-user", create.userName)
        assertArrayEquals(byteArrayOf(5, 5), create.userId)
        assertEquals(listOf(-7L, -257L), create.algorithms)
        assertArrayEquals(id, create.excluded.single())
        val made = Cbor.decode(Hybrid.createAnswer(ByteArray(148)).drop(1).toByteArray()) as Map<*, *>
        assertEquals("none", made[1L])
        assertEquals(148, (made[2L] as ByteArray).size)
        val attested = Cbor.decode(Hybrid.createAnswer(ByteArray(148), byteArrayOf(9), listOf(byteArrayOf(7), byteArrayOf(8))).drop(1).toByteArray()) as Map<*, *>
        assertEquals("android-key", attested[1L])
        assertEquals(-7L, (attested[3L] as Map<*, *>)["alg"])
        assertEquals(2, ((attested[3L] as Map<*, *>)["x5c"] as List<*>).size)

        val info = Cbor.decode(Hybrid.info()) as Map<*, *>
        assertEquals(true, (info[4L] as Map<*, *>)["uv"])
        assertArrayEquals(WebAuthn.AAGUID, info[3L] as ByteArray)
    }
}
