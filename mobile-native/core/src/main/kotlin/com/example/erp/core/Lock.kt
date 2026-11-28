package com.example.erp.core

/**
 * The rules of the fingerprint lock. Decided by the owner (26 November 2026: fingerprint only, 5 misses erase)
 * and the developer (27 November 2026: asked again after 5 minutes away, 8 hours without a connection).
 */
object LockRules {
    /** Misses in a row that erase the key. A match sets the count back to zero. */
    const val MAX_MISSES = 5

    /** Away from the app this long (another app, screen off), and the fingerprint is asked again. */
    const val AWAY_MS = 5 * 60 * 1000L

    /** Hours the app still opens without a connection. Used from the sign-in part on. */
    const val OFFLINE_HOURS = 8

    fun triesLeft(misses: Int): Int = (MAX_MISSES - misses).coerceIn(0, MAX_MISSES)

    /** What a miss says where a decision is signed; null before any miss. */
    fun missWords(misses: Int): String? {
        if (misses <= 0) return null
        val left = triesLeft(misses)
        return "Not signed. " + (if (left == 1) "1 try left" else "$left tries left") + ". After $MAX_MISSES misses in a row the key is erased."
    }

    fun erases(misses: Int): Boolean = misses >= MAX_MISSES

    /**
     * [leftAt] and [now] come from a clock that only runs forward and cannot be set by the person (time since the
     * phone started). A clock that went backwards means the phone restarted: locked.
     */
    fun mustLock(leftAt: Long?, now: Long): Boolean = leftAt != null && (now < leftAt || now - leftAt >= AWAY_MS)
}
