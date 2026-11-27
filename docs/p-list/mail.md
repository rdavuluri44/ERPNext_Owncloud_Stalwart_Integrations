# Mail: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Mail: P items

Stalwart mail server and Bulwark webmail: delivery, policy, migration, attachments.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P12 — PTR and external mail delivery

**App:** mail · **Also touches:** none · **State:** blocked

**Status:** provider request pending and external deliverability unverified.

The final audit still returned PTR `provider-host.example.net` for 203.0.113.10, rather than mx.example.com. Follow up with the hosting provider, verify matching forward/reverse DNS and mail authentication, then test external reception/sending and delivery results. Earlier internal mail and SMTP envelope tests are not proof of external deliverability.

### P15 — Existing SMTP health alerts

**App:** mail · **Also touches:** none · **State:** open

**Status:** pre-existing email-health alerts were visible during browser acceptance; current delivery health was not re-certified by package consolidation.

Inspect the latest native SMTP/queue errors and the hourly monitor, verify the sole integration sender using an authenticated TLS/NOOP test, and distinguish stale alerts from a current failure. Earlier envelope checks and the working web inbox do not prove current outbound mail. Coordinate a real send/receipt acceptance test when scheduled.

### P17 — Automatic Drive links for Mail attachments over 200 KB

**App:** mail · **Also touches:** drive, dms · **State:** open

**Status:** not implemented. The deployed Files picker transfers bytes into an ordinary email attachment, with a 25 × 1024 × 1024 byte limit. It does not enforce a 200 KB threshold or create expiring links.

