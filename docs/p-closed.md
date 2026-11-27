# Closed P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 27 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](p-list.md) for the rules).

# Closed P items

P items leave their app list when the task is completed, or becomes redundant or irrelevant (owner rule,
21 November 2026). Each leaves one line here so its number is never reused. The full text is in the git history
of `docs/pending/`; what was done is in the release log and `docs/decisions.md`. To reopen work, add a new
item with a new number that refers to the old one.

| P | Title | App | Outcome | Date | Reason |
|---|---|---|---|---|---|
| P27 | Collabora Calc search-based AutoFilter | editor | closed | 2026-11-19 | Obsolete: Collabora replaced by ONLYOFFICE (P42) and retired; ONLYOFFICE has its own filter search |
| P34 | Automatic private sheet views in Collabora Calc | editor | superseded | 2026-11-19 | Private sheet views now come from the ONLYOFFICE start page (P42, editor list) |
| P42 | Replace Collabora with ONLYOFFICE | editor | completed | 2026-11-19 | ONLYOFFICE on production since 18 Nov (release a135fd4); Collabora retired 19 Nov |
| P37 | Move production ERP onto the repository-built deployment | erp | completed | 2026-11-18 | Production ERP on the repository build since 18 Nov (release 3a92645) |
| P02 | Off-server backups and restore test | general | completed | 2026-11-18 | Nightly encrypted off-server backups, weekly drill and restore rehearsals live since 18 Nov; hardening remainder is P40 |
| P36 | Modular repository layout at the TrueNAS rebuild | general | completed | 2026-11-17 | Module manifest and READMEs done 17 Nov; the P list is now organised by app |
| P39 | Full restore rehearsal on the old VPS (done) | general | completed | 2026-11-18 | Full restore rehearsal from backup passed 18 Nov (about 24 minutes of machine time) |
| P55 | Replace the old logo everywhere with the approved one | general | completed | 2026-11-20 | Approved logo and favicons live 20 Nov (792cef8); demo brand for the test site is P63 |
| P38 | Colleague's mobile app: test-only access and safe contributions | mobile | closed | 2026-11-20 | Closed by the owner: the owner builds the app (P50); the colleague contributes by pull request |
| P01 | Idle menus and real-time connection recovery | portal | completed | 2026-11-18 | Idle-menu and realtime recovery live since the P37 move; owner idle test passed; a new item if freezes return |
| P52 | "All Apps" menu item keeps coming back (bake the removal into the repository) | portal | completed | 2026-11-20 | "All apps" removal built into the repository, live 20 Nov (792cef8) |
| P58 | Next ERP release: favicon B in the ERP image; two-column app menu | portal | completed | 2026-11-21 | Favicon B and the two-column app menu live 21 Nov (3a93de8) |
| P44 | Sign-in (authentik) as a repository stack | signin | completed | 2026-11-19 | Identity stack proven restorable 19 Nov; moving production sign-in onto it is P49 |
| P56 | Logging out of any app lands on the website | signin | completed | 2026-11-20 | Logout lands on the website, one passkey prompt: live 20 Nov (792cef8); framed sign-out fix 21 Nov |
| P56 | Logout ends on the website; one passkey prompt; portal keeps its name | signin | completed | 2026-11-20 | Logout lands on the website, one passkey prompt: live 20 Nov (792cef8); framed sign-out fix 21 Nov |
| P33 | Move the permanent test site to a TrueNAS VM and retire the old VPS | test-site | completed | 2026-11-19 | Test site on the TrueNAS VM since 17 Nov; old VPS retired 19 Nov |

## History notes (moved from the list on 21 November 2026)

### Legacy status groups (16 November 2026 list)

The list used to be grouped by status instead of by app. Where each group's items went:

