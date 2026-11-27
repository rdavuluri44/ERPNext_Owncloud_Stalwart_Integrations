# Face enrolment of field workers, consent and withdrawal

**Status:** draft, applies when built (P95; the server part is in progress) · **Owner of this SOP:** HR · **Last
reviewed:** 27 November 2026

## Purpose

Supervisors mark field team attendance by photographing each worker; the server recognises the face. That works only
if each worker was enrolled correctly (the right person, good photographs) and agreed to it. Enrolling the wrong
person, or without consent, makes attendance records wrong and breaks the worker's trust and the law.

## Who

- **HR**, the **project manager** of the worker's site, or the worker's own **supervisor** or **engineer** (the engineer
  assigned to that supervisor; owner, 27 November 2026): enrols, records consent, handles withdrawal. The system
  refuses another team's supervisor or engineer, and records who enrolled each worker.
- **Worker:** reads the agreement, accepts or refuses.
- **Supervisor:** uses face attendance and the path without a face for workers who refused.

## When

- A new field worker joins, or a whole team is enrolled at once (bulk onboarding).
- The face model changes (the system reports workers who "need re-enrolment").
- A worker withdraws consent, or leaves.

## Steps

1. Use **one good phone** for enrolment (a recent model with a good camera, held steady), in even light, with a
   plain background. Not the supervisor's own phone for their own team.
2. For each worker: check their original identity document against the person and the employee record.
3. Show the **face attendance agreement** ([draft](face-attendance-agreement.md)). It opens in **English**; offer the
   worker the other languages and let them choose the one they want to read (owner, 27 November 2026). If a
   translation and the English differ, the English version governs. Explain what is kept (encrypted face
   templates on the company's server, no photographs), why, for how long (until they withdraw or leave), and that they
   may refuse or withdraw at any time: their attendance is then marked by the supervisor and approved by the
   project manager. **You explain all of this to the worker yourself, in a language they understand**, and answer
   their questions: by ticking "I agree" the worker confirms that you did (owner, 27 November 2026). If you cannot
   explain it in their language, do not enrol them; ask HR or someone who speaks it. The worker ticks the separate
   acceptance box themselves.
4. If the worker refuses: do not enrol them; tell the supervisor they use attendance without a face.
5. If the worker accepts: record the agreement version and the language the worker read, confirm the identity check, and capture the
   face from every angle the app asks for (front, left, right, up, down). Repeat if the app reports that the angles do
   not look like the same person.
6. Bulk onboarding: work through the team list one worker at a time; never enrol from photographs brought by someone
   else, from a screen, or from a group photo.
7. **Withdrawal:** when a worker asks to withdraw, record the reason in their words and withdraw at once in the app.
   The face templates are deleted permanently; the consent record stays, marked withdrawn. Tell the supervisor.
8. **Leavers:** nothing to do for the face data: it is deleted automatically when the employee is no longer active.
   Check it in the leaver procedure (A14).

## Checks

- Identity document seen in original.
- The worker ticked the acceptance box themselves, after you explained the agreement in a language they understand
  and they read or heard it in English or in the language they chose.
- A supervisor or engineer who enrolled their own team: the project manager looks over the new enrolments in the
  next approval round (the consent record names who recorded it).
- The app confirmed the enrolment with the number of angles.

## Record

- The system keeps the consent record (agreement version, language, who recorded it, when, identity checked) and
  the encrypted templates; no photographs and no copy of the identity document.
- The agreement text and its versions: [draft 1](face-attendance-agreement.md), for the lawyer's review; the languages
  and translations are in the private companion.

## When it goes wrong

- The worker does not match their document, or someone else answers for them: stop and tell HR.
- The app keeps refusing the angles: improve the light, remove caps and dark glasses, try again; if it still fails,
  use attendance without a face and tell HR.
- A worker says they never agreed: withdraw at once (step 7) and tell HR.

## Private companion

The agreement text, its languages and the company named in it are in the private operations repository (client
identity).