Carry the earlier requirement for both outgoing and incoming attachments, implemented through supported current Mail/Stalwart and Drive paths. External access uses expiring bearer links without sign-in; forwarded links remain usable until expiry/revocation. Decide expiry, threshold units/per-file versus aggregate sizing, inline/small attachment behavior, access auditing and cleanup. Preserve signed/encrypted incoming originals and agree raw MIME retention/storage accounting. Server-side enforcement, permission/failure/retry tests and external-recipient acceptance remain due. See [Mail scope and evidence](../roadmap.md#3-mail-attachments-and-mail-access-policy).

**Owner direction (24 November 2026):** the aim is that mail does not fill the disk, now that P69 keeps mail for up to
seven years.
- **Outgoing:** documents larger than 200 KB are picked from Drive and sent as a link, not attached.
- **Incoming:** every incoming attachment is processed by Paperless and stored there under the document policy; the
  attachment in the mailbox is replaced by a reference to the Paperless document, so it can be found and linked again
  later.

**To settle with P69 (proposed, not yet decided):**
- **Archive keeps the original.** The P69 journal copy is made at the SMTP stage, before any Paperless processing, so
  the archive holds the unchanged message with its attachments. Recommended: keep it so (legal evidence; changing a
  signed message breaks its signature). The space saving then comes from the users' mailboxes, not from the archive.
- **A linked file must last as long as the mail.** A sent Drive link points to a file a user could later delete. Files
  sent as links (and Paperless documents referenced from mail) must be locked for the P69 retention period, or copied
  into a protected space at send time.
- **Order of steps:** P69 first (it protects mail from now on), then P17 on top of it.

### P18 — Allowed Mail clients and protocol access policy

**App:** mail · **Also touches:** none · **State:** open

**Status:** discussion required; the previous “suite-only” wording is not a selected policy for the new stack.

Discuss portal/webmail versus native Mail clients and required JMAP/IMAP/POP/submission/DAV access. Preserve current authenticated public Mail/private administration, SMTP reception, ERP/authentik SMTP sending and required integrations while deciding. Do not disable endpoints or alter exposure from this note. See [access-policy discussion](../roadmap.md#access-policy-requiring-discussion).

### P19 — Three Google Workspace mailboxes to Stalwart

**App:** mail · **Also touches:** general · **State:** open

**Linked (owner, 21 November 2026):** taken up together with **P70** (domain split: `tenant.example` becomes production's
mail domain on our server) and **P63** (demo on `example.com`); still blocked by P12 (PTR).

**Feasibility: possible (24 November 2026).** The registrar transfer, DNS control
and three-mailbox migration have documented routes. Published terms were reviewed.
Account-specific agreements and administrative access, a pilot import and mailbox
reconciliation remain to be verified. The item stays open.

**Registrar and DNS.** WHOIS lists Openprovider as the registrar of `tenant.example`,
with a client transfer lock and signed delegation. Google hosts the authoritative
DNS and receives mail. Google's published India Domain Registration Terms make the
customer the registrant for domains bought through the service and refer registration
support to the registrar partner. Google's transfer guide explains how to find that
partner and reach Advanced DNS Settings. Under .IN policy the eligible registrant
can request the transfer authorization code from Openprovider or the reseller.
Confirm the registrant account and current provider agreement before requesting it.
Separately obtain Cloud DNS access or a complete zone export from the project owner
or reseller. Keep Google's MX during the registrar transfer. Confirm nameserver and
DNSSEC DS handling with the registrar before changing either. [Google registration terms](https://workspace.google.com/intl/en_in/terms/domain_terms/),
[Google transfer guide](https://knowledge.workspace.google.com/admin/domains/transfer-your-domain-to-another-host),
[.IN registry transfer rules](https://www.registry.in/faqs) and
[Cloud DNS export](https://docs.cloud.google.com/dns/docs/records).

**Mailbox copy.** Production Stalwart reports 1.1.0. Use the external mail provider's documented OAuth
IMAP to Vandelay archive to Stalwart JMAP route, subject to Workspace app approval
and a pilot. Use a protected source archive per account and preserve raw mail
including MIME attachments. Reconcile every in-scope source message with the target,
including Inbox, Sent, Drafts, Archive and custom labels. Account explicitly for
Spam and Trash, and verify timestamps, flags, multi-label messages and a repeat copy
for duplicates. Provider-only behavior, such as category views, filters and scheduled
sending, needs separate handling. Inventory aliases, forwarding and send-as separately.
Contacts, calendars and Google Drive remain outside P19. No live mailbox contents
were inspected or transferred during this feasibility review.
[Google Workspace IMAP settings](https://knowledge.workspace.google.com/admin/sync/turn-pop-and-imap-on-or-off-for-users),
[Stalwart hosted migration](https://stalw.art/docs/migration/guide/hosted/) and
[Label mapping for the external mail provider](https://stalw.art/docs/migration/import-export/import/takeout/).

**Cutover acceptance.** Keep Google Workspace active while staging, validating and
catching up. Change MX only after P12 reverse DNS and external delivery are verified
and the owner approves the window. Retain the old route and reconcile mail delivered
to either service through the rollback window. Workspace cancellation is outside the
approved scope. See [migration scope](../roadmap.md#5-three-google-workspace-mailboxes).

### P69 — Mail retention: keep every message, users cannot delete permanently

**App:** mail · **Also touches:** general · **State:** open

**Status:** owner request and go, 21 November 2026; paused the same day. Owner chose **Community edition only** and gave the go for an isolated test on 24 November 2026. **Isolated test passed** (results below); public branch `p69/community-retention` at `ffee5bb` (rehearsal script, CI passed, no PR yet). Not on the real test mail, not on production. Owner decided retention, access and scope on 24 November 2026 and gave the go for records, code, test-site rollout and a PR (production needs a separate go).

Configure Stalwart so that company mail is **retained** and a user cannot remove it for good: deleting in webmail,
phone or desktop clients must not destroy the company's copy. Plan first, then test on the test site, then production.

**To decide and verify:**
1. **Mechanism:** (a) a journal or archive copy of every incoming and outgoing message delivered to an archive
   mailbox or store that ordinary users cannot open or change (Sieve or routing rule on the server, so no client can
   bypass it); (b) server-side protection of the users' own mailboxes (deny expunge, or keep deleted messages for a
   retention period); (c) both. Check which of these the installed Stalwart version supports natively and which need
   an Enterprise licence; no unsupported patches.
2. **Retention period** per mailbox or role (for example years for business mail; Indian legal requirements for
   accounts, tax and contract correspondence to be confirmed by the owner), and what happens after it.
3. **Who may search or restore** archived mail (owner only, or a compliance role), with an access log; staff are told
   that company mail is retained (privacy notice, as in P48's DPDP notice).
4. **Storage and backups:** size estimate, the archive included in the nightly encrypted backup (P02/P40) and its
   restore tested; the ransomware protections apply.
5. **Scope:** all company mailboxes including the three migrated Google mailboxes (P19); shared and system senders.

**Acceptance:** on test, a user deletes and empties trash for a message in webmail and in an IMAP client; the archive
still holds it and the owner can retrieve it; a user cannot reach the archive; the backup contains it and restores.

**Findings (21 November 2026, Stalwart docs; production runs Stalwart 1.1.0, Community):**
- **Undelete archive is Enterprise only:** `DataRetention.archiveDeletedItemsFor` keeps deleted and expunged messages
  for a set time and lets users (and admins with impersonation) restore them; Community cannot use it.
- **Community controls:** permissions per role can remove permanent deletion: `imapExpunge`, `jmapEmailDestroy`,
  `pop3Dele` (and `imapDelete`, `jmapMailboxDestroy` for deleting whole folders). Deleting would then only move mail to
  Trash. The Trash auto-expunge (`expungeTrashAfter`, default 30 days) must then be switched off, or Trash empties
  itself. Without an archive, an allowed expunge is final.
- **Journal copy:** system Sieve scripts run at the SMTP stages and can `redirect` a copy to an archive address; they
  cannot file into a mailbox. Whether this also catches mail sent from webmail (JMAP submission) is not documented:
  to test on the test site.
- **Plan (proposed):** (1) remove the permanent-delete permissions from the user role and switch off Trash
  auto-expunge; (2) a journal copy of inbound and outbound mail to an archive account no user can open, if the test
  shows it catches all paths; (3) owner decides on Enterprise only if (1)+(2) fall short. Webmail and phone clients
  must be checked: what a user sees when "empty trash" is refused.

**Decided (owner, 24 November 2026):** option (a) on the **Community edition only**: remove permanent deletion from
the user role, switch off Trash auto-expunge, and a journal copy of all mail to a hidden archive account. The
Enterprise undelete window (option c) is out of scope.

**Isolated test, 24 November 2026 (test VM, throwaway servers; real test and production mail untouched):**
- **Setup:** Stalwart 1.1.0 at the production image digest (`f772aa6e…`) on an internal-only Docker network with a
  `.test` domain; the policy applied by `integrations/mail/community_retention.py` at public `ffee5bb` to a fresh
  server; Bulwark webmail from the image the test site runs (pin 1.21.2), basic sign-in instead of SSO, behind a proxy.
- **Journal copy:** a system Sieve script (`redirect :copy` at the SMTP DATA stage) copied every message to the hidden
  archive account on all three paths tried: inbound SMTP, authenticated SMTP submission (port 465) and JMAP submission
  (the protocol webmail uses). An attachment arrived intact and the recovery administrator retrieved its exact bytes.
- **Archive locked:** the archive account has no credentials and only `emailReceive`; an ordinary user's attempt to
  read it returned `accountNotFound`.
- **JMAP (webmail protocol):** permanent delete and folder deletion returned `forbidden`.
- **IMAP:** `EXPUNGE`, `UID EXPUNGE` and folder `DELETE` were refused and **the server closed the IMAP session** each
  time; `CLOSE` returned OK without removing anything. The original and the archive copy were verified afterwards.
- **Webmail as a user sees it (headless Chrome):** Delete moves the message to Trash ("Moved to Trash", undo offered).
  In Trash, **Delete forever** first asks "Delete this message forever? You can't get it back." and after confirming
  shows "The message could not be deleted. Try again. Failed to delete email: You are not authorized to destroy objects
  of this type"; the message stays. **Empty Trash** asks "Delete the message in Trash forever? You can't undo this."
  and after confirming shows **no message at all** (none visible 4 s later); the message stays, also after a page
  reload. The Trash banner keeps saying "You can empty the Trash folder to permanently remove all messages." On the
  server afterwards: the user's copy in Trash ("Deleted Items"), the archive copy in the archive account, Trash
  auto-expunge off.
- **Backup and restore (cold copy):** with the server stopped, its config and data volumes were archived and restored
  into a second isolated server; archived messages, the exact attachment, the archive lock and the auto-expunge
  setting all survived.
- **Clean-up:** all six throwaway containers, their six volumes, the network and the work folder (with its disposable
  admin credential) were removed the same day; the test site's own mail containers kept running.

**Not tested:** real phone and desktop mail apps (only raw IMAP commands; how they react to the closed session is
unknown); POP3 delete (`pop3Dele` removed but not exercised); outgoing mail to outside recipients (the test network had
no internet); the SSO sign-in path of webmail; the project's real nightly encrypted backup (P02/P40) instead of a
cold volume copy; disk growth from the journal copy; the real test mail server.

**Findings for the rollout:**
- The webmail texts mislead users: the confirmation dialogs promise a permanent delete, Empty Trash fails silently,
  and the Trash banner offers permanent removal. A small overlay change (hide or relabel Delete forever and Empty
  Trash, explain that company mail is kept) belongs to the rollout.
- The rehearsal script refuses anything but a `.test` domain on purpose. The rollout needs its own reviewed change
  (test site first, then production) with a recorded before-state for rollback, as the script already writes.
- Phone and desktop clients may show errors or reconnect when their expunge is refused; check on a real device.

**Decided (owner, 24 November 2026), answering points 2, 3 and 5:**
- **(2) Retention: seven years at most.** Mail is kept for seven years and then removed from the archive and from the
  users' mailboxes (Trash included). Stalwart Community has no built-in age limit for this, so a scheduled purge job is
  part of the build. To confirm with the company's accountant: Indian law keeps books of account for eight years
  (Companies Act s.128(5)), and GST and income-tax records can need longer than seven years in some cases.
- **(3) Access: administrator only.** One administrator account gets read-only access to the archive through the
  normal sign-in, and every access is logged (to be verified on the Community edition). Staff are told that company
  mail is kept (notice as in P48).
- **(5) Scope: all mailboxes**, including the three migrated Google mailboxes (P19) and shared and system senders.
- **Also adopted (recommended by the agent):** a one-time copy of every existing mailbox into the archive at switch-on
  (the journal only catches new mail); a disk-space alert with P72; the webmail text change for Delete forever and
  Empty Trash.
- **Related:** P17 (Drive links out, Paperless references in) reduces mailbox size; how it fits with the archive is
  noted in P17.

**Build and test site (24 November 2026):** draft public PR #69 (`p69/community-retention`, contains #68). The
tool is `integrations/mail/retention.py` (apply with before-state receipt and restart, rollback, backfill, purge,
status). The webmail policy locks the delete action to Trash, and 16 English webmail texts are replaced.
- **Isolated 1.1.1 test:** 26 of 26 end-to-end checks passed.
- **Test site:** webmail `b2d81a9` and the policy are live. Backfill copied 18 messages. The purge count found 0.
  A JMAP probe was journaled, its delete was refused, and its archive copy survived account removal. Receipt
  `p69-test-mail-retention-b2d81a9`; rollback `<server path>`.
- **Found while testing:**
  - The journal starts only after a restart.
  - Stalwart's default log folder does not exist in the image, so **the test server logged nothing**
    (production likely the same; check at the P75 promotion). The tool moves the log to the data volume.
  - The same message in a group and a member mailbox is archived once (`alreadyExists`).
  - A build under umask 077 broke webmail on test for about five minutes (incident receipt; fixed in `b2d81a9`).
- **Reader (owner, 24 November 2026): option (a), a dedicated `archive-reader` sign-in.** On test the mailbox account
  `archive-reader` exists and `retention.py apply` (reader included) verified. A temporary app password showed
  read-only access to the archive (list yes; delete and change refused), and the sign-in was logged by name. The
  app password was revoked.
  **Found:** test webmail signs in through the shared production Authentik (`sso.example.com`, application
  `test-office-mail`). The mailbox comes from the "Office mail identity mapping" (email to mailbox). So the
  `archive-reader` sign-in needs a new Authentik user and a mapping entry **in production Authentik**, which needs a
  separate owner go. The owner enrols its passkey.
  **Done (owner go, 24 November 2026):** in production Authentik, user `archive-reader` was created (no usable
  password, group Testers only) and the shared mapping gained the entry for it. The owner's mapping is unchanged
  (verified). Receipt `p69-production-authentik-archive-reader-20261124`; rollback snapshot
  `<server path>` on the VPS. The passkey cannot come through an invitation: the
  enrollment flow requires the staff group, and the reader's mailbox does not receive mail yet. Instead, the owner
  impersonates `archive-reader` (reason required, logged) and adds a passkey under its MFA devices.
**26 November 2026:**
- **Passkey:** the owner impersonated `archive-reader` and enrolled a Bitwarden passkey (second attempt, 03:09 UTC;
  the first attempt never reached authentik and left a useless Bitwarden entry). Impersonation ended cleanly.
- **Sign-in refused:** the production passkey sign-in gate (`<namespace>-passkey-approved-account`) admits superusers and
  "<staff group>" only, so `archive-reader` was denied (the recovery deny message). Test webmail uses the same
  production sign-in. Options put to the owner: an app password in a desktop mail client, a change to the gate, or
  the staff group. **Owner chose (2): a gate change limited to mail.** PR #78 (`p69/archive-reader-signin`, merged `81d73dd`):
  group Mail Archive Readers passes the gate; only the mail applications admit it (mode "any" over plain group
  bindings); the reader leaves Testers. Tested on throwaway authentik 2026.8.5 and 2026.8.7: 23/23. **Applied to
  production authentik after P83; owner signed in to test webmail as archive-reader, read the shared archive, and
  delete and move were refused** (receipt `p69-production-authentik-archive-reader-signin-81d73dd`).
- **Correction (backfill count):** the 24 November receipt says "Backfill copied 18 earlier messages". Checked message
  by message on 26 November: the mailboxes hold 18 copies of 11 distinct messages (4 are in more than one mailbox);
  all 11 are archived, and the 12th archived message is the probe whose account was removed. The tool counted
  copies it skipped as "already archived" as copied. Fix: report copied and already-archived separately (in #69).
- Open question for production: the reader's own mailbox offers Compose; whether `archive-reader` may send mail was not
  checked (decide with the P69 production go).
- **Before #78:** its advisory check found the authentik security release; P83 upgraded test and production first.
- A one-time recovery link for `archive-reader` (to test without the owner) was refused by the Claude Code safety
  check before it ran; nothing was created.
- Webmail texts: all 12 distinct new texts are in the running test webmail (no visual check yet).
- Phone test: throwaway Stalwart 1.1.1 `p69-phone` on the test VM, IMAPS on the tailnet address only, retention
  applied, 6 test messages (7 copies, all journaled to its archive). Sign-in details in a 0600 file on the owner's
  laptop Desktop. Waiting for the owner; delete the server and the file afterwards.
- Found: production authentik logs `property_mapping_exception` for anonymous requests about once or twice a day
  since at least 23 November (mapping name not recorded). Not investigated; no owner decision yet.
- **Open:**
  - Phone mail app on a tailnet-only throwaway server, with the owner.
  - Real-user webmail look (the archive reader's sign-in itself passed 26 November).
  - Production-only checks after promotion: outside delivery journaled, nightly backup contains the archive (restore
    the mail volume into a throwaway server), counting purge reviewed before the timer. The migrated Google mailboxes
    may hold mail older than seven years.

**Go (owner, 24 November 2026):** (1) records; (2) code on `p69/community-retention`: policy step for test and
production with before-state and rollback, one-time copy, seven-year purge job, administrator read-only access with
an access log, webmail text change, README, decision entry, tests and an advisory check; (3) deploy to the test site
and test (SSO webmail, mail to an outside address, nightly backup contains the archive and restores, disk-size
measurement, a real phone mail app with the owner); (4) open the PR with the evidence. Production promotion needs a
separate go.

**Owner decided (27 November 2026): a dedicated archive-reader sign-in reads the archive** (not the owner's own
mailbox). Public draft #69 was brought up to date with main the same evening (`60e5875`, CI passed; its 16 webmail
text replacements still match the pinned webmail 1.21.2). Still open before it leaves draft: setting the reader on
the test mail server and a real-user look at the new texts. Both wait for the test host; the webmail image is built
together with #142 (P53), which changes the same image.
