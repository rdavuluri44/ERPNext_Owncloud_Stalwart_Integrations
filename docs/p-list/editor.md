# Editor: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Editor: P items

ONLYOFFICE Docs: the document and spreadsheet editor behind Drive, private sheet views, file safety.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P61 — Editor file safety: a document is never left unusable or its edits lost

**App:** editor · **Also touches:** drive · **State:** in progress

**Status:** open, owner request 21 November 2026 ("account for all scenarios that
happened and might happen and make sure that a file is never left in this position");
**priority: highest (production business data).** Not started. Incident record:
21 November shared-workbook incident (private record).

**What happened (evidence, UTC, 20 November):** `<shared register workbook>` (Drive
space Acts) worked until about 16:00 IST. 10:46:54 last good save of the old copy. At
11:03:55 ONLYOFFICE's save to Drive (WOPI PutFile) returned HTTP 500 (the cause is
unknown: the Drive and collaboration logs of that hour were erased when those
containers were recreated at 12:17 for the P56 release) and the unsaved edits were parked as
"forgotten". From 11:07 the editor failed to apply stored edits (`changesError: Cannot
read properties of null`), again at 11:35, 11:57 to 12:00 and 12:54 to 13:15. The file
was deleted and re-uploaded at 11:05:59 and again at 11:33:53 (each upload made DMS link
files), saves worked 11:06 to 12:56, and nothing was saved after 12:56:45, so the owner's
manual deletion of views never persisted and the views "came back". The 40 empty
"Temporary View" entries are old (present in the first saved version of 18 November
09:39, before ONLYOFFICE went live, so Collabora-era leftovers) and did not grow in the
ONLYOFFICE period; they are not the cause. A second parked file (a different small
workbook, 3 sheets) holds edits that never reached Drive: copy in
`<rollback folder>` on production, owner to say whose it is.

**Update 25 November 2026 (read-only debug):** the same workbook's document (ONLYOFFICE key used since
20 Nov 11:32 UTC) still raised `changesError` after the 21 Nov guard: 23 Nov 12:40 (`reading 'c'` of null) and
24 Nov 05:41 to 08:28 UTC (7 x `reading 'Tm'` of undefined, 1 x `'c'`, 1 x `waitAuth`), from two people's sessions.
`Tm` is the editor's get-index method of a sheet or sheet view, so a change from one person referred to a sheet or view
the other person's copy did not have (scenario 12). Saving was **not** affected: Drive kept a version every few minutes
all through, and nothing was parked as forgotten. The server log has no client stack, so the exact code path is not
proven. Also found: the editor-page changes of PR #34 (view cap) and PR #42 (retry keeper), merged 23 Nov, are not on
production (it runs `2c542f0`) and are not in the release records; `tools/editor_safety.py` is not installed on
production. Next steps proposed in the 25 Nov handover.

**Owner decision (26 November 2026): option A, private sheet views stay on for everyone.** Production check the same
day (read-only): no `changesError`, no forgotten file and no failed save logged since 24 November 08:28 UTC, while 15
documents were edited on 25 November and 84 on 26 November (editor cache folders). This shows the problem has not
returned, not that its cause is gone: it needed two people in the same workbook at once. If it returns, switch the
views off for that file only (option C) until the fix. **Item stays open (owner) for the test-site work:** reproduce
the two-person case with a synthetic workbook, make the editor page log the full error stack, then release PR #34 and
#42 with the P61 safety tool (test first, then production).

**Scenarios (seen = happened to us) and the safeguard for each**

| # | Scenario | Seen | Safeguard |
|---|---|---|---|
| 1 | Save to Drive fails (PutFile 500, proof keys, WOPI lock conflict, oCIS busy), edits parked in "forgotten" | yes | alarm within minutes on `PutFile error` / `storeForgotten`; **rescue job** copies every forgotten file to a recovery folder and tells the owner; root cause logged |
| 2 | Editor cannot apply stored edits (`changesError` null reference), file cannot be opened or edited | yes | `editor_unstick` tool: force save, rescue forgotten, drop the stuck document key through ONLYOFFICE's command service (JWT), reopen check; runbook for people |
| 3 | Edits made but never saved, so deletions "come back" | yes | save-health probe (below) and a visible "not saved" alert path; document the symptom |
| 4 | Diagnosis impossible because container logs vanish on recreate | yes | archive logs before any recreate (P59 promotion plan pre-step) and keep rotated logs on disk for 30 days |
| 5 | Users re-upload or delete the file as a workaround (duplicates, DMS link files, lost history) | yes | runbook "file will not open: do not delete"; versions are restored from Drive's version list; rescue tool covers the rest |
| 6 | Planned or unplanned restart of ONLYOFFICE, the editor bridge, Drive or the host with people editing | yes (reboot 20 Nov) | pre-restart **force save** of every open document; P57 post-boot check also opens and saves a probe document; Stalwart/editor bridge checks already in P57 |
| 7 | Silent breakage of saving after a release, certificate, proof-key or network change | partly | **synthetic save probe** (headless browser opens a probe workbook through Drive, edits, saves, checks that a new version appears) after every promotion and every 15 minutes; failure pages the owner |
| 8 | Private sheet views multiply in a shared workbook (old automation could loop) | no evidence on this file; reproduced in simulation | PR #12 (one attempt per person and sheet), plus a cap: never create when a sheet already has many views; one-off cleaner for legacy "Temporary View" shells (done by hand for the shared workbook) |
| 9 | Disk or cache full on the ONLYOFFICE or Drive volumes (document cache was 255 MB and is never pruned) | no | disk and cache alert at 80 percent, scheduled cache prune of closed documents |
| 10 | File corruption, bad macro or manual edit, huge file slowness | no | Drive keeps every save as a version (27 in two hours here) and the nightly backup covers Drive; restore drill already passes (P39); runbook for restoring one file |
| 11 | Two editors with different page versions (browser cached the old start page) | possible | versioned start-page URL and a restart of the editor with every promotion (P59 plan step) |
| 13 | Stored sheet views the editor cannot read (empty filters in a Private view): blank grid, `changesError` null reference, file cannot be used | yes (the shared workbook, 20-21 Nov) | sanitiser that strips unreadable view data (part of the unstick tool and run before each file is opened by the automation); decide with the owner whether the private-view automation stays on, is limited, or is paused until the cause is proven; test on the test site with two users and filters |
| 12 | Changes to sheet-view or sheet structure by one person break the other person's open session | suspected (null reference on views) | after the legacy views are cleaned, repeat the two-person test on test; keep the editor start page minimal |

