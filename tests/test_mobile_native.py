"""mobile-native module: the native Android app stays neutral and keeps its safety rules.

The Kotlin code has its own unit tests (`gradle checkAll` in mobile-native). These checks run without Android
tools, so every contributor and the repository check see at once when a protection is removed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'mobile-native'
APP = NATIVE / 'app/src/main'
KOTLIN = APP / 'kotlin/com/example/erp/app'


class MobileNativeTests(unittest.TestCase):
    def test_app_identity_is_neutral_and_set_privately(self):
        build = (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('providers.gradleProperty("erpAppId").getOrElse("com.example.erp.next")', build)
        self.assertIn('minSdk = 28', build)
        self.assertEqual((APP / 'res/values/strings.xml').read_text(encoding='utf-8').count('>ERP<'), 1)

    def test_the_icon_is_our_own_neutral_mark_in_the_accent_colour(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:icon="@mipmap/ic_launcher"', manifest)
        icon = (APP / 'res/mipmap-anydpi/ic_launcher.xml').read_text(encoding='utf-8')
        for layer in ('<background android:drawable="@color/icon_ground"', '<foreground ', '<monochrome '):
            self.assertIn(layer, icon)
        themes = (APP / 'res/values/themes.xml').read_text(encoding='utf-8')
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        self.assertIn('<color name="icon_ground">#0B4F9E</color>', themes)
        self.assertIn('0x0B4F9E', palette, 'the icon ground is the accent of the day look')
        # Vector drawings only: no picture files that could carry a brand.
        pictures = [p.name for p in (APP / 'res').rglob('*') if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')]
        self.assertEqual(pictures, [])

    def test_nothing_leaves_the_phone_by_backup_or_screenshot(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:allowBackup="false"', manifest)
        self.assertIn('android:dataExtractionRules="@xml/no_backup"', manifest)
        rules = (APP / 'res/xml/no_backup.xml').read_text(encoding='utf-8')
        for part in ('cloud-backup', 'device-transfer'):
            block = rules.split(f'<{part}>')[1].split(f'</{part}>')[0]
            self.assertEqual(set(re.findall(r'<exclude domain="(\w+)"', block)),
                             {'root', 'file', 'database', 'sharedpref', 'external'}, part)
        self.assertNotIn('<include', rules)
        # Screenshots are blocked in every build for people; only a test build, on made-up data, allows them.
        self.assertIn('if (!BuildConfig.DEBUG) window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)', (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8'))

    def test_only_the_permissions_the_app_uses(self):
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertEqual(re.findall(r'uses-permission android:name="android\.permission\.(\w+)"', manifest), ['INTERNET', 'POST_NOTIFICATIONS', 'USE_FULL_SCREEN_INTENT', 'SYSTEM_ALERT_WINDOW', 'RECEIVE_BOOT_COMPLETED', 'USE_BIOMETRIC'])
        self.assertEqual(manifest.count('android:exported="true"'), 1, 'only the launcher screen is open to other apps')

    def test_a_message_that_names_an_action_must_carry_one(self):
        parts = (KOTLIN / 'Parts.kt').read_text(encoding='utf-8')
        # The action message cannot be built without its action; the plain status line has no click.
        self.assertRegex(parts, r'fun ActionMessage\(kind: StatusKind, text: String, actionLabel: String, onAct: \(\) -> Unit')
        # Status lines, pills and notice cards only tell; none of them can be tapped.
        for block in ('Status', 'Pill', 'Notice'):
            body = parts.split(f'fun {block}(')[1].split('\n}\n')[0]
            self.assertNotIn('clickable', body, block)
            self.assertNotIn('onClick', body, block)

    def test_status_tints_are_part_of_the_tested_palette(self):
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        look = (NATIVE / 'core/src/test/kotlin/com/example/erp/core/LookTest.kt').read_text(encoding='utf-8')
        for tint in ('okSoft', 'warnSoft', 'badSoft'):
            self.assertIn(f'val {tint}: Long', palette)
            self.assertIn(f'look.{tint}', look, f'the contrast test covers {tint}')

    def test_the_bar_is_the_five_agreed_places_and_unfinished_ones_stay_out_of_the_real_app(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        block = frame.split('enum class Place')[1].split('\n}')[0]
        self.assertEqual(re.findall(r'^    ([A-Z]+)\("(\w+)"', block, re.M),
                         [('TODAY', 'Today'), ('INBOX', 'Inbox'), ('CHAT', 'Chat'), ('MAIL', 'Mail'), ('MORE', 'More')])
        # Only More is finished; the others exist in test builds only until their real screens do.
        self.assertEqual(re.findall(r'^    ([A-Z]+)\([^\n]*testOnly = true\)', block, re.M), ['TODAY', 'INBOX', 'CHAT', 'MAIL'])
        self.assertNotIn('ComingScreen', frame)
        # Everything behind More has a screen.
        tools = re.findall(r'^    ([A-Z]+)\("', frame.split('enum class Tool')[1].split('\n}')[0], re.M)
        self.assertEqual(tools, ['ALERTS', 'DISPLAY', 'PHONE', 'TRACE', 'DELEGATION', 'WELCOME'])
        # What runs against a stand-in is in test builds only.
        self.assertEqual(re.findall(r'^    ([A-Z]+)\([^\n]*testOnly = true\)', frame.split('enum class Tool')[1].split('\n}')[0], re.M), ['DELEGATION', 'WELCOME'])
        for tool in tools:
            self.assertRegex(frame, rf'Tool\.{tool} -> \w+Screen\(')

    def test_delegation_is_signed_and_keeps_to_its_rules(self):
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Delegation.kt').read_text(encoding='utf-8')
        # Everything: never the higher official, nobody on leave, only with approved leave, never past its end.
        self.assertIn('all.filter { it.relation != Relation.HIGHER && !it.onLeave }', rules)
        self.assertIn('leaveNow(facts.leave, now) == null -> NO_LEAVE', rules)
        self.assertIn('leave.until).withSecond(0)', rules)
        # One step only, and never to the sender.
        self.assertIn('item.delegatedBy == null && item.delegatedTo == null', rules)
        self.assertIn('all.filter { it.id != item.fromId && it.name != item.from }', rules)
        screen = (KOTLIN / 'InboxScreen.kt').read_text(encoding='utf-8')
        delegate = screen.split('fun delegate(target: Item?, choice: DelegateChoice) {')[1].split('\n    }\n')[0]
        # Nothing is delegated before the fingerprint matched.
        self.assertLess(delegate.index('actions.sign(what)'), delegate.index('if (signed) {'))
        self.assertLess(delegate.index('if (signed) {'), delegate.index('actions.delegate('))
        self.assertLess(delegate.index('if (signed) {'), delegate.index('actions.delegateAll('))
        self.assertEqual(screen.count('actions.delegate('), 1)
        self.assertEqual(screen.count('actions.delegateAll('), 1)
        more = (KOTLIN / 'DelegateScreen.kt').read_text(encoding='utf-8')
        again = more.split('fun DelegationScreen(')[1]
        self.assertLess(again.index('sign(Delegations.questionAll('), again.index('if (signed) {'))
        # Another app can start the first screen, so a wish to open one thing counts only with this app's own word.
        main = (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8')
        self.assertIn('AlertCenter.asked(this, intent)?.let { goItem = it }', main)
        self.assertNotIn('getStringExtra(AlertCenter.OPEN_ITEM)', main)
        self.assertIn('if (intent.getStringExtra(OPEN_TOKEN) != token(context)) return null', (KOTLIN / 'AlertCenter.kt').read_text(encoding='utf-8'))
        self.assertLess(again.index('if (signed) {'), again.index('onDelegateAll(choice.to, choice.until)'))
        # What a person chooses or types stays in memory only.
        self.assertNotIn('rememberSaveable', more)
        self.assertNotRegex(more, r'Safe|SharedPreferences|HttpTransport|Saver|File\(')

    def test_an_attendance_sheet_is_signed_once_and_a_rejected_worker_needs_a_reason(self):
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Review.kt').read_text(encoding='utf-8')
        self.assertIn('rejected.filterKeys { it in mine }.values.all { !it.isNullOrBlank() }', rules)
        screen = (KOTLIN / 'InboxScreen.kt').read_text(encoding='utf-8')
        review = screen.split('fun review(target: Item, approve: List<String>, reject: Map<String, String>) {')[1].split('\n    }\n')[0]
        # Nothing is sent before the fingerprint matched, and the question carries both numbers.
        self.assertLess(review.index('actions.sign(Reviews.question(target, approve.size, reject.size))'), review.index('if (signed) {'))
        self.assertLess(review.index('if (signed) {'), review.index('actions.review('))
        self.assertEqual(screen.count('actions.review('), 1)
        part = (KOTLIN / 'ReviewScreen.kt').read_text(encoding='utf-8')
        # The button is there only when every rejected worker has a reason and, if anything is approved, the person looked.
        self.assertLess(part.index('closely -> Notice('), part.index('MainButton(Reviews.words(item, 0, mine.size)'))
        self.assertLess(part.index('!Reviews.ready(item, marked) ->'), part.index('else -> MainButton(Reviews.words(item, approve, reject)'))
        self.assertLess(part.index('approve > 0 && !seen -> Unit'), part.index('else -> MainButton(Reviews.words(item, approve, reject)'))
        self.assertNotIn('rememberSaveable', part)

    def test_every_destination_in_the_frame_has_a_screen(self):
        main = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        places = re.findall(r'^\s+([A-Z_]+)\("', main.split('enum class Place')[1].split('}')[0], re.M)
        self.assertTrue(places)
        for place in places:
            self.assertRegex(main, rf'Place\.{place} -> \w+Screen\(', f'{place} has no screen')

    def test_the_welcome_stand_in_stays_out_of_the_real_app(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'WELCOME\("Welcome preview", "[^"]+", R\.drawable\.ic_key, testOnly = true\)')
        self.assertIn('Place.entries.filter { !it.testOnly || state.testBuild }', frame)
        self.assertIn('Tool.entries.filter { !it.testOnly || state.testBuild }', frame)
        # The first screen is decided in the rules module, never by the person, and a key on the phone wins.
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Welcome.kt').read_text(encoding='utf-8')
        self.assertIn('key == KeyState.PRESENT -> Welcome.Unlock', rules.split('fun welcomeFor(')[1].split('\n')[1])
        # Every button of a Welcome screen needs its action: none has a default.
        screen = (KOTLIN / 'WelcomeScreen.kt').read_text(encoding='utf-8')
        actions = screen.split('class WelcomeActions(')[1].split(')\n')[0]
        self.assertEqual(actions.count('() -> Unit,'), 6)
        self.assertNotIn('= {', actions)

    def test_the_lock_opens_only_for_a_strong_fingerprint(self):
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        for needed in ('.setUserAuthenticationRequired(true)', '.setInvalidatedByBiometricEnrollment(true)',
                       'setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)',
                       '.setAllowedAuthenticators(BIOMETRIC_STRONG)', 'isUserAuthenticationRequirementEnforcedBySecureHardware',
                       'BiometricPrompt.CryptoObject(cipher)'):
            self.assertIn(needed, lock)
        # No PIN, pattern or weak face unlock anywhere in the app.
        kotlin = ''.join(p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt'))
        self.assertNotRegex(kotlin, r'DEVICE_CREDENTIAL|BIOMETRIC_WEAK|setDeviceCredentialAllowed')
        # A miss is written before anything else happens, and the fifth erases.
        count = lock.split('fun countMiss(): Boolean {')[1].split('lateinit var prompt')[0]
        self.assertLess(count.index('prefs.edit(commit = true) { putInt(MISSES, now) }'), count.index('erase(KeyLoss.MISSES)'))
        self.assertIn('countMiss()', lock.split('override fun onAuthenticationFailed()')[1].split('override fun')[0])
        self.assertIn('countMiss()', lock.split('override fun onAuthenticationError(')[1].split('when (errorCode)')[0])
        self.assertIn('info.userAuthenticationValidityDurationSeconds <= 0', lock)
        # A fingerprint question is never answered to a rebuilt screen, and the stand-in cannot reach a real build.
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        for change in ('orientation', 'screenSize', 'uiMode', 'fontScale'):
            self.assertIn(change, manifest.split('android:configChanges="')[1].split('"')[0])
        # The open app exists in memory only, and the app is shown only while it is open.
        self.assertNotRegex(lock.split('object Session')[1], r'prefs|SharedPreferences|File')
        main = (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8')
        self.assertIn('if (!Session.isOpen) {', main)
        # Test builds, and only test builds, see the stand-ins.
        self.assertIn('val testBuild = BuildConfig.DEBUG', main)
        self.assertIn('check(BuildConfig.DEBUG || view.key != KeyState.NONE)', main)
        self.assertIn('Session.left()', main.split('override fun onStop()')[1].split('}')[0])
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Lock.kt').read_text(encoding='utf-8')
        self.assertIn('const val MAX_MISSES = 5', rules)
        self.assertIn('const val AWAY_MS = 5 * 60 * 1000L', rules)

    def test_the_safe_stores_nothing_in_the_clear_and_goes_with_the_key(self):
        safe = (KOTLIN / 'Safe.kt').read_text(encoding='utf-8')
        # Every write is sealed with the data key first, and a locked app writes nothing.
        put = safe.split('fun put(')[1].split('\n    }')[0]
        self.assertIn('Session.withKey { Seal.seal(it, name, value.toByteArray()) } ?: return false', put)
        self.assertLess(put.index('Seal.seal(it, name,'), put.index('putString('))
        self.assertIn('.commit()', put)
        self.assertEqual(safe.count('putString('), 1)
        self.assertIn('Session.withKey { Seal.open(it, name, sealed) }', safe)
        # The data key is used only through the one guarded door, which a wipe cannot interrupt.
        self.assertNotIn('Session.dataKey', safe)
        session = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8').split('object Session')[1]
        self.assertEqual(session.count('@Synchronized'), 3)
        # The safe is emptied when the key is erased and when a new one is made.
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        erase = lock.split('private fun erase(')[1].split('\n    }')[0]
        self.assertIn('Safe.wipe(app)', erase)
        self.assertIn('Session.lock()', erase)
        self.assertIn('Safe.wipe(app)', lock.split('fun make(')[1].split('fun open(')[0])
        # Only the lock's own state and the display settings are stored unsealed.
        kotlin = {p.name: p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt')}
        writers = sorted(name for name, text in kotlin.items() if 'getSharedPreferences(' in text)
        self.assertEqual(writers, ['AlertCenter.kt', 'MainActivity.kt', 'PhoneLock.kt', 'Safe.kt'])
        # What the alerts remember unsealed are two sets of short fingerprints, nothing else.
        # Fingerprints of what waits and of chats with something unread, and two plain counts: nothing readable.
        self.assertEqual(sorted(set(re.findall(r'put\w+\("(\w+)"', kotlin['AlertCenter.kt']))), ['chats', 'deciding', 'mails', 'notices', 'rejected'])
        self.assertEqual(re.findall(r'getSharedPreferences\("(\w+)"', kotlin['MainActivity.kt']), ['display'])
        seal = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Seal.kt').read_text(encoding='utf-8')
        self.assertIn('"AES/GCM/NoPadding"', seal)
        self.assertIn('SecureRandom().nextBytes(it)', seal)
        self.assertEqual(seal.count('cipher.updateAAD(name.toByteArray())'), 2)

    def test_the_chat_stand_in_stays_out_of_the_real_app_and_sends_nothing(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'CHAT\("Chat", "Chat", R\.drawable\.ic_chat, testOnly = true\)')
        # The stand-in keeps everything in memory: no storage, no network, no safe.
        preview = (KOTLIN / 'ChatPreview.kt').read_text(encoding='utf-8')
        self.assertNotRegex(preview, r'Safe|SharedPreferences|HttpTransport|Saver|File\(')
        screen = (KOTLIN / 'ChatScreen.kt').read_text(encoding='utf-8')
        # People are told that company rooms are kept, and every chat button needs its action.
        self.assertIn('if (room.company) Text("Company room. Messages here are kept by the company."', screen)
        actions = screen.split('class ChatActions(')[1].split('\n)')[0]
        self.assertEqual(actions.count('->'), 3)
        self.assertNotIn('= {', actions)
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Chat.kt').read_text(encoding='utf-8')
        self.assertIn('const val KEEP_DAYS = 7L', rules)

    def test_the_mail_stand_in_stays_out_of_the_real_app_and_the_protections_are_built_in(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'MAIL\("Mail", "Mail", R\.drawable\.ic_mail, testOnly = true\)')
        preview = (KOTLIN / 'MailPreview.kt').read_text(encoding='utf-8')
        self.assertNotRegex(preview, r'Safe|SharedPreferences|HttpTransport|Saver|File\(|UriHandler|Intent')
        screen = (KOTLIN / 'MailScreen.kt').read_text(encoding='utf-8')
        # A link is opened only from the question that shows its real host, and nowhere else.
        self.assertEqual(screen.count('onOpenLink(link)'), 1)
        asked = screen.split('if (asked == link && host != null) {')[1].split('\n            }')[0]
        self.assertIn('It leads to $host.', asked)
        self.assertIn('onOpenLink(link)', asked)
        self.assertNotRegex(screen, r'WebView|UriHandler|Intent\(')
        # No "save to phone": the owner's decision is a setting that is off.
        self.assertNotRegex(screen, r'[Ss]ave to (the )?phone"\s*,')
        self.assertIn('This mail goes outside the company', screen)
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Mail.kt').read_text(encoding='utf-8')
        self.assertIn('RECEIVED("Received")', rules)
        self.assertNotIn('"Inbox"', rules.split('enum class Folder')[1].split('}')[0])
        self.assertIn('domain.isEmpty() || domain !in company', rules)
        # The host shown is never converted from special letters (programs disagree on the result), and a link with
        # anything outside plain printable ASCII, or a numeric host, cannot be opened.
        self.assertNotIn('IDN', rules)
        self.assertIn("link.all { it in '!'..'~' }", rules)
        self.assertIn('!numeric && !local', rules)
        # What is being written is kept in memory only, never in the state Android stores outside the app.
        for name in ('MailScreen.kt', 'ChatScreen.kt'):
            text = (KOTLIN / name).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'(body|subject|to|draft|asked|file) by rememberSaveable', name)

    def test_today_shows_counts_only_and_its_stand_in_asks_no_server(self):
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Today.kt').read_text(encoding='utf-8')
        # What Today knows holds no amount and no other person's name: counts, states and times only.
        facts = rules.split('data class TodayFacts(')[1].split('\n)')[0]
        self.assertNotRegex(facts, r'(?i)amount|total:|rupee|BigDecimal|Money|names?:')
        # Nothing the server writes freely reaches Today: no text field at all in what Today knows.
        self.assertNotRegex(facts, r': (List<)?String')
        self.assertIn('!facts.online -> null', rules.split('fun emptyLine(')[1].split('\n    }')[0])
        # "Nothing is waiting" is never said when a check failed.
        empty = rules.split('fun emptyLine(')[1].split('\n    }')[0]
        self.assertLess(empty.index('facts.failed.isNotEmpty() -> null'), empty.index('"Nothing is waiting for you today."'))
        # A deadline today sorts first.
        self.assertIn('compareBy<Card> { !urgent(it) }', rules)
        preview = (KOTLIN / 'TodayPreview.kt').read_text(encoding='utf-8')
        self.assertNotRegex(preview, r'Safe|SharedPreferences|HttpTransport|Saver|File\(')
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'TODAY\("Today", "Today", R\.drawable\.ic_today, testOnly = true\)')
        screen = (KOTLIN / 'TodayScreen.kt').read_text(encoding='utf-8')
        # A card is a button only when it has somewhere to lead.
        self.assertIn('onClick = if (lead != null) ({ onOpen(lead) }) else null', screen)

    def test_a_decision_needs_the_fingerprint_and_inbox_is_a_stand_in(self):
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertRegex(frame, r'INBOX\("Inbox", "Inbox", R\.drawable\.ic_inbox, testOnly = true\)')
        # The frame cannot be built without the fingerprint question: it has no default.
        self.assertIn('    sign: (what: String, done: (Boolean, String?) -> Unit) -> Unit,', frame)
        self.assertIn('    alertActions: AlertActions,', frame)
        main = (KOTLIN / 'MainActivity.kt').read_text(encoding='utf-8')
        self.assertIn('sign = ::sign,', main)
        self.assertIn('lock.confirm(this, what)', main)
        self.assertIn('done(result is LockResult.Confirmed,', main)
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        # Signing is the same proof as opening: the chip's key, misses counted, and the released key thrown away.
        confirm = lock.split('fun confirm(')[1].split('private fun unlock(')[0]
        self.assertIn('it.fill(0)', confirm)
        self.assertIn('ask(activity, title, cipher, countMisses = true, done = done, what = what)', lock)
        self.assertIn('setDescription(what)', lock)
        screen = (KOTLIN / 'InboxScreen.kt').read_text(encoding='utf-8')
        # A decision is sent only from inside the answer to the fingerprint question, and only after a match.
        self.assertEqual(screen.count('actions.decide('), 1)
        decide = screen.split('fun decide(')[1].split('\n    }\n')[0]
        self.assertLess(decide.index('actions.sign(Inbox.question(decision, target))'), decide.index('if (signed) {'))
        self.assertLess(decide.index('if (signed) {'), decide.index('actions.decide('))
        # Approve exists only once the person said they looked; nothing typed is kept outside the app's memory.
        self.assertIn('if (seen) MainButton("Approve with your fingerprint", onApprove)', screen)
        self.assertNotRegex(screen, r'(typed|quick|until|trouble|result) by rememberSaveable')
        actions = screen.split('class InboxActions(')[1].split('\n)')[0]
        self.assertNotIn('= {', actions)
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Inbox.kt').read_text(encoding='utf-8')
        # Two decisions and no final one. No "decide later": who does not decide delegates or is reminded.
        self.assertIn('enum class Decision(val done: String) { APPROVED("Approved"), REJECTED("Rejected") }', rules)
        self.assertNotRegex(rules + screen, r'Hold\b|Decide later|ON_HOLD')
        self.assertIn('OutlineButton("Remind me in 2 hours", onRemind)', screen)
        preview = (KOTLIN / 'InboxPreview.kt').read_text(encoding='utf-8')
        self.assertNotRegex(preview, r'Safe|SharedPreferences|HttpTransport|Saver|File\(')

    def test_an_alert_shows_only_the_apps_own_words_and_decides_nothing(self):
        rules = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Alerts.kt').read_text(encoding='utf-8')
        # Every word comes from a fixed sentence in the rules; an unknown kind is dropped.
        self.assertIn('else -> return state to AlertAction.Ignore', rules)
        self.assertNotRegex(rules, r'data\["(title|body|message|text|site_label)"\]')
        center = (KOTLIN / 'AlertCenter.kt').read_text(encoding='utf-8')
        self.assertEqual(center.count('.setContentTitle(alert.words)'), 2)
        # No second line of text, no ready-made notification from the signal, nothing but the short fields.
        self.assertNotRegex(center, r'setContentText|setStyle|setSubText|message\.notification')
        # No choice on a ringing alert decides: each opens the app (and its lock) or only stops the ringing for now.
        self.assertEqual(re.findall(r'\.addAction\(0, "([\w ]+)", (\w+)\(', center),
                         [('Stop', 'tap'), ('Open', 'open'), ('Approve', 'open'), ('Reject', 'open'), ('Remind in 2 hours', 'tap'), ('Open', 'open'), ('Remind in 2 hours', 'tap')])
        # The reminder is fixed at 2 hours (2 minutes in test builds), has no chooser, and asks for nothing exact.
        self.assertIn('val REMIND_MS = if (BuildConfig.DEBUG) 2 * 60_000L else 2 * 60 * 60_000L', center)
        self.assertNotRegex(center, r'setExact|setAlarmClock|SCHEDULE_EXACT_ALARM')
        self.assertIn('.setFullScreenIntent(page, true)', center)
        # "Over other apps" is used for one thing: opening the app's own full page for a ringing alert, where the
        # person allowed it and the phone is in use. No window is ever drawn over another app.
        self.assertIn('if (page && onTop(context) == true && inUse(context) && pageDue(context)) runCatching { context.startActivity(page(context, alert)) }', center)
        self.assertEqual(center.count('context.startActivity('), 1)
        for name, text in ((p.name, p.read_text(encoding='utf-8')) for p in KOTLIN.glob('*.kt')):
            self.assertNotRegex(text, r'TYPE_APPLICATION_OVERLAY|TYPE_SYSTEM_ALERT|WindowManager\)?\.addView|\.addView\(', name)
        # While the app is open and unlocked nothing is put over it, and the list entry makes no sound.
        self.assertIn('val inside = inApp?.takeIf { Session.isOpen }', center)
        self.assertIn('manager.notify(alert.slot.id, entry(context, alert).setSilent(true).build())', center)
        # Looking at a place removes that place's alert only; approvals go by a decision alone.
        frame_text = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertEqual(sorted(re.findall(r'alertActions\.seen\("(\w+)"\)', frame_text)), ['chat', 'mail', 'notice'])
        self.assertIn('.setTimeoutAfter(RING_MS)', center)
        # The ringing kind never asks to get past the phone's silent mode.
        self.assertNotRegex(center, r'setBypassDnd|IMPORTANCE_MAX|USAGE_ALARM')
        ring = (KOTLIN / 'RingActivity.kt').read_text(encoding='utf-8')
        # Nothing is done on the lock screen: the page knows no lock, no safe, no signing and no decision.
        self.assertNotRegex(ring, r'actions\.|Decision|PhoneLock|Safe|Session|\.confirm\(|sign\(')
        self.assertIn('startActivity(AlertCenter.openApp(this, slot, item, start))', ring)
        self.assertIn('AlertCenter.receive(this, message.data)', center)
        self.assertIn('PendingIntent.FLAG_IMMUTABLE', center)
        self.assertIn('Intent(context, MainActivity::class.java)', center)
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('<service android:name=".AlertService" android:exported="false">', manifest)
        self.assertIn('<receiver android:name=".AlertReceiver" android:exported="false">', manifest)
        page = manifest.split('android:name=".RingActivity"')[1].split('/>')[0]
        for needed in ('android:exported="false"', 'android:showWhenLocked="true"', 'android:excludeFromRecents="true"'):
            self.assertIn(needed, page)
        self.assertIn('<meta-data android:name="firebase_messaging_auto_init_enabled" android:value="false" />', manifest)
        # A lost key takes the alerts with it; a tapped alert only names a place and goes through the lock.
        lock = (KOTLIN / 'PhoneLock.kt').read_text(encoding='utf-8')
        self.assertIn('AlertCenter.clear(app)', lock.split('private fun erase(')[1].split('\n    }')[0])
        frame = (KOTLIN / 'AppFrame.kt').read_text(encoding='utf-8')
        self.assertIn('if (goTo in places) {', frame)
        # Google's messaging only: no analytics, no settings file, no build plug-in; its values are set privately.
        build = (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8') + (NATIVE / 'build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('implementation("com.google.firebase:firebase-messaging:26.0.2")', build)
        self.assertNotRegex(build, r'google-services|firebase-analytics|firebase-crashlytics|firebase-bom')
        self.assertIn('"ALERTS_APP" to "erpAlertsApp"', build)
        self.assertNotIn('erpAlerts', (NATIVE / 'gradle.properties').read_text(encoding='utf-8'))
        self.assertFalse((NATIVE / 'app/google-services.json').exists() and 'google-services.json' not in (NATIVE / '.gitignore').read_text(encoding='utf-8'))

    def test_the_look_follows_the_phone_and_never_the_wallpaper(self):
        kotlin = ''.join(p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt'))
        self.assertIn('isSystemInDarkTheme()', kotlin, 'day and night follow the phone')
        self.assertIn('Sensor.TYPE_LIGHT', kotlin, 'Outdoor mode follows bright light')
        self.assertIn('"outdoor-automatic", true', kotlin, 'automatic by default; the person can switch it off')
        self.assertNotRegex(kotlin, r'dynamic(Light|Dark)ColorScheme', 'status colours must not change with the wallpaper')
        # Screens name colours by their job only; raw colour numbers live in the tested palette.
        for path in KOTLIN.glob('*.kt'):
            if path.name != 'Theme.kt':
                self.assertNotRegex(path.read_text(encoding='utf-8'), r'Color\(0x|Color\.(White|Black|Red|Green|Gray)', path.name)
        night = (APP / 'res/values-night/themes.xml').read_text(encoding='utf-8')
        self.assertIn('#0F141A', night, 'no white flash at start in night mode')
        palette = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Palette.kt').read_text(encoding='utf-8')
        self.assertIn('0x0F141A', palette, 'the start colour is the page colour of the dark look')

    def test_text_sizes_scale_with_the_phone(self):
        theme = (KOTLIN / 'Theme.kt').read_text(encoding='utf-8')
        self.assertNotRegex(theme, r'fontSize = [^,]*\.dp', 'text sizes are in sp so they follow the font size set on the phone')
        sizes = [int(n) for n in re.findall(r'fontSize = \((\d+) \+ more\)\.sp', theme)]
        self.assertTrue(sizes and min(sizes) >= 15, 'no text smaller than 15')

    def test_the_robot_walks_every_link_in_every_look_and_size(self):
        robot = (NATIVE / 'app/src/test/kotlin/com/example/erp/app/ScreensTest.kt').read_text(encoding='utf-8')
        self.assertIn('for (place in Place.entries)', robot, 'every place, also ones added later')
        for look in ('LIGHT', 'DARK', 'OUTDOOR'):
            self.assertIn(f'walk(Palettes.{look}', robot)
        self.assertIn('fontScale = 2.0f', robot, 'double font size')
        self.assertIn('w1100dp', robot, 'tablet width')
        self.assertIn('48.dp', robot, 'tap targets are measured')
        self.assertIn('runs off the side', robot, 'text overflow is measured')
        build = (NATIVE / 'build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('":app:testDebugUnitTest"', build, 'the check command runs the robot')

    def test_every_save_goes_through_the_one_calling_layer(self):
        saver = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Saver.kt').read_text(encoding='utf-8')
        for point in ('Point.SCREEN', 'Point.NETWORK', 'Point.GATEWAY', 'Point.SERVER', 'Point.READ_BACK'):
            self.assertIn(point, saver)
        # A raw server error text is never the sentence a person reads.
        self.assertIn('"The server has a problem right now.', saver)

    def test_the_app_reaches_one_server_encrypted_and_follows_no_redirect(self):
        net = (KOTLIN / 'HttpTransport.kt').read_text(encoding='utf-8')
        self.assertIn('connection.instanceFollowRedirects = false', net)
        self.assertIn('uri.scheme == "https" || (uri.scheme == "http" && uri.host == LOOPBACK)', net)
        self.assertIn('const val LOOPBACK = "127.0.0.1"', net)
        self.assertIn('connection.setRequestProperty("X-Request-ID", trackingId)', net)
        self.assertIn('"Authorization", "Bearer $it"', net)
        # The network is opened in this one file only, and the phone itself refuses unencrypted traffic too.
        kotlin = {p.name: p.read_text(encoding='utf-8') for p in KOTLIN.glob('*.kt')}
        opens = sorted(name for name, text in kotlin.items() if re.search(r'openConnection|HttpURLConnection|java\.net\.Socket|OkHttp', text))
        self.assertEqual(opens, ['HttpTransport.kt'])
        # The one other connection is Google's messaging library's own, used in one file only.
        self.assertEqual(sorted(name for name, text in kotlin.items() if 'com.google.firebase' in text), ['AlertCenter.kt'])
        manifest = (APP / 'AndroidManifest.xml').read_text(encoding='utf-8')
        self.assertIn('android:usesCleartextTraffic="false"', manifest)
        self.assertIn('android:windowSoftInputMode="adjustResize"', manifest)
        self.assertNotIn('networkSecurityConfig', manifest)
        # The server's address is set privately, never here.
        build = (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        self.assertIn('providers.gradleProperty("erpServer").getOrElse("")', build)
        self.assertNotIn('erpServer', (NATIVE / 'gradle.properties').read_text(encoding='utf-8'))

    def test_reports_leave_values_out_by_default(self):
        trace = (NATIVE / 'core/src/main/kotlin/com/example/erp/core/Trace.kt').read_text(encoding='utf-8')
        self.assertIn('fun report(withValues: Boolean = false)', trace)
        self.assertIn('if (withValues && mark.detail != null)', trace)

    def test_versions_and_checksums_are_pinned(self):
        text = (NATIVE / 'build.gradle.kts').read_text(encoding='utf-8') + (NATIVE / 'app/build.gradle.kts').read_text(encoding='utf-8')
        for line in re.findall(r'(?:implementation|testImplementation)\("([^"]+)"\)', text):
            if line.startswith('androidx.compose.') and ':compose-bom:' not in line:
                continue  # versions come from the pinned Compose list
            self.assertRegex(line, r':\d+(\.\d+)+$', f'{line} has no exact version')
        self.assertNotRegex(text, r'[:"]\+"|latest\.release|-SNAPSHOT')
        metadata = (NATIVE / 'gradle/verification-metadata.xml').read_text(encoding='utf-8')
        self.assertIn('<verify-metadata>true</verify-metadata>', metadata)
        self.assertGreater(metadata.count('<sha256 '), 300)

    def test_source_names_no_host(self):
        for path in list(NATIVE.rglob('*.kt')) + list(NATIVE.rglob('*.kts')):
            if 'build' in path.parts:
                continue
            for host in re.findall(r'https?://([A-Za-z0-9.-]+)', path.read_text(encoding='utf-8')):
                self.fail(f'{path.relative_to(ROOT)} names {host}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
