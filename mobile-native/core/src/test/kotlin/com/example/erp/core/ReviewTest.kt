package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ReviewTest {
    private val now = LocalDateTime.of(2026, 11, 28, 9, 15)
    private val sheet = Item(
        "a", ItemKind.ATTENDANCE_APPROVE, "Attendance, Site A, 5 workers", "Engineer, A. Example", now,
        entries = listOf(
            Entry("w1", "Worker 1", "Checked in 08:52"),
            Entry("w2", "Worker 2", "Checked in 08:55", unusual = "Outside the site by 140 m"),
            Entry("w3", "Worker 3", "Checked in 08:57"),
            Entry("w4", "Worker 4", "Checked in 09:01"),
            Entry("w5", "Worker 5", "Checked in 08:49", notMine = "You marked this one yourself."),
        ),
    )

    @Test
    fun everyoneIsApprovedUnlessMarkedAndWhatIsNotMineIsNeverCounted() {
        assertEquals(4 to 0, Reviews.counts(sheet, emptySet()))
        assertEquals(3 to 1, Reviews.counts(sheet, setOf("w2")))
        assertEquals(0 to 4, Reviews.counts(sheet, setOf("w1", "w2", "w3", "w4")))
        // A mark on an entry I may not review, or on one that is not there, changes nothing.
        assertEquals(4 to 0, Reviews.counts(sheet, setOf("w5", "nobody")))
        // An entry sent twice is one worker.
        assertEquals(4 to 0, Reviews.counts(sheet.copy(entries = sheet.entries + sheet.entries.first()), emptySet()))
        // Only an attendance sheet is reviewed this way; a payment with entries keeps its own question.
        assertTrue(Reviews.applies(sheet))
        assertFalse(Reviews.applies(sheet.copy(kind = ItemKind.PAYMENT, amount = "100")))
        assertFalse(Reviews.applies(sheet.copy(entries = emptyList())))
        // A sheet that came without its workers is not decided as a whole instead.
        assertFalse(Inbox.canDecide(sheet.copy(entries = emptyList())))
        assertTrue(Inbox.canDecide(sheet))
    }

    @Test
    fun theButtonAndTheFingerprintQuestionSayTheNumbersOfBothSides() {
        assertEquals("Approve 4", Reviews.words(sheet, 4, 0))
        assertEquals("Approve 3, reject 1", Reviews.words(sheet, 3, 1))
        assertEquals("Reject 4", Reviews.words(sheet, 0, 4))
        assertEquals("Verify 3, reject 1", Reviews.words(sheet.copy(kind = ItemKind.ATTENDANCE_VERIFY), 3, 1))
        assertEquals("Approve 3, reject 1: Attendance, Site A, 5 workers", Reviews.question(sheet, 3, 1))
        // The sheet's name is one short line, as in every question.
        assertEquals("Approve 4: " + "T".repeat(80), Reviews.question(sheet.copy(title = "T".repeat(200)), 4, 0))
    }

    @Test
    fun aRejectedWorkerMustHaveAReason() {
        assertTrue(Reviews.ready(sheet, emptyMap()))
        assertFalse(Reviews.ready(sheet, mapOf("w2" to null)))
        assertFalse(Reviews.ready(sheet, mapOf("w2" to " ")))
        assertTrue(Reviews.ready(sheet, mapOf("w2" to "Not at this site")))
        assertFalse(Reviews.ready(sheet, mapOf("w2" to "Not at this site", "w3" to null)))
        // Nothing of mine in the sheet: nothing to send.
        assertFalse(Reviews.ready(sheet.copy(entries = sheet.entries.takeLast(1)), emptyMap()))
    }

    @Test
    fun oneSignedStepBecomesTheServersCallsTheApprovedTogetherTheRejectedPerReason() {
        val calls = Reviews.calls(sheet, mapOf("w2" to "Not at this site", "w4" to "Photo not clear", "w1" to "Not at this site", "w5" to "ignored"))
        assertEquals(
            listOf(
                Reviews.Call(true, listOf("w3")),
                Reviews.Call(false, listOf("w1", "w2"), "Not at this site"),
                Reviews.Call(false, listOf("w4"), "Photo not clear"),
            ),
            calls,
        )
        assertEquals(listOf(Reviews.Call(true, listOf("w1", "w2", "w3", "w4"))), Reviews.calls(sheet, emptyMap()))
        // Every entry of mine is in exactly one call; what is not mine is in none.
        assertEquals(listOf("w1", "w2", "w3", "w4"), calls.flatMap { it.entries }.sorted())
    }

    @Test
    fun theAnswerSaysWhatHappenedToEachGroup() {
        assertEquals("4 approved.", Reviews.sentence(sheet, 4, 0, 0))
        assertEquals("3 approved. 1 rejected and sent back to be corrected.", Reviews.sentence(sheet, 3, 1, 0))
        assertEquals("2 approved. 1 rejected and sent back to be corrected. 1 could not be done and is still in the list.", Reviews.sentence(sheet, 2, 1, 1))
        assertEquals("2 could not be done and are still in the list.", Reviews.sentence(sheet, 0, 0, 2))
        assertEquals("3 verified.", Reviews.sentence(sheet.copy(kind = ItemKind.ATTENDANCE_VERIFY), 3, 0, 0))
        assertEquals("Nothing was done.", Reviews.sentence(sheet, 0, 0, 0))
    }

    @Test
    fun theReasonsOfferedFitWhatIsRejected() {
        assertTrue("Photo not clear" in Reviews.reasons(ItemKind.ATTENDANCE_APPROVE))
        assertEquals(Reviews.reasons(ItemKind.ATTENDANCE_APPROVE), Reviews.reasons(ItemKind.ATTENDANCE_VERIFY))
        assertFalse("Photo not clear" in Reviews.reasons(ItemKind.PAYMENT))
        assertTrue("Amount is wrong" in Reviews.reasons(ItemKind.PAYMENT))
        assertFalse("Amount is wrong" in Reviews.reasons(ItemKind.LEAVE))
        for (kind in ItemKind.entries) assertTrue(kind.name, Reviews.reasons(kind).size in 3..5)
    }
}
