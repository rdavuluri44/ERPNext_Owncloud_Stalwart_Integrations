package com.example.erp.app

import android.Manifest
import android.annotation.SuppressLint
import android.app.ActivityManager
import android.app.AlarmManager
import android.app.Application
import android.app.KeyguardManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.RingtoneManager
import android.os.Build
import android.os.PowerManager
import android.os.SystemClock
import android.provider.Settings
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.core.content.edit
import com.example.erp.core.AlertAction
import com.example.erp.core.AlertState
import com.example.erp.core.Alerts
import com.example.erp.core.Lead
import com.example.erp.core.Slot
import com.example.erp.core.Strength
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/** The kinds of alert the person can switch in the phone's own settings. The app keeps no second set of switches. */
enum class AlertKind(val id: String, val title: String, val text: String, val importance: Int, val rings: Boolean = false) {
    APPROVALS("approvals", "Approvals: ringing", "Something waits for your decision. Rings and shows a full page.", NotificationManager.IMPORTANCE_HIGH, rings = true),
    APPROVALS_LIST("approvals-list", "Approvals: in the list", "Stays in the list after the ringing stops. No sound.", NotificationManager.IMPORTANCE_LOW),
    REJECTED("rejected", "Rejected, to correct", "Something you sent came back. Normal sound.", NotificationManager.IMPORTANCE_DEFAULT),
    CHAT("chat", "Chat", "A message for you. Normal sound.", NotificationManager.IMPORTANCE_DEFAULT),
    MAIL("mail", "Mail", "New mail. No sound.", NotificationManager.IMPORTANCE_LOW),
    NOTICES("notices", "Notices", "Information. No sound.", NotificationManager.IMPORTANCE_LOW),
}

/** What can be done about blocked alerts. */
enum class Fix(val label: String) {
    ALLOW("Allow alerts"),
    APP_SETTING("Open the phone's setting"),
    KIND_SETTING("Open the phone's setting"),
    FULL_PAGE("Allow the full page"),
    ON_TOP("Allow it over other apps"),
}

/** Whether alerts can show on this phone. [blocked] says why not in plain words, with the one thing that fixes it. */
data class AlertsView(
    val blocked: String? = null,
    val fix: Fix? = null,
    /** False on a phone (Android 14 and newer) where the person has not allowed the full page over the locked screen. */
    val fullPage: Boolean = true,
    /**
     * The full page while the phone is in use: true when the person allowed this app to open over other apps, false
     * when not yet, null on a phone that does not have that setting. Without it an approval comes as a banner then.
     */
    val onTop: Boolean? = true,
    /** False when this build was made without the values for Google's messaging: it can show alerts, but receives none. */
    val connected: Boolean = false,
    /** Test builds: the address Google delivers this phone's alerts to, for one test signal from the owner. */
    val address: String? = null,
)

/**
 * Everything the app does with an alert on the phone. A signal comes in ([receive]), the rule in
 * [Alerts.handle] says what to show, and this shows or removes it. It works while the app is locked or closed and
 * touches nothing that is locked away: what it shows are the rule's fixed words, and what it remembers are short
 * fingerprints, never a reference or any content.
 *
 * A ringing alert is two entries, as in the earlier app: one that rings and opens the full page over a locked
 * screen and stops after [RING_MS], and a quiet one that stays in the list so the alert is not lost.
 */
object AlertCenter {
    const val OPEN_PLACE = "open-place"
    const val WORDS = "words"
    const val SLOT = "slot"
    const val ACTION_SHOW = "com.example.erp.app.ALERT_SHOW"
    const val ACTION_STOP = "com.example.erp.app.ALERT_STOP"
    const val ACTION_REMIND = "com.example.erp.app.ALERT_REMIND"
    const val ACTION_REMIND_DUE = "com.example.erp.app.ALERT_REMIND_DUE"
    const val OPEN_ITEM = "open-item"
    const val OPEN_START = "open-start"
    const val ITEM = "item"
    const val TEST = "test"
    const val RING_MS = 30_000L

    /**
     * "Remind me in 2 hours": fixed, the person cannot choose, and it rings at every hour of the day (the developer's
     * decision of 28 November 2026). Test builds wait 2 minutes instead, so the repeat can be tried.
     */
    val REMIND_MS = if (BuildConfig.DEBUG) 2 * 60_000L else 2 * 60 * 60_000L
    private const val REMIND_AT = "remind-at"
    private const val REMIND_ASKED = "remind-asked"
    private const val TOKEN = "token"
    private const val PAGE_AT = "page-at"
    private const val PAGE_GAP_MS = 60_000L
    private const val OPEN_TOKEN = "open-token"
    private const val PREFS = "alerts"
    private const val FIELD = "signal:"
    private const val FLAGS = PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT

