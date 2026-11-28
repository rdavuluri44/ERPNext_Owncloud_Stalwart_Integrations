package com.example.erp.app

import android.Manifest
import android.content.Context
import android.content.Intent
import android.graphics.Color as AndroidColor
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.app.ActivityCompat
import androidx.core.content.edit
import androidx.core.net.toUri
import androidx.fragment.app.FragmentActivity
import com.example.erp.core.AccessRequest
import com.example.erp.core.AlertAction
import com.example.erp.core.Approval
import com.example.erp.core.Format
import com.example.erp.core.KeyLoss
import com.example.erp.core.KeyState
import com.example.erp.core.Lead
import com.example.erp.core.LockRules
import com.example.erp.core.OutdoorSwitch
import com.example.erp.core.Palettes
import com.example.erp.core.Point
import com.example.erp.core.Reply
import com.example.erp.core.Saver
import com.example.erp.core.Slot
import com.example.erp.core.Trace
import com.example.erp.core.Tracer
import com.example.erp.core.Transport
import com.example.erp.core.welcomeFor
import java.time.LocalDateTime
import java.util.UUID
import kotlin.concurrent.thread

/** What the lock screen shows: read from the phone each time the app comes into sight and after every touch. */
private class LockView(val key: KeyState, val loss: KeyLoss?, val misses: Int, val phone: PhoneCheck, val trouble: String? = null)

// FragmentActivity: the fingerprint question of the AndroidX library needs it.
class MainActivity : FragmentActivity() {
    private val tracer = Tracer()
    private val outdoorSwitch = OutdoorSwitch()
    private val lock by lazy { PhoneLock(this) }
    private var lockView by mutableStateOf<LockView?>(null)
    private var asking = false
    private var traces by mutableStateOf(emptyList<Trace>())

    /** Every call of the app goes through this one saving layer and this one connection. */
    private val saver by lazy {
        val server = BuildConfig.SERVER
        Saver(tracer, if (server.isEmpty()) Transport { _, _, _ -> Reply.NoConnection("no server address is set in this build") } else HttpTransport(server))
    }

    /** Test builds: one real call to the server's "are you there" function, so the path can be seen in Data trace. */
    private fun tryConnection() {
        // ponytail: one thread per tap is enough for a test button; real features get a shared worker with sign-in.
        thread {
            saver.save(UUID.randomUUID().toString(), "Connection test", "frappe.ping", emptyMap())
            runOnUiThread { traces = tracer.all() }
        }
    }
    private var alerts by mutableStateOf(AlertsView())
    private var goTo by mutableStateOf<Place?>(null)
    private var goItem by mutableStateOf<InboxJump?>(null)

    /** An alert that arrived while the app is open and unlocked: shown as a line at the top. */
    private var line by mutableStateOf<AlertAction.Show?>(null)
    private var askedForAlerts = false

    private fun readAlerts() {
        val blocked = AlertCenter.blocked(this)
        val connected = AlertCenter.connect(this)
        alerts = alerts.copy(blocked = blocked?.first, fix = blocked?.second, fullPage = AlertCenter.fullPageAllowed(this), onTop = AlertCenter.onTop(this), connected = connected)
        // Test builds only: the delivery address, for one test signal from the owner.
        if (connected && BuildConfig.DEBUG && alerts.address == null) AlertCenter.address { address -> alerts = alerts.copy(address = address) }
    }

    /** Some phones lack one of the detailed settings pages; the app's own alert settings are always there. */
    private fun openSetting(page: Intent) {
        val appSetting = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
        runCatching { startActivity(page) }.onFailure { runCatching { startActivity(appSetting) } }
    }

