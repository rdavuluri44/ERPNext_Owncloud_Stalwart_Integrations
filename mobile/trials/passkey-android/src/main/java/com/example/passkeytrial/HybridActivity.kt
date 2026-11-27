package com.example.passkeytrial

import android.Manifest
import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.ParcelUuid
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.widget.TextView
import androidx.fragment.app.FragmentActivity
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import java.security.SecureRandom
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import okio.ByteString.Companion.toByteString

/**
 * Own QR route (P82 trial, question 2): the app itself reads a computer's sign-in QR code and answers it, so the
 * route does not depend on Android 14's passkey services. Steps: read the QR code, open a tunnel at the relay,
 * announce the phone over Bluetooth, agree an encrypted channel with the computer, answer its request after a
 * fingerprint match. Nothing here is paired, and the relay only ever sees encrypted bytes.
 */
class HybridActivity : FragmentActivity() {
    // TRIAL ONLY: the public relay the standard assigns number 0 (run by Google). Owner (26 Nov 2026): the real app uses it too, until the own QR route is retired.
    private val relayId = 0
    private val fidoUuid = ParcelUuid.fromString("0000fff9-0000-1000-8000-00805f9b34fb")
    private val random = SecureRandom()
    private lateinit var status: TextView
    private var socket: WebSocket? = null
    private var noise: Hybrid.Noise? = null
    private var channel: Hybrid.Channel? = null
    private var qr: Hybrid.Qr? = null
    private var advertising: AdvertiseCallback? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        status = TextView(this).apply { textSize = 18f; setPadding(48, 160, 48, 48) }
        setContentView(status)
        if (Build.VERSION.SDK_INT >= 31 && checkSelfPermission(Manifest.permission.BLUETOOTH_ADVERTISE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.BLUETOOTH_ADVERTISE), 1)
        } else scan()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) scan() else stop("Bluetooth permission refused")
    }

    /** [line] goes to the log; [detail] (site and user names) is shown on the screen only. */
    private fun say(line: String, detail: String = "") {
        Store.log(this, "qr: $line")
        runOnUiThread { status.text = if (detail.isEmpty()) line else "$line\n$detail" }
    }

    private fun stop(reason: String) {
        say("STOPPED: $reason")
        close()
    }

    private fun close() {
        advertising?.let { callback -> runCatching { advertiser()?.stopAdvertising(callback) } }
        advertising = null
        socket?.close(1000, null)
        socket = null
    }

    override fun onDestroy() {
        close()
        super.onDestroy()
    }

    private fun advertiser() = (getSystemService(BLUETOOTH_SERVICE) as BluetoothManager).adapter?.takeIf { it.isEnabled }?.bluetoothLeAdvertiser

    private fun scan() {
        if (advertiser() == null) return stop("switch Bluetooth on first")
        val options = GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build()
        GmsBarcodeScanning.getClient(this, options).startScan()
            .addOnSuccessListener { code -> connect(code.rawValue.orEmpty()) }
            .addOnCanceledListener { stop("scan cancelled") }
            .addOnFailureListener { stop("QR reader failed: $it") }
    }

    private fun connect(text: String) {
        val parsed = try {
            Hybrid.parseQr(text)
        } catch (e: Exception) {
            return stop("not a computer sign-in QR code")
        }
        qr = parsed
        say("QR code read (request: ${parsed.requestType ?: "not named"}); connecting to the relay")
        val url = "wss://${Hybrid.relayDomain(relayId)}/cable/new/" + Hybrid.tunnelId(parsed.secret).toByteString().hex()
        val client = OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS).readTimeout(0, TimeUnit.SECONDS).build()
        socket = client.newWebSocket(Request.Builder().url(url).header("Sec-WebSocket-Protocol", "fido.cable").build(), Listener())
    }

    private inner class Listener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            val routing = runCatching { WebAuthn.hex(response.header("X-Cable-Routing-Id").orEmpty()) }.getOrNull()
            if (routing == null || routing.size != 3) return stop("the relay gave no routing ID")
            val plaintext = Hybrid.advertPlaintext(ByteArray(10).also(random::nextBytes), routing, relayId)
            val code = qr!!
            noise = Hybrid.Noise(code.peerKey, Hybrid.psk(code.secret, plaintext))
            advertise(Hybrid.advert(Hybrid.eidKey(code.secret), plaintext))
        }

        override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
            try {
                handle(webSocket, bytes.toByteArray())
            } catch (e: Exception) {
                stop("message refused: $e")
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) = stop("relay connection failed: $t (HTTP ${response?.code})")
        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) = say("the computer closed the connection ($code)")
    }

    private fun advertise(data: ByteArray) {
        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .setConnectable(false)
            .setTimeout(30000)
            .build()
        val advert = AdvertiseData.Builder().addServiceUuid(fidoUuid).addServiceData(fidoUuid, data).setIncludeDeviceName(false).build()
        val callback = object : AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings?) = say("relay connected; announcing over Bluetooth, waiting for the computer")
            override fun onStartFailure(errorCode: Int) = stop("Bluetooth announcement failed (code $errorCode)")
        }
        advertising = callback
        try {
            advertiser()?.startAdvertising(settings, advert, callback) ?: stop("Bluetooth is off")
        } catch (e: SecurityException) {
            stop("Bluetooth permission missing")
        }
    }

    private fun handle(webSocket: WebSocket, message: ByteArray) {
        val open = channel
        if (open == null) {
            val (answer, made) = noise!!.respond(message, qr!!.peerKey)
            advertising?.let { runCatching { advertiser()?.stopAdvertising(it) } }
            channel = made
            webSocket.send(answer.toByteString())
            webSocket.send(made.seal(Hybrid.greeting()).toByteString())
            return say("encrypted channel agreed with the computer; waiting for its request")
        }
        val frame = open.open(message)
        if (frame.isEmpty()) return
        when (frame[0].toInt()) {
            Hybrid.FRAME_SHUTDOWN -> { say("finished"); close() }
            Hybrid.FRAME_CTAP -> request(webSocket, open, frame[1].toInt(), frame.copyOfRange(2, frame.size))
            else -> Store.log(this, "qr: ignored frame type ${frame[0]}")
        }
    }

    private fun reply(webSocket: WebSocket, open: Hybrid.Channel, answer: ByteArray) {
        webSocket.send(open.seal(byteArrayOf(Hybrid.FRAME_CTAP.toByte()) + answer).toByteString())
    }

    private fun refuse(webSocket: WebSocket, open: Hybrid.Channel, code: Int, reason: String) {
        say("REFUSED: $reason")
        reply(webSocket, open, byteArrayOf(code.toByte()))
    }

    private fun request(webSocket: WebSocket, open: Hybrid.Channel, command: Int, parameters: ByteArray) {
        when (command) {
            Hybrid.CMD_GET_INFO -> reply(webSocket, open, byteArrayOf(Hybrid.STATUS_OK.toByte()) + Hybrid.info())
            Hybrid.CMD_GET_ASSERTION -> signIn(webSocket, open, Hybrid.parseSignIn(parameters))
            Hybrid.CMD_MAKE_CREDENTIAL -> create(webSocket, open, Hybrid.parseCreate(parameters))
            else -> refuse(webSocket, open, Hybrid.STATUS_INVALID_COMMAND, "unknown command $command (${parameters.size} more bytes)")
        }
    }

    private fun signIn(webSocket: WebSocket, open: Hybrid.Channel, ask: Hybrid.SignIn) {
        val named = ask.allowed.map(WebAuthn::b64)
        val passkey = Store.passkeys(this).firstOrNull { it.rpId == ask.rpId && (named.isEmpty() || it.id in named) }
            ?: return refuse(webSocket, open, Hybrid.STATUS_NO_CREDENTIALS, "no passkey here for the site the computer names")
        say("the computer asks to sign in", "${passkey.userName} at ${ask.rpId}")
        val authData = WebAuthn.authData(ask.rpId, WebAuthn.GET_FLAGS)
        runOnUiThread {
            Biometric.sign(this, passkey.alias, authData + ask.clientDataHash, "Sign in to ${ask.rpId} on the computer") { signed ->
                val signature = signed.getOrElse {
                    val why = if (it is KeyPermanentlyInvalidatedException) "KEY DESTROYED: a fingerprint or face was added" else "not confirmed: $it"
                    return@sign refuse(webSocket, open, Hybrid.STATUS_OPERATION_DENIED, why)
                }
                reply(webSocket, open, Hybrid.signInAnswer(WebAuthn.unb64(passkey.id), authData, signature, WebAuthn.unb64(passkey.userHandle)))
                say("DONE: signed in on the computer", "${passkey.userName} at ${ask.rpId}")
            }
        }
    }

    private fun create(webSocket: WebSocket, open: Hybrid.Channel, ask: Hybrid.Create) {
        if (-7L !in ask.algorithms) return refuse(webSocket, open, Hybrid.STATUS_OPERATION_DENIED, "the site does not accept ES256 keys")
        val excluded = ask.excluded.map(WebAuthn::b64)
        if (Store.passkeys(this).any { it.rpId == ask.rpId && it.id in excluded }) {
            return refuse(webSocket, open, Hybrid.STATUS_CREDENTIAL_EXCLUDED, "this phone already holds a passkey the site excludes")
        }
        val id = ByteArray(16).also(random::nextBytes)
        val passkey = Store.Passkey(WebAuthn.b64(id), ask.rpId, WebAuthn.b64(ask.userId), ask.userName)
        val made = try {
            Keys.make(this, passkey.alias, ask.clientDataHash)
        } catch (e: Exception) {
            return refuse(webSocket, open, Hybrid.STATUS_OPERATION_DENIED, "key not made: $e")
        }
        say("the computer asks to make a passkey; key made, ${made.report}", "${ask.userName} at ${ask.rpId}")
        val authData = WebAuthn.authData(ask.rpId, WebAuthn.CREATE_FLAGS, id, WebAuthn.coseKey(made.publicKey.w.affineX, made.publicKey.w.affineY))
        runOnUiThread {
            Biometric.sign(this, passkey.alias, authData + ask.clientDataHash, "Create a passkey for ${ask.rpId}") { signed ->
                if (signed.isFailure) {
                    Keys.delete(passkey.alias)
                    return@sign refuse(webSocket, open, Hybrid.STATUS_OPERATION_DENIED, "not confirmed: ${signed.exceptionOrNull()}")
                }
                Store.add(this, passkey)
                val attest = Store.attest(this)
                reply(webSocket, open, if (attest) Hybrid.createAnswer(authData, signed.getOrThrow(), made.certificates) else Hybrid.createAnswer(authData))
                say("DONE: passkey made, attestation=${if (attest) "android-key, ${made.chain}" else "none"}", "${ask.userName} at ${ask.rpId}")
            }
        }
    }
}