- **Explicitly deferred:** P01, P02
- **Implementation still due:** P03, P04, P05, P06, P07
- **Deployed, but final acceptance still due:** P08, P09, P10, P11, P12, P13, P14, P15
- **Carried-forward development and decisions:** P16, P17, P18, P19, P20, P21, P22, P23, P24, P25, P26
- **Audit disposition (completed requests, no action):** P27, P28, P29, P30, P31, P32, P33, P35, P36, P34, P38, P42, P39, P45, P49, P50, P51, P52, P53, P54, P55, P56, P57, P56, P58, P59, P60, P61, P62, P63, P46, P47, P48, P44, P43, P40, P41, P37

### Audit disposition

The following requests are complete and are **not pending upgrade/implementation jobs**: core Frappe/ERPNext/HR upgrade; production ERP/SSO consolidation on the new controller; old application/test retirement; Onboarding migration/name/O icon; sole noreply integration sender; final portal and native Desk menu layout/alignment/dividers; Drive/Collabora address mapping; compact TXT/Markdown headers; editor button color matching and outside-click dismissal; Microsoft office-format creation choices; public authenticated Mail with private administration; webmail file-storage disablement; common user sign-in group and Drive client display names.

Current production versions: **Frappe 16.56.0, ERPNext 16.55.0, HRMS 16.53.2**. The installed-app table and the retained feature details are in the [current handover](retained.md).

Only the current retained requests are included here; superseded historical proposals are excluded.
| P65 | Relayed test sign-in loses the requested page (X-Forwarded-Uri dropped) | test-site | completed | 2026-11-21 | Forwarded headers trusted on the SSO host's private entry point from the test VM only; live 21 Nov (942d84d); test gateway returns to the requested page |
| P60 | Portal address `/ezone` instead of `/place_holder` | portal | redundant | 2026-11-21 | Owner chose the portal at / once signed in (P63): the address is clean without renaming the page |
| P75 | Stalwart 1.1.0 to 1.1.1 (security fixes) before P69 | mail | completed | 2026-11-24 | Released to production 24 Nov (bb546d7) |
| P83 | authentik 2026.8.7 security fixes | signin | completed | 2026-11-26 | authentik 2026.8.7 on test and production 26 Nov; owner browser check passed |
| P23 | PWA offline and poor-connectivity behavior | mobile | superseded | 2026-11-26 | Owner 26 Nov 2026: no PWA offline work; offline capture is built in the native app (P50, with P14, P64, P74, P82) |
| P84 | Client identity out of the public repository, and a check that keeps it out | general | completed | 2026-11-26 | Fingerprint check in CI (PR #84, merge 3fbdd9f); client name removed from the public code; test worker profile reads the client's mail domain privately |
| P59 | Promotion plan and drift check: no stack left behind | general | completed | 2026-11-26 | Promotion plan, drift check, served-content checks, container log archiving and no forced image cleanup live on production (PR #35, #62, #92); stack releases continue in P94 |
| P97 | Uploaded files that can run script are always downloaded (GHSA-94mh-qq29-qwrf) | erp | completed | 2026-11-26 | Upstream's forced-download rule (any case, 14 file types) in our ERP web server template, GHSA-94mh-qq29-qwrf (PR #103, merge bf8d5c8); on test and production since 26 Nov 2026 (one mounted file; receipts and release log); owner's browser check passed. The drift check cannot see mounted files and still lists the template: P99. Rest of upstream's template changes: P98. |
| P99 | Drift check sees mounted runtime files, not only image tags and notes | general | completed | 2026-11-26 | The drift check compares every read-only mounted runtime file with main (equal, behind, changed by hand, not compared), records are written at deployment and by a record command; the nightly run uses main's code (PR #111, merge c4872e3); on production since 26 Nov 2026; P97's file recorded; five stacks re-linked after a render comparison. |
| P98 | ERP web server template: take up upstream's trusted-HTTPS forwarding changes | erp | completed | 2026-11-27 | Part A: the ERP web server clears X-Forwarded-SSL and X-Forwarded-Protocol as upstream (PR #115, merge cbe976c), on test and production since 26 Nov 2026; part B (upstream's trusted-forwarding switch, set to on) is a re-apply step at the next frappe_docker bump in register BUILD-2, guarded by a test (owner: close now). |
