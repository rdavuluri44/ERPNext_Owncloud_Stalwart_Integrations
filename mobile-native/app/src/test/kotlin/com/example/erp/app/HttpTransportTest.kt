package com.example.erp.app

import com.example.erp.core.Outcome
import com.example.erp.core.Point
import com.example.erp.core.Reply
import com.example.erp.core.Saver
import com.example.erp.core.Tracer
import java.net.InetAddress
import java.net.ServerSocket
import java.net.URI
import kotlin.concurrent.thread
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

/** The real connection against a pretend server on this computer: what is sent, and how every answer is read. */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35])
class HttpTransportTest {
    private val id = "req_0123456789abcdef"

    /** Answers one request with a fixed answer and keeps what it was sent. */
    private class Pretend(status: Int, body: String, extraHeaders: String = "") : AutoCloseable {
        private val socket = ServerSocket(0, 1, InetAddress.getByName("127.0.0.1"))

        @Volatile
        var request = ""
        private val worker = thread {
            runCatching {
                socket.accept().use { client ->
                    val input = client.getInputStream().bufferedReader(Charsets.ISO_8859_1)
                    val head = StringBuilder()
                    var length = 0
                    while (true) {
                        val line = input.readLine() ?: break
                        if (line.isEmpty()) break
                        head.appendLine(line)
                        if (line.startsWith("Content-Length:", ignoreCase = true)) length = line.substringAfter(":").trim().toInt()
                    }
                    val chars = CharArray(length)
                    var read = 0
                    while (read < length) {
                        val n = input.read(chars, read, length - read)
                        if (n < 0) break
                        read += n
                    }
                    request = head.toString() + "\n" + String(chars, 0, read)
                    val bytes = body.toByteArray()
                    val headers = "HTTP/1.1 $status Answer\r\nContent-Length: ${bytes.size}\r\nConnection: close\r\n$extraHeaders\r\n"
                    client.getOutputStream().apply { write(headers.toByteArray() + bytes); flush() }
                }
            }
        }
        val base: String get() = URI("http", null, "127.0.0.1", socket.localPort, null, null, null).toString()

        override fun close() {
            if (request.isEmpty()) socket.close() // nobody called: stop waiting
            worker.join(3000)
            socket.close()
        }
    }

    private fun address(scheme: String, rest: String) = "$scheme://$rest"

    @Test
    fun aCallCarriesItsTrackingNumberAndTokenAndReadsTheRecordBack() {
        Pretend(200, """{"message": {"name": "FAE-1", "state": "Submitted", "remarks": null, "count": 3}}""").use { server ->
            val reply = HttpTransport(server.base) { "token-abc" }.call("custom_hr.api.self_check_in", mapOf("site" to "SITE-0001", "remarks" to null), id)
            assertEquals(Reply.Answer(200, null, mapOf("name" to "FAE-1", "state" to "Submitted", "remarks" to null, "count" to "3")), (reply as Reply.Answer).copy(tookMs = 0))
            val sent = server.request
            assertTrue(sent, sent.startsWith("POST /api/method/custom_hr.api.self_check_in HTTP/1.1"))
            assertTrue(sent, sent.contains("X-Request-ID: $id"))
            assertTrue(sent, sent.contains("Authorization: Bearer token-abc"))
            assertTrue(sent, sent.endsWith("""{"site":"SITE-0001","remarks":null}"""))
            assertFalse("the token is never part of an address", sent.lineSequence().first().contains("token"))
        }
    }

    @Test
    fun amountsComeBackWrittenOutInFullNeverAsPowersOfTen() {
        Pretend(200, """{"message": {"grand_total": 12500000.50, "qty": 0.0005, "rate": 150000.0, "count": 12500000, "done": true}}""").use { server ->
            val fields = (HttpTransport(server.base).call("frappe.ping", emptyMap(), id) as Reply.Answer).fields
            assertEquals(mapOf("grand_total" to "12500000.5", "qty" to "0.0005", "rate" to "150000", "count" to "12500000", "done" to "true"), fields)
        }
    }

    @Test
    fun anAnswerWithoutARecordOrWithoutABodyIsRead() {
        Pretend(200, "{}").use { server ->
            assertEquals(Reply.Answer(200), (HttpTransport(server.base).call("frappe.ping", emptyMap(), id) as Reply.Answer).copy(tookMs = 0))
        }
        Pretend(403, "").use { server ->
            assertEquals(Reply.Answer(403), (HttpTransport(server.base).call("frappe.ping", emptyMap(), id) as Reply.Answer).copy(tookMs = 0))
        }
    }

    @Test
    fun withoutASignInNoTokenHeaderIsSent() {
        Pretend(200, """{"message": "pong"}""").use { server ->
            val reply = HttpTransport(server.base).call("frappe.ping", emptyMap(), id) as Reply.Answer
            assertEquals(mapOf("value" to "pong"), reply.fields)
            assertFalse(server.request.contains("Authorization"))
        }
    }

