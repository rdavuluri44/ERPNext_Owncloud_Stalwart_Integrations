package com.example.erp.core

/**
 * Reviewing an attendance approval worker by worker (the developer's decisions of 28 November 2026; the earlier
 * app and the server already work per worker).
 *
 * All workers are to be approved unless the person marks one for rejection. A rejected worker must have a reason
 * (elsewhere a reason is optional): whoever marked the attendance has to know what was wrong with which worker.
 * The rest are approved in the same signed step. A rejected entry goes back to be corrected; nothing is final.
 */
data class Entry(
    val id: String,
    val name: String,
    /** What was recorded, in words: "Checked in 08:52". */
    val text: String,
    /** What is out of the ordinary about it, in words, when something is. */
    val unusual: String? = null,
    /** Why I may not review this one (I marked it myself, it is my own attendance); null when I may. */
    val notMine: String? = null,
    /** The server's mark of this entry's version: a worker can be corrected while the sheet is open. */
    val modified: String = "",
)

object Reviews {
    /** The reasons offered for a rejection fit what is being rejected. */
    fun reasons(kind: ItemKind): List<String> = when (kind) {
        ItemKind.ATTENDANCE_VERIFY, ItemKind.ATTENDANCE_APPROVE -> listOf("Wrong worker", "Photo not clear", "Wrong time", "Not at this site", "Was not present")
        ItemKind.PURCHASE -> listOf("Quantity is wrong", "Price is wrong", "A document is missing", "Not needed now")
        ItemKind.PAYMENT -> listOf("Amount is wrong", "A document is missing", "Wrong party", "Already paid")
        ItemKind.LEAVE -> listOf("Dates do not fit", "Nobody to cover", "Not enough leave left")
    }

    /** Only an attendance sheet is reviewed this way: anything with an amount keeps the question that says the amount. */
    fun applies(item: Item): Boolean = item.entries.isNotEmpty() && (item.kind == ItemKind.ATTENDANCE_VERIFY || item.kind == ItemKind.ATTENDANCE_APPROVE)

    /** The sheet's workers, each once: an entry sent twice is one worker, counted and signed once. */
    fun entries(item: Item): List<Entry> = item.entries.distinctBy { it.id }

    /** The entries I may review. The others are shown, with the reason, and stay out of every count. */
    fun mine(item: Item): List<Entry> = entries(item).filter { it.notMine == null }

    /** How many will be approved and how many rejected, for the marks as they are now. */
    fun counts(item: Item, rejected: Set<String>): Pair<Int, Int> {
        val mine = mine(item)
        val reject = mine.count { it.id in rejected }
        return mine.size - reject to reject
    }

    /** The engineer's check is called verifying; it is the same step. */
    private fun verb(item: Item) = if (item.kind == ItemKind.ATTENDANCE_VERIFY) "Verify" else "Approve"

    /** "Approve 5, reject 1", "Approve 6", "Reject 6". */
    fun words(item: Item, approve: Int, reject: Int): String = listOfNotNull(
        "${verb(item)} $approve".takeIf { approve > 0 },
        (if (approve > 0) "reject $reject" else "Reject $reject").takeIf { reject > 0 },
    ).joinToString(", ")

    /** What the fingerprint question says: the touch signs exactly these numbers for this sheet. */
    fun question(item: Item, approve: Int, reject: Int): String = words(item, approve, reject) + ": " + Inbox.short(item.title)

    /** There is something to send, and every rejected worker has a reason. */
    fun ready(item: Item, rejected: Map<String, String?>): Boolean {
        val mine = mine(item).map { it.id }.toSet()
        return mine.isNotEmpty() && rejected.filterKeys { it in mine }.values.all { !it.isNullOrBlank() }
    }

    /** One call to the server: one decision, one reason, some entries. The server takes them that way. */
    data class Call(val approve: Boolean, val entries: List<String>, val reason: String? = null)

    /** The signed step as the server's calls: the approved ones together, the rejected ones together per reason. */
    fun calls(item: Item, rejected: Map<String, String>): List<Call> {
        val mine = mine(item).map { it.id }
        val approved = mine.filter { it !in rejected }
        val byReason = mine.filter { it in rejected }.groupBy { rejected.getValue(it) }
        return listOfNotNull(Call(true, approved).takeIf { approved.isNotEmpty() }) + byReason.map { (reason, entries) -> Call(false, entries, reason) }
    }

    /** What happened, said per group; what could not be done is said too and stays in the list. */
    fun sentence(item: Item, approved: Int, rejected: Int, failed: Int): String {
        val done = if (item.kind == ItemKind.ATTENDANCE_VERIFY) "verified" else "approved"
        return listOfNotNull(
            "$approved $done.".takeIf { approved > 0 },
            "$rejected rejected and sent back to be corrected.".takeIf { rejected > 0 },
            "$failed could not be done and ${if (failed == 1) "is" else "are"} still in the list.".takeIf { failed > 0 },
        ).joinToString(" ").ifEmpty { "Nothing was done." }
    }
}
