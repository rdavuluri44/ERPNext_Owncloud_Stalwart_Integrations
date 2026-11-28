package com.example.erp.core

import java.time.LocalDateTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MailTest {
    private val now = LocalDateTime.of(2026, 11, 27, 18, 0)
    private val me = Person("You", "you@example.com")
    private val manager = Person("Project manager", "pm@example.com")
    private val engineer = Person("Engineer", "engineer@example.com")
    private val company = setOf("example.com")

    private fun web(rest: String, scheme: String = "https") = "$scheme://$rest"

    private fun mail(id: String, thread: String, minutesAgo: Long, folder: Folder = Folder.RECEIVED, unread: Boolean = false) =
        Mail(id, thread, folder, manager, listOf(me), listOf(engineer), "Pour checklist", "Please check.\nThanks", now.minusMinutes(minutesAgo), unread)

    @Test
    fun aFolderIsShownAsConversationsNewestFirst() {
        val mails = listOf(mail("a", "t1", 300), mail("b", "t2", 200, unread = true), mail("c", "t1", 10), mail("d", "t3", 5, Folder.SENT))
        val received = Mails.conversations(mails, Folder.RECEIVED)
        assertEquals(listOf("t1", "t2"), received.map { it.thread })
        assertEquals(listOf("a", "c"), received[0].mails.map { it.id }) // oldest first inside a conversation
        assertFalse(received[0].unread)
        assertTrue(received[1].unread)
        assertEquals(listOf("t3"), Mails.conversations(mails, Folder.SENT).map { it.thread })
        assertEquals("Received", Folder.RECEIVED.label) // "Inbox" is the approvals place
    }

    @Test
    fun onlyAnExactCompanyDomainIsInside() {
        assertFalse(Mails.outside("pm@example.com", company))
        assertFalse(Mails.outside(" PM@Example.COM. ", company))
        for (address in listOf(
            "accounts@supplier-example.net",
            "support@example.com.account-check.net", // the company's name in front of someone else's domain
            "support@mail.example.com", // a subdomain is not the company unless it is listed
            "support@example.co",
            "support@notexample.com",
            "example.com",
            "",
        )) {
            assertTrue(address, Mails.outside(address, company))
        }
    }

    @Test
    fun whatIsTypedInToIsSortedIntoUsableAndNot() {
        assertEquals(listOf("pm@example.com", "engineer@example.com") to emptyList<String>(), Mails.addresses("pm@example.com, engineer@example.com; pm@example.com"))
        assertEquals(listOf("pm@example.com") to listOf("engineer", "a@b", "x@@example.com"), Mails.addresses("pm@example.com engineer a@b x@@example.com"))
        val notAddresses = listOf("a@-.-", "a@1.2", ".a@example.com", "a..b@example.com", "a.@example.com", "a@example", "a@-example.com", "a\u202e@example.com", "<pm@example.com>")
        assertEquals(emptyList<String>() to notAddresses, Mails.addresses(notAddresses.joinToString(", ")))
        val real = listOf("first.last+site@mail.example.co.in", "o'brien@example.com", "A.B-c_d@EXAMPLE.technology", "x@example.xn--h2brj9c")
        assertEquals(real to emptyList<String>(), Mails.addresses(real.joinToString("; ")))
        // An absurdly long "address" is refused without being examined, and nothing crashes.
        val huge = "a." .repeat(5000) + "a@example.com"
        assertEquals(emptyList<String>() to listOf(huge), Mails.addresses(huge))
        assertEquals("Pour checklist for Friday", Mails.oneLine("  Pour\nchecklist\r\n for\u2028Friday\u0085 "))
        assertEquals(emptyList<String>() to emptyList<String>(), Mails.addresses("  "))
    }

    @Test
    fun subjectsDoNotCollectPrefixesAndReplyAllLeavesMeOut() {
        assertEquals("Re: Pour checklist", Mails.replySubject("Pour checklist"))
        assertEquals("Re: Pour checklist", Mails.replySubject("RE: re: Fwd: Pour checklist"))
        assertEquals("Fwd: Pour checklist", Mails.forwardSubject("Re: Pour checklist"))
        val received = mail("a", "t1", 5).copy(to = listOf(me, engineer), cc = listOf(engineer, Person("Me again", "YOU@example.com")))
        assertEquals(listOf(manager, engineer), Mails.replyAll(received, me.address))
        assertEquals("\n\nProject manager wrote:\n> Please check.\n> Thanks", Mails.quoted(received))
        assertEquals("Please check.", Mails.firstLine("\n> an old line\nPlease check.\nThanks"))
    }

    @Test
    fun aLinkShowsWhereItReallyLeads() {
        val body = "Open ${web("portal.supplier-example.net/invoices/1042")}. Or (${web("portal.supplier-example.net/invoices/1042")}) and ${web("example.com/help", "http")}!"
        assertEquals(listOf(web("portal.supplier-example.net/invoices/1042"), web("example.com/help", "http")), Mails.links(body))
        assertEquals("portal.supplier-example.net", Mails.realHost(web("portal.supplier-example.net/invoices/1042")))
        // The company's name in front does not make it the company's site.
        assertEquals("example.com.account-check.net", Mails.realHost(web("example.com.account-check.net/login")))
        // A name before "@" is not where the browser goes.
        assertEquals("account-check.net", Mails.realHost(web("example.com@account-check.net/login")))
        assertEquals("example.com", Mails.realHost(web("EXAMPLE.com:8443/x?y=1")))
        // A name already in its coded form is shown exactly as the browser will use it.
        assertEquals("xn--exmple-qta.com", Mails.realHost(web("xn--exmple-qta.com/login")))
        val cannotBeSure = listOf(
            web("ex\u00e1mple.com"), // look-alike letters
            web("busine\u00df.example"), // "ß": one program reads "ss", the browser keeps it and goes elsewhere
            web("\u03c3\u03c5\u03c2.example"), // final sigma, the same disagreement
            web("exam\u200dple.com"), // an invisible joiner
            web("example.com/\u202egnp.exe"), // a character that makes the address read backwards
            web("a@b@account-check.net/login"), // two "@": not a form the app can read for sure
            web("2130706433/"), // a number is a network address to a browser
            web("0x7f.1/"),
            web("127.1/"),
            web("192.168.1.1/"),
            web("example.com\\@account-check.net"),
            web("exa%6dple.com"),
            web("example.com./"),
            web("[::1]/"),
            web("exa_mple.com"),
            web("localhost/admin"),
            web("intranet/login"),
        )
        for (link in cannotBeSure) assertNull(link, Mails.realHost(link))
        for (bad in listOf("javascript:alert(1)", "intent://scan/#Intent;end", "file:///sdcard/x", "mailto:a@example.com", "example.com", "", web(""))) {
            assertNull(bad, Mails.realHost(bad))
        }
    }
}
