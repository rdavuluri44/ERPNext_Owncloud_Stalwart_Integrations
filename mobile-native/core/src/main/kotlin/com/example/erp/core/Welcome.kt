package com.example.erp.core

import java.time.LocalDateTime

/**
 * Which first screen a person gets. It is decided here, from what the phone knows (its key) and what the server
 * says about this phone's access request. The person never chooses a path, so they cannot land on a wrong one.
 */

/** What this phone knows about its own key. */
enum class KeyState { NONE, PRESENT, LOST }

/** Why a key that existed is gone. */
enum class KeyLoss(val sentence: String) {
    MISSES("The fingerprint was not recognised 5 times in a row, so the key was erased to keep your account safe."),
    NEW_FINGERPRINT("The fingerprints or the screen lock of this phone were changed, so the key was destroyed. A key only opens for the fingerprints that were on the phone when it was made."),
    REMOVED("The key was removed because it was not used for 7 days, or an admin removed it."),
}

enum class Approval { WAITING, CONFIRMED, REFUSED }

/** The server's answer about this phone's access request. */
data class AccessRequest(
    val sentAt: LocalDateTime,
    val projectManager: Approval = Approval.WAITING,
    val projectManagerAt: LocalDateTime? = null,
    val admin: Approval = Approval.WAITING,
    val adminAt: LocalDateTime? = null,
    /** The approver's own words when one of them refused. */
    val refusedBecause: String? = null,
    val expired: Boolean = false,
) {
    val refused: Boolean get() = projectManager == Approval.REFUSED || admin == Approval.REFUSED
    val approved: Boolean get() = projectManager == Approval.CONFIRMED && admin == Approval.CONFIRMED
}

sealed interface Welcome {
    /** New here: no key and no request. */
    data object RequestAccess : Welcome

    /** A request is with the approvers. */
    data class Pending(val request: AccessRequest) : Welcome

    /** One approver said no; the reason is shown and a new request can be sent. */
    data class Refused(val request: AccessRequest) : Welcome

    /** Nobody approved in the allowed days. */
    data class Expired(val request: AccessRequest) : Welcome

    /** Both approved and this phone has no key yet. */
    data object MakeKey : Welcome

    /** The daily screen: this phone has a key. */
    data object Unlock : Welcome

    /** The key that was here is gone and nothing new was asked for yet. */
    data class KeyGone(val why: KeyLoss) : Welcome
}

/**
 * The one decision. A key on the phone always wins (a stale request must never put a working person back into
 * onboarding). Without a key the newest request decides; a refusal is told before an expiry, and "approved" needs
 * both approvers, whatever order the answers arrive in.
 */
fun welcomeFor(key: KeyState, loss: KeyLoss?, request: AccessRequest?): Welcome = when {
    key == KeyState.PRESENT -> Welcome.Unlock
    request == null -> if (key == KeyState.LOST) Welcome.KeyGone(loss ?: KeyLoss.REMOVED) else Welcome.RequestAccess
    request.refused -> Welcome.Refused(request)
    request.expired -> Welcome.Expired(request)
    request.approved -> Welcome.MakeKey
    else -> Welcome.Pending(request)
}

/** A mobile number with the middle hidden, for showing back what was sent: "+91 90••• ••000". */
fun hideMiddle(number: String): String {
    val digits = number.filter { it.isDigit() }
    if (digits.length < 7) return "•".repeat(digits.length)
    val local = digits.takeLast(10)
    val country = digits.dropLast(10)
    return (if (country.isEmpty()) "" else "+$country ") + local.take(2) + "••• ••" + local.takeLast(3)
}
