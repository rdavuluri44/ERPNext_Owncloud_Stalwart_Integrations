package com.example.passkeytrial

import android.content.Intent
import android.os.Bundle
import androidx.annotation.RequiresApi
import androidx.credentials.CreatePublicKeyCredentialRequest
import androidx.credentials.CreatePublicKeyCredentialResponse
import androidx.credentials.exceptions.CreateCredentialUnknownException
import androidx.credentials.provider.PendingIntentHandler
import androidx.fragment.app.FragmentActivity
import java.security.SecureRandom
import org.json.JSONArray
import org.json.JSONObject

/** Makes a passkey: a new fingerprint-locked key in the secure hardware, proven with one signature. */
@RequiresApi(34)
class CreateActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val request = PendingIntentHandler.retrieveProviderCreateCredentialRequest(intent)
        val call = request?.callingRequest as? CreatePublicKeyCredentialRequest ?: return fail("no passkey request")
        val caller = Caller(this, request.callingAppInfo, call.clientDataHash)
        Store.log(this, "create: ${caller.summary}")
        if (!caller.allowed) return fail("caller not verified")

        val json = JSONObject(call.requestJson)
        val rpId = json.getJSONObject("rp").optString("id").ifEmpty { return fail("the request names no site") }
        if (!caller.mayUse(rpId)) return fail("the calling site may not make a key for the site it names")
        val algorithms = json.getJSONArray("pubKeyCredParams").let { list -> (0 until list.length()).map { list.getJSONObject(it).getInt("alg") } }
        if (-7 !in algorithms) return fail("the site does not accept ES256 keys")
        val user = json.getJSONObject("user")
        val excluded = json.optJSONArray("excludeCredentials")?.let { list -> (0 until list.length()).map { list.getJSONObject(it).getString("id") } }.orEmpty()
        if (Store.passkeys(this).any { it.rpId == rpId && it.id in excluded }) return fail("this phone already holds a passkey the site excludes")

        val id = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val passkey = Store.Passkey(WebAuthn.b64(id), rpId, user.getString("id"), user.optString("name", "user"))
        val (clientData, hash) = caller.clientData("webauthn.create", json.getString("challenge"))
        val made = try {
            Keys.make(this, passkey.alias, hash)
        } catch (e: Exception) {
            return fail("key not made: $e")
        }
        Store.log(this, "create: key made, ${made.report}, certificates=${made.certificates.size}")

        val cose = WebAuthn.coseKey(made.publicKey.w.affineX, made.publicKey.w.affineY)
        val authData = WebAuthn.authData(rpId, WebAuthn.CREATE_FLAGS, id, cose)
        Biometric.sign(this, passkey.alias, authData + hash, "Create a passkey for $rpId") { signed ->
            val signature = signed.getOrElse {
                Keys.delete(passkey.alias)
                return@sign fail("not confirmed: $it")
            }
            val attest = Store.attest(this)
            val attestation = if (attest) WebAuthn.attestationObject(authData, signature, made.certificates) else WebAuthn.attestationObject(authData)
            val response = JSONObject()
                .put("clientDataJSON", WebAuthn.b64(clientData.toByteArray()))
                .put("attestationObject", WebAuthn.b64(attestation))
                .put("authenticatorData", WebAuthn.b64(authData))
                .put("transports", JSONArray(listOf("internal", "hybrid")))
                .put("publicKeyAlgorithm", -7)
                .put("publicKey", WebAuthn.b64(made.publicKey.encoded))
            val credential = JSONObject()
                .put("id", passkey.id)
                .put("rawId", passkey.id)
                .put("type", "public-key")
                .put("authenticatorAttachment", "platform")
                .put("response", response)
                .put("clientExtensionResults", JSONObject())
            Store.add(this, passkey)
            Store.log(this, "create: DONE attestation=${if (attest) "android-key, ${made.chain}" else "none"}")
            val result = Intent()
            PendingIntentHandler.setCreateCredentialResponse(result, CreatePublicKeyCredentialResponse(credential.toString()))
            setResult(RESULT_OK, result)
            finish()
        }
    }

    private fun fail(reason: String) {
        Store.log(this, "create: REFUSED $reason")
        val result = Intent()
        PendingIntentHandler.setCreateCredentialException(result, CreateCredentialUnknownException(reason))
        setResult(RESULT_OK, result)
        finish()
    }
}
