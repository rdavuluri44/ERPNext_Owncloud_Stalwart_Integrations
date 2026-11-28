package com.example.erp.core

import java.time.LocalDateTime

/**
 * Delegation: handing a decision to someone else (the developer's decisions of 28 November 2026).
 *
 * One thing can go to the deputy, a peer or the higher official. Everything can go to the deputy or a peer only,
 * and only while the person is on approved leave, for the leave days or fewer. Version 1 makes no difference
 * between kinds of approval: one list of people, and "everything" means every kind. The person who delegated can
 * still decide; the receiver cannot delegate the same thing again; nothing is passed on automatically.
 *
 * These rules decide what the app offers. Whether a receiver may really decide is the server's to check, and two
 * things only the server can do: when everything is delegated, an approval the receiver sent themselves must not
 * reach them, and what was delegated to me must not travel on with my own delegation.
 */
enum class Relation(val words: String) {
    DEPUTY("Your deputy"),
    PEER("Same role"),
    HIGHER("Higher official"),
}

/** Someone the server says may receive. [name] is role and name. [onLeave]: away themselves during my leave. */
data class Receiver(val id: String, val name: String, val relation: Relation, val onLeave: Boolean = false)

/** My approved leave, as the server knows it. */
data class Leave(val from: LocalDateTime, val until: LocalDateTime)

/** Everything of mine goes to [to] between [from] and [until]. */
data class Delegation(val to: Receiver, val from: LocalDateTime, val until: LocalDateTime)

/** What the server says about delegation for me. [toMe]: whose approvals I decide now, in words. */
data class DelegationFacts(
    val receivers: List<Receiver> = emptyList(),
    val leave: Leave? = null,
    val running: Delegation? = null,
    val toMe: List<String> = emptyList(),
)

object Delegations {
    val REASONS = listOf("Travelling", "At the site", "They know it better", "Cannot look at it today")

    const val NO_LEAVE = "You can delegate everything only while you are on approved leave. No approved leave is recorded for you."
    const val ALREADY = "A delegation is already set. End it first, under More, Delegation."

    /** One step only: what was delegated to me, or what I delegated already, is not delegated again. */
    fun canDelegate(item: Item): Boolean = Inbox.canDecide(item) && item.delegatedBy == null && item.delegatedTo == null

    /** For one thing: the deputy first, then peers, then the higher official; never the person who sent it. */
    fun forOne(all: List<Receiver>, item: Item): List<Receiver> = all.filter { it.id != item.fromId && it.name != item.from }.sortedBy { it.relation }

    /** For everything: the deputy or a peer, never the higher official, and nobody who is on leave in those days. */
    fun forAll(all: List<Receiver>): List<Receiver> = all.filter { it.relation != Relation.HIGHER && !it.onLeave }.sortedBy { it.relation }

    /** The approved leave that still has time left; null when there is none. */
    fun leaveNow(leave: Leave?, now: LocalDateTime): Leave? = leave?.takeIf { it.until.isAfter(start(it, now).plusMinutes(15)) }

    /** Why everything cannot be delegated now; null when it can. */
    fun whyNotAll(facts: DelegationFacts, now: LocalDateTime): String? = when {
        facts.running != null -> ALREADY
        leaveNow(facts.leave, now) == null -> NO_LEAVE
        else -> null
    }

    /** It starts with the leave, or now when the leave has begun. */
    fun start(leave: Leave, now: LocalDateTime): LocalDateTime = maxOf(leave.from, now)

    /** The end the person wants, kept inside the leave: it can end earlier, never later. */
    fun until(wanted: LocalDateTime, leave: Leave, now: LocalDateTime): LocalDateTime =
        minOf(maxOf(wanted, start(leave, now).plusMinutes(15)), leave.until).withSecond(0).withNano(0)

    /** What the fingerprint question says: the touch signs exactly this. */
    fun question(to: Receiver, item: Item): String =
        "Delegate" + Inbox.amount(item)?.let { " $it" }.orEmpty() + " to ${Inbox.short(to.name)}: ${Inbox.short(item.title)}"

    /** Says when it starts too, when that is not now: the touch signs the whole period. */
    fun questionAll(to: Receiver, from: LocalDateTime, until: LocalDateTime, now: LocalDateTime): String =
        "Delegate all approvals " + (if (from.isAfter(now)) "from ${Format.dateTime(from, now)} " else "") + "until ${Format.dateTime(until, now)} to ${Inbox.short(to.name)}"

    fun runningLine(delegation: Delegation, now: LocalDateTime): String =
        if (delegation.from.isAfter(now)) "From ${Format.dateTime(delegation.from, now)} until ${Format.dateTime(delegation.until, now)} your approvals go to ${delegation.to.name}."
        else "Your approvals go to ${delegation.to.name} until ${Format.dateTime(delegation.until, now)}. You can still decide them yourself."

    /** The line on a thing that was delegated, for either side; null when it was not. */
    fun itemLine(item: Item): String? {
        val why = item.delegationReason?.let { " $it." }.orEmpty()
        return when {
            item.delegatedBy != null -> "Delegated to you by ${item.delegatedBy}.$why You decide it with your own fingerprint."
            item.delegatedTo != null -> "You delegated this to ${item.delegatedTo}.$why You can still decide it yourself."
            else -> null
        }
    }
}
