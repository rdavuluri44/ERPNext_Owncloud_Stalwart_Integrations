package com.example.passkeytrial

import android.content.Context
import android.util.Log
import java.io.File
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import org.json.JSONArray
import org.json.JSONObject

/** What the trial remembers: the list of passkeys (public details only; private keys never leave the secure hardware) and a log. */
object Store {
    private const val TAG = "PasskeyTrial"
    private const val BROWSERS = "https://www.gstatic.com/gpm-passkeys-privileged-apps/apps.json"

    class Passkey(val id: String, val rpId: String, val userHandle: String, val userName: String) {
        val alias get() = "passkey-$id"
    }

    private fun prefs(context: Context) = context.getSharedPreferences("trial", Context.MODE_PRIVATE)

    fun passkeys(context: Context): List<Passkey> {
        val rows = JSONArray(prefs(context).getString("passkeys", "[]"))
        return (0 until rows.length()).map { rows.getJSONObject(it) }
            .map { Passkey(it.getString("id"), it.getString("rpId"), it.getString("userHandle"), it.getString("userName")) }
    }

    private fun save(context: Context, list: List<Passkey>) {
        val rows = JSONArray()
        list.forEach { rows.put(JSONObject().put("id", it.id).put("rpId", it.rpId).put("userHandle", it.userHandle).put("userName", it.userName)) }
        prefs(context).edit().putString("passkeys", rows.toString()).apply()
    }

    fun add(context: Context, passkey: Passkey) = save(context, passkeys(context) + passkey)

    fun clear(context: Context) {
        passkeys(context).forEach { Keys.delete(it.alias) }
        save(context, emptyList())
    }

    fun log(context: Context, line: String) {
        Log.i(TAG, line)
        val stamp = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date())
        val text = (prefs(context).getString("log", "") + "\n$stamp $line").takeLast(20000)
        prefs(context).edit().putString("log", text).apply()
    }

    fun logText(context: Context): String = prefs(context).getString("log", "")!!.trim()
    fun clearLog(context: Context) = prefs(context).edit().remove("log").apply()

    /** Trial switch: send Android key attestation (the key's certificates) instead of "none" when a key is made. */
    fun attest(context: Context) = prefs(context).getBoolean("attest", false)
    fun setAttest(context: Context, on: Boolean) = prefs(context).edit().putBoolean("attest", on).apply()

    private fun browsersFile(context: Context) = File(context.filesDir, "privileged-browsers.json")

    /** Google's public list of browsers allowed to state a website's address; null until fetched once. */
    fun browsers(context: Context): String? = browsersFile(context).takeIf { it.exists() }?.readText()

    fun fetchBrowsers(context: Context) = Thread {
        runCatching { browsersFile(context).writeText(URL(BROWSERS).readText()) }
            .onFailure { log(context, "browser list not fetched: $it") }
    }.start()
}