    private fun fixAlerts(fix: Fix) {
        val appSetting = Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
        when {
            // The phone shows its own question once or twice; after that only its settings can switch alerts on.
            fix == Fix.ALLOW && Build.VERSION.SDK_INT >= 33 && !askedForAlerts -> {
                askedForAlerts = true
                // The phone's own question. Asked the older way on purpose: the newer way needs a newer part than
                // the fingerprint library brings, and one more library is not worth it for one question.
                ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), ASK_ALERTS)
            }
            fix == Fix.ON_TOP -> openSetting(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, "package:$packageName".toUri()))
            fix == Fix.FULL_PAGE -> if (Build.VERSION.SDK_INT >= 34) openSetting(Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, "package:$packageName".toUri()))
            fix == Fix.KIND_SETTING -> openSetting(
                Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName).putExtra(Settings.EXTRA_CHANNEL_ID, AlertKind.APPROVALS.id),
            )
            else -> openSetting(appSetting)
        }
    }

    /** An alert was tapped: remember where it leads. The fingerprint is asked first, as on every opening. */
    private fun opened(intent: Intent?) {
        // Reopened from the list of recent apps: the old alert's wish was followed once already.
        if (intent == null || intent.flags and Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY != 0) return
        goTo = when (intent?.getStringExtra(AlertCenter.OPEN_PLACE)) {
            Lead.INBOX.name -> Place.INBOX
            Lead.CHAT.name -> Place.CHAT
            Lead.MAIL.name -> Place.MAIL
            else -> goTo
        }
        // A shortcut of an alert: one thing to open. It only chooses the screen; the lock and the signing stay as they are.
        AlertCenter.asked(this, intent)?.let { goItem = it }
    }

    @Deprecated("The platform's older way of answering a permission question; see fixAlerts.")
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        @Suppress("DEPRECATION")
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == ASK_ALERTS) readAlerts()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        opened(intent)
    }

    private val safe by lazy { Safe(this) }
    private var safeNote by mutableStateOf<String?>(null)

    /** Test builds: the note is stored as a time and shown the app's way of writing times. */
    private fun readSafeNote() {
        val saved = safe.get(TEST_NOTE)?.let { runCatching { LocalDateTime.parse(it) }.getOrNull() }
        safeNote = saved?.let { "A note saved ${Format.dateTime(it, LocalDateTime.now())} was read back from the safe." }
    }

    private fun readLock(trouble: String? = null) {
        lockView = LockView(lock.state(), lock.loss, lock.misses, checkPhone(this), trouble)
    }

    private fun touch(ask: (FragmentActivity, (LockResult) -> Unit) -> Unit) {
        if (asking) return
        asking = true
        Session.askOnArrival = false
        ask(this) { result ->
            asking = false
            if (result is LockResult.Opened) Session.open(result.dataKey)
            readSafeNote()
            readLock((result as? LockResult.Trouble)?.sentence)
        }
    }

    /** One decision, signed: the fingerprint question shows what is signed. Nothing is signed while another question is open. */
    private fun sign(what: String, done: (Boolean, String?) -> Unit) {
        if (asking) return
        asking = true
        lock.confirm(this, what) { result ->
            asking = false
            // Five misses erase the key here too; the app is then locked and shows why.
            if (result is LockResult.Erased) readLock()
            // A miss does not end the phone's question; the person closes it. They are still told how many tries are left.
            done(result is LockResult.Confirmed, (result as? LockResult.Trouble)?.sentence ?: LockRules.missWords(lock.misses))
        }
    }

    override fun onStart() {
        super.onStart()
        Session.back()
        AlertCenter.inApp = { alert -> runOnUiThread { line = alert } }
        if (!asking) readLock()
        readSafeNote()
        readAlerts()
    }

    override fun onResume() {
        super.onResume()
        // The daily path: arrive, touch the sensor. After the person closed the question it waits for a tap.
        if (!Session.isOpen && Session.askOnArrival && lockView?.key == KeyState.PRESENT) touch(lock::open)
    }

    override fun onStop() {
        super.onStop()
        AlertCenter.inApp = null
        line = null
        Session.left()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // No screenshots, and a blank card in the app switcher: the app will show personal data.
        // Test builds allow screenshots while the app is being built and tested on made-up data (the developer's
        // decision of 28 November 2026). A build for people always blocks them.
        if (!BuildConfig.DEBUG) window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        val testBuild = BuildConfig.DEBUG
        val settings = getSharedPreferences("display", Context.MODE_PRIVATE)
        val sensors = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val lightSensor: Sensor? = sensors.getDefaultSensor(Sensor.TYPE_LIGHT)
        if (savedInstanceState == null) opened(intent)

        setContent {
            var automatic by remember { mutableStateOf(settings.getBoolean("outdoor-automatic", true)) }
            var forced by remember { mutableStateOf(settings.getBoolean("outdoor-forced", false)) }
            var bright by remember { mutableStateOf(false) }
            var lux by remember { mutableStateOf<Float?>(null) }

            // The light sensor is listened to only while the automatic switch is on and the app is on screen.
            DisposableEffect(automatic, lightSensor) {
                val listener = object : SensorEventListener {
                    override fun onSensorChanged(event: SensorEvent) {
                        lux = event.values[0]
                        bright = outdoorSwitch.reading(event.values[0])
                    }

                    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit
                }
                if (automatic && lightSensor != null) sensors.registerListener(listener, lightSensor, SensorManager.SENSOR_DELAY_NORMAL)
                onDispose { sensors.unregisterListener(listener) }
            }

            val outdoor = forced || (automatic && bright)
            val palette = Palettes.pick(phoneIsDark = isSystemInDarkTheme(), outdoor = outdoor)
            // Status and navigation bar icons must stay readable on the look in use, also when Outdoor overrides night mode.
            SideEffect {
                val style = if (palette == Palettes.DARK) SystemBarStyle.dark(AndroidColor.TRANSPARENT)
                else SystemBarStyle.light(AndroidColor.TRANSPARENT, AndroidColor.TRANSPARENT)
                enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
            }

            ErpTheme(palette) {
                val view = lockView
                if (!Session.isOpen) {
                    if (view != null) Box(Modifier.fillMaxSize().background(Look.Ground).safeDrawingPadding()) { LockScreen(view) }
                } else if (view != null) AppFrame(
                    FrameState(
                        palette, testBuild, traces, view.phone, "${Build.MANUFACTURER} ${Build.MODEL}", BuildConfig.VERSION_NAME,
                        hasLightSensor = lightSensor != null, automaticOutdoor = automatic, forcedOutdoor = forced, lux = lux,
                        safeNote = safeNote,
                        alerts = alerts,
                    ),
                    sign = ::sign,
                    alertActions = AlertActions(
                        fix = ::fixAlerts,
                        openKind = { kind ->
                            openSetting(Intent(Settings.ACTION_CHANNEL_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName).putExtra(Settings.EXTRA_CHANNEL_ID, kind.id))
                        },
                        // A test arrives after a short wait and through the phone's alarm service, so the phone can be
                        // locked or the app closed first, as with a real signal.
                        signal = { data -> AlertCenter.schedule(applicationContext, data, TEST_WAIT_SECONDS) },
                        removeAll = { AlertCenter.clear(this) },
                        remind = { AlertCenter.remindLater(applicationContext, Slot.DECIDE, asked = true) },
                        seen = { what -> AlertCenter.receive(applicationContext, mapOf("kind" to "read", "what" to what)) },
                    ),
                    goTo = goTo,
                    goItem = goItem,
                    onWent = { goTo = null; goItem = null },
                    line = line?.words,
                    onLine = { open ->
                        val alert = line
                        line = null
                        if (open && alert != null) {
                            goTo = Place.INBOX
                            goItem = alert.item?.let { InboxJump(it) }
                        }
                    },
                    onAddSample = { addSample(); traces = tracer.all() },
                    onAutomaticOutdoor = { automatic = it; settings.edit { putBoolean("outdoor-automatic", it) } },
                    onForcedOutdoor = { forced = it; settings.edit { putBoolean("outdoor-forced", it) } },
                    onTryConnection = ::tryConnection,
                    onSafeNote = { safe.put(TEST_NOTE, LocalDateTime.now().toString()); readSafeNote() },
                )
            }
        }
    }

    /**
     * The locked app. Which screen is shown is decided by the rule [welcomeFor], from this phone's key.
     * Until sign-in exists (Phase 1 part 4) nothing can say "approved", so a phone without a key is treated as
     * approved and goes straight to "Make your key" (cleanup list). A key made this way opens nothing but the
     * app's own screens: there is no sign-in to protect yet.
     */
    @androidx.compose.runtime.Composable
    private fun LockScreen(view: LockView) {
        // The stand-in below must never reach people: a real build waits for sign-in.
        check(BuildConfig.DEBUG || view.key != KeyState.NONE) { "sign-in is not built yet" }
        val now = LocalDateTime.now()
        val approved = AccessRequest(now, Approval.CONFIRMED, now, Approval.CONFIRMED, now)
        WelcomeScreen(
            welcomeFor(view.key, view.loss, if (view.key == KeyState.NONE) approved else null),
            WelcomeFacts(
                account = "",
                mobile = "",
                now = now,
                triesLeft = if (view.misses > 0) LockRules.triesLeft(view.misses) else null,
                keyProblem = if (view.phone.usable) null else "its fingerprint sensor is not ready. Save your fingerprint in the phone's Settings, then come back.",
                trouble = view.trouble,
            ),
            WelcomeActions(
                // The three request buttons belong to screens this rule cannot reach before the server part exists.
                requestAccess = {},
                checkAgain = {},
                cancelRequest = {},
                requestAgain = { lock.forgetLoss(); readLock() },
                makeKey = { touch(lock::make) },
                unlock = { touch(lock::open) },
            ),
        )
    }

    /** Test builds only: one failed and one complete trace, so the screen can be checked before real calls exist (Phase 1). */
    private fun addSample(): Trace? = sampleTraces(tracer)
}

private const val TEST_NOTE = "test-note"
private const val ASK_ALERTS = 7

/** One failed and one complete made-up trace. Used by the test-build button and by the screen tests. */
fun sampleTraces(tracer: Tracer): Trace? {
    val bad = UUID.randomUUID().toString()
    tracer.start(bad, "Sample: check-out refused")
    listOf(Point.SCREEN, Point.PHONE_STORE, Point.GATEWAY).forEach { tracer.mark(bad, it, true) }
    tracer.mark(bad, Point.NETWORK, true, tookMs = 420)
    tracer.mark(bad, Point.SERVER, false, "refused by a server rule (417)", detail = "sample values: distance_m=180, radius_m=100")
    val good = UUID.randomUUID().toString()
    tracer.start(good, "Sample: check-in saved")
    listOf(Point.SCREEN, Point.PHONE_STORE, Point.NETWORK, Point.GATEWAY, Point.SERVER).forEach { tracer.mark(good, it, true) }
    return tracer.mark(good, Point.READ_BACK, true, "matches")
}
