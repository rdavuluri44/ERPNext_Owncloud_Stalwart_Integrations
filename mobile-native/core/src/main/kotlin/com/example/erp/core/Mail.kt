package com.example.erp.core

import java.net.URI
import java.time.LocalDateTime

/**
 * The rules of mail that do not depend on a server or a screen (screen plan of 27 November 2026, points 14 to 17,
 * with the owner's changes: the list of received mail is "Received", because "Inbox" is the approvals place).
 */
enum class Folder(val label: String) { RECEIVED("Received"), SENT("Sent"), DRAFTS("Drafts"), ARCHIVE("Archive"), TRASH("Trash") }

data class Person(val name: String, val address: String)

data class Mail(
    val id: String,
    /** Mails that answer each other share one conversation. */
    val thread: String,
    val folder: Folder,
    val from: Person,
    val to: List<Person>,
    val cc: List<Person> = emptyList(),
    val subject: String,
    val body: String,
    val at: LocalDateTime,
    val unread: Boolean = false,
    /** File names. */
    val attachments: List<String> = emptyList(),
    /** Pictures the mail would fetch from the internet. They are not loaded until the person asks. */
    val remotePictures: Int = 0,
)

/** The mails of one conversation in one folder, oldest first. */
data class Conversation(val mails: List<Mail>) {
    val thread: String get() = mails.first().thread
    val newest: Mail get() = mails.last()
    val unread: Boolean get() = mails.any { it.unread }
}

object Mails {
    /** The folder as conversations, the one with the newest mail first. */
    fun conversations(mails: List<Mail>, folder: Folder): List<Conversation> =
        mails.filter { it.folder == folder }.groupBy { it.thread }.values
            .map { thread -> Conversation(thread.sortedBy { it.at }) }
            .sortedByDescending { it.newest.at }

    /**
     * True unless the address is at one of the company's own domains, compared exactly. An address that only
     * contains or resembles a company domain, and one that cannot be read, is outside.
     */
    fun outside(address: String, company: Set<String>): Boolean {
        val domain = address.trim().substringAfterLast('@', "").lowercase().trimEnd('.')
        return domain.isEmpty() || domain !in company
    }

    // The name before the "@" may use the characters the mail standard allows without quotes (also an apostrophe).
    private const val NAME = "[A-Za-z0-9!#\$%&'*+/=?^_`{|}~-]+"
    private val ADDRESS = Regex("$NAME(\\.$NAME)*@([A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?\\.)+([A-Za-z]{2,}|xn--[A-Za-z0-9-]+)")

    /** No real address is longer; anything longer is refused unread, so a huge pasted text cannot stall or crash the check. */
    private const val MAX_ADDRESS = 254

    /** Every kind of line break, also the ones a plain "white space" search misses. */
    val LINE_BREAK = Regex("[\\r\\n\\u000B\\u000C\\u0085\\u2028\\u2029]")

    /** A subject as it is sent: one line, single spaces. */
    fun oneLine(text: String): String = text.replace(LINE_BREAK, " ").replace(Regex("\\s+"), " ").trim()
    private val BETWEEN = Regex("[,;\\s]+")

    /** What was typed in "To", as addresses: the ones that can be sent to, and the ones that cannot. */
    fun addresses(typed: String): Pair<List<String>, List<String>> =
        typed.split(BETWEEN).filter { it.isNotEmpty() }.distinct().partition { it.length <= MAX_ADDRESS && ADDRESS.matches(it) }

    private val PREFIX = Regex("^((re|fwd?|fw)\\s*:\\s*)+", RegexOption.IGNORE_CASE)

    fun replySubject(subject: String): String = "Re: " + subject.replace(PREFIX, "")

    fun forwardSubject(subject: String): String = "Fwd: " + subject.replace(PREFIX, "")

    /** Everyone a "reply all" goes to: the sender and all other recipients, never the person themselves, each once. */
    fun replyAll(mail: Mail, me: String): List<Person> =
        (listOf(mail.from) + mail.to + mail.cc).filter { !it.address.equals(me, ignoreCase = true) }.distinctBy { it.address.lowercase() }

    fun firstLine(body: String): String = Format.short(body.lineSequence().map { it.trim() }.firstOrNull { it.isNotEmpty() && !it.startsWith(">") }.orEmpty(), 80)

    /** The answered mail, quoted under a reply. */
    fun quoted(mail: Mail): String = "\n\n${mail.from.name} wrote:\n" + mail.body.lines().joinToString("\n") { "> $it" }

    private val HOST = Regex("[a-z0-9]([a-z0-9.-]*[a-z0-9])?")
    private val LINK = Regex("https?://[^\\s<>\"')\\]]+")

    /** The web links written in a mail's text, each once. */
    fun links(body: String): List<String> = LINK.findAll(body).map { it.value.trimEnd('.', ',', ';', ':', '!', '?') }.distinct().toList()

    /**
     * Where a link really leads: the host the browser would go to. A name placed before an "@" is ignored, because
     * the browser ignores it too. Null when the app cannot be sure, and such a link is never opened:
     * - anything that is not a plain web address (other kinds of link, a host the parser cannot read);
     * - a link with any character outside plain printable ASCII. Converting look-alike or special letters is not
     *   done here on purpose: programs disagree on the result (one turns "ß" into "ss", browsers keep it), so the
     *   name shown could differ from the site opened. A name already in its coded form ("xn--...") is shown as it is;
     * - a host written as a number, which a browser reads as a network address the person would not recognise;
     * - a name without a dot ("localhost", "intranet"): that is the phone itself or its own network.
     */
    fun realHost(link: String): String? = try {
        val uri = if (link.all { it in '!'..'~' }) URI(link) else null
        val host = uri?.host?.lowercase()
        val last = host?.substringAfterLast('.').orEmpty()
        val numeric = last.isNotEmpty() && (last.all { it.isDigit() } || last.startsWith("0x"))
        val local = host == null || '.' !in host
        if (uri?.scheme?.lowercase() in setOf("http", "https") && host != null && HOST.matches(host) && !numeric && !local) host else null
    } catch (e: Exception) {
        null
    }
}
