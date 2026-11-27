# Standard operating procedures (SOPs)

Every step the system relies on a **person** to do or check, because no code enforces it, has a written SOP here
(P96; working agreements, 26 November 2026). SOPs are written alongside the build, not after it.

- **One SOP per procedure**, written for **roles**, never for named people: purpose, who, when, what is checked, what
  is recorded and where, and what to do when it goes wrong. Use the [template](#template) below.
- **Public here, private companion:** client names, site names, host names, live object names, accounts and contacts
  go in the private operations repository's companion, not here. A public SOP says "see the private companion" at
  the step that needs them.
- **Kept current:** a change that adds or alters a manual step updates its SOP in the same pull request; a design
  decision that creates one names the SOP to be written. An SOP describes what is **live**; a step that is decided
  but not built is marked *draft, applies when built*.
- **Design decisions describe use** (owner, 26 November 2026): when a decision says how people will use the
  system (who does what, on which device, what they see, what happens when it goes wrong), it is written into the
  SOPs in the same change, without waiting to be asked: the picture by role in
  [How we use the system](how-we-use-the-system.md), and the steps in the procedure concerned.

**Start here:** [How we use the system](how-we-use-the-system.md) (sign-in, ERP Mobile and attendance, by role).

## Inventory (study of 26 November 2026)

Built from the decision log, the P list, the module READMEs, the runbooks and the private records. **Status:**
*in use* (people do it today), *partly* (some of it, or on test only), *designed* (decided, not built), *gap*
(referred to but never described). **SOP:** a link once written; otherwise still to write. **Private:** needs a
private companion.

### A. Sign-in and identity

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| A1 | Invite a new user (approved group, 1–5 attempts, approved passkey provider) | admin | new person | in use | [invite a user](invite-a-user.md) | yes |
| A2 | Lost-passkey recovery: the project manager checks the phone in person and confirms, then the admin invites | project manager, admin | lost device or passkey | in use | [invite a user](invite-a-user.md) (recovery part) | yes |
| A3 | Administrator bootstrap and the owner's emergency sign-in link | owner, operator | fresh instance, lockout | in use | — | yes |
| A4 | Group membership, including the Apple exception group | admin; owner decides the exception group | joiner, role change, review | in use | — | yes |
| A5 | Change the approved passkey providers | operator via PR, owner go | policy change | in use | — | yes |
| A6 | Admin impersonation (reason, logging) | admin | service account set-up | in use, not described | — | yes |
| A7 | Joiner access app by app (ERP roles, site membership, mailbox, Drive and DMS first sign-in) | admin | joiner | partly | — | yes |
| A8 | Sign-in and logout acceptance after a sign-in or ERP deploy | owner | every such deploy | in use | — | yes |
| A9 | Onboarding in ERP Mobile: identity check, then admin approval (P82) | project manager, admin | "Request access" | designed | [onboarding](onboarding-identity-and-biometrics.md) | no |
| A10 | Only the person's own fingerprints and face on the phone; confirmation in the app (proposal) (P82) | project manager, employee | onboarding | designed | [onboarding](onboarding-identity-and-biometrics.md) | no |
| A11 | Re-onboarding after a 5-miss erase, or a new, lost or replacement phone (P82) | employee, project manager, admin | lockout, phone change | designed | [onboarding](onboarding-identity-and-biometrics.md) | no |
| A12 | Device and session review (phones and computers); unused-key grace days per group (P82) | admin | periodic, leavers | designed | — | no |
| A13 | Dual approval for super-administrator access (P28) | two approvers | before privileged sessions | designed | — | yes |
| A15 | Handling alerts about sign-ins from unusual places or networks; marking office and site networks as usual (P82) | admin | on each alert | designed | [admin alerts](admin-alerts-and-daily-checks.md) | yes |
| A14 | Leaver offboarding across every app; the Frappe HR exit procedure triggers key removal and purges the app data (owner, 26 Nov) | HR, admin | person leaves | designed | [leavers](leaver-offboarding.md) (draft) | yes |

### B. Mobile app and devices

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| B1 | Build, sign and distribute the app (and signing-key custody) | maintainer, owner go | each release | designed; key custody a gap | — | yes |
| B2 | Photo-store Drive account and its token renewal | operator | set-up, renewal failure | in use | — | yes |
| B3 | Per-person storage quota and camera viewers | admin | joiner, request | designed | — | yes |
| B4 | Lost or stolen phone (remote wipe, key removal, sessions ended) | employee, admin | loss or theft | **gap** | — | no |

### C. Attendance and HR

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| C1 | Set up a Field Site (fence, accuracy, members, engineer, approval box, check-in block) | admin, HR | new or changed site | in use | — | yes |
| C2 | Worker assignments and shift allocation | HR, supervisor | worker joins or moves | in use, not described | — | yes |
| C3 | Team capture and engineer verification | supervisor, engineer | every shift | in use | — | no |
| C4 | Attendance approval (single and bulk, offline-marked entries) | project manager | daily | in use | [attendance approval](attendance-approval.md) | no |
| C5 | Self check-in and check-out (selfie today; biometric when P82 is built) | employee | every shift | in use; change designed | — | no |
| C6 | Corrections, returns, void and cancel (P24) | supervisor, project manager, HR | errors | **gap**: rules not agreed | — | no |
| C7 | Face enrolment of field workers with one good phone (P95) | HR, project manager, or the worker's supervisor or engineer | onboarding, model change | designed | [face enrolment](field-face-enrolment-and-consent.md) | yes |
| C8 | Face consent, withdrawal, and attendance without a face (P95); [agreement draft](face-attendance-agreement.md) | HR, project manager, supervisor or engineer, worker | onboarding, any time | designed | [face enrolment](field-face-enrolment-and-consent.md) | yes |
| C9 | Uncertain matches and the offline queue (P95) | supervisor, project manager | after capture or sync | designed | — | no |
| C10 | Legal opinion on face attendance (P95) | owner | see P95 | designed | — | yes |

### D. Mail

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| D1 | Sender accounts and their source-address restriction | operator | network change, recreate | in use | — | yes |
| D2 | Shared mailbox membership and send-as | admin | joiner, role change | in use, not described | — | yes |
| D3 | Mail server after a restart (settings reload) | operator | reboot, upgrade | in use; missing from the reboot list | — | yes |
| D4 | Mail archive access and its access-log review | archive reader, admin | business or legal request | in use; log review a gap | — | yes |
| D5 | Seven-year purge and the staff notice | owner, admin | before enabling the purge | designed | — | yes |
| D6 | Mail domain cutover, MX and reverse-DNS changes | owner, operator | cutover | designed | — | yes |

### E. Documents, Drive and editor

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| E1 | A file will not open (do not delete; rescue, restore a version) | user, admin | incident | in use | — | no |
| E2 | Editor bridge after a Drive restart | operator | restart, release | in use by hand | — | yes |
| E3 | Document-worker enrolment per owner | operator | new owner, test refresh | in use | — | yes |
| E4 | Vendor KYC and amendment review | ERP staff, approver | vendor onboarding | in use, no checklist | — | no |

### F. Backups and recovery

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| F1 | Quarterly recovery-essentials check | owner | every 3 months | in use | — | yes |
| F2 | Offline USB copy (steps, frequency, encryption, storage place) | owner | periodic | **gap** | — | yes |
| F3 | Backup-store protection and snapshot rollback | owner | storage change, ransomware | partly | — | yes |
| F4 | Full restore or rehearsal on a clean server | operator | disaster, rehearsal | in use | — | yes |
| F5 | Watching backup, restore-drill and monitoring results: the admin receives the alerts, plus a Desk widget for the sign-in admin (P72, P53) | admin | daily | partly | [admin alerts](admin-alerts-and-daily-checks.md) | yes |
| F6 | Restore one file, record or mailbox | operator | user request | **gap** | — | yes |

### G. Releases and deployments

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| G1 | Production promotion (plan, rollback point, logs, checks, drift, release record) | operator, owner go | each release | in use | [production release](production-release.md) | yes |
| G2 | Advisory and adoption checks; upstream-watch digest | agent, owner | promotion, upgrade, new dependency | in use | — | no |
| G3 | Upgrade checklist: walk the register | operator | version change | in use | — | yes |
| G4 | Re-check manual live settings | operator | upgrade, recreate, reboot | in use | — | yes |
| G5 | Move a hand-made service onto the repository build | operator, owner | migration | in use | — | yes |
| G6 | Planned reboot and after-restart checks | operator | kernel update, restart | in use | — | yes |
| G7 | Install host timers by hand | operator | new host, rebuild | in use | — | yes |
| G8 | Test-site deployment | operator, developer group | each test deploy | partly | — | yes |
| G9 | Test data refresh | owner, System Manager | on demand | in use | — | yes |
| G10 | Production approval on GitHub and a break-glass deploy or rollback | owner | P71 | designed; break-glass a gap | — | yes |

### H. Security and secrets

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| H1 | Secret exposure and rotation (one step per secret) | agent reports, operator rotates | exposure, schedule | **gap** | — | yes |
| H2 | Certificate renewal and its reminder | operator | before expiry | **gap**: no reminder | — | yes |
| H3 | DNS changes at the registrar | owner | cutover | ad hoc | — | yes |
| H4 | Retire a host (keys, tailnet device, old sign-in providers) | operator, owner | retirement | used once | — | yes |
| H5 | VPN devices and branch routers | admin, owner | P29, P48 | designed | — | yes |
| H6 | Clean up throwaway servers and temporary login files after tests | operator | after a test | **gap** | — | yes |

### I. Records and publication

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| I1 | Event receipts for manual changes, incidents, deploys and rollbacks | operator, agent | each event | in use | — | yes |
| I2 | Handover, release log, decision log, PR test record and overlap review | agent, owner | session close, each PR | in use | — | yes |
| I3 | Publish the public P list (leak scan, report read) | agent, owner | each P list change | in use | — | yes |
| I4 | Upstream posts | agent, owner | needs and workarounds | in use | — | no |

### J. Clients and branding

| # | Procedure | Who | When | Status | SOP | Private |
|---|---|---|---|---|---|---|
| J1 | Client-identity guard (diff search, fingerprints, leak response) | agent, owner | each push, new client, leak | in use | — | yes |
| J2 | Replace the branding per deployment | operator | new deployment or client | partly | — | yes |
| J3 | Demo site per prospect | admin | new prospect | designed | — | yes |
| J4 | Test outbound allow list and test recipients' consent | admin | test flows | designed | — | yes |
| J5 | Licence and contract review before the first client | owner | before the first client | open | — | yes |

### Gaps to settle (no procedure yet, or only a draft)

Lost or stolen phone (B4); attendance corrections and
cancel rules (C6); offline USB copy
(F2); restoring a single file, record or mailbox (F6); break-glass deploy and rollback (G10); secret rotation (H1);
certificate reminders (H2); app signing-key custody (B1); impersonation and archive access-log review (A6, D4);
the mail server reload missing from the reboot list (D3); test clean-up (H6); vendor KYC checklist (E4).

## Template

```markdown
# <Procedure name>

**Status:** in use | draft, applies when built (P..) · **Owner of this SOP:** <role> · **Last reviewed:** <date>

## Purpose
Why this is done by a person, and what goes wrong if it is skipped.

## Who
Roles only (owner, admin, project manager, HR, supervisor, employee, operator).

## When
The trigger, and how often.

## Steps
1. ...

## Checks
What must be true before finishing.

## Record
What is written down, where, and how long it is kept.

## When it goes wrong
Who to tell, and what to do.

## Private companion
Which details are in the private operations repository (if any).
```