    private fun kind(slot: Slot) = when (slot) {
        Slot.DECIDE -> AlertKind.APPROVALS_LIST
        Slot.REJECTED -> AlertKind.REJECTED
        Slot.MESSAGE -> AlertKind.CHAT
        Slot.MAIL -> AlertKind.MAIL
        Slot.NOTICE -> AlertKind.NOTICES
    }

    /** The phone's number for the ringing entry of a slot; the quiet entry uses the slot's own number. */
    private fun ringId(slot: Slot) = 100 + slot.id

    /** Makes the kinds known to the phone. Safe to call every time the app starts. */
    fun prepare(context: Context) {
        val manager = context.getSystemService(NotificationManager::class.java)
        for (kind in AlertKind.entries) {
            val channel = NotificationChannel(kind.id, kind.title, kind.importance).apply { description = kind.text }
            if (kind.rings) {
                // Approvals sound like a call, not like a message. The phone's silent mode still wins: this kind
                // never asks to get past "Do not disturb".
                channel.setSound(
                    RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE),
                    AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build(),
                )
                channel.enableVibration(true)
            }
            manager.createNotificationChannel(channel)
        }
    }

    private fun allowed(context: Context) =
        Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    /** Opens the app itself at a place; the fingerprint is asked there before anything is shown. */
    fun openApp(context: Context, slot: Slot, item: String? = null, start: InboxJump.Start = InboxJump.Start.ITEM): Intent = Intent(context, MainActivity::class.java)
        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        .putExtra(OPEN_PLACE, slot.lead.name)
        // A shortcut names one thing and, at most, the screen to start on. It decides nothing by itself.
        .apply { if (item != null) putExtra(OPEN_ITEM, item).putExtra(OPEN_START, start.name).putExtra(OPEN_TOKEN, token(context)) }

    /** A random word only this app knows, kept with its alerts. It goes when they are cleared, with every old alert. */
    @Synchronized
    private fun token(context: Context): String {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return prefs.getString(TOKEN, null) ?: java.util.UUID.randomUUID().toString().also { prefs.edit(commit = true) { putString(TOKEN, it) } }
    }

    /**
     * The one thing an alert of this app asked to open, and the screen to start on; null for anything else. The
     * app's first screen can be started by any app, so the wish counts only with this app's own word in it.
     */
    fun asked(context: Context, intent: Intent?): InboxJump? {
        // Reopened from the list of recent apps: Android hands over the old alert's wish again. It was followed once.
        if (intent == null || intent.flags and Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY != 0) return null
        val item = intent.getStringExtra(OPEN_ITEM)?.takeIf { it.isNotEmpty() && it.length <= 200 } ?: return null
        if (intent.getStringExtra(OPEN_TOKEN) != token(context)) return null
        return InboxJump(item, InboxJump.Start.entries.find { it.name == intent.getStringExtra(OPEN_START) } ?: InboxJump.Start.ITEM)
    }

    private fun state(context: Context): AlertState {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        fun marks(name: String) = prefs.getStringSet(name, emptySet()).orEmpty().toSet()
        return AlertState(marks("deciding"), marks("rejected"), marks("chats"), prefs.getInt("mails", 0), prefs.getInt("notices", 0))
    }

    /**
     * Set while the app is open on the screen and unlocked. What arrives then is shown inside the app instead of
     * over it: no banner and no full page; the entry goes to the phone's list without a sound.
     */
    @Volatile
    var inApp: ((AlertAction.Show) -> Unit)? = null

    @SuppressLint("MissingPermission") // checked by allowed(), which the check tool does not follow
    /**
     * @param page whether this alert may open the full page over a phone in use: only something new, the person's
     *   own reminder or their own test. A repeated signal rings the banner and nothing more.
     */
    private fun show(context: Context, alert: AlertAction.Show, page: Boolean) {
        val manager = NotificationManagerCompat.from(context)
        val inside = inApp?.takeIf { Session.isOpen }
        if (inside != null) {
            if (allowed(context)) manager.notify(alert.slot.id, entry(context, alert).setSilent(true).build())
            // Something that waits for the person themselves gets a line in the app and one short sound; a chat or a
            // mail only changes its number.
            if (alert.strength != Strength.QUIET && alert.slot.lead == Lead.INBOX) {
                // The sound only where the person allows this app's alerts and the ringing kind; the line always.
                if (blocked(context) == null) runCatching { RingtoneManager.getRingtone(context, RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))?.play() }
                inside(alert)
            }
            return
        }
        if (!allowed(context)) return
        // The quiet entry first: it is what stays in the list after the ringing stops.
        manager.notify(alert.slot.id, entry(context, alert).build())
        if (alert.strength != Strength.RING) return
        manager.notify(ringId(alert.slot), ring(context, alert).build())
        // A locked or dark phone gets the full page from the phone itself. A phone in use gets only the banner,
        // unless the person allowed this app to open over other apps: then the same page is opened here.
        if (page && onTop(context) == true && inUse(context) && pageDue(context)) runCatching { context.startActivity(page(context, alert)) }
    }

    /** One signal: from Google while the app is closed, or a test made on the phone. */
    @Synchronized
    fun receive(context: Context, data: Map<String, String>) {
        // A phone without its key (never made, or erased after five misses) shows nothing: there is nobody to show it to.
        if (!PhoneLock.hasKey(context)) return
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val before = state(context)
        val (after, action) = Alerts.handle(data, before)
        if (after != before) prefs.edit(commit = true) {
            putStringSet("deciding", after.deciding); putStringSet("rejected", after.rejected); putStringSet("chats", after.chats)
            putInt("mails", after.mails); putInt("notices", after.notices)
        }
        val manager = NotificationManagerCompat.from(context)
        when (action) {
            is AlertAction.Remove -> {
                manager.cancel(action.slot.id)
                manager.cancel(ringId(action.slot))
                RingActivity.close(action.slot)
                if (action.slot == Slot.DECIDE) stopReminding(context) // nothing waits any more
            }
            // Over a phone in use only for an approval the phone did not know yet, or the phone's own test.
            is AlertAction.Show -> show(context, action, page = action.test || after.deciding.size > before.deciding.size)
            AlertAction.Ignore -> Unit
        }
    }

    /** The entry that stays in the list. Only the rule's fixed words: no second line, no name, no amount. */
    private fun entry(context: Context, alert: AlertAction.Show) = NotificationCompat.Builder(context, kind(alert.slot).id)
        .setSmallIcon(R.drawable.ic_bell)
        .setContentTitle(alert.words)
        .setContentIntent(open(context, alert))
        .setAutoCancel(true)
        // A ringing alert makes its sound through its ringing entry; a count that only goes down makes none.
        .setOnlyAlertOnce(alert.strength != Strength.ALERT)
        .setCategory(NotificationCompat.CATEGORY_STATUS)
        // Safe to show in full on a locked phone, because it holds nothing private.
        .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)

    /**
     * Opens the app at the alert's place; when exactly one thing waits, at that thing. Each different target has its
     * own number, because the phone tells such requests apart by number, not by what they carry.
     */
    private fun open(context: Context, alert: AlertAction.Show, start: InboxJump.Start = InboxJump.Start.ITEM): PendingIntent {
        val number = alert.slot.id + if (alert.item == null) 0 else 200 + 100 * start.ordinal
        return PendingIntent.getActivity(context, number, openApp(context, alert.slot, alert.item, start), FLAGS)
    }

    /** The full page of a ringing alert: its fixed words and what it may lead to. */
    private fun page(context: Context, alert: AlertAction.Show): Intent =
        Intent(context, RingActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_USER_ACTION)
            .putExtra(WORDS, alert.words).putExtra(SLOT, alert.slot.name).putExtra(ITEM, alert.item).putExtra(TEST, alert.test)

    /** The screen is on and the phone is unlocked: the person is doing something else on it. Never during a call. */
    private fun inUse(context: Context): Boolean =
        context.getSystemService(PowerManager::class.java).isInteractive && !context.getSystemService(KeyguardManager::class.java).isKeyguardLocked &&
            context.getSystemService(AudioManager::class.java).mode == AudioManager.MODE_NORMAL

    /** The page is not thrown over the person's work again and again: at most once in [PAGE_GAP_MS]. */
    private fun pageDue(context: Context): Boolean {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val now = SystemClock.elapsedRealtime()
        val last = prefs.getLong(PAGE_AT, 0L)
        if (last in 1..now && now - last < PAGE_GAP_MS) return false
        prefs.edit(commit = true) { putLong(PAGE_AT, now) }
        return true
    }

    /**
     * Whether this app may open its full page over other apps: the person's own switch in the phone's settings.
     * Null on a phone that has no such switch (phones with little memory do not).
     */
    fun onTop(context: Context): Boolean? = when {
        context.getSystemService(ActivityManager::class.java).isLowRamDevice -> null
        else -> Settings.canDrawOverlays(context)
    }

    /**
     * The entry that rings: on a locked phone it opens the full page ([RingActivity]); on a phone in use it is a
     * banner with the same choices. No choice decides anything: "Approve", "Reject" and "Open" lead to the app and
     * its fingerprint, where the person sees the thing first; "Remind in 2 hours" only stops the ringing for now.
     */
    private fun ring(context: Context, alert: AlertAction.Show): NotificationCompat.Builder {
        val id = ringId(alert.slot)
        val page = PendingIntent.getActivity(context, id, page(context, alert), FLAGS)
        fun tap(action: String) = PendingIntent.getBroadcast(context, id, Intent(context, AlertReceiver::class.java).setAction(action).putExtra(SLOT, alert.slot.name), FLAGS)
        val builder = NotificationCompat.Builder(context, AlertKind.APPROVALS.id)
            .setSmallIcon(R.drawable.ic_bell)
            .setContentTitle(alert.words)
            .setCategory(NotificationCompat.CATEGORY_REMINDER)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setFullScreenIntent(page, true)
            .setContentIntent(page)
            .setAutoCancel(true)
            .setTimeoutAfter(RING_MS)
        return when {
            alert.test -> builder.addAction(0, "Stop", tap(ACTION_STOP)).addAction(0, "Open", open(context, alert))
            // The phone shows three choices on a banner at most; "Delegate" is on the full page and in the thing itself.
            alert.item != null -> builder.addAction(0, "Approve", open(context, alert)).addAction(0, "Reject", open(context, alert, InboxJump.Start.REJECT)).addAction(0, "Remind in 2 hours", tap(ACTION_REMIND))
            else -> builder.addAction(0, "Open", open(context, alert)).addAction(0, "Remind in 2 hours", tap(ACTION_REMIND))
        }
    }

    /** A choice was made, or the full page closed: the ringing stops. The quiet entry stays in the list. */
    fun stopRing(context: Context, slot: Slot) = NotificationManagerCompat.from(context).cancel(ringId(slot))

    private fun reminder(context: Context) =
        PendingIntent.getBroadcast(context, 400, Intent(context, AlertReceiver::class.java).setAction(ACTION_REMIND_DUE), FLAGS)

    /** Kept by the phone's alarm service, so it comes when the app is closed; its time is written down for a restart. */
    private fun setReminder(context: Context, at: Long) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit(commit = true) { putLong(REMIND_AT, at) }
        context.getSystemService(AlarmManager::class.java).setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, reminder(context))
    }

    private fun stopReminding(context: Context) {
        context.getSystemService(AlarmManager::class.java).cancel(reminder(context))
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit(commit = true) { remove(REMIND_AT); remove(REMIND_ASKED) }
    }

    /** "Remind me in 2 hours": the ringing stops now and comes back, again and again, until nothing waits. */
    @Synchronized
    fun remindLater(context: Context, slot: Slot, asked: Boolean = false) {
        stopRing(context, slot)
        if (asked) context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit(commit = true) { putBoolean(REMIND_ASKED, true) }
        setReminder(context, System.currentTimeMillis() + REMIND_MS)
    }

    /** The reminder's time has come: ring again and set the next one, or end when nothing waits any more. */
    @Synchronized
    fun remindDue(context: Context) {
        val waiting = state(context)
        val alert = Alerts.remind(waiting, asked = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getBoolean(REMIND_ASKED, false))
        if (!PhoneLock.hasKey(context) || alert !is AlertAction.Show) return stopReminding(context)
        show(context, alert, page = true) // the person asked for this reminder
        // What the phone knows to be waiting is reminded of again and again. A reminder asked for inside the app for
        // something the phone had no alert for comes once: the phone cannot learn when that thing is decided.
        if (waiting.deciding.isEmpty()) stopReminding(context) else setReminder(context, System.currentTimeMillis() + REMIND_MS)
    }

    /** The phone forgets its alarms when it restarts: a reminder that was running is set again. */
    @Synchronized
    fun afterRestart(context: Context) {
        val at = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong(REMIND_AT, 0L)
        if (at > 0L) setReminder(context, maxOf(at, System.currentTimeMillis() + 60_000L))
    }

    /** Sign-out and a lost key: every alert goes, and what was remembered about them. */
    @Synchronized // with receive(), so a signal being handled cannot write back what is cleared here
    fun clear(context: Context) {
        RingActivity.close(null)
        context.getSystemService(AlarmManager::class.java).cancel(reminder(context))
        NotificationManagerCompat.from(context).cancelAll()
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit(commit = true) { clear() }
    }

    /**
     * Makes a signal arrive after [seconds], also when the app is closed in between: the phone's alarm service
     * keeps it, not the app. Not exact (that would need a special permission): the phone may deliver it up to
     * about a minute late. Used for the tests on the Alerts screen.
     */
    fun schedule(context: Context, data: Map<String, String>, seconds: Int) {
        val show = Intent(context, AlertReceiver::class.java).setAction(ACTION_SHOW)
        for ((name, value) in data) show.putExtra(FIELD + name, value)
        val pending = PendingIntent.getBroadcast(context, data.hashCode(), show, FLAGS)
        context.getSystemService(AlarmManager::class.java).setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, System.currentTimeMillis() + seconds * 1000L, pending)
    }

    /** The signal a scheduled alarm carries. */
    fun scheduled(intent: Intent): Map<String, String> =
        intent.extras?.let { extras -> extras.keySet().filter { it.startsWith(FIELD) }.associate { it.removePrefix(FIELD) to extras.getString(it).orEmpty() } }.orEmpty()

    /** Why alerts cannot show right now, and what fixes it; null when they can. */
    fun blocked(context: Context): Pair<String, Fix>? {
        val manager = NotificationManagerCompat.from(context)
        return when {
            !allowed(context) -> "the phone has not been allowed to show this app's alerts." to Fix.ALLOW
            !manager.areNotificationsEnabled() -> "alerts for this app are switched off in the phone's settings." to Fix.APP_SETTING
            manager.getNotificationChannel(AlertKind.APPROVALS.id)?.importance == NotificationManager.IMPORTANCE_NONE ->
                "the kind \"Approvals: ringing\" is switched off in the phone's settings." to Fix.KIND_SETTING
            else -> null
        }
    }

    /** Android 14 and newer: whether the person allowed this app's full page over the locked screen. Earlier: always. */
    fun fullPageAllowed(context: Context): Boolean =
        Build.VERSION.SDK_INT < 34 || context.getSystemService(NotificationManager::class.java).canUseFullScreenIntent()

    /**
     * Tells Google's messaging which app this is, from the values set privately for the build. There is no
     * settings file in the project. False when the build has no values: it then receives nothing.
     */
    fun connect(context: Context): Boolean {
        val values = listOf(BuildConfig.ALERTS_APP, BuildConfig.ALERTS_KEY, BuildConfig.ALERTS_PROJECT, BuildConfig.ALERTS_SENDER)
        if (values.any { it.isEmpty() }) return false
        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(
                context,
                FirebaseOptions.Builder().setApplicationId(BuildConfig.ALERTS_APP).setApiKey(BuildConfig.ALERTS_KEY)
                    .setProjectId(BuildConfig.ALERTS_PROJECT).setGcmSenderId(BuildConfig.ALERTS_SENDER).build(),
            )
        }
        return true
    }

    /** Asks Google for this phone's delivery address. Only called where it is used (test builds today; sign-in later). */
    fun address(done: (String?) -> Unit) {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task -> done(if (task.isSuccessful) task.result else null) }
    }
}

