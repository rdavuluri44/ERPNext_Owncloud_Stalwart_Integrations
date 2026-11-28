package com.example.erp.app

import com.example.erp.core.Reply
import com.example.erp.core.Transport
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URI
import org.json.JSONArray
import org.json.JSONObject

/**
 * The one real connection to the server. Every call of the app goes through here, so these hold for all of them:
 * - it talks to the one configured server and to nothing else: a redirect is never followed, it is handed back
 *   (the saving layer reads it as "signed out");
 * - encrypted only (https). The single exception is the device's own loopback address, which the tests' pretend
 *   server uses; nothing sent there leaves the device;
 * - the tracking number travels with every call;
 * - the sign-in token, when there is one, goes only into the Authorization header, never into an address.
 * It must be called off the main thread.
 */
class HttpTransport(base: String, private val token: () -> String? = { null }) : Transport {
    private val root: URI

    init {
        val uri = runCatching { URI(base) }.getOrNull()
        require(
            uri != null && uri.host != null && uri.userInfo == null && uri.query == null && uri.fragment == null &&
                uri.path.orEmpty().trim('/').isEmpty(),
        ) { "the server address is a host and nothing else" }
        require(uri.scheme == "https" || (uri.scheme == "http" && uri.host == LOOPBACK)) { "the server is reached encrypted only" }
        root = uri
    }

    override fun call(method: String, args: Map<String, String?>, trackingId: String): Reply {
        require(METHOD.matches(method)) { "not a server method name" }
        require(TRACKING.matches(trackingId)) { "not a tracking number" }
        val started = System.nanoTime()
        fun took() = (System.nanoTime() - started) / 1_000_000
        val connection = try {
            root.resolve("/api/method/$method").toURL().openConnection() as HttpURLConnection
        } catch (e: IOException) {
            return Reply.NoConnection(e.javaClass.simpleName, took())
        }
        try {
            connection.requestMethod = "POST"
            connection.instanceFollowRedirects = false
            connection.connectTimeout = CONNECT_MS
            connection.readTimeout = READ_MS
            connection.useCaches = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("X-Request-ID", trackingId)
            token()?.let { connection.setRequestProperty("Authorization", "Bearer $it") }
            val body = JSONObject()
            for ((name, value) in args) body.put(name, value ?: JSONObject.NULL)
            connection.doOutput = true
            connection.outputStream.use { it.write(body.toString().toByteArray()) }
            val status = connection.responseCode
            val text = (if (status < 400) connection.inputStream else connection.errorStream)?.use(::readCapped).orEmpty()
            return answer(status, text, took())
        } catch (e: IOException) {
            // No signal, a timeout, an unknown host, a certificate that is not the server's.
            return Reply.NoConnection(e.javaClass.simpleName, took())
        } finally {
            connection.disconnect()
        }
    }

    private companion object {
        const val LOOPBACK = "127.0.0.1"
        const val CONNECT_MS = 10_000
        const val READ_MS = 30_000
        const val MAX_BYTES = 1_048_576
        val METHOD = Regex("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)*")
        val TRACKING = Regex("[A-Za-z0-9_-]{16,80}")

        /** An answer larger than any real one is cut, so a faulty server cannot fill the phone's memory. */
        fun readCapped(stream: InputStream): String {
            val buffer = ByteArray(8192)
            val out = java.io.ByteArrayOutputStream()
            while (out.size() < MAX_BYTES) {
                val n = stream.read(buffer, 0, minOf(buffer.size, MAX_BYTES - out.size()))
                if (n < 0) break
                out.write(buffer, 0, n)
            }
            return out.toString(Charsets.UTF_8.name())
        }

        fun answer(status: Int, text: String, tookMs: Long): Reply {
            val json = runCatching { JSONObject(text) }.getOrNull()
            if (json == null) {
                // The server's functions always answer in JSON. A "success" that is a page came from something in
                // between (a sign-in page, a hotspot's page), so the function was not reached: never "saved".
                return Reply.Answer(if (status in 200..299) 502 else status, tookMs = tookMs)
            }
            val message = json.opt("message")
            val fields: Map<String, String?> = when (message) {
                is JSONObject -> message.keys().asSequence().associateWith { if (message.isNull(it)) null else plain(message.get(it)) }
                null, JSONObject.NULL -> emptyMap()
                else -> mapOf("value" to plain(message))
            }
            return Reply.Answer(status, if (status >= 400) sentence(json) else null, fields, tookMs)
        }

        /**
         * A value as text. Numbers are written out in full: the reader's own form for large and small numbers
         * ("1.25E7") is not an amount anyone can read or compare.
         * ponytail: the reader keeps about 15 significant digits of a decimal; enough for any amount in rupees and
         * paise. Read the number's original text (android.util.JsonReader) if a longer number ever matters.
         */
        fun plain(value: Any): String = when (value) {
            is Double, is Float -> java.math.BigDecimal(value.toString()).stripTrailingZeros().toPlainString()
            else -> value.toString()
        }

        /** The server's own words for a refusal. Whether a person may read them is decided by the saving layer. */
        fun sentence(json: JSONObject): String? {
            val first = runCatching { JSONObject(JSONArray(json.getString("_server_messages")).getString(0)).getString("message") }.getOrNull()
            return first ?: (json.opt("message") as? String) ?: (json.opt("exception") as? String)
        }
    }
}
