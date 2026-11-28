package com.example.erp.core

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Test

class SealTest {
    private val key = ByteArray(32) { it.toByte() }
    private val secret = "a sign-in token".toByteArray()

    @Test
    fun whatIsSealedOpensWithTheSameKeyAndName() {
        assertArrayEquals(secret, Seal.open(key, "token", Seal.seal(key, "token", secret)))
        assertArrayEquals(ByteArray(0), Seal.open(key, "empty", Seal.seal(key, "empty", ByteArray(0))))
    }

    @Test
    fun theStoredBytesDoNotShowTheValueAndNeverRepeat() {
        val first = Seal.seal(key, "token", secret)
        val second = Seal.seal(key, "token", secret)
        assertFalse("the same value sealed twice looks different", first.contentEquals(second))
        assertFalse(String(first, Charsets.ISO_8859_1).contains("sign-in"))
    }

    @Test
    fun aWipedKeySealsNothing() {
        assertThrows(IllegalArgumentException::class.java) { Seal.seal(ByteArray(32), "token", secret) }
        assertThrows(IllegalArgumentException::class.java) { Seal.seal(ByteArray(16) { 1 }, "token", secret) }
    }

    @Test
    fun aWrongKeyAWrongNameOrAChangedByteOpensNothing() {
        val sealed = Seal.seal(key, "token", secret)
        assertNull("another key", Seal.open(ByteArray(32) { 9 }, "token", sealed))
        assertNull("a key wiped to zeros", Seal.open(ByteArray(32), "token", sealed))
        assertNull("passed off under another name", Seal.open(key, "refresh", sealed))
        for (at in sealed.indices) {
            val changed = sealed.copyOf().also { it[at] = (it[at].toInt() xor 1).toByte() }
            assertNull("byte $at changed", Seal.open(key, "token", changed))
        }
        assertNull("cut short", Seal.open(key, "token", sealed.copyOf(20)))
        assertNull(Seal.open(key, "token", ByteArray(0)))
    }
}
