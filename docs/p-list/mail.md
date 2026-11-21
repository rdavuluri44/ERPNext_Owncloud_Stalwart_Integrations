# Mail: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
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

**App:** mail · **Also touches:** drive · **State:** open

**Status:** not implemented. The deployed Files picker transfers bytes into an ordinary email attachment, with a 25 × 1024 × 1024 byte limit. It does not enforce a 200 KB threshold or create expiring links.

Carry the earlier requirement for both outgoing and incoming attachments, implemented through supported current Mail/Stalwart and Drive paths. External access uses expiring bearer links without sign-in; forwarded links remain usable until expiry/revocation. Decide expiry, threshold units/per-file versus aggregate sizing, inline/small attachment behavior, access auditing and cleanup. Preserve signed/encrypted incoming originals and agree raw MIME retention/storage accounting. Server-side enforcement, permission/failure/retry tests and external-recipient acceptance remain due. See [Mail scope and evidence](../roadmap.md#3-mail-attachments-and-mail-access-policy).

### P18 — Allowed Mail clients and protocol access policy

**App:** mail · **Also touches:** none · **State:** open

**Status:** discussion required; the previous “suite-only” wording is not a selected policy for the new stack.

Discuss portal/webmail versus native Mail clients and required JMAP/IMAP/POP/submission/DAV access. Preserve current authenticated public Mail/private administration, SMTP reception, ERP/authentik SMTP sending and required integrations while deciding. Do not disable endpoints or alter exposure from this note. See [access-policy discussion](../roadmap.md#access-policy-requiring-discussion).

### P19 — Three Google Workspace mailboxes to Stalwart

**App:** mail · **Also touches:** general · **State:** open

**Linked (owner, 21 November 2026):** taken up together with **P70** (domain split: `tenant.example` becomes production's
mail domain on our server) and **P63** (demo on `example.com`); still blocked by P12 (PTR).

**Status:** planned migration; source identities, domain, sizes, destination mappings, tooling and cutover are not yet specified. This is separate from the earlier retired local-server no-migration decision.

Keep email, folders/labels and sent-mail scope; exclude contacts, calendars and Google Drive. Inventory and map source/destination access, plan deduplication and capacity/recovery, preserve source messages and historical MIME, validate initial/catch-up copies, then separately agree mail DNS cutover and rollback. Google Workspace cancellation or other-product changes are not authorized. No mail copying or DNS changes are started. See [migration scope](../roadmap.md#5-three-google-workspace-mailboxes).

### P69 — Mail retention: keep every message, users cannot delete permanently

**App:** mail · **Also touches:** general · **State:** open

**Status:** owner request and go, 21 November 2026; mechanism check done, then **paused by the owner** until P69 is taken up again (see the decision waiting at the end).

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

**Paused (owner, 21 November 2026): resume here.** Decision waiting for the owner: (a, recommended) free edition,
remove permanent deletion from the user role, switch off Trash auto-expunge, and a journal copy of all mail to a
hidden archive account (tested on the test site first, including mail sent from webmail); (b) free edition, block
permanent deletion only (mail of a removed mailbox or account is still lost); (c) price and terms of the Enterprise
licence for its built-in undelete window. Sources: Stalwart docs pages on deleted items, data retention, permissions
and system Sieve scripts.

