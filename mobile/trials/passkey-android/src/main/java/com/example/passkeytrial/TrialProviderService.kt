package com.example.passkeytrial

import android.app.PendingIntent
import android.content.Intent
import android.os.CancellationSignal
import android.os.OutcomeReceiver
import androidx.annotation.RequiresApi
import androidx.credentials.exceptions.ClearCredentialException
import androidx.credentials.exceptions.CreateCredentialException
import androidx.credentials.exceptions.CreateCredentialUnknownException
import androidx.credentials.exceptions.GetCredentialException
import androidx.credentials.provider.BeginCreateCredentialRequest
import androidx.credentials.provider.BeginCreateCredentialResponse
import androidx.credentials.provider.BeginCreatePublicKeyCredentialRequest
import androidx.credentials.provider.BeginGetCredentialRequest
import androidx.credentials.provider.BeginGetCredentialResponse
import androidx.credentials.provider.BeginGetPublicKeyCredentialOption
import androidx.credentials.provider.CreateEntry
import androidx.credentials.provider.CredentialEntry
import androidx.credentials.provider.CredentialProviderService
import androidx.credentials.provider.ProviderClearCredentialStateRequest
import androidx.credentials.provider.PublicKeyCredentialEntry
import java.util.concurrent.atomic.AtomicInteger
import org.json.JSONObject

/**
 * Android 14+ asks this service "can you make a passkey?" and "which passkeys do you hold for this site?".
 * It only answers with entries for the system's own sheet; the fingerprint and the signing happen in the two
 * activities the person lands in after picking an entry.
 */
@RequiresApi(34)
class TrialProviderService : CredentialProviderService() {
    private val codes = AtomicInteger((System.currentTimeMillis() % 100000).toInt())

    private fun pending(target: Class<*>, credentialId: String? = null): PendingIntent {
        val intent = Intent(this, target).setPackage(packageName).putExtra(EXTRA_ID, credentialId)
        // Mutable on purpose: Android adds the request to it. The intent is explicit, so nobody else can receive it.
        return PendingIntent.getActivity(this, codes.incrementAndGet(), intent, PendingIntent.FLAG_MUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
    }

    override fun onBeginCreateCredentialRequest(
        request: BeginCreateCredentialRequest,
        cancellationSignal: CancellationSignal,
        callback: OutcomeReceiver<BeginCreateCredentialResponse, CreateCredentialException>,
    ) {
        Store.log(this, "begin create: type=${request.type} caller=${request.callingAppInfo?.packageName}")
        if (request !is BeginCreatePublicKeyCredentialRequest) {
            callback.onError(CreateCredentialUnknownException("only passkeys"))
            return
        }
        val entry = CreateEntry.Builder("This phone only", pending(CreateActivity::class.java)).build()
        callback.onResult(BeginCreateCredentialResponse.Builder().addCreateEntry(entry).build())
    }

    override fun onBeginGetCredentialRequest(
        request: BeginGetCredentialRequest,
        cancellationSignal: CancellationSignal,
        callback: OutcomeReceiver<BeginGetCredentialResponse, GetCredentialException>,
    ) {
        val entries = mutableListOf<CredentialEntry>()
        for (option in request.beginGetCredentialOptions.filterIsInstance<BeginGetPublicKeyCredentialOption>()) {
            val json = JSONObject(option.requestJson)
            val rpId = json.optString("rpId")
            val allowed = json.optJSONArray("allowCredentials")?.let { list -> (0 until list.length()).map { list.getJSONObject(it).getString("id") } }.orEmpty()
            val held = Store.passkeys(this).filter { it.rpId == rpId && (allowed.isEmpty() || it.id in allowed) }
            Store.log(this, "begin get: caller=${request.callingAppInfo?.packageName} named=${allowed.size} offered=${held.size}")
            held.forEach { entries += PublicKeyCredentialEntry.Builder(this, it.userName, pending(GetActivity::class.java, it.id), option).build() }
        }
        callback.onResult(BeginGetCredentialResponse.Builder().setCredentialEntries(entries).build())
    }

    override fun onClearCredentialStateRequest(
        request: ProviderClearCredentialStateRequest,
        cancellationSignal: CancellationSignal,
        callback: OutcomeReceiver<Void?, ClearCredentialException>,
    ) = callback.onResult(null) // nothing to clear: the trial keeps no signed-in state

    companion object {
        const val EXTRA_ID = "credential-id"
    }
}