    @Test
    fun aRefusalBringsTheServersOwnSentence() {
        val body = """{"exc_type": "ValidationError", "_server_messages": "[\"{\\\"message\\\": \\\"You are 180 m outside the site.\\\"}\"]"}"""
        Pretend(417, body).use { server ->
            val result = Saver(Tracer(), HttpTransport(server.base)).save(id, "Check-in", "custom_hr.api.self_check_in", mapOf("site" to "SITE-0001"))
            assertEquals(Outcome.REFUSED, result.outcome)
            assertEquals("You are 180 m outside the site.", result.sentence)
            assertEquals(Point.SERVER, result.trace.fault?.point)
        }
    }

    @Test
    fun signedOutAndNotAllowedAreToldApart() {
        Pretend(401, """{"message": "Not signed in"}""").use { server ->
            val result = Saver(Tracer(), HttpTransport(server.base)).save(id, "Check-in", "custom_hr.api.self_check_in", emptyMap())
            assertEquals(Outcome.NOT_SIGNED_IN, result.outcome)
            assertEquals(Point.GATEWAY, result.trace.fault?.point)
        }
        Pretend(403, """{"exc_type": "PermissionError", "_server_messages": "[\"{\\\"message\\\": \\\"You cannot record attendance at this site.\\\"}\"]"}""").use { server ->
            val result = Saver(Tracer(), HttpTransport(server.base)).save(id, "Check-in", "custom_hr.api.self_check_in", emptyMap())
            assertEquals(Outcome.NOT_ALLOWED, result.outcome)
            assertEquals("You cannot record attendance at this site.", result.sentence)
            assertEquals(Point.SERVER, result.trace.fault?.point)
        }
    }

    @Test
    fun aRedirectIsNeverFollowedAndMeansSignedOut() {
        // The redirect points at a second server that would answer "saved". It must never be asked, and so never
        // sees the sign-in token.
        Pretend(200, """{"message": {"name": "FAE-1"}}""").use { other ->
            Pretend(307, "", "Location: ${other.base}/api/method/custom_hr.api.self_check_in\r\n").use { server ->
                val result = Saver(Tracer(), HttpTransport(server.base) { "token-abc" }).save(id, "Check-in", "custom_hr.api.self_check_in", emptyMap())
                assertEquals(Outcome.NOT_SIGNED_IN, result.outcome)
            }
            assertEquals("the other server was not called", "", other.request)
        }
    }

    @Test
    fun aPageInsteadOfAnAnswerIsNeverSaved() {
        Pretend(200, "<html><body>Sign in to this network</body></html>").use { server ->
            val result = Saver(Tracer(), HttpTransport(server.base)).save(id, "Check-in", "custom_hr.api.self_check_in", emptyMap())
            assertEquals(Outcome.SERVER_FAILED, result.outcome)
        }
        Pretend(500, "<html>Internal Server Error</html>").use { server ->
            val reply = HttpTransport(server.base).call("frappe.ping", emptyMap(), id) as Reply.Answer
            assertEquals(500, reply.status)
            assertNull(reply.message)
        }
    }

    @Test
    fun nothingListeningIsNoConnection() {
        val port = ServerSocket(0).use { it.localPort }
        val base = URI("http", null, "127.0.0.1", port, null, null, null).toString()
        val result = Saver(Tracer(), HttpTransport(base)).save(id, "Check-in", "custom_hr.api.self_check_in", emptyMap())
        assertEquals(Outcome.NO_CONNECTION, result.outcome)
        assertEquals(Point.NETWORK, result.trace.fault?.point)
    }

    @Test
    fun onlyAnEncryptedPlainHostIsAcceptedAsTheServer() {
        HttpTransport(address("https", "erp.example.com"))
        HttpTransport(address("https", "erp.example.com:8443/"))
        for (bad in listOf(
            address("http", "erp.example.com"), // not encrypted
            address("http", "localhost"), // only the loopback number itself, never a name that can be pointed elsewhere
            address("https", "erp.example.com/app"), // a path
            address("https", "user:secret@erp.example.com"), // a password in the address
            address("https", "erp.example.com?next=x"),
            address("ftp", "erp.example.com"),
            "erp.example.com",
            "",
        )) {
            assertThrows(bad, IllegalArgumentException::class.java) { HttpTransport(bad) }
        }
    }

    @Test
    fun aMethodNameCannotLeaveTheServersFunctionPath() {
        val transport = HttpTransport(address("https", "erp.example.com"))
        for (bad in listOf("../../login", "a/b", "ping?x=1", "ping#x", "", "a..b", " ping")) {
            assertThrows(bad, IllegalArgumentException::class.java) { transport.call(bad, emptyMap(), id) }
        }
        assertThrows(IllegalArgumentException::class.java) { transport.call("frappe.ping", emptyMap(), "short") }
    }
}
