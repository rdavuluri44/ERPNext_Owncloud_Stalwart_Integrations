package com.example.erp.app

import android.annotation.SuppressLint
import android.content.Context
import android.util.Base64
import androidx.core.content.edit
import com.example.erp.core.Seal

/**
 * The app's safe: the one place where anything secret is kept on the phone (the sign-in tokens first). Every value
 * is locked with the data key that only a fingerprint match releases ([Session]), so while the app is locked the
 * stored file is unreadable, also to the app itself. Nothing here is in a backup (the app has none). It is emptied
 * when the key is erased or made anew ([PhoneLock]) and on sign-out.
 */
class Safe(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE)

    /** False when the app is locked: nothing is written, and never in the clear. */
    @SuppressLint("UseKtx") // the suggested form hides whether the write succeeded
    fun put(name: String, value: String): Boolean {
        val sealed = Session.withKey { Seal.seal(it, name, value.toByteArray()) } ?: return false
        // False too when the phone could not write it (storage full): the caller must not believe it is kept.
        return prefs.edit().putString(name, Base64.encodeToString(sealed, Base64.NO_WRAP)).commit()
    }

    /** Null when the app is locked, when nothing is stored, or when what is stored was not locked with this key. */
    fun get(name: String): String? {
        val sealed = prefs.getString(name, null)?.let { runCatching { Base64.decode(it, Base64.NO_WRAP) }.getOrNull() } ?: return null
        return Session.withKey { Seal.open(it, name, sealed) }?.toString(Charsets.UTF_8)
    }

    companion object {
        const val FILE = "safe"

        /** Works while locked too: emptying needs no key. */
        fun wipe(context: Context) = context.applicationContext.getSharedPreferences(FILE, Context.MODE_PRIVATE).edit(commit = true) { clear() }
    }
}
