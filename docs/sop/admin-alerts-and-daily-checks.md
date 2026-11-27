# Alerts and daily checks for the admin

**Status:** partly in use. The checks exist and write their results on the servers; **delivery to the admin (mail,
phone, the Desk widget) is decided but not built** (P72, P53), so today someone has to look · **Owner of this SOP:**
admin · **Last reviewed:** 26 November 2026

## Purpose

The system checks itself (sites reachable, backups made, restore drills, stacks in step with `main`, new security
advisories, replies to our upstream posts), but a result nobody reads protects nothing. The owner decided on 26
November 2026 that the **admin** receives the alerts and that the sign-in admin also sees alerts and exceptions in a
widget on their Desk. Until that delivery exists, this SOP is the daily look.

## Who

- **Admin:** looks every working day and acts or passes on.
- **Operator** (a person or an agent with server access): reads what is only on the servers, and fixes.
- **Owner:** decides on anything marked urgent or needing a production change.

## When

Every working day, first thing. Also after any release, restart or power or network incident.

## Steps

1. **Monitoring page:** every site and service up; no disk, memory or certificate warning. A certificate with
   fewer than 14 days left is to renew now (there is no reminder yet).
2. **Backups:** last night's backup finished for every part (ERP, documents, sign-in, mail, files), and the
   weekly restore drill passed. A missing result is a failure, not "probably fine".
3. **Upstream watch digest** (new each day only when something changed): anything marked **upgrade now** goes to
   the owner the same day, before feature work. Read the "upstream posts" page of the digest for replies to our
   posts.
4. **Drift check:** every production stack clean. A stack "behind" means a release missed it.
5. **Office editor safety check:** no failed saves waiting.
6. **Mail health:** the mail health check is green and the sender accounts work.
7. **Sign-in exceptions (when P82 is built):** keys removed for no use, keys erased after wrong attempts, waiting
   or refused onboardings, unknown computers, failed certificate checks, and sign-ins from unusual places or
   networks. For an unusual place: ask the person, by phone or in person, whether it was them. If not, or if they
   cannot be reached and it looks wrong, end their sessions and remove the key; they onboard again. Mark known
   office and site networks as usual so they stop alerting.
8. Write one line for the day: all clear, or what was found and who has it.

## Checks

- Every item above was looked at, not assumed.
- Each finding has a person and a next step.

## Record

The day's line and any finding go where the private companion says (proposal: the day's handover, or a simple
log the owner can read). Incidents and manual changes on the servers get an event record (private operations
rules).

## When it goes wrong

- **A site or service is down:** tell the operator and the owner at once; after a restart follow the after-restart
  checklist (`docs/production-moves.md`).
- **A backup or restore drill failed:** treat it as urgent the same day; a second missed night means there is no
  recent copy.
- **An "upgrade now" finding:** the owner decides; the fix follows branch, test, merge, production like any
  change.
- **A check itself did not run:** that is a finding too (a timer stopped, a server was down).
- **Nobody can look on a given day:** say so to the owner beforehand; the look is not optional.

## Private companion

Where each result is read (addresses, server paths, the monitoring page), who the operator is, and where the daily
line is written are in the private operations repository.
