package com.example.passkeytrial

import android.content.Intent
import android.os.Bundle
import android.security.keystore.KeyPermanentlyInvalidatedException
import androidx.annotation.RequiresApi
import androidx.credentials.GetCredentialResponse
import androidx.credentials.GetPublicKeyCredentialOption
import androidx.credentials.PublicKeyCredential
import androidx.credentials.exceptions.GetCredentialUnknownException
import androidx.credentials.provider.PendingIntentHandler
import androidx.fragment.app.FragmentActivity
import org.json.JSONObject

/** Signs in with a held passkey: one fingerprint match, one signature. */
@RequiresApi(34)
class GetActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val request = PendingIntentHandler.retrieveProviderGetCredentialRequest(intent)
        val option = request?.credentialOptions?.filterIsInstance<GetPublicKeyCredentialOption>()?.firstOrNull() ?: return fail("no passkey request")
        val caller = Caller(this, request.callingAppInfo, option.clientDataHash)
        Store.log(this, "get: ${caller.summary}")
        if (!caller.allowed) return fail("caller not verified")

        val json = JSONObject(option.requestJson)
        val rpId = json.optString("rpId")
        val passkey = Store.passkeys(this).firstOrNull { it.id == intent.getStringExtra(TrialProviderService.EXTRA_ID) && it.rpId == rpId }
            ?: return fail("no such passkey for the named site")
        if (!caller.mayUse(rpId)) return fail("the calling site may not use the key of the site it names")

        val (clientData, hash) = caller.clientData("webauthn.get", json.getString("challenge"))
        val authData = WebAuthn.authData(rpId, WebAuthn.GET_FLAGS)
        Biometric.sign(this, passkey.alias, authData + hash, "Sign in to $rpId") { signed ->
            val signature = signed.getOrElse {
                return@sign fail(if (it is KeyPermanentlyInvalidatedException) "KEY DESTROYED: a fingerprint or face was added" else "not confirmed: $it")
            }
            val response = JSONObject()
                .put("clientDataJSON", WebAuthn.b64(clientData.toByteArray()))
                .put("authenticatorData", WebAuthn.b64(authData))
                .put("signature", WebAuthn.b64(signature))
                .put("userHandle", passkey.userHandle)
            val credential = JSONObject()
                .put("id", passkey.id)
                .put("rawId", passkey.id)
                .put("type", "public-key")
                .put("authenticatorAttachment", "platform")
                .put("response", response)
                .put("clientExtensionResults", JSONObject())
            Store.log(this, "get: DONE")
            val result = Intent()
            PendingIntentHandler.setGetCredentialResponse(result, GetCredentialResponse(PublicKeyCredential(credential.toString())))
            setResult(RESULT_OK, result)
            finish()
        }
    }

    private fun fail(reason: String) {
        Store.log(this, "get: REFUSED $reason")
        val result = Intent()
        PendingIntentHandler.setGetCredentialException(result, GetCredentialUnknownException(reason))
        setResult(RESULT_OK, result)
        finish()
    }
}