/** Starts with the app's process, also when Google wakes the closed app for a signal. */
class ErpApp : Application() {
    override fun onCreate() {
        super.onCreate()
        AlertCenter.prepare(this)
        AlertCenter.connect(this)
    }
}

/**
 * Receives signals from Google. Only the signal's own short fields are read. The server must send data-only signals:
 * one that carries a ready-made notification text is shown by Google's library itself while the app is in the
 * background, without coming here.
 */
class AlertService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        // A test is the phone's own: one that comes from outside is dropped.
        if (message.data["kind"] != "test") AlertCenter.receive(this, message.data)
    }

    // ponytail: the address is sent to our server after sign-in (Phase 1 part 4); until then a new one is only shown in test builds.
    override fun onNewToken(token: String) = Unit
}

/**
 * A scheduled test signal arriving, the "Stop" and "Remind in 2 hours" buttons of a ringing alert, the reminder
 * coming due, and the phone having restarted. Not open to other apps: only this app and the phone itself reach it.
 */
class AlertReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val slot = Slot.entries.find { it.name == intent.getStringExtra(AlertCenter.SLOT) }
        when (intent.action) {
            AlertCenter.ACTION_SHOW -> AlertCenter.receive(context, AlertCenter.scheduled(intent))
            AlertCenter.ACTION_STOP -> slot?.let { AlertCenter.stopRing(context, it) }
            AlertCenter.ACTION_REMIND -> slot?.let { AlertCenter.remindLater(context, it, asked = true) }
            AlertCenter.ACTION_REMIND_DUE -> AlertCenter.remindDue(context)
            Intent.ACTION_BOOT_COMPLETED -> AlertCenter.afterRestart(context)
        }
    }
}
