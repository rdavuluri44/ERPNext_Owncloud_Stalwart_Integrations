# P list: roadmap and work items

> **Generated file: do not edit by hand.** This is the project's work list (every "P" number used in
> commits, pull requests, READMEs and `docs/decisions.md`) published from the maintainers' private
> list on 27 November 2026, with every line kept. Only these categories are replaced, by placeholders: the
> deploying organisation's name (`<tenant>`), host names (`example.com`), IP addresses
> (documentation ranges), server file paths and rollback folders, mail addresses, names of people and
> of third parties' internal products, business file names, and links to private records
> (marked "private record"). Everything else (scope, status, reasons, design, evidence, priorities)
> is unchanged. Changes are made in the private list and re-published; to propose a change or
> take up an item, open a pull request or an issue that names the P number.

> Sanitized current pending list. Package consolidation does not imply completion of these independent provider/device tasks.

# Pending tasks — current reconciled list

Updated **16 November 2026 (Asia/Kolkata)** after auditing the retained deployment and the repository-built isolated test workspace. See [current retained setup](retained.md) and [test acceptance](test-acceptance.md). Items below distinguish incomplete implementation from unverified acceptance. No dates or automations have been scheduled by this document.

The eight selected topics from the previous repository are reconciled in the [carried-forward roadmap](roadmap.md), including what is already deployed, superseded or still requires a decision.

## How to use this list (owner, 21 November 2026)

A **P item** is one self-contained unit of work with a number, a status and a clear scope
(why, what, how it is tested, what it depends on). The numbers never change and are never
reused; commits, pull requests, release records and handovers refer to them (P58, P60).

- **Related P items are taken up together.** When several items touch the same module,
  stack or decision, they are built on one branch, tested on the test site together and
  merged as one release, so a stack is changed once and not several times. The items stay
  separate in this list (each keeps its own status and history) while the release names
  all of them.
- **Why:** development stays modular (one module, one purpose, reusable on its own), and
  connectivity between sessions is simple: a new session, a new contributor or an AI
  agent reads this file, picks an item or a related group and knows its scope, status and
  dependencies without the earlier conversation. Records need not be re-explained.
- **How a group is chosen:** shared module or stack, shared test, shared production
  promotion, or one depends on the other (the Priority order below shows dependencies).
  Examples, not a plan: P60 with P59 (route files and promotion plan); P49 with P45 and
  P08 (sign-in stack and logout); P13 with P25 (users and enrollment); P12, P15 and P19
  (mail delivery, health and migration); P29, P30 and P48 (mesh, DNS, router); P50 with
  P14 (mobile app and push).
- **App lists (owner, 21 November 2026):** the list is organised by app, because many changes will now
  land in every app. Each P item lives in `docs/pending/<app>.md` (`erp`, `portal`, `signin`, `drive`,
  `editor`, `mail`, `dms`, `raven`, `mobile`, `test-site`); items that address the platform or security in
  general are in `general`. This file is the **index**: how to use the list, the priority order across all
  apps, the by-app tables and the legacy groups. An item has one home (its main app) and names the other
  apps it touches on its `**App:**` line (`**App:** x · **Also touches:** y, z · **State:** open`; states:
  open, in progress, blocked, parked, recurring, done, closed). Numbers run across the project and never
  change. **To add or change an item:** edit it in its app's list, then run `python3 tools/p_index.py` (index),
  then publish (below). To work on an app, read its list and the items it is "also touched" by in the index.
- **Public copy (owner, 21 November 2026):** this list is published in full as `docs/p-list.md` in
  the public repository so the team can see the roadmap. Every time this file changes, regenerate it
  with `tools/publish_p_list.py` (private rules in `tools/publication-rules.private.json`) and open a pull
  request. **Never skip details:** the tool replaces text inside lines only, never removes or summarises a
  line, and writes every substitution to `docs/publication/last-report.md`; only the sensitive categories
  in the rules are replaced; the leak scan must be clean and the report read before the pull request.
- **Only open work is listed (owner, 21 November 2026):** a P item is **removed** from its app list when the
  task is completed, or becomes redundant or irrelevant, in the same session: `python3 tools/p_close.py --finished`
  (every item whose State is done or closed) or `--item Pnn --outcome redundant|irrelevant|superseded --reason "..."`.
  It leaves one line in [the closed log](p-closed.md) (number, title, app, outcome, date, reason), so numbers are never
  reused; the full text stays in git history and the work in the release log and `docs/decisions.md`. Then publish.
