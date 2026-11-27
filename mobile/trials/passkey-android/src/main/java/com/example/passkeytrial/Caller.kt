package com.example.passkeytrial

import android.content.Context
import android.net.Uri
import androidx.annotation.RequiresApi
import androidx.credentials.provider.CallingAppInfo
import org.json.JSONObject

/**
 * Who asks, and for which website. A browser (or Google Play services, for a computer's QR sign-in) states the
 * website's address; Android lets us trust that only for callers on Google's public list. An ordinary app is
 * identified by its signing certificate.
 */
@RequiresApi(34)
class Caller(context: Context, private val info: CallingAppInfo, private val suppliedHash: ByteArray?) {
    /** The website, only when Android verified the caller against the list of real browsers. */
    val origin: String?

    /** False for every caller we must not serve (see [WebAuthn.callerAllowed]). */
    val allowed: Boolean
    val summary: String

    init {
        val list = Store.browsers(context)
        var seen: String? = null
        var note = if (list == null) "browser list missing" else "ok"
        if (list != null) {
            try {
                seen = info.getOrigin(list)
            } catch (e: IllegalStateException) {
                note = "caller states a website but is NOT on the browser list"
            }
        }
        origin = seen
        allowed = WebAuthn.callerAllowed(seen, info.isOriginPopulated(), info.packageName == context.packageName)
        summary = "caller=${info.packageName} statesWebsite=${info.isOriginPopulated()} verified=${seen != null} hashSupplied=${suppliedHash != null} allowed=$allowed ($note)"
    }

    /** A verified website may use only its own site's key. Our own app (no website) decides the site itself. */
    fun mayUse(rpId: String): Boolean {
        if (!allowed) return false
        val host = origin?.let { Uri.parse(it).host } ?: return true
        return WebAuthn.siteMayUse(host, rpId)
    }

    /**
     * A verified browser sends the hash of its own client data, and only then is a supplied hash signed.
     * For our own app we write the client data ourselves, so the signature always names who really asked.
     */
    fun clientData(type: String, challenge: String): Pair<String, ByteArray> {
        check(allowed) { "caller not allowed" }
        if (origin != null && suppliedHash != null) return "{}" to suppliedHash
        val certificate = info.signingInfo.apkContentsSigners[0].toByteArray()
        val json = JSONObject()
            .put("type", type)
            .put("challenge", challenge)
            .put("origin", "android:apk-key-hash:" + WebAuthn.b64(WebAuthn.sha256(certificate)))
            .put("androidPackageName", info.packageName)
            .toString()
        return json to WebAuthn.sha256(json.toByteArray())
    }
}
