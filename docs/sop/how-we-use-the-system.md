# How we use the system: sign-in, ERP Mobile and attendance

**Status:** the agreed way of working, written from the owner's decisions of 25 and 26 November 2026 (P82, P95,
P96). Each part says whether it is **live** today or **decided, not built yet** · **Owner of this SOP:** HR ·
**Last reviewed:** 26 November 2026

## Purpose

The decisions taken while designing the app describe how people are meant to use it. This page puts that picture
in one place, by role, so that staff, project managers and admins know what to expect and what is expected of
them. The step-by-step procedures are linked; the reasons are in `docs/decisions.md`.

## The idea in five lines

- Your **phone is your key.** The key lives in your phone only, opens only with your own fingerprint, and cannot be
  copied or shared.
- A **computer** is opened with the phone: scan the QR code, with the phone next to the computer.
- **Attendance** needs you there: your fingerprint and the site's location for your own check-in; your face in the
  supervisor's photograph for field teams.
- **People confirm what software cannot:** the project manager confirms who you are and whose fingerprints are on
  the phone; approvers confirm attendance.
- **Anything unusual is shown to the admin**, and a key that is not used, or is misused, removes itself.

## Every employee with the app (decided, not built yet; today people sign in with an invited passkey)

| Situation | What you do | What the system does |
|---|---|---|
| First time | Install ERP Mobile, tap **Request access**, give your work mail, mobile number and a face photo. Meet your project manager with your phone and ID. | After the project manager and then the admin approve, the key is made in your phone and you are signed in. The photo is not kept. |
| Before onboarding | Remove any fingerprint or face on the phone that is not yours, and confirm it in the app. | Every fingerprint on the phone at that moment can open the key, so this check matters. |
| Every sign-in | Fingerprint (or a strong face unlock). No PIN. | One match, one sign-in. Needs internet; without it the app opens for a limited time and keeps your captures until you are back online. |
| On a computer | Open the sign-in page, scan its QR code in the app, Bluetooth on, phone next to the computer. | Signs you in on that computer. Works on every supported Android phone. |
| How many sessions | One phone and one computer at a time. | A new sign-in ends the older one of the same kind and tells you. |
| Leaving your desk | Sign out, or close the browser. | You are signed out after 30 minutes without activity anyway. |
| Signing out in the app | One tap. | Signs you out everywhere: the Desk and every app. |
| Wrong finger | Dry the finger and the sensor; the app shows how many tries are left. | After 5 misses in a row the key is erased and you onboard again. A successful sign-in resets the count. |
| Adding a fingerprint or face later | Do not, unless you accept onboarding again. | Adding one destroys the key (removing one does not). |
| Away for a while | Nothing; onboard again when you are back. | A key not used for 7 days is removed by the server (the admin can set other periods per group). |
| New, lost or replaced phone | Meet your project manager with the phone. | The project manager checks it in person and confirms in their app; nothing is re-issued on a message or a call. A lost phone: tell the admin at once. |
| Your own attendance | Check in and out in the app at the site, with your fingerprint. | Checks you are inside the site's fence; no selfie. Goes to the project manager for approval. |
| Your personal work files | Keep them in the app. | They stay in place if you leave; nothing is deleted. |

Procedures: [onboarding and re-onboarding](onboarding-identity-and-biometrics.md); today's
[invitation](invite-a-user.md).

## Supervisor of a field team (photograph and location: live; recognition by face: decided, partly built)

| Situation | What you do | What the system does |
|---|---|---|
| Marking the team | Photograph each worker, one at a time. No need to choose the worker first. | Recognises the worker among your team for that shift and records the attendance in your name. |
| The phone asks the worker to turn the head or blink | Let them; it takes seconds. | Checks on the phone that it is a live person, not a picture or a screen. |
| The system is not sure | Pick from the two or three closest names it shows. | Marks your choice for the project manager. |
| No connection | Keep photographing; the app shows "queued". | Sends the captures when you are online; what it cannot settle goes to the project manager. You get no instant confirmation offline. |
| A worker who did not agree to face attendance | Mark them the usual way (choose the worker, photograph). | The project manager approves as before. |
| Machine workers | Give the machine or standby as today. | A recognised operator without it waits for the project manager. |

You never hold the team's face data: it stays on the server, never on your phone.

## Project manager (approval: live; the rest decided, partly built)

- **Onboarding and recovery:** meet the person, check their ID and their phone, see that only their own fingerprints
  and face are enrolled, and confirm in your app. You are the check that software cannot do.
  ([procedure](onboarding-identity-and-biometrics.md))
- **Face queue:** each day, clear the photographs the server could not settle: pick the worker or reject with a
  reason. You cannot decide your own captures.
- **Approvals:** open the evidence, then approve or return with a reason. Official attendance exists only after
  your approval. ([procedure](attendance-approval.md))
- **Leavers:** reassign their workers and approvals before their account closes.
  ([procedure](leaver-offboarding.md))

## HR

- **Field workers without a phone:** enrol each one's face with one good phone, against their ID, after they
  accepted the [agreement](face-attendance-agreement.md) themselves, in a language they read. They may refuse or
  withdraw at any time. ([procedure](field-face-enrolment-and-consent.md))
- **Exits:** record the separation in Frappe HR. That is what closes the person's access: by the admin's checklist
  today, automatically once built (keys, devices and sessions removed, app data purged, face data deleted).

## Admin (sign-in administrator)

- **Approve** access after the project manager's identity check; remove keys and devices when asked or needed.
- **Groups:** decide who is in the Apple exception group (kept small; its members may use Apple Passwords on their
  own Apple devices and get one extra tablet session) and how many unused days each group's keys are allowed.
- **Computers:** only company computers with a certificate can sign in; you list and remove them. (decided, not
  built)
- **Alerts:** you receive the system's alerts and exceptions, on a widget on your Desk and by mail when built, by
  the daily look until then: unusual sign-in places, erased or expired keys, waiting onboardings, unknown
  computers, backups and monitoring. ([procedure](admin-alerts-and-daily-checks.md))
- **Sign-in locations** of staff are personal data: only you see them, and the history is kept 90 days.

## What is temporary or still to come

- **Older phones (below Android 14)** use the app's own QR route for computers. It is retired when no such phone
  is left; nothing changes for the user.
- **iPhones:** an Apple version of the app follows; until then the exception group covers Apple users.
- **Before real sign-ins and before production:** the security review of the QR route, and the legal opinion on
  face attendance.

## Keeping this page true

When a design decision changes how people use the system, this page and the procedure it links are updated in the
same change, without waiting to be asked (see the [rules](README.md)).
