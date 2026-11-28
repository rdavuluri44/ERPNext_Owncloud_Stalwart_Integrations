package com.example.erp.app

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.semantics.getOrNull
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.hasClickAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onRoot
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.unit.dp
import com.example.erp.core.Palette
import com.example.erp.core.Palettes
import com.example.erp.core.Tracer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/**
 * The robot that walks every link. In every look, at phone and tablet width, at normal and double font size, it
 * opens every place in the frame and every item on it, and fails when a destination is missing, when anything
 * that can be tapped is smaller than a finger, or when text runs off the side of the screen.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [35])
class ScreensTest {
    @get:Rule
    val compose = createComposeRule()

    private val phone = PhoneCheck(
        listOf(
            PhoneLine(StatusKind.OK, R.drawable.ic_fingerprint, "Fingerprint sensor", "Ready to use."),
            PhoneLine(StatusKind.WARN, R.drawable.ic_phone, "Android 15", "Supported."),
        ),
        usable = true,
    )

    /** What the fingerprint question was asked to sign, in order; and whether the pretend finger matches. */
    private val signed = mutableListOf<String>()
    private var fingerprintMatches = true

    /** What the Alerts screen asked for, in order. */
    private val alertCalls = mutableListOf<String>()

    /** The places whose alert was told to go because the person looked at them. */
    private val seenCalls = mutableListOf<String>()
    private var lineAnswers = mutableListOf<Boolean>()

    private fun show(palette: Palette, testBuild: Boolean = true, withTraces: Boolean = true, alerts: AlertsView = AlertsView(connected = true, address = "delivery-address-for-tests"), goTo: Place? = null, goItem: InboxJump? = null, line: String? = null) {
        val tracer = Tracer()
        if (withTraces) sampleTraces(tracer)
        compose.setContent {
            var traces by androidx.compose.runtime.remember { mutableStateOf(tracer.all()) }
            var automatic by androidx.compose.runtime.remember { mutableStateOf(true) }
            var forced by androidx.compose.runtime.remember { mutableStateOf(false) }
            var note by androidx.compose.runtime.remember { mutableStateOf<String?>(null) }
            ErpTheme(if (forced) Palettes.OUTDOOR else palette) {
                AppFrame(
                    FrameState(if (forced) Palettes.OUTDOOR else palette, testBuild, traces, phone, "Test Phone", "0.1.0", hasLightSensor = true, automaticOutdoor = automatic, forcedOutdoor = forced, lux = 24f, safeNote = note, alerts = alerts),
                    alertActions = AlertActions(
                        fix = { alertCalls += "fix ${it.name}" },
                        openKind = { alertCalls += "kind ${it.id}" },
                        signal = { alertCalls += "signal ${it["kind"]}" },
                        removeAll = { alertCalls += "remove all" },
                        remind = { alertCalls += "remind" },
                        seen = { seenCalls += it },
                    ),
                    goTo = goTo,
                    goItem = goItem,
                    line = line,
                    onLine = { lineAnswers += it },
                    sign = { what, done -> signed += what; done(fingerprintMatches, if (fingerprintMatches) null else com.example.erp.core.LockRules.missWords(1)) },
                    onAddSample = { sampleTraces(tracer); traces = tracer.all() },
                    onAutomaticOutdoor = { automatic = it },
                    onForcedOutdoor = { forced = it },
                    onTryConnection = { tracer.start("req_0123456789abcdef", "Connection test"); tracer.mark("req_0123456789abcdef", com.example.erp.core.Point.NETWORK, false, "no answer"); traces = tracer.all() },
                    onSafeNote = { note = "A note saved Today, 10:42 was read back from the safe." },
                )
            }
        }
    }

    /** A place in the bar (or rail). A card on Today can carry the same word, so the bar's own kind of button is asked for. */
    private fun place(place: Place) = compose.onNode(hasText(place.label) and androidx.compose.ui.test.isSelectable())

    /** Opens one of the screens behind More, from wherever the app is. */
    private fun tool(tool: Tool) {
        place(Place.MORE).performClick()
        tap(tool.title)
    }

    /** Everything that can be tapped is at least 48 dp tall, and no text reaches past the screen's side. */
    private fun checkLayout(where: String) {
        val root = compose.onRoot().fetchSemanticsNode()
        val density = root.layoutInfo.density
        val min = with(density) { 48.dp.toPx() }
        val tappable = SemanticsMatcher("can be tapped") { it.config.getOrNull(androidx.compose.ui.semantics.SemanticsActions.OnClick) != null }
        for (node in compose.onAllNodes(tappable).fetchSemanticsNodes()) {
            assertTrue("$where: a tap target is only ${node.size.height} px tall (needs $min)", node.size.height >= min - 1)
        }
        val text = SemanticsMatcher("has text") { it.config.getOrNull(SemanticsProperties.Text) != null }
        for (node in compose.onAllNodes(text).fetchSemanticsNodes()) {
            val words = node.config[SemanticsProperties.Text].joinToString()
            assertTrue("$where: \"$words\" has no size", node.size.width > 0 && node.size.height > 0)
            assertTrue("$where: \"$words\" runs off the side", node.boundsInRoot.left >= -1 && node.boundsInRoot.right <= root.size.width + 1)
        }
    }

    private fun walk(palette: Palette, wide: Boolean) {
        show(palette)
        val name = "${palette.name}${if (wide) " wide" else ""}"
        // Every place in the bar opens its own screen.
        for (place in Place.entries) {
            place(place).performClick()
            compose.onNode(hasText(place.title) and !hasClickAction()).assertIsDisplayed()
            checkLayout("$name / ${place.label}")
        }
        // Every made-up day on Today: each role and each situation.
        place(Place.TODAY).performClick()
        for (day in Day.entries) {
            compose.onNodeWithText("Role: ${day.label}").assertIsDisplayed()
            checkLayout("$name / today, ${day.label}")
            compose.onNodeWithText("Role: ${day.label}").performClick()
        }
        compose.onNodeWithText("Role: ${Day.SUPERVISOR.label}").assertIsDisplayed()
        // Inbox: the three views; every waiting item opens, and so do "Reject" and "Decide later"; all lead back.
        place(Place.INBOX).performClick()
        for (view in listOf("Done", "Sent", "Waiting")) {
            tap(view)
            checkLayout("$name / inbox, $view")
        }
        for (item in listOf("Purchase request: cement", "Attendance, Site A, 6 workers", "Payment to a supplier", "Purchase request: steel", "Leave, 3 days", "Advance for site expenses")) {
            tap(item)
            reach(compose.onNode(hasText(item) and !hasClickAction())).assertIsDisplayed()
            checkLayout("$name / inbox item $item")
            reach(compose.onNodeWithContentDescription("Back")).performClick()
        }
        tap("Payment to a supplier")
        tap("Reject")
        shown("Accounts, S. Example is told. A reason is not required")
        checkLayout("$name / inbox reject")
        tap("Do not reject")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        tap("Done")
        tap("Purchase request: sand")
        shown("A decision cannot be undone here.")
        checkLayout("$name / inbox, a past decision")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Everything behind More opens its own screen and leads back to More.
        for (tool in Tool.entries) {
            tool(tool)
            reach(compose.onNode(hasText(tool.title) and !hasClickAction())).assertIsDisplayed()
            checkLayout("$name / ${tool.title}")
            compose.onNodeWithContentDescription("Back").performClick()
            compose.onNode(hasText("More") and !hasClickAction()).assertIsDisplayed()
        }
        // Every item on Data trace opens its detail, and the way back works.
        tool(Tool.TRACE)
        for (action in listOf("Sample: check-out refused", "Sample: check-in saved")) {
            compose.onNode(hasText(action, substring = true) and hasClickAction()).performScrollTo().performClick()
            compose.onNodeWithText("1. Screen: OK").assertIsDisplayed()
            compose.onNodeWithText("Copy this trace").performScrollTo().assertIsDisplayed()
            checkLayout("$name / trace detail")
            if (!wide) compose.onNodeWithText("Back to the list").performScrollTo().performClick()
            compose.onNode(hasText("Data trace") and !hasClickAction()).assertIsDisplayed()
        }
        // Every situation of the Welcome screens, and the help screen behind each one and the way back.
        tool(Tool.WELCOME)
        for (situation in Situation.entries) {
            compose.onNodeWithText("Situation: ${situation.label}").assertIsDisplayed()
            checkLayout("$name / welcome, ${situation.label}")
            compose.onNodeWithContentDescription("Help").performClick()
            shown("How it works")
            checkLayout("$name / how it works")
            compose.onNodeWithText("Back").performScrollTo().performClick()
            compose.onNodeWithText("Situation: ${situation.label}").performClick()
        }
        compose.onNodeWithText("Situation: ${Situation.NEW.label}").assertIsDisplayed()
        // Every chat room opens and leads back, and so does the list of colleagues.
        place(Place.CHAT).performClick()
        for (room in listOf("Notices", "Site A", "Site A engineers", "Project manager")) {
            tap(room)
            reach(compose.onNode(hasText(room) and !hasClickAction())).assertIsDisplayed()
            checkLayout("$name / chat room $room")
            if (!wide) reach(compose.onNodeWithContentDescription("Back")).performClick()
        }
        tap("New chat with a colleague")
        compose.onNodeWithText("New chat").assertIsDisplayed()
        checkLayout("$name / new chat")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        compose.onNode(hasText("Chat") and !hasClickAction()).assertIsDisplayed()
        // Every mail conversation opens and leads back; so do the folders, a new mail and an attachment.
        place(Place.MAIL).performClick()
        for (sender in listOf("Project manager", "Supplier accounts", "IT Support", "HR (2)")) {
            tap(sender)
            reach(compose.onNode(hasText("Reply") and hasClickAction())).assertIsDisplayed()
            checkLayout("$name / mail from $sender")
            if (!wide) reach(compose.onNodeWithContentDescription("Back")).performClick()
        }
        tap("Folder: Received")
        shown("Folders")
        checkLayout("$name / mail folders")
        tap("Sent")
        shown("Folder: Sent")
        tap("Write a mail")
        shown("New mail")
        checkLayout("$name / new mail")
        tap("Discard this mail")
        tap("Folder: Sent")
        tap("Received")
        tap("Project manager")
        tap("pour-checklist.pdf")
        shown("Attachments open here, inside the app.")
        checkLayout("$name / attachment")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        reach(compose.onNode(hasText("Reply") and hasClickAction())).assertIsDisplayed()
    }

    private fun type(label: String, text: String) = reach(compose.onNode(androidx.compose.ui.test.hasSetTextAction() and hasText(label))).performTextInput(text)

    private fun absent(text: String) = assertEquals(text, 0, compose.onAllNodesWithText(text, substring = true).fetchSemanticsNodes().size)

    @Test
    fun mailFromOutsideSaysSoAndALinkShowsWhereItLeadsBeforeItOpens() {
        show(Palettes.LIGHT)
        place(Place.MAIL).performClick()
        // Unread is said in words; an outside sender too.
        reach(compose.onNode(hasText("Project manager") and hasText("New") and hasClickAction())).assertIsDisplayed()
        reach(compose.onNode(hasText("IT Support") and hasText("Outside") and hasClickAction())).assertIsDisplayed()
        tap("Supplier accounts")
        shown("This sender is not in the company.")
        // Pictures from the internet wait for a tap.
        shown("2 pictures from the internet are not loaded")
        tap("Show pictures")
        shown("2 pictures from the internet shown.")
        // The link says where it leads, asks, and "do not open" opens nothing.
        tap("Link to portal.supplier-example.net")
        shown("It leads to portal.supplier-example.net.")
        tap("Do not open")
        shown("Stand-in: nothing is sent.")
        tap("Link to portal.supplier-example.net")
        tap("Open portal.supplier-example.net")
        shown("the browser would open portal.supplier-example.net")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Opening read it. The company's name in front of another domain is shown as what it is.
        tap("IT Support")
        shown("Link to example.com.account-check.net")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        assertEquals(0, compose.onAllNodes(hasText("Supplier accounts") and hasText("New")).fetchSemanticsNodes().size)
        // A sender inside the company carries no warning.
        tap("Project manager")
        absent("This sender is not in the company.")
    }

    @Test
    fun aReplyIsFilledInWarnsBeforeLeavingTheCompanyAndLandsInSent() {
        show(Palettes.LIGHT)
        place(Place.MAIL).performClick()
        tap("Project manager")
        tap("Reply to all") // the sender and the engineer in copy, not me
        shown("pm@example.com, engineer@example.com")
        shown("Re: Pour checklist for Friday")
        shown("Project manager wrote:")
        absent("goes outside the company")
        tap("Send")
        shown("Stand-in: put in Sent, not sent.")
        tap("Folder: Received")
        tap("Sent")
        reach(compose.onNode(hasText("To: pm@example.com, engineer@example.com") and hasClickAction())).assertIsDisplayed()
        // A new mail: no Send until it can be sent, an unreadable address is named, an outside one is warned about.
        tap("Write a mail")
        assertEquals(0, compose.onAllNodes(hasText("Send") and hasClickAction()).fetchSemanticsNodes().size)
        type("To", "engineer")
        type("Subject", "Tomorrow")
        shown("Not a mail address: engineer.")
        assertEquals(0, compose.onAllNodes(hasText("Send") and hasClickAction()).fetchSemanticsNodes().size)
        type("To", "@supplier-example.net")
        shown("This mail goes outside the company: engineer@supplier-example.net")
        tap("Send")
        reach(compose.onNode(hasText("To: engineer@supplier-example.net") and hasClickAction())).assertIsDisplayed()
        // Back from a new mail leads to the list, never into a mail read earlier.
        tap("Folder: Sent")
        tap("Received")
        tap("HR (2)")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        tap("Write a mail")
        tap("Discard this mail")
        shown("Folder: Received")
        assertEquals(0, compose.onAllNodes(hasText("Reply") and hasClickAction()).fetchSemanticsNodes().size)
        // Also straight after a reply was sent: a new mail then leads back to the list, not into that conversation.
        tap("HR (2)")
        tap("Reply")
        tap("Send")
        tap("Write a mail")
        type("Subject", "One\nline")
        shown("One line")
        tap("Discard this mail")
        shown("Folder: Received")
        assertEquals(0, compose.onAllNodes(hasText("Reply") and hasClickAction()).fetchSemanticsNodes().size)
    }

    @Test
    fun aMessageIsSentWaitsWithoutSignalAndNoticesCannotBeWrittenTo() {
        show(Palettes.LIGHT)
        place(Place.CHAT).performClick()
        // Notices first, then my site; unread shown in words.
        compose.onNode(hasText("Site A") and hasText("2 new") and hasClickAction()).assertIsDisplayed()
        compose.onNode(hasText("Site A") and hasClickAction()).performClick()
        shown("Company room. Messages here are kept by the company.")
        assertEquals("nothing to send yet, so no Send button", 0, compose.onAllNodesWithText("Send").fetchSemanticsNodes().size)
        compose.onNode(androidx.compose.ui.test.hasSetTextAction()).performTextInput("On my way")
        tap("Send")
        shown("On my way")
        assertEquals(0, compose.onAllNodesWithText("Waiting to send").fetchSemanticsNodes().size)
        // A tap on a message answers it.
        reach(compose.onNode(hasText("Two more vibrators", substring = true) and hasClickAction())).performClick()
        shown("Replying to Store keeper")
        tap("Signal: on (stand-in)") // now without signal
        compose.onNode(androidx.compose.ui.test.hasSetTextAction()).performTextInput("I have it")
        tap("Send")
        shown("Reply to Store keeper")
        shown("Waiting to send")
        tap("Signal: off (stand-in)") // back online: it is sent
        assertEquals(0, compose.onAllNodesWithText("Waiting to send").fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Opening the room read its messages; the list shows my last line.
        assertEquals(0, compose.onAllNodesWithText("2 new").fetchSemanticsNodes().size)
        reach(compose.onNode(hasText("You: I have it", substring = true) and hasClickAction())).assertIsDisplayed()
        // Nobody writes in Notices.
        tap("Notices")
        shown("Nobody can write in this room.")
        assertEquals(0, compose.onAllNodes(androidx.compose.ui.test.hasSetTextAction()).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // A new one-to-one chat opens empty, is not a company room, and the same colleague opens the same chat again.
        tap("New chat with a colleague")
        tap("HR")
        shown("No messages yet.")
        assertEquals(0, compose.onAllNodesWithText("Company room", substring = true).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        tap("New chat with a colleague")
        tap("HR")
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        assertEquals(1, compose.onAllNodes(hasText("HR") and hasClickAction()).fetchSemanticsNodes().size)
    }

    /** Scrolled to as a person would; something outside any scrolling area is simply where it is. */
    private fun reach(node: androidx.compose.ui.test.SemanticsNodeInteraction) = node.also { runCatching { it.performScrollTo() } }

    private fun tap(label: String) = reach(compose.onNode(hasText(label) and hasClickAction())).performClick()

    private fun shown(text: String) = reach(compose.onNodeWithText(text, substring = true)).assertIsDisplayed()

    /** Every button of the Welcome screens leads to the situation it names; none is a dead end. */
    @Test
    fun everyWelcomeButtonLeadsSomewhere() {
        show(Palettes.LIGHT)
        tool(Tool.WELCOME)
        shown("Your phone becomes your key.")
        tap("Request access")
        shown("Request sent")
        shown("Meet them with this phone and your ID.")
        shown("+91 90••• ••000")
        // Cancelling asks once more, and "keep" really keeps.
        tap("Cancel my request")
        shown("Cancel this request?")
        tap("Keep my request")
        shown("Request sent")
        tap("Check again") // the project manager confirmed
        shown("Checks your request next.")
        tap("Check again") // the admin approved
        shown("Approved. Make your key")
        shown("STEP 5 OF 5")
        tap("Make my key")
        shown("Welcome back")
        shown("This phone's key belongs to name@example.com.")
        tap("Open with fingerprint") // the stand-in answers with a miss
        shown("3 tries left")
        tap("Open with fingerprint") // and then with the last one
        shown("not recognised 5 times in a row")
        compose.onNodeWithText("Situation: ${Situation.GONE.label}").performClick() // round to "new here"
        repeat(Situation.UNLOCK.ordinal) { compose.onNodeWithText("Situation:", substring = true).performClick() }
        // From waiting, a confirmed cancel leads back to the start.
        compose.onNodeWithText("Situation: ${Situation.UNLOCK.label}").performClick() // after a miss
        shown("3 tries left")
        repeat(Situation.entries.size - Situation.MISS.ordinal + Situation.WAITING.ordinal) { compose.onNodeWithText("Situation:", substring = true).performClick() }
        tap("Cancel my request")
        tap("Yes, cancel my request")
        shown("Your phone becomes your key.")
    }

    @Test
    fun refusedRanOutAndKeyGoneSayWhyAndLeadToANewRequest() {
        show(Palettes.LIGHT)
        tool(Tool.WELCOME)
        fun go(to: Situation) {
            while (compose.onAllNodesWithText("Situation: ${to.label}").fetchSemanticsNodes().isEmpty()) compose.onNodeWithText("Situation:", substring = true).performClick()
        }
        go(Situation.OFFLINE)
        shown("Cannot check right now: no connection.")
        go(Situation.REFUSED)
        shown("The admin refused this request. Reason given: The mobile number does not match our records.")
        tap("Request again")
        shown("Your phone becomes your key.")
        go(Situation.EXPIRED)
        shown("not approved in the allowed time")
        tap("Request again")
        shown("Your phone becomes your key.")
        go(Situation.WEAK_PHONE)
        shown("No key was made.")
        assertEquals(0, compose.onAllNodesWithText("Make my key").fetchSemanticsNodes().size)
        go(Situation.GONE)
        shown("not recognised 5 times in a row")
        tap("Request a new key")
        shown("Your phone becomes your key.")
    }

    @Test fun everyLinkLight() = walk(Palettes.LIGHT, wide = false)

    @Test fun everyLinkDark() = walk(Palettes.DARK, wide = false)

    @Test fun everyLinkOutdoor() = walk(Palettes.OUTDOOR, wide = false)

    @Test @Config(qualifiers = "w1100dp-h800dp") fun everyLinkOnATablet() = walk(Palettes.LIGHT, wide = true)

    @Test @Config(qualifiers = "w1100dp-h800dp") fun everyLinkOnATabletInTheDark() = walk(Palettes.DARK, wide = true)

    @Test @Config(fontScale = 2.0f) fun everyLinkAtDoubleFontSize() = walk(Palettes.LIGHT, wide = false)

    @Test @Config(fontScale = 2.0f) fun everyLinkOutdoorAtDoubleFontSize() = walk(Palettes.OUTDOOR, wide = false)

    @Test
    fun aFailedTraceNamesItsPointAndKeepsValuesToTestBuilds() {
        show(Palettes.LIGHT, testBuild = true)
        tool(Tool.TRACE)
        // The row card says the state in words (a pill) and where it stopped, before anything is opened.
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasText("Failed") and hasText("Stopped at 5. Server function") and hasClickAction()).assertIsDisplayed()
        compose.onNode(hasText("Sample: check-in saved", substring = true) and hasText("Saved") and hasClickAction()).performScrollTo().assertIsDisplayed()
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performScrollTo().performClick()
        compose.onNodeWithText("5. Server function: Failed").assertIsDisplayed()
        compose.onNodeWithText("Usually means: a server rule said no, or the server failed.").performScrollTo().assertIsDisplayed()
        compose.onNodeWithText("6. Read-back: Not reached").performScrollTo().assertIsDisplayed() // below the first screenful: scrolled to, as a person would
        assertEquals(1, compose.onAllNodesWithText("sample values", substring = true).fetchSemanticsNodes().size)
    }

    @Test
    fun theRealAppShowsNoValuesAndNoSampleButton() {
        val tracer = Tracer()
        sampleTraces(tracer)
        compose.setContent {
            ErpTheme(Palettes.LIGHT) {
                AppFrame(FrameState(Palettes.LIGHT, testBuild = false, tracer.all(), phone, "Test Phone", "0.1.0", true, true, false, lux = 24f), { _, done -> done(true, null) }, AlertActions({}, {}, {}, {}, {}, {}), {}, {}, {})
            }
        }
        // The real app opens on More, its only finished place; no unfinished place and no stand-in can be reached.
        compose.onNode(hasText("More") and !hasClickAction()).assertIsDisplayed()
        for (unfinished in listOf(Place.TODAY, Place.INBOX, Place.CHAT, Place.MAIL)) {
            assertEquals("${unfinished.label} is not in the real app", 0, compose.onAllNodesWithText(unfinished.label).fetchSemanticsNodes().size)
        }
        assertEquals("the Welcome stand-in is not in the real app", 0, compose.onAllNodesWithText(Tool.WELCOME.title).fetchSemanticsNodes().size)
        tool(Tool.TRACE)
        assertEquals(0, compose.onAllNodesWithText("Add a sample trace", substring = true).fetchSemanticsNodes().size)
        assertEquals(0, compose.onAllNodesWithText("Try the connection", substring = true).fetchSemanticsNodes().size)
        compose.onNode(hasText("Sample: check-out refused", substring = true) and hasClickAction()).performClick()
        assertEquals(0, compose.onAllNodesWithText("sample values", substring = true).fetchSemanticsNodes().size)
        tool(Tool.ALERTS)
        shown("Test my alerts")
        absent("Signal:")
        absent("Delivery address")
        tool(Tool.PHONE)
        assertEquals(0, compose.onAllNodesWithText("Safe", substring = true).fetchSemanticsNodes().size)
        tool(Tool.DISPLAY)
        assertEquals(0, compose.onAllNodesWithText("lux", substring = true).fetchSemanticsNodes().size)
    }

    @Test
    fun theSafeTestCardSaysWhatIsInTheSafeAndOnlyInTestBuilds() {
        show(Palettes.LIGHT)
        tool(Tool.PHONE)
        shown("Empty.")
        tap("Save a test note in the safe")
        shown("was read back from the safe")
        checkLayout("safe test card")
    }

    @Test
    fun tryingTheConnectionAddsARowThatSaysWhereItStopped() {
        show(Palettes.LIGHT, withTraces = false)
        tool(Tool.TRACE)
        tap("Try the connection (test builds)")
        compose.onNode(hasText("Connection test") and hasText("Failed") and hasText("Stopped at 3. Network") and hasClickAction()).assertIsDisplayed()
        checkLayout("after a connection test")
    }

    @Test
    fun theBarHasTheFivePlacesAndMoreAlwaysLeadsBackToItsList() {
        show(Palettes.LIGHT)
        // The app opens on Today.
        compose.onNode(hasText("Today") and !hasClickAction()).assertIsDisplayed()
        // A tap on More shows More's list, also from inside one of its screens.
        tool(Tool.DISPLAY)
        place(Place.MORE).performClick()
        compose.onNode(hasText("More") and !hasClickAction()).assertIsDisplayed()
        for (item in Tool.entries) reach(compose.onNode(hasText(item.title) and hasClickAction())).assertIsDisplayed()
    }

    @Test
    fun approvingNeedsTheEvidenceSeenAndTheFingerprintAndSaysWhatIsSigned() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        // What came back to me is first; what is due today comes before the rest.
        shown("REJECTED, TO CORRECT (1)")
        shown("DUE TODAY (1)")
        tap("Payment to a supplier")
        shown("1,50,000.00")
        shown("Prepared by Accounts, S. Example")
        // No Approve until the person says they have looked at it.
        assertEquals(0, compose.onAllNodes(hasText("Approve with your fingerprint") and hasClickAction()).fetchSemanticsNodes().size)
        reach(compose.onNode(hasText("I have looked at everything above", substring = true) and hasClickAction())).performClick()
        // A finger that does not match decides nothing and says so.
        fingerprintMatches = false
        tap("Approve with your fingerprint")
        shown("Not signed. 4 tries left. After 5 misses in a row the key is erased.")
        assertEquals(listOf("Approve 1,50,000.00: Payment to a supplier"), signed)
        fingerprintMatches = true
        tap("Approve with your fingerprint")
        shown("Approved. It moves on to the next step.")
        tap("Back to the list")
        absent("Payment to a supplier")
        tap("Done")
        reach(compose.onNode(hasText("Payment to a supplier") and hasText("Approved") and hasClickAction())).assertIsDisplayed()
    }

    @Test
    fun rejectingNeedsNoReasonAndTheSenderIsTold() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Leave, 3 days")
        tap("Reject")
        shown("A reason is not required")
        tap("Reject with your fingerprint") // without any reason
        assertEquals(listOf("Reject: Leave, 3 days"), signed)
        shown("Rejected. Site supervisor, K. Example is told.")
        reach(compose.onNode(hasText("Open the next one", substring = true) and hasClickAction())).performClick() // leads on
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // With a quick reason and own words.
        tap("Payment to a supplier")
        tap("Reject")
        // The reasons fit a payment: nothing about photos here.
        absent("Photo not clear")
        tap("Amount is wrong")
        type("In your own words (optional)", "Invoice says less")
        tap("Reject with your fingerprint")
        tap("Back to the list")
        tap("Done")
        tap("Payment to a supplier")
        shown("Rejected by you")
        shown("Reason: Amount is wrong: Invoice says less")
        // What was rejected back to me says by whom and why, can be presented again, and offers no decision.
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        tap("Waiting")
        tap("Purchase request: cement")
        shown("Rejected by Management, R. Example")
        shown("Where its kind allows, it can be presented again.")
        assertEquals(0, compose.onAllNodes(hasText("Reject") and hasClickAction()).fetchSemanticsNodes().size)
        assertEquals(0, compose.onAllNodes(hasText("Decide later") and hasClickAction()).fetchSemanticsNodes().size)
    }

    @Test
    fun whoDoesNotDecideNowIsRemindedInTwoHoursAndThereIsNoDecideLater() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Leave, 3 days")
        // The four ways, and no fifth.
        for (way in listOf("Reject", "Delegate", "Remind me in 2 hours")) reach(compose.onNode(hasText(way) and hasClickAction())).assertIsDisplayed()
        absent("Decide later")
        tap("Remind me in 2 hours")
        assertEquals(listOf("remind"), alertCalls)
        assertEquals("a reminder decides nothing and needs no fingerprint", emptyList<String>(), signed)
        shown("You will be reminded in 2 hours, and again every 2 hours while it waits.")
        // It is still there to decide.
        tap("Leave, 3 days")
        shown("I have looked at everything above")
    }

    private fun switch(label: String) = reach(compose.onNode(hasText(label, substring = true) and hasClickAction())).performClick()

    private fun button(label: String) = compose.onAllNodes(hasText(label) and hasClickAction()).fetchSemanticsNodes().size

    @Test
    fun anAttendanceSheetIsReviewedWorkerByWorkerAndOneFingerprintSignsBothSides() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Attendance, Site A, 6 workers")
        shown("Outside the site by 140 m")
        // What I marked myself is shown, and is not mine to review.
        shown("You marked this worker yourself, so someone else reviews this one.")
        assertEquals(0, compose.onAllNodes(hasText("Reject Worker 6", substring = true)).fetchSemanticsNodes().size)
        // Nothing can be sent before the person has looked.
        assertEquals(0, button("Approve 5 with your fingerprint"))
        switch("I have looked at everything above")
        assertEquals(1, button("Approve 5 with your fingerprint"))
        // One worker is rejected: a reason is needed before anything can be sent.
        switch("Reject Worker 3")
        shown("Choose why for each worker you reject.")
        assertEquals(0, button("Approve 4, reject 1 with your fingerprint"))
        tap("Not at this site")
        fingerprintMatches = false
        tap("Approve 4, reject 1 with your fingerprint")
        shown("Not signed. 4 tries left.")
        fingerprintMatches = true
        tap("Approve 4, reject 1 with your fingerprint")
        assertEquals(List(2) { "Approve 4, reject 1: Attendance, Site A, 6 workers" }, signed)
        shown("4 approved. 1 rejected and sent back to be corrected.")
        tap("Back to the list")
        absent("Attendance, Site A, 6 workers")
    }

    @Test
    fun theSheetCanBeNarrowedToWhatNeedsALookAndEveryWorkerCanBeRejected() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Attendance, Site A, 6 workers")
        switch("I have looked at everything above")
        tap("To look at closely (2)")
        absent("Worker 1")
        shown("Time changed by hand")
        // Nothing is signed from a narrowed list, and "I have looked" is taken back.
        shown("Showing 2 of 6. Go back to All to approve or reject.")
        assertEquals(0, button("Approve 5 with your fingerprint"))
        tap("Show the photo of Worker 5")
        shown("No photo in the made-up data.")
        checkLayout("attendance, to look at closely")
        tap("All (6)")
        assertEquals("looked is asked again after narrowing", 0, button("Approve 5 with your fingerprint"))
        for (n in 1..5) {
            switch("Reject Worker $n")
            reach(compose.onAllNodes(hasText("Was not present") and hasClickAction())[n - 1]).performClick()
        }
        // Nothing is approved, so "I have looked" is not asked for.
        tap("Reject 5 with your fingerprint")
        assertEquals(listOf("Reject 5: Attendance, Site A, 6 workers"), signed)
        shown("5 rejected and sent back to be corrected.")
    }

    @Test
    fun rejectingAllWorkersNeedsOneReasonAndCoversOnlyWhatIsMine() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Attendance, Site A, 6 workers")
        // Six on the sheet, five of them mine: the sixth I marked myself.
        tap("Reject all 5 with one reason")
        shown("Choose why.")
        assertEquals(0, button("Reject 5 with your fingerprint"))
        // The single switches are away while all are rejected.
        assertEquals(0, compose.onAllNodes(hasText("Reject Worker 1", substring = true)).fetchSemanticsNodes().size)
        tap("Was not present")
        tap("Reject 5 with your fingerprint")
        assertEquals(listOf("Reject 5: Attendance, Site A, 6 workers"), signed)
        shown("5 rejected and sent back to be corrected.")
    }

    @Test
    fun rejectOnAnAlertForAnAttendanceSheetOpensTheSheetNotAWholeReject() {
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("attendance-a", InboxJump.Start.REJECT))
        shown("THE WORKERS")
        absent("Reject with your fingerprint")
        absent("A reason is not required")
    }

    @Test
    fun nothingIsDecidedWhenItChangedWasTakenIsMineOrThereIsNoConnection() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Purchase request: steel")
        // This one changes under the person, who must look again.
        reach(compose.onNode(hasText("I have looked at everything above", substring = true) and hasClickAction())).performClick()
        tap("Approve with your fingerprint")
        shown("This was changed after you opened it. Nothing was decided.")
        tap("Look at it again")
        shown("Changed by the sender")
        assertEquals(0, compose.onAllNodes(hasText("Approve with your fingerprint") and hasClickAction()).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Someone else was faster.
        tap("Attendance, Site B, 3 workers")
        reach(compose.onNode(hasText("I have looked at everything above", substring = true) and hasClickAction())).performClick()
        tap("Approve 3 with your fingerprint")
        shown("Already approved by Admin, P. Example")
        tap("Back to the list")
        // I do not decide what I sent myself.
        tap("Advance for site expenses")
        shown("You sent this. Someone else must decide it.")
        assertEquals(0, compose.onAllNodes(hasText("Reject") and hasClickAction()).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // Without a connection the item can be read and nothing can be decided.
        tap("Signal: on (stand-in)")
        shown("Deciding needs a connection.")
        tap("Leave, 3 days")
        shown("Needs a connection. Nothing can be decided now.")
        assertEquals(0, compose.onAllNodes(hasText("Reject") and hasClickAction()).fetchSemanticsNodes().size)
        reach(compose.onNodeWithContentDescription("Back")).performClick()
        // What I sent: who has it, since when, the rejected one first.
        tap("Sent")
        shown("With Management, R. Example for 2 h.")
    }

    @Test
    fun theAlertsScreenSaysWhetherAlertsWorkAndLetsEveryoneTestTheirPhone() {
        show(Palettes.LIGHT)
        tool(Tool.ALERTS)
        shown("Alerts can show on this phone.")
        shown("An alert never shows a name or an amount")
        tap("Test my alerts")
        // Each kind leads to the phone's own switch for it.
        reach(compose.onNode(hasText("Approvals: ringing") and hasClickAction())).performClick()
        // Test builds: one button per kind of signal, and the delivery address for the owner's test.
        tap("Signal: reminder, 3 waiting, 8 hours")
        tap("Signal: with a name and an amount in it")
        shown("delivery-address-for-tests")
        tap("Remove every alert now")
        assertEquals(listOf("signal test", "kind approvals", "signal reminder", "signal approval", "remove all"), alertCalls)
    }

    @Test
    fun aPaymentWhoseAmountIsMissingOrUnreadableCannotBeDecided() {
        val now = java.time.LocalDateTime.of(2026, 11, 28, 9, 15)
        fun payment(id: String, amount: String?) = com.example.erp.core.Item(id, com.example.erp.core.ItemKind.PAYMENT, "50,000.00 cement $id", "Accounts, S. Example", now.minusHours(1), amount = amount)
        val calls = mutableListOf<String>()
        val actions = InboxActions(sign = { what, done -> calls += what; done(true, null) }, decide = { id, _, _, _ -> calls += id; com.example.erp.core.DecisionResult.NotAllowed }, review = { id, _, _, _ -> calls += id; com.example.erp.core.DecisionResult.NotAllowed }, remind = { calls += "remind" },
            delegate = { id, _, _, _ -> calls += id; com.example.erp.core.DecisionResult.NotAllowed }, delegateAll = { _, _ -> calls += "all"; com.example.erp.core.DecisionResult.NotAllowed })
        compose.setContent {
            ErpTheme(Palettes.LIGHT) { InboxScreen(listOf(payment("one", null), payment("two", "12x")), emptyList(), emptyList(), now, online = true, actions = actions) }
        }
        for (id in listOf("one", "two")) {
            reach(compose.onNode(hasText("50,000.00 cement $id") and hasClickAction())).performClick()
            shown("The amount is missing or cannot be read on this phone, so nothing can be decided here. Open it on the web.")
            absent("I have looked at everything above")
            absent("Reject")
            absent("Decide later")
            absent("Delegate")
            reach(compose.onNodeWithContentDescription("Back")).performClick()
            compose.waitForIdle()
        }
        assertEquals(emptyList<String>(), calls)
    }

    @Test
    fun theFullPageForSeveralWaitingThingsOnlyLeadsToTheListOrRemindsLater() {
        val taps = mutableListOf<String>()
        compose.setContent {
            ErpTheme(Palettes.LIGHT) { RingPage("3 approvals waiting", onOpen = { taps += "open" }, onReject = { taps += "reject" }, onRemind = { taps += "remind" }) }
        }
        shown("3 approvals waiting")
        shown("Open the app to see it, behind its lock.")
        checkLayout("ring page")
        tap("Remind me in 2 hours")
        tap("Open")
        assertEquals(listOf("remind", "open"), taps)
        // The page cannot know which of the three is meant.
        absent("Approve")
        absent("Reject")
        absent("Later")
    }

    @Test
    fun theFullPageForOneWaitingThingOffersTheWaysInAndSaysThatNothingIsDecidedHere() {
        val taps = mutableListOf<String>()
        compose.setContent {
            ErpTheme(Palettes.LIGHT) { RingPage("Payment waiting", oneThing = true, onOpen = { taps += "approve" }, onReject = { taps += "reject" }, onDelegate = { taps += "delegate" }, onRemind = { taps += "remind" }) }
        }
        shown("Payment waiting")
        shown("Approve, Reject and Delegate open it in the app, behind its lock. You see it before you decide.")
        checkLayout("ring page, one thing")
        tap("Approve")
        tap("Reject")
        tap("Delegate")
        tap("Remind me in 2 hours")
        assertEquals(listOf("approve", "reject", "delegate", "remind"), taps)
        absent("Open")
    }

    @Test
    fun theFullPageOfATestCanOnlyBeOpenedOrStopped() {
        compose.setContent { ErpTheme(Palettes.DARK) { RingPage("Test alert. This is how an approval rings.", test = true, onOpen = {}, onRemind = {}) } }
        shown("Stop")
        absent("Remind me in 2 hours")
        absent("Approve")
        checkLayout("ring page, test")
    }

    @Test
    fun approveOnAnAlertOpensThatThingAndStillNeedsTheLookAndTheFingerprint() {
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("payment"))
        shown("Payment to a supplier")
        shown("I have looked at everything above")
        absent("Approve with your fingerprint")
        assertEquals(emptyList<String>(), signed)
    }

    @Test
    fun rejectOnAnAlertOpensTheRejectScreenOfThatThingAndSignsNothingByItself() {
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("leave", InboxJump.Start.REJECT))
        shown("Leave, 3 days")
        shown("Reject with your fingerprint")
        assertEquals(emptyList<String>(), signed)
    }

    @Test
    fun aShortcutToSomethingThatIsNotMineToDecideOrNotThereDecidesNothing() {
        // What I sent myself: the item is shown, without Reject.
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("advance", InboxJump.Start.REJECT))
        shown("You sent this. Someone else must decide it.")
        absent("Reject with your fingerprint")
    }

    private fun delegateButtons() = compose.onAllNodes(hasText("Delegate") and hasClickAction()).fetchSemanticsNodes().size

    @Test
    fun delegatingOneThingIsSignedGoesToAChosenPersonAndICanStillDecideIt() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Leave, 3 days")
        tap("Delegate")
        shown("Only this one")
        shown("All my approvals until a date")
        // Nothing can be sent before a person is chosen.
        shown("Choose a person first.")
        assertEquals(0, compose.onAllNodes(hasText("Delegate with your fingerprint") and hasClickAction()).fetchSemanticsNodes().size)
        // One thing can also go to the higher official.
        shown("Management, R. Example")
        tap("Deputy manager, D. Example")
        // A finger that does not match delegates nothing.
        fingerprintMatches = false
        tap("Delegate with your fingerprint")
        shown("Not signed. 4 tries left.")
        fingerprintMatches = true
        tap("Delegate with your fingerprint")
        assertEquals(List(2) { "Delegate to Deputy manager, D. Example: Leave, 3 days" }, signed)
        shown("Delegated to Deputy manager, D. Example. You can still decide it yourself.")
        tap("Back to the list")
        shown("DELEGATED BY YOU (1)")
        tap("Leave, 3 days")
        shown("You delegated this to Deputy manager, D. Example.")
        // I can still decide it; I cannot delegate it a second time.
        shown("I have looked at everything above")
        assertEquals(0, delegateButtons())
    }

    @Test
    fun whatWasDelegatedToMeIsMineToDecideButNotToPassOn() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Machinery working, Site B, 2 days")
        shown("Delegated to you by Project manager, P. Example. Travelling. You decide it with your own fingerprint.")
        reach(compose.onNode(hasText("Reject") and hasClickAction())).assertIsDisplayed()
        assertEquals(0, delegateButtons())
    }

    @Test
    fun everythingIsDelegatedFromTheApprovalOnlyToTheDeputyOrAPeerAndInsideTheLeave() {
        show(Palettes.LIGHT)
        place(Place.INBOX).performClick()
        tap("Leave, 3 days")
        tap("Delegate")
        tap("All my approvals until a date")
        shown("Your approved leave:")
        // Never the higher official, and nobody who is on leave too.
        absent("Management, R. Example")
        absent("Project manager, V. Example")
        tap("1 day later") // cannot go past the leave
        tap("Project manager, P. Example")
        tap("Delegate with your fingerprint")
        assertEquals(1, signed.size)
        assertEquals(true, signed.single().startsWith("Delegate all approvals until ") && signed.single().endsWith(", 18:00 to Project manager, P. Example"))
        shown("Delegated. Your approvals go to Project manager, P. Example until")
        tap("Back to the list")
        shown("End it under More, Delegation.")
        // A second one cannot be set while one runs.
        tap("Attendance, Site A, 6 workers")
        tap("Delegate")
        shown("A delegation is already set. End it first, under More, Delegation.")
    }

    @Test
    fun delegationUnderMoreSetsItBeforeLeaveEndsItAndNeedsApprovedLeave() {
        show(Palettes.LIGHT)
        tool(Tool.DELEGATION)
        shown("Nothing is delegated. Your approvals come to you.")
        shown("Project manager, P. Example delegated one approval to you.")
        tap("Delegate my approvals")
        absent("Management, R. Example")
        absent("Only this one")
        tap("Deputy manager, D. Example")
        tap("Delegate with your fingerprint")
        assertEquals(true, signed.single().endsWith("to Deputy manager, D. Example"))
        shown("Your approvals go to Deputy manager, D. Example until")
        checkLayout("delegation, set")
        tap("End it now")
        shown("Nothing is delegated. Your approvals come to you.")
        // Without approved leave everything cannot be delegated, and the screen says why.
        tap("Leave: approved (stand-in)")
        tap("Delegate my approvals")
        shown("You can delegate everything only while you are on approved leave. No approved leave is recorded for you.")
        assertEquals(1, signed.size)
    }

    @Test
    fun delegateOnAnAlertOpensTheDelegateScreenOfThatThingAndSignsNothingByItself() {
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("payment", InboxJump.Start.DELEGATE))
        shown("Payment to a supplier · 1,50,000.00")
        shown("Only this one")
        checkLayout("delegate, from an alert")
        assertEquals(emptyList<String>(), signed)
    }

    @Test
    fun anAlertForOneChatOrOneMailOpensExactlyThatAndItsAlertGoesWhenThePlaceIsLookedAt() {
        show(Palettes.LIGHT, goTo = Place.CHAT, goItem = InboxJump("direct-Project manager"))
        // The chat itself, not the list of chats.
        reach(compose.onNodeWithContentDescription("Back")).assertIsDisplayed()
        absent("Site A engineers")
        assertEquals(listOf("chat", "notice"), seenCalls)
        place(Place.MAIL).performClick()
        compose.waitForIdle()
        assertEquals(listOf("chat", "notice", "mail"), seenCalls)
        // Looking at Inbox removes no approval alert: only a decision does.
        place(Place.INBOX).performClick()
        compose.waitForIdle()
        assertEquals(3, seenCalls.size)
    }

    @Test
    fun anAlertForOneMailOpensThatConversation() {
        show(Palettes.LIGHT, goTo = Place.MAIL, goItem = InboxJump("t4"))
        shown("Re: Leave plan for December")
        reach(compose.onNodeWithContentDescription("Back")).assertIsDisplayed()
    }

    @Test
    fun thePlacesShowHowMuchWaitsAndTheNumberFollowsWhatIsDone() {
        show(Palettes.LIGHT)
        // Made-up numbers of the stand-ins: 7 to decide or correct, 3 unread messages, 2 unread mails.
        for (badge in listOf("Inbox: 7", "Chat: 3", "Mail: 2")) compose.onNodeWithContentDescription(badge, useUnmergedTree = true).assertExists()
        place(Place.INBOX).performClick()
        tap("Leave, 3 days")
        tap("Reject")
        tap("Reject with your fingerprint")
        compose.waitForIdle()
        compose.onNodeWithContentDescription("Inbox: 6", useUnmergedTree = true).assertExists()
    }

    @Test
    fun anApprovalArrivingWhileTheAppIsOpenShowsOneLineThatLeadsToIt() {
        show(Palettes.LIGHT, line = "Payment waiting")
        shown("Payment waiting")
        checkLayout("line of an alert in the open app")
        tap("Open")
        assertEquals(listOf(true), lineAnswers)
    }

    @Test
    fun aShortcutToSomethingUnknownLeavesTheList() {
        show(Palettes.LIGHT, goTo = Place.INBOX, goItem = InboxJump("Pay A. Example 1,50,000.00", InboxJump.Start.DELEGATE))
        shown("Waiting for me")
        shown("That one is already decided, or no longer waits for you.")
        absent("Reject with your fingerprint")
        absent("Pay A. Example 1,50,000.00")
    }

    @Test @Config(fontScale = 2.0f)
    fun theFullPageHoldsAtDoubleFontSize() {
        compose.setContent {
            ErpTheme(Palettes.OUTDOOR) { RingPage("Machinery working waiting", oneThing = true, onOpen = {}, onRemind = {}) }
        }
        shown("Machinery working waiting")
        checkLayout("ring page, outdoor, double font")
        reach(compose.onNode(hasText("Remind me in 2 hours") and hasClickAction())).assertIsDisplayed()
    }

    @Test
    fun aPhoneThatHasNotAllowedTheFullPageSaysSoAndLeadsToTheSetting() {
        show(Palettes.LIGHT, alerts = AlertsView(fullPage = false, connected = true))
        tool(Tool.ALERTS)
        shown("The full page over a locked screen is not allowed on this phone yet.")
        tap("Allow the full page")
        assertEquals(listOf("fix FULL_PAGE"), alertCalls)
    }

    @Test
    fun theFullPageWhileThePhoneIsInUseIsThePersonsChoiceAndSomePhonesCannot() {
        show(Palettes.LIGHT, alerts = AlertsView(onTop = false, connected = true))
        tool(Tool.ALERTS)
        shown("While you use the phone, an approval comes as a banner at the top.")
        tap("Allow it over other apps")
        assertEquals(listOf("fix ON_TOP"), alertCalls)
        checkLayout("alerts, full page over other apps not allowed yet")
    }

    @Test
    fun aPhoneWithoutTheSettingSaysThatApprovalsComeAsABannerWhileItIsInUse() {
        show(Palettes.LIGHT, alerts = AlertsView(onTop = null, connected = true))
        tool(Tool.ALERTS)
        shown("This phone cannot show the full page then.")
        absent("Allow it over other apps")
    }

    @Test
    fun blockedAlertsSayWhyAndOfferTheOneFix() {
        show(Palettes.LIGHT, alerts = AlertsView(blocked = "the phone has not been allowed to show this app's alerts.", fix = Fix.ALLOW, connected = false))
        tool(Tool.ALERTS)
        shown("Alerts are blocked: the phone has not been allowed to show this app's alerts.")
        absent("Alerts can show on this phone.")
        shown("This build is not connected to the alert service")
        shown("None: this build is not connected to the alert service.")
        tap("Allow alerts")
        assertEquals(listOf("fix ALLOW"), alertCalls)
        checkLayout("alerts, blocked")
    }

    @Test
    fun aTappedAlertOpensItsPlaceAndNeverAPlaceTheBuildDoesNotShow() {
        show(Palettes.LIGHT, goTo = Place.INBOX)
        compose.onNode(hasText("Inbox") and !hasClickAction()).assertIsDisplayed()
        shown("Waiting for me")
    }

    @Test
    fun inARealBuildATappedAlertCannotOpenAnUnfinishedPlace() {
        compose.setContent {
            ErpTheme(Palettes.LIGHT) {
                AppFrame(FrameState(Palettes.LIGHT, testBuild = false, emptyList(), phone, "Test Phone", "0.1.0", true, true, false, lux = 24f), { _, done -> done(true, null) }, AlertActions({}, {}, {}, {}, {}, {}), {}, {}, {}, goTo = Place.INBOX)
            }
        }
        compose.onNode(hasText("More") and !hasClickAction()).assertIsDisplayed()
        absent("Waiting for me")
    }

    private fun day(day: Day) {
        place(Place.TODAY).performClick()
        while (compose.onAllNodesWithText("Role: ${day.label}").fetchSemanticsNodes().isEmpty()) compose.onNodeWithText("Role:", substring = true).performClick()
    }

    @Test
    fun todayShowsEachRoleItsOwnDayInCountsOnly() {
        show(Palettes.LIGHT)
        // The supervisor: own attendance, the team, what came back. None of these screens exists yet, so none is a button.
        shown("Site supervisor · Site A")
        shown("Up to date.")
        shown("Marked 18 of 24. Not sent yet.")
        shown("2 entries were sent back to correct.")
        assertEquals(0, compose.onAllNodes(hasText("My team today") and hasClickAction()).fetchSemanticsNodes().size)
        absent("To approve")
        // The engineer: what has a deadline today is first and says its time; it leads to Inbox.
        day(Day.ENGINEER)
        shown("12 entries at 2 sites. Due today, 23:30.")
        absent("My team today")
        tap("To verify")
        compose.onNode(hasText("Inbox") and !hasClickAction()).assertIsDisplayed()
        shown("Waiting for me")
        // The project manager: what waits, by count; the unread counts lead to Chat and Mail.
        day(Day.PROJECT_MANAGER)
        shown("8 waiting, the oldest for 2 h.")
        shown("3 sites: 1 approved, 1 verified, 1 not sent yet.")
        reach(compose.onNode(hasText("12 unread.") and hasClickAction())).performClick()
        shown("Folder: Received")
        day(Day.PROJECT_MANAGER)
        reach(compose.onNode(hasText("5 unread.") and hasClickAction())).performClick()
        shown("New chat with a colleague")
        // Staff see their own day and nothing of anyone else's.
        day(Day.STAFF)
        shown("Not checked in yet. You are outside the site.")
        shown("Leave: waiting for approval.")
        absent("To approve")
        absent("My sites today")
    }

    @Test
    fun todaySaysPlainlyWhenThereIsNothingOrWhenItCouldNotCheck() {
        show(Palettes.LIGHT)
        day(Day.NEW_PERSON)
        shown("You are set up. Your site and your team appear here")
        day(Day.HOLIDAY)
        shown("Today is a holiday for your site.")
        absent("My attendance")
        day(Day.OFFLINE)
        shown("No connection: 3 things wait to be sent.")
        absent("Nothing is waiting")
        shown("Without a connection the app opens for 3 more hours.")
        shown("3 things are saved on this phone and not sent yet.")
        day(Day.QUIET)
        shown("Your phone's clock is 12 minutes behind.")
        shown("Nothing is waiting for you today.")
        // A failed check is named and never hidden behind "nothing waiting"; "Try again" leads somewhere.
        day(Day.FAILED)
        shown("Could not check: purchases, leave.")
        shown("Your key was not used for 5 days.")
        absent("Nothing is waiting")
        tap("Try again") // the same day again, now with every check answered
        compose.onNodeWithText("Role: ${Day.FAILED.label}").assertIsDisplayed()
        absent("Could not check")
        shown("8 waiting, the oldest for 2 h.")
    }

    @Test
    fun anEmptyTraceListSaysWhatWillAppear() {
        show(Palettes.LIGHT, withTraces = false)
        tool(Tool.TRACE)
        compose.onNodeWithText("No actions yet", substring = true).assertIsDisplayed()
        compose.onNodeWithText("Add a sample trace (test builds)").performClick()
        compose.onNode(hasText("Sample: check-in saved", substring = true) and hasClickAction()).assertIsDisplayed()
    }

    @Test
    fun theOutdoorSwitchChangesTheLookAndSaysSo() {
        show(Palettes.DARK)
        tool(Tool.DISPLAY)
        compose.onNodeWithText("Dark: follows your phone's night mode").assertIsDisplayed()
        compose.onNode(hasText("Outdoor mode now", substring = true) and hasClickAction()).performClick()
        compose.onNodeWithText("Outdoor: strongest contrast, larger text").assertIsDisplayed()
        compose.onNode(hasText("Outdoor mode now", substring = true) and hasClickAction()).performClick()
        compose.onNodeWithText("Dark: follows your phone's night mode").assertIsDisplayed()
    }
}