- **Rules that stay:** the owner decides what starts and when; every group still follows
  branch, test, merge, `main`, production (`AGENTS.md`), and the release record names
  every P item it carries, the tested commit and the rollback point. When an item is
  done, mark its status here in the same session.

## Priority order (assessed 21 November 2026; the owner adjusts, then we work from the top)

Ranked by: (1) live defect or outage risk, (2) security and data loss, (3) what blocks
people from using the system (user rollout), (4) dated deadlines, (5) dependencies,
(6) effort. Items marked **owner** were prioritised by the owner. Nothing here starts
until the owner says; the table only fixes the order to take them up.

**Tier 0: in flight or owner priority (take up first)**

| Rank | Item | Why now | Depends on / note |
|---|---|---|---|
| 1 | **P74** document and photo store in the mobile app (Drive) | server part on production 25 Nov (`059f8bf`); next: phone test | app #66 needs #64 |
| 2 | **P61** editor file safety | production business data: a shared workbook became unusable and edits were parked unsaved (20 Nov); owner request | start with the unstick and rescue tool; relates to P57, P59 |
| 3 | **P59** promotion plan and drift check | a stack was missed in the 21 Nov promotion; prevents repeats | none; do before the next multi-stack release |
| 4 | **P57** survive reboots (released 21 Nov; production reboot passed 22 Nov) | **26 Nov: Prometheus did not come back after a production reboot** (started by hand after 26 minutes) | remaining: lasting fix and a boot check that counts containers (follow-ups 6 to 9, owner's go needed); repeat the reboot drill on the test VPS after the move |
| 4a | **P82** ERP Mobile holds the passkeys; 1 phone + 1 computer session per user | **owner** 25 Nov: sign-ins that cannot be shared or left on a shared computer; owner starts it in another session | Android first, Apple later; with P50; amended 26 Nov (PM then admin approval, strong sensors only, 5-miss erase, no selfie, Android 9–13 kept); P95 face attendance and P96 SOPs alongside (not yet ranked) |
| 4b | **P84** client identity out of the public repository, with an automatic check; **P85** Unformat brand public as the default | **owner** 26 Nov: client names must leave the public repository "tomorrow if not today" | after PR #80 is cleared; history rewrite is an owner decision; P85 needs the trademark owner |

**Tier 1: high (business-critical, next)**

| Rank | Item | Why | Depends on / note |
|---|---|---|---|
| 5 | **P62** daily upstream watch (releases, security flaws, upgrade advice) | security: new flaws and fixes reach us only by chance today; advice only, no automatic upgrades | none; baseline first, dry-run a week; owner may place it higher |
| 5a | **P100** mobile app checks in CI (build, typecheck, lint, tests, secret scan, code scanner, dependency advisories; app dependencies in the daily watch) | **owner** 26 Nov: tier 1; the build loop for every screen relies on these checks and CI checks nothing in `mobile/` today | scanners need an adoption check first; overlaps PR #75 (template) and P71 (workflows); next to P62 because it extends the watch |
| 6 | **P72** monitoring and alerting | VPS metrics, uptime, probe logs and backup audit live | phone delivery deferred; remaining storage and logging checks in P72 |
| 7 | **P64** native app sign-in on production: latent auth-hook crash, stale client list | crash fix live since 21 Nov (`4a5151f`) | remaining: correct the stale native client list on production when the app goes live (P50) |
| 8 | **P71** GitHub CI/CD and central secrets management: Actions deploy test and production, owner approves production; secrets in one managed place; "Refresh code" button removed | owner decision 21 Nov; removes the hand-run steps behind several slips today | plan settled 21 Nov, **scheduled for later** (owner go needed); order in the item; takes over deploy parts of P67, P54, P59 |
| 9 | **P67** test deployments as one complete step (gateway, profiles, setup) | hand-run steps and profile drift found installing PR #15 | with P54, P59 |
| 10 | **P49** sign-in pages and templates into the repository (finishes P45) | a claim-name mismatch already caused an ERP sign-in outage (20 Nov); authentik settings (JIT, memory, brand, flows) live only in its database | P45 remainder; rehearse on test |
| 11 | **P08** global logout and fresh passkey, end to end | security acceptance; parts verified 21 Nov (logout ends the session; passkey is asked, Bitwarden answers silently) | owner checks each app as initiator |
| 12 | **P13** remaining users, permissions, worker enrollment | adoption: 10 of about 20 users | P25 |
| 13 | **P25** invitation, passkey enrollment and recovery acceptance | needed before more users join; lost-device recovery untested | real SMTP and devices |
| 14 | **P12** PTR and external mail delivery; **P15** SMTP health | mail is live but external delivery is unverified; PTR still the provider's | provider (the hosting provider); blocks P19 |
| 15 | **P11** certificate renewal acceptance | dated: ERP, SSO, Drive, Respond expire **30 Jan 2027**; Office, Mail, DMS in February | do well before January |
| 16 | **P69** mail retention: keep every message, users cannot delete permanently (owner request) | data loss and compliance: today a user can delete company mail for good | Community edition chosen; isolated test passed 24 Nov (journal copy on all paths, permanent delete refused in webmail and IMAP, restore kept it); decided: 7 years max, administrator only, all mailboxes; on test since 24 Nov (draft PR #69); reader (a) on test incl. Authentik user; waiting: owner passkey for archive-reader, phone check; with P02/P40 backups, P17 and P19 |
| 17 | **P24** field attendance pilot and corrections | real workers waiting on acceptance | business rules for cancellation |
| 18 | **P43** tablet layout and touch check | tablets will be used (ONLYOFFICE touch is view-only) | test site |

**Tier 2: medium (planned, useful, not urgent)**

| Item | Note |
|---|---|
| **P50** native mobile app | strategic; planning only, many open decisions (look, security, notifications, build order); pilot is HR attendance |
| **P70** mail and WhatsApp domain split (`tenant.example` production, `example.com` demo) | owner decision 21 Nov; foundation of P19 and P63, taken up together; waits for the owner |
| **P63** demo mode for the test site (neutral UN/format brand, line-art landing page, no tenant traces; test mail and messages only to the test group) | UI released 21 Nov (PR #20, `6db2536`); rest paused by the owner: clean refreshed data, sign-in brand, test-group allow list, test/demo marker, vendor enrolment (decisions waiting in the item) |
| **P66** test-site errors invisible (Error Log rows stay queued) | flush the deferred inserts on test; alarm |
| **P68** check for imports of names that do not exist | static check plus "tests import the real module" |
| **P05**, **P06** GSTIN lookup and PAN checks | blocked on the India Compliance API secret and a PAN verification source |
| **P03** eKYC (Digio), **P04** WhatsApp | blocked on provider accounts; P04 also needs a Meta business number |
| **P51** data refresh at 8 pm; **P54** branch deploy button | P54 blocked until the first crippled refresh passes its audit; P51 owner said later |
| **P20** Paperless links on ERP transactions; **P21** correspondence register | needs agreed fields and roles |
| **P16**, **P17**, **P18** Raven attachments, Drive links for big mail attachments, mail client policy | P18 is a discussion first |
| **P09**, **P10**, **P14** fullscreen, desktop and phone sync, push acceptance | small to medium acceptance work on real devices; P14 follows P50 |
| **P26** banking and payroll sandbox | needs sandbox accounts; no live transfers |
| **P28** dual approval for super-administrator | owner deferred the model |
| **P31**, **P32**, **P07** keyboard navigation, native-module navigation, UI coverage | usability; P31 and P32 share design |
| **P41** quarterly recovery check | recurring: next due **18 Feb 2027** |
| **P40** remainder (offline USB copy, test VM settings backup, tailnet rule) | hardening; backups already live |
| **P35** presentation polish and upstream sharing | module READMEs, forum and tracker posts |

**Long-term plans** (category tag `**Category:** long-term plan` at the end of an item's tag line: ideas kept on record,
not ranked or scheduled; the owner decides if and when one starts)

| Item | Note |
|---|---|
| **P73** federated chat (Matrix or XMPP) in the mobile app, replacing Raven | owner idea 22 Nov; 26 Nov: replace Raven, chat built into the app; protocol comparison first |

**Tier 3: low or later**

| Item | Note |
|---|---|
| **P19** three Google mailboxes to Stalwart | after P12 is resolved; taken up with P70 and P63 |
| **P22** AI assistant | read-only first; provider and data policy undecided |
| **P29**, **P30**, **P48** Headscale, Technitium DNS, branch router | one chain, P48 depends on P29 and P30; nothing is broken today |
| **P46** TrueNAS NVR | one-camera trial started 26 Nov; hardware for more cameras after the trial |
| **P53** Desk widgets and universal search | **taken up 27 Nov:** the admin alerts widget (with P72), and help, notifications, search and sign-out moved from the apps to the Desk; the day-planning widgets stay **parked** |
| **P107** user support: "Report a problem" in the apps, and an admin support desk (Frappe Helpdesk proposed) | **parked by the owner** 27 Nov: take up later; no RustDesk, no paid tool; P103 first |

**Done, closed, redundant or irrelevant items** are not in the lists any more: see [the closed log](p-closed.md) (one line each; numbers are never reused).



<!-- APP-INDEX-BEGIN -->
## Work lists by app

Each P item lives in the list of the app it belongs to; items that address the platform or security in
general are in `general`. Numbers run across the whole project and never change. A new item goes into
its app's list (copy the `**App:**` line from a neighbour), then run `python3 tools/p_index.py`.

| App | List | Items | Not done |
|---|---|---|---|
| General | [pending/general.md](p-list/general.md) | 30 | 30 |
| DMS | [pending/dms.md](p-list/dms.md) | 1 | 1 |
| Drive | [pending/drive.md](p-list/drive.md) | 1 | 1 |
| Editor | [pending/editor.md](p-list/editor.md) | 3 | 3 |
| ERP | [pending/erp.md](p-list/erp.md) | 15 | 15 |
| Mail | [pending/mail.md](p-list/mail.md) | 6 | 6 |
| Mobile | [pending/mobile.md](p-list/mobile.md) | 9 | 9 |
| Portal (eZone) | [pending/portal.md](p-list/portal.md) | 4 | 4 |
| Raven and Insights | [pending/raven.md](p-list/raven.md) | 1 | 1 |
| Sign-in | [pending/signin.md](p-list/signin.md) | 8 | 8 |
| Test site | [pending/test-site.md](p-list/test-site.md) | 6 | 6 |

## All P items (index)

| P | Title | App | Also touches | State |
|---|---|---|---|---|
| P03 | Employee eKYC India | [ERP](p-list/erp.md) | none · **State:** blocked | blocked |
| P04 | WhatsApp onboarding and vendor/PO replies | [ERP](p-list/erp.md) | none · **State:** blocked | blocked |
| P05 | Live GSTIN lookup and form prefill | [ERP](p-list/erp.md) | none · **State:** blocked | blocked |
| P06 | PAN verification and automatic constitution deduction | [ERP](p-list/erp.md) | none · **State:** open | open |
| P07 | Remaining Frappe UI coverage review | [Portal (eZone)](p-list/portal.md) | erp, raven · **State:** open | open |
| P08 | Latest global logout and fresh passkey sign-in | [Sign-in](p-list/signin.md) | portal, erp, drive, mail, dms · **State:** in progress | in progress |
| P09 | Portal fullscreen toggle | [Portal (eZone)](p-list/portal.md) | none · **State:** open | open |
| P10 | Desktop/iPhone Drive and calendar/contact clients | [Drive](p-list/drive.md) | mail · **State:** open | open |
| P11 | Certificate issuance and renewal acceptance | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P12 | PTR and external mail delivery | [Mail](p-list/mail.md) | none · **State:** blocked | blocked |
| P13 | Remaining users, app permissions and worker enrollment | [General](p-list/general.md) | signin, mail, dms · **State:** in progress | in progress |
| P14 | Retained mobile/browser push acceptance | [Mobile](p-list/mobile.md) | erp, raven · **State:** open | open |
| P15 | Existing SMTP health alerts | [Mail](p-list/mail.md) | none · **State:** open | open |
| P16 | Raven attachments and Drive storage integration | [Raven and Insights](p-list/raven.md) | drive · **State:** open | open |
| P17 | Automatic Drive links for Mail attachments over 200 KB | [Mail](p-list/mail.md) | drive, dms · **State:** open | open |
| P18 | Allowed Mail clients and protocol access policy | [Mail](p-list/mail.md) | none · **State:** open | open |
| P19 | Three Google Workspace mailboxes to Stalwart | [Mail](p-list/mail.md) | general · **State:** open | open |
| P20 | Paperless document links on ERP transactions | [DMS](p-list/dms.md) | erp · **State:** open | open |
| P21 | Client/project correspondence register and DMS integration | [ERP](p-list/erp.md) | dms · **State:** open | open |
| P22 | Permission-controlled ERP AI assistant and business automation (Activepieces) | [ERP](p-list/erp.md) | raven, mail, drive, dms, general · **State:** open | open |
| P24 | Field attendance pilot and correction acceptance | [ERP](p-list/erp.md) | none · **State:** open | open |
| P25 | Invitation, passkey enrollment and recovery acceptance | [Sign-in](p-list/signin.md) | none · **State:** open | open |
| P26 | Banking and payroll provider sandbox acceptance | [ERP](p-list/erp.md) | none · **State:** blocked | blocked |
| P28 | Dual approval for ERP super-administrator access | [ERP](p-list/erp.md) | general · **State:** open | open |
| P29 | Self-hosted mesh VPN with Headscale and Headplane | [General](p-list/general.md) | none · **State:** open | open |
| P30 | Technitium filtered DNS for mesh devices and branch routers | [General](p-list/general.md) | none · **State:** open | open |
| P31 | Keyboard-first navigation to nested ERP/Frappe menus | [ERP](p-list/erp.md) | portal · **State:** open | open |
| P32 | Native-module integration and reversible add-on navigation | [ERP](p-list/erp.md) | none · **State:** open | open |
| P35 | Public release and upstream sharing | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P40 | Backup hardening against ransomware | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P41 | Owner recovery essentials (recurring) | [General](p-list/general.md) | none · **State:** recurring | recurring |
| P43 | Tablet layout and touch check (all apps) | [General](p-list/general.md) | portal, drive, editor, mail, dms · **State:** open | open |
| P45 | Production Drive, DMS, Mail and sign-in on the repository build | [General](p-list/general.md) | drive, dms, mail, signin · **State:** in progress | in progress |
| P46 | TrueNAS as network video recorder (NVR) | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P47 | Company website as the front door of the app portal | [Portal (eZone)](p-list/portal.md) | none · **State:** in progress | in progress |
| P48 | Remote branch router and gateway firewall | [General](p-list/general.md) | none · **State:** blocked | blocked |
| P49 | Bring production's sign-in pages and templates into the repository | [Sign-in](p-list/signin.md) | none · **State:** open | open |
| P50 | Native mobile app for phones and tablets (modules `mobile-app` and `mobile-native`) | [Mobile](p-list/mobile.md) | none · **State:** open | open |
| P51 | Data refresh runs at 8 pm, not on demand | [Test site](p-list/test-site.md) | none · **State:** open | open |
| P53 | Desk: day-planning widgets and dashboards from all apps | [Portal (eZone)](p-list/portal.md) | signin, mail, drive, dms · **State:** in progress | in progress |
| P54 | Branch deploy button for the "developer" group on the test site | [Test site](p-list/test-site.md) | none · **State:** blocked | blocked |
| P57 | The platform survives restarts and reboots without an outage | [General](p-list/general.md) | drive, mail, editor · **State:** in progress | in progress |
| P61 | Editor file safety: a document is never left unusable or its edits lost | [Editor](p-list/editor.md) | drive · **State:** in progress | in progress |
| P62 | Daily upstream watch: new releases, security flaws, patches, upgrade decisions | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P63 | Demo mode for the test site (`test.example.com`): neutral brand, no tenant traces | [Test site](p-list/test-site.md) | portal, signin, mail, erp · **State:** in progress | in progress |
| P64 | Native app sign-in on production: latent auth-hook crash and a stale client list | [Mobile](p-list/mobile.md) | signin, erp · **State:** in progress | in progress |
| P66 | Errors on the test site are invisible: Error Log rows stay queued | [Test site](p-list/test-site.md) | general, erp · **State:** open | open |
| P67 | Test deployments: one complete step, no hand-run pieces or drifting profiles | [General](p-list/general.md) | test-site · **State:** open | open |
| P68 | A repository check for imports of names that do not exist | [General](p-list/general.md) | none · **State:** open | open |
| P69 | Mail retention: keep every message, users cannot delete permanently | [Mail](p-list/mail.md) | general · **State:** open | open |
| P70 | Mail and WhatsApp domain split: `tenant.example` for production, `example.com` for the demo | [General](p-list/general.md) | mail, test-site, erp, signin · **State:** open | open |
| P71 | GitHub CI/CD and central secrets management: Actions deploy test and production; "Refresh code" button removed | [General](p-list/general.md) | test-site, erp, mail, drive, dms, signin · **State:** open | open |
| P72 | Monitoring and alerting: know when something breaks (on the TrueNAS, watched from outside) | [General](p-list/general.md) | erp, drive, mail, dms, signin, editor, test-site · **State:** open | open |
| P73 | Federated chat (Matrix or XMPP) in the mobile app, replacing Raven | [General](p-list/general.md) | mobile, raven, erp, signin · **State:** open · **Category:** long-term plan | open |
| P74 | Document and photo store in the mobile app (Drive / oCIS) | [Mobile](p-list/mobile.md) | drive, erp, signin · **State:** in progress | in progress |
| P76 | Owner's passkey sign-in on the test site | [Sign-in](p-list/signin.md) | test-site · **State:** in progress | in progress |
| P77 | First administrator chosen at setup; built-in `akadmin` switched off | [Sign-in](p-list/signin.md) | test-site · **State:** in progress | in progress |
| P78 | Invitation link attempts chosen by the administrator | [Sign-in](p-list/signin.md) | none · **State:** in progress | in progress |
| P79 | Approved passkey providers as one setting | [Sign-in](p-list/signin.md) | test-site · **State:** in progress | in progress |
| P80 | Editor stays registered with Drive after every Drive restart | [Editor](p-list/editor.md) | drive, general · **State:** open | open |
| P81 | Editor follow-ups: Compose safety net and release rule | [Editor](p-list/editor.md) | drive, general · **State:** open | open |
| P82 | ERP Mobile holds the passkeys; one phone and one computer session per user | [Sign-in](p-list/signin.md) | mobile, portal, erp, test-site · **State:** open | open |
| P85 | Unformat brand public as the default; client brands supplied privately | [General](p-list/general.md) | portal, mobile, erp, signin · **State:** in progress | in progress |
| P86 | Personal business files in the app, with a quota per user | [Mobile](p-list/mobile.md) | drive, erp, signin · **State:** open | open |
| P87 | Camera videos in the mobile app (Frigate) | [Mobile](p-list/mobile.md) | general, signin · **State:** open | open |
| P88 | Project camera sites connected to the NVR over the mesh | [General](p-list/general.md) | mobile · **State:** open | open |
| P89 | Register of our changes to upstream apps, and an upgrade checklist | [General](p-list/general.md) | erp, portal, signin, drive, editor, mail, dms, raven, mobile · **State:** in progress | in progress |
| P90 | Traefik security upgrade: pin Coolify's proxy to 3.7.20 | [General](p-list/general.md) | none · **State:** in progress | in progress |
| P91 | Upgrade checks that cannot miss a changed upstream file; upstream watch gaps | [General](p-list/general.md) | erp, editor, mail, signin, drive, dms · **State:** in progress | in progress |
| P92 | Out-of-date Collabora material, ONLYOFFICE version, WhatsApp entry, hosting provider's name | [General](p-list/general.md) | editor, drive · **State:** in progress | in progress |
| P93 | "Request response" button missing on Job Offer | [ERP](p-list/erp.md) | general · **State:** in progress | in progress |
| P94 | Bring production stacks back in line with main | [General](p-list/general.md) | editor, signin, portal, test-site · **State:** open | open |
| P95 | Face recognition for field team attendance | [ERP](p-list/erp.md) | mobile, signin, test-site · **State:** in progress | in progress |
| P96 | SOPs for every manual procedure, written alongside the build | [General](p-list/general.md) | signin, mobile, erp, portal, drive, editor, mail, dms, raven, test-site · **State:** in progress | in progress |
| P100 | Mobile app checks in CI, and the app's dependencies in the daily watch | [Mobile](p-list/mobile.md) | general · **State:** open | open |
| P101 | Test Drive, test Paperless, test mail and the test editor sign in through the test sign-in server | [Test site](p-list/test-site.md) | signin, drive, dms, mail, editor · **State:** open | open |
| P102 | Admin tools: single sign-on by default, the tailnet as the backup door | [General](p-list/general.md) | signin, test-site · **State:** open | open |
| P103 | Request ID on every app action, and "what happened to my request" | [ERP](p-list/erp.md) | mobile · **State:** open | open |
| P104 | Version handshake between the server and the mobile apps | [ERP](p-list/erp.md) | mobile · **State:** open | open |
| P105 | Test site ready for the native app's five-phone test round | [Test site](p-list/test-site.md) | erp, signin, mobile · **State:** blocked | blocked |
| P106 | Short video clips with site incidents | [Mobile](p-list/mobile.md) | drive, erp · **State:** open | open |
| P107 | User support: "Report a problem" in the apps, and an admin support desk | [General](p-list/general.md) | erp, mobile, portal, signin · **State:** parked | parked |
| P108 | Remove Raven from ERPNext; all messages through our own channels | [General](p-list/general.md) | raven, mail, mobile, portal, signin, general · **State:** open | open |
| P109 | A light mail client in the phone app (JMAP) | [Mobile](p-list/mobile.md) | mail, signin · **State:** open · **Category:** now | open |
<!-- APP-INDEX-END -->