**Build order (each item is a normal branch, test, merge, production):** (a) the
unstick-and-rescue tool and runbook; (b) log archiving before recreation (with P59);
(c) alarms on the editor and Drive logs plus the forgotten-file rescue job (systemd
timer, like the P57 host checks); (d) the synthetic save probe; (e) pre-restart force
save; (f) cache and disk alerts; (g) PR #12 and the view cap. Related: P57, P59, P42.
**Honest limit:** nothing guarantees that a save never fails; the aim is that a failure
is seen within minutes, no edit is lost, and a stuck file is recoverable without deleting
it.

### P80 — Editor stays registered with Drive after every Drive restart

**App:** editor · **Also touches:** drive, general · **State:** open

**Status:** open, owner go 25 November 2026 ("A, B and D together as one P item"). Not started.
Incident: release log, 25 November "office files only download in Drive"; receipt
`production-editor-bridge-restart-20261125`.

**Why:** Drive (oCIS 8.2.3) learns which editors exist only when the editor bridge
(`collaboration`) starts and registers. When `ocis` is recreated or restarted alone,
office files offer only a download until the bridge is restarted. On 25 Nov this cut
editing on production for about 6.5 hours after the P74 window. The nightly backup
starts both together, and the bridge's first registration failed on 24 and 25 Nov
(Docker's restart policy recovered it).

**Scope (one branch, tested and released together):**
- **A. One shared "restart Drive" step.** A small versioned helper that recreates or
  starts `ocis`, waits until healthy, restarts `collaboration`, then checks the
  bridge's log for registration errors and runs the check in D. Every release window,
  its recover branch and the test deploy script use it. The test deploy script
  (today host-private, not in Git) moves into the private repository.
- **B. Backup start order.** `integrations/backup/backup.py` `stop_and_copy` starts
  the group's containers in order: `ocis` first, waits for healthy (bounded), then
  `collaboration`, and still always restarts everything on failure. Public module
  change with unit tests.
- **D. A check that can see a missing editor.** Signed-in check that ONLYOFFICE is in
  Drive's app list, using a dedicated low-rights Drive account whose token stays on the
  server. Runs in the P57 host checks every 5 minutes and after every release and
  backup, and alerts the owner. First step of P61 (d), the open-and-save probe.

**Acceptance:** on the test site: (1) recreate `ocis` alone with the helper, and the
editor opens a document right after; (2) recreate `ocis` without the helper, and the
check in D alerts within 5 minutes; (3) a backup run leaves the bridge registered with
no `AddAppProvider failed` or NATS errors, three runs in a row; (4) unit tests for the
start order and the check pass in CI. Then production via the normal release, with a
browser check of one document and one spreadsheet right after.

**Depends on / relates to:** P57 (host checks), P59 (promotion plan), P61 (d), P72
(monitoring alerts). Follow-up: P81.

**Public #76 brought up to date with main (27 November 2026): `92b41fe`, CI passed.** Main's reboot comparison and
alert mail (P57) and this item's editor check are both kept in `tools/host_check.py`. The earlier test-host evidence
(`c68db04`) predates the combined file, so **a retest on the test host is needed before merge**.

### P81 — Editor follow-ups: Compose safety net and release rule

**App:** editor · **Also touches:** drive, general · **State:** open

**Status:** open, owner 25 November 2026 ("then C and E"); after P80.

- **C. Compose safety net:** add `restart: true` to the bridge's `depends_on: ocis` in
  the Drive template, so Compose restarts the bridge whenever it recreates `ocis`. Test
  first on the test VM whether it also applies with `up --no-deps` as our scripts use;
  keep it as a safety net beside P80 A, not a replacement.
- **E. Release rule:** a Drive or editor change is not done until a document has been
  opened right after the window (agent's headless browser on a test account, or the
  owner). "Not covered" for that check blocks calling the release done. Goes into the
  promotion README and the P59 plan template.
- **F (when convenient):** check oCIS issues for the registration behaviour and report
  it upstream if it is not known.
