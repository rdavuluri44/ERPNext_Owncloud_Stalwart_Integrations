# P list: roadmap and work items

> **Generated file: do not edit by hand.** This is the project's work list (every "P" number used in
> commits, pull requests, READMEs and `docs/decisions.md`) published from the maintainers' private
> list on 21 November 2026, with every line kept. Only these categories are replaced, by placeholders: the
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
| 1 | **P61** editor file safety | production business data: a shared workbook became unusable and edits were parked unsaved (20 Nov); owner request | start with the unstick and rescue tool; relates to P57, P59 |
| 2 | **P59** promotion plan and drift check | a stack was missed in the 21 Nov promotion; prevents repeats | none; do before the next multi-stack release |
| 3 | **P57** survive reboots (PR #7 open) | production lost Drive editor, proxy entry point and Mail sign-in after one reboot | add the Stalwart reload step; reboot drill on test; no production reboot as a test |

**Tier 1: high (business-critical, next)**

| Rank | Item | Why | Depends on / note |
|---|---|---|---|
| 4 | **P62** daily upstream watch (releases, security flaws, upgrade advice) | security: new flaws and fixes reach us only by chance today; advice only, no automatic upgrades | none; baseline first, dry-run a week; owner may place it higher |
| 5 | **P64** native app sign-in on production: latent auth-hook crash, stale client list | production defect (dormant today); fix tested on test | merge PR #15, ERP release |
| 6 | **P67** test deployments as one complete step (gateway, profiles, setup) | hand-run steps and profile drift found installing PR #15 | with P54, P59 |
| 7 | **P49** sign-in pages and templates into the repository (finishes P45) | a claim-name mismatch already caused an ERP sign-in outage (20 Nov); authentik settings (JIT, memory, brand, flows) live only in its database | P45 remainder; rehearse on test |
| 8 | **P08** global logout and fresh passkey, end to end | security acceptance; parts verified 21 Nov (logout ends the session; passkey is asked, Bitwarden answers silently) | owner checks each app as initiator |
| 9 | **P13** remaining users, permissions, worker enrollment | adoption: 10 of about 20 users | P25 |
| 10 | **P25** invitation, passkey enrollment and recovery acceptance | needed before more users join; lost-device recovery untested | real SMTP and devices |
| 11 | **P12** PTR and external mail delivery; **P15** SMTP health | mail is live but external delivery is unverified; PTR still the provider's | provider (the hosting provider); blocks P19 |
| 12 | **P11** certificate renewal acceptance | dated: ERP, SSO, Drive, Respond expire **30 Jan 2027**; Office, Mail, DMS in February | do well before January |
| 13 | **P69** mail retention: keep every message, users cannot delete permanently (owner request) | data loss and compliance: today a user can delete company mail for good | paused by the owner; mechanism checked, one decision waiting in the item; with P02/P40 backups and P19 |
| 14 | **P24** field attendance pilot and corrections | real workers waiting on acceptance | business rules for cancellation |
| 15 | **P43** tablet layout and touch check | tablets will be used (ONLYOFFICE touch is view-only) | test site |

**Tier 2: medium (planned, useful, not urgent)**

| Item | Note |
|---|---|
| **P50** native mobile app | strategic; planning only, many open decisions (look, security, notifications, build order); pilot is HR attendance |
| **P70** mail and WhatsApp domain split (`tenant.example` production, `example.com` demo) | owner decision 21 Nov; foundation of P19 and P63, taken up together; waits for the owner |
| **P63** demo mode for the test site (neutral UN/format brand, line-art landing page, no tenant traces; test mail and messages only to the test group) | UI on test (branch `p63-demo-ui`); rest paused by the owner: clean refreshed data, sign-in brand, test-group allow list, test/demo marker, vendor enrolment (decisions waiting in the item) |
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
| **P23** PWA offline | audit first |
| **P41** quarterly recovery check | recurring: next due **18 Feb 2027** |
| **P40** remainder (offline USB copy, test VM settings backup, tailnet rule) | hardening; backups already live |
| **P35** presentation polish and upstream sharing | module READMEs, forum and tracker posts |

**Tier 3: low or later**

| Item | Note |
|---|---|
| **P19** three Google mailboxes to Stalwart | after P12 is resolved; taken up with P70 and P63 |
| **P22** AI assistant | read-only first; provider and data policy undecided |
| **P29**, **P30**, **P48** Headscale, Technitium DNS, branch router | one chain, P48 depends on P29 and P30; nothing is broken today |
| **P46** TrueNAS NVR | hardware and selection first |
| **P53** Desk widgets and universal search | **parked by the owner**: do not start |

**Done, closed, redundant or irrelevant items** are not in the lists any more: see [the closed log](p-closed.md) (one line each; numbers are never reused).



<!-- APP-INDEX-BEGIN -->
## Work lists by app

Each P item lives in the list of the app it belongs to; items that address the platform or security in
general are in `general`. Numbers run across the whole project and never change. A new item goes into
its app's list (copy the `**App:**` line from a neighbour), then run `python3 tools/p_index.py`.

| App | List | Items | Not done |
|---|---|---|---|
| General | [pending/general.md](p-list/general.md) | 17 | 17 |
| DMS | [pending/dms.md](p-list/dms.md) | 1 | 1 |
| Drive | [pending/drive.md](p-list/drive.md) | 1 | 1 |
| Editor | [pending/editor.md](p-list/editor.md) | 1 | 1 |
| ERP | [pending/erp.md](p-list/erp.md) | 11 | 11 |
| Mail | [pending/mail.md](p-list/mail.md) | 6 | 6 |
| Mobile | [pending/mobile.md](p-list/mobile.md) | 4 | 4 |
| Portal (eZone) | [pending/portal.md](p-list/portal.md) | 4 | 4 |
| Raven and Insights | [pending/raven.md](p-list/raven.md) | 1 | 1 |
| Sign-in | [pending/signin.md](p-list/signin.md) | 3 | 3 |
| Test site | [pending/test-site.md](p-list/test-site.md) | 4 | 4 |

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
| P11 | Certificate issuance and renewal acceptance | [General](p-list/general.md) | none · **State:** open | open |
| P12 | PTR and external mail delivery | [Mail](p-list/mail.md) | none · **State:** blocked | blocked |
| P13 | Remaining users, app permissions and worker enrollment | [General](p-list/general.md) | signin, mail, dms · **State:** in progress | in progress |
| P14 | Retained mobile/browser push acceptance | [Mobile](p-list/mobile.md) | erp, raven · **State:** open | open |
| P15 | Existing SMTP health alerts | [Mail](p-list/mail.md) | none · **State:** open | open |
| P16 | Raven attachments and Drive storage integration | [Raven and Insights](p-list/raven.md) | drive · **State:** open | open |
| P17 | Automatic Drive links for Mail attachments over 200 KB | [Mail](p-list/mail.md) | drive · **State:** open | open |
| P18 | Allowed Mail clients and protocol access policy | [Mail](p-list/mail.md) | none · **State:** open | open |
| P19 | Three Google Workspace mailboxes to Stalwart | [Mail](p-list/mail.md) | general · **State:** open | open |
| P20 | Paperless document links on ERP transactions | [DMS](p-list/dms.md) | erp · **State:** open | open |
| P21 | Client/project correspondence register and DMS integration | [ERP](p-list/erp.md) | dms · **State:** open | open |
| P22 | Permission-controlled ERP AI assistant | [ERP](p-list/erp.md) | none · **State:** open | open |
| P23 | PWA offline and poor-connectivity behavior | [Mobile](p-list/mobile.md) | portal · **State:** open | open |
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
| P46 | TrueNAS as network video recorder (NVR) | [General](p-list/general.md) | none · **State:** open | open |
| P47 | Company website as the front door of the app portal | [Portal (eZone)](p-list/portal.md) | none · **State:** in progress | in progress |
| P48 | Remote branch router and gateway firewall | [General](p-list/general.md) | none · **State:** blocked | blocked |
| P49 | Bring production's sign-in pages and templates into the repository | [Sign-in](p-list/signin.md) | none · **State:** open | open |
| P50 | Native mobile app for phones and tablets (module `mobile-app`) | [Mobile](p-list/mobile.md) | none · **State:** open | open |
| P51 | Data refresh runs at 8 pm, not on demand | [Test site](p-list/test-site.md) | none · **State:** open | open |
| P53 | Desk: day-planning widgets and dashboards from all apps | [Portal (eZone)](p-list/portal.md) | signin, mail, drive, dms · **State:** parked | parked |
| P54 | Branch deploy button for the "developer" group on the test site | [Test site](p-list/test-site.md) | none · **State:** blocked | blocked |
| P57 | The platform survives restarts and reboots without an outage | [General](p-list/general.md) | drive, mail, editor · **State:** in progress | in progress |
| P59 | Promotion plan and drift check: no stack left behind | [General](p-list/general.md) | none · **State:** open | open |
| P61 | Editor file safety: a document is never left unusable or its edits lost | [Editor](p-list/editor.md) | drive · **State:** in progress | in progress |
| P62 | Daily upstream watch: new releases, security flaws, patches, upgrade decisions | [General](p-list/general.md) | none · **State:** open | open |
| P63 | Demo mode for the test site (`test.example.com`): neutral brand, no tenant traces | [Test site](p-list/test-site.md) | portal, signin, mail, erp · **State:** in progress | in progress |
| P64 | Native app sign-in on production: latent auth-hook crash and a stale client list | [Mobile](p-list/mobile.md) | signin, erp · **State:** in progress | in progress |
| P66 | Errors on the test site are invisible: Error Log rows stay queued | [Test site](p-list/test-site.md) | general, erp · **State:** open | open |
| P67 | Test deployments: one complete step, no hand-run pieces or drifting profiles | [General](p-list/general.md) | test-site · **State:** open | open |
| P68 | A repository check for imports of names that do not exist | [General](p-list/general.md) | none · **State:** open | open |
| P69 | Mail retention: keep every message, users cannot delete permanently | [Mail](p-list/mail.md) | general · **State:** open | open |
| P70 | Mail and WhatsApp domain split: `tenant.example` for production, `example.com` for the demo | [General](p-list/general.md) | mail, test-site, erp, signin · **State:** open | open |
<!-- APP-INDEX-END -->
