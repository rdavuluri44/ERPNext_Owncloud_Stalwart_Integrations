package com.example.erp.core

/**
 * The data-flow tracker. Every action (a check-in, an approval) gets one tracking number at the first tap; each
 * point its data passes writes one mark against that number. A red mark names where it went wrong.
 */
enum class Point(val label: String, val faultMeans: String) {
    SCREEN("Screen", "the form let something wrong through, or blocked something right"),
    PHONE_STORE("Phone store", "lost or stuck on the phone"),
    NETWORK("Network", "no signal, a timeout or a wrong address"),
    GATEWAY("Gateway", "not signed in, or not allowed in"),
    SERVER("Server function", "a server rule said no, or the server failed"),
    READ_BACK("Read-back", "stored differently from what was sent"),
    FOLLOW_UP("Follow-up", "saved correctly, but nobody was told"),
    DISPLAY("Display", "shown differently from the web"),
}

/**
 * One line of a trace.
 * [note] is safe to share: point names, results, field names, the server's refusal sentence. Never a value.
 * [detail] may hold values (what was sent, what came back) and is shown in test builds only.
 */
data class Mark(val point: Point, val ok: Boolean, val note: String, val tookMs: Long? = null, val at: Long, val detail: String? = null)

data class Trace(val id: String, val action: String, val startedAt: Long, val marks: List<Mark>) {
    /** The first point that failed, or null when every mark so far is green. */
    val fault: Mark? get() = marks.firstOrNull { !it.ok }

    /** Green only when nothing failed and the data reached the server and was read back the same. */
    val complete: Boolean get() = fault == null && marks.any { it.point == Point.SERVER } && marks.any { it.point == Point.READ_BACK }

    /** Plain text for sending to a developer. Values are left out unless [withValues] (test builds only). */
    fun report(withValues: Boolean = false): String = buildString {
        append(action).append(" [").append(id).append("]\n")
        for (point in Point.entries) {
            val mark = marks.lastOrNull { it.point == point }
            append(point.ordinal + 1).append(". ").append(point.label).append(": ")
            when {
                mark == null -> append("not reached")
                mark.ok -> append("ok")
                else -> append("FAILED")
            }
            if (mark != null) {
                if (mark.note.isNotEmpty()) append(" - ").append(mark.note)
                if (mark.tookMs != null) append(" (").append(mark.tookMs).append(" ms)")
                if (withValues && mark.detail != null) append("\n   ").append(mark.detail)
            }
            append('\n')
        }
    }
}

/**
 * Keeps the last [limit] traces. In Phase 0 they live in memory; they move into the encrypted store with it.
 * Safe to call from any thread.
 */
class Tracer(private val limit: Int = 200, private val clock: () -> Long = System::currentTimeMillis) {
    private val traces = LinkedHashMap<String, Trace>()

    init {
        require(limit > 0)
    }

    /** Starts a trace. The tracking number is the action's own unique request ID, so the server sees the same number. */
    @Synchronized
    fun start(id: String, action: String): Trace {
        require(Regex("[A-Za-z0-9_-]{16,80}").matches(id)) { "tracking number must be 16 to 80 letters, digits, _ or -" }
        val trace = Trace(id, action, clock(), emptyList())
        traces.remove(id)
        traces[id] = trace
        while (traces.size > limit) traces.remove(traces.keys.first())
        return trace
    }

    /** Adds a mark. A mark for an unknown tracking number is dropped: the trace was wiped (sign-out) or pushed out. */
    @Synchronized
    fun mark(id: String, point: Point, ok: Boolean, note: String = "", tookMs: Long? = null, detail: String? = null): Trace? {
        val trace = traces[id] ?: return null
        return trace.copy(marks = trace.marks + Mark(point, ok, note, tookMs, clock(), detail)).also { traces[id] = it }
    }

    /** Newest first. */
    @Synchronized
    fun all(): List<Trace> = traces.values.reversed()

    @Synchronized
    fun find(id: String): Trace? = traces[id]

    /** Sign-out and remote wipe: nothing stays. */
    @Synchronized
    fun clear() = traces.clear()
}
