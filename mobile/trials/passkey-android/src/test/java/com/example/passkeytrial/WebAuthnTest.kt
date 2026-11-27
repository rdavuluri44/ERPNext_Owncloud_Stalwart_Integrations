package com.example.passkeytrial

import java.math.BigInteger
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WebAuthnTest {
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }

    @Test
    fun cborMatchesTheStandardExamples() { // RFC 8949, appendix A
        assertEquals("00", hex(Cbor.encode(0)))
        assertEquals("17", hex(Cbor.encode(23)))
        assertEquals("1818", hex(Cbor.encode(24)))
        assertEquals("190100", hex(Cbor.encode(256)))
        assertEquals("1a000f4240", hex(Cbor.encode(1000000)))
        assertEquals("26", hex(Cbor.encode(-7)))
        assertEquals("3863", hex(Cbor.encode(-100)))
        assertEquals("4401020304", hex(Cbor.encode(byteArrayOf(1, 2, 3, 4))))
        assertEquals("6449455446", hex(Cbor.encode("IETF")))
        assertEquals("83010203", hex(Cbor.encode(listOf(1, 2, 3))))
        assertEquals("a201020304", hex(Cbor.encode(linkedMapOf(1 to 2, 3 to 4))))
    }

    @Test
    fun coordinatesAreAlways32Bytes() {
        assertEquals(32, WebAuthn.fixed32(BigInteger.ONE).size)
        assertEquals(1, WebAuthn.fixed32(BigInteger.ONE)[31].toInt())
        val high = BigInteger(1, ByteArray(32) { 0xff.toByte() }) // BigInteger adds a sign byte here
        assertEquals(33, high.toByteArray().size)
        assertArrayEquals(ByteArray(32) { 0xff.toByte() }, WebAuthn.fixed32(high))
    }

    @Test
    fun publicKeyIsAnEs256CoseKey() {
        val key = WebAuthn.coseKey(BigInteger.ONE, BigInteger.TWO)
        assertEquals(77, key.size)
        assertEquals("a5010203262001215820", hex(key.copyOf(10)))
        assertEquals("225820", hex(key.copyOfRange(42, 45)))
    }

    @Test
    fun authDataForSignInIs37BytesAndNeverMarkedAsBackedUp() {
        val data = WebAuthn.authData("example.org", WebAuthn.GET_FLAGS)
        assertEquals(37, data.size)
        assertArrayEquals(WebAuthn.sha256("example.org".toByteArray()), data.copyOf(32))
        assertEquals(0x05, data[32].toInt())
        assertEquals(0, data[32].toInt() and 0x18) // backup-eligible and backed-up bits stay off
        assertArrayEquals(ByteArray(4), data.copyOfRange(33, 37))
    }

    @Test
    fun authDataForANewKeyCarriesIdentityIdAndKey() {
        val id = ByteArray(16) { it.toByte() }
        val key = WebAuthn.coseKey(BigInteger.ONE, BigInteger.TWO)
        val data = WebAuthn.authData("example.org", WebAuthn.CREATE_FLAGS, id, key)
        assertEquals(37 + 16 + 2 + 16 + 77, data.size)
        assertEquals(0x45, data[32].toInt())
        assertArrayEquals(WebAuthn.AAGUID, data.copyOfRange(37, 53))
        assertEquals("0010", hex(data.copyOfRange(53, 55)))
        assertArrayEquals(id, data.copyOfRange(55, 71))
        assertArrayEquals(key, data.copyOfRange(71, data.size))
    }

    @Test
    fun attestationIsNoneWithoutASignatureAndAndroidKeyWithOne() {
        val data = ByteArray(37)
        val none = hex(WebAuthn.attestationObject(data))
        assertTrue(none.startsWith("a363666d74646e6f6e656761747453746d74a0686175746844617461" + "5825"))
        val signed = hex(WebAuthn.attestationObject(data, byteArrayOf(9), listOf(byteArrayOf(7))))
        assertTrue(signed.startsWith("a363666d746b616e64726f69642d6b6579" + "6761747453746d74a363616c672663736967410963783563814107"))
    }

    @Test
    fun aSiteMayOnlyUseItsOwnOrParentAddress() {
        assertTrue(WebAuthn.siteMayUse("example.org", "example.org"))
        assertTrue(WebAuthn.siteMayUse("login.example.org", "example.org"))
        assertFalse(WebAuthn.siteMayUse("evilexample.org", "example.org"))
        assertFalse(WebAuthn.siteMayUse("example.org", "login.example.org"))
        assertFalse(WebAuthn.siteMayUse("example.org", ""))
        assertFalse(WebAuthn.siteMayUse("example.org", "org")) // a bare ending is never a site
        assertFalse(WebAuthn.siteMayUse("example.org", ".org"))
    }

    @Test
    fun onlyAVerifiedBrowserOrOurOwnAppIsServed() {
        assertTrue(WebAuthn.callerAllowed("https://example.org", statesWebsite = true, ownApp = false)) // verified browser
        assertTrue(WebAuthn.callerAllowed(null, statesWebsite = false, ownApp = true)) // our own app, names no website
        // The reviewed hole: an app that claims a website without being a verified browser, with or without a hash.
        assertFalse(WebAuthn.callerAllowed(null, statesWebsite = true, ownApp = false))
        assertFalse(WebAuthn.callerAllowed(null, statesWebsite = true, ownApp = true))
        assertFalse(WebAuthn.callerAllowed(null, statesWebsite = false, ownApp = false)) // any other app on the phone
    }

    @Test
    fun base64UrlHasNoPaddingAndRoundTrips() {
        val bytes = byteArrayOf(-1, -2, -3, 4)
        assertEquals("__79BA", WebAuthn.b64(bytes))
        assertArrayEquals(bytes, WebAuthn.unb64("__79BA"))
    }
}
