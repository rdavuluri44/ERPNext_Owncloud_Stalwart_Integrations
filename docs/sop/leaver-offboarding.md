# When someone leaves: closing every way in

**Status:** draft for the owner's review. The manual checklist below is what has to be done **today**; the
automatic part decided on 26 November 2026 (P82, P95) is not built yet · **Owner of this SOP:** HR · **Last
reviewed:** 26 November 2026

## Purpose

A person who has left must not be able to sign in, read mail or files, or be marked present. Today nothing does
this by itself: each app has its own account, key or membership, and until this SOP no record described the steps.
The owner decided that the **exit procedure in Frappe HR** will trigger the removal of the person's sign-in keys,
devices and sessions and purge their data in the mobile app, with their face templates deleted too; until that is
built, the admin does it by hand from this list on the day HR records the exit.

## Who

- **HR:** records the exit in Frappe HR and tells the admin the last working day.
- **Admin:** closes the accounts and memberships.
- **Project manager:** reassigns the leaver's team and approvals.
- **Owner:** decides the open points below.

## When

On the last working day, at the agreed time. For a dismissal or a suspected misuse: at once, before the person is
told where that is possible; steps 2 and 3 first.

## Steps

1. **HR:** record the separation in Frappe HR and set the employee's status to Left with the relieving date. Tell
   the admin and the project manager.
2. **Sign-in service (admin):** deactivate the person's account; remove their passkeys and any recovery
   invitation; end all their sessions; remove them from every group (approved users, exception group, testers,
   archive readers).
3. **ERP (admin):** disable the person's ERP user; check that no API key or token is left on it.
4. **Attendance (project manager, then admin):** if the person was a supervisor, engineer or approver, reassign
   their workers and approvals first (the system refuses to remove a supervisor who still has active workers), then
   remove them from every Field Site. Decide their own waiting attendance entries before the account closes.
5. **Mail (admin):** remove the person from every shared mailbox and send-as right. Mailboxes are shared in the
   present setup, so there is no personal mailbox to close or redirect (owner, 26 November 2026). Company mail is
   kept under the retention rule; do not delete it.
6. **Drive, documents and chat (admin):** end their sessions and app tokens. **Their personal business files stay
   where they are; nothing is deleted** (owner, 26 November 2026). Hand over shared spaces they managed to their
   manager.
7. **Phone and computers:** ask the person to remove ERP Mobile; when P82 is built, removing the key in the sign-in
   service makes the app purge itself. Remove their computers from the allowed list when computer binding exists.
8. **Face data (P95, when in use):** it is deleted automatically when the employee is no longer Active. Check that
   the worker no longer appears under Field Face Enrolment.
9. **Check from outside:** try the person's sign-in the next day (it must be refused), and look at the sign-in
   service's device and session list for anything left.

## Checks

- Sign-in refused; no session, passkey or group left on the account.
- ERP user disabled; no site membership; no workers or approvals still pointing at them.
- No shared mailbox or send-as right; the person's files are still in place and nobody deleted them.

## Record

HR's separation record in Frappe HR. The admin notes the date each step was done; where, is in the private
companion (proposal: a checklist on the employee's separation record).

## When it goes wrong

- **The person still has company data on a private phone or computer:** tell the owner; ending the sessions and
  keys stops new access, it does not remove what was already downloaded.
- **A step cannot be done (for example the only approver of a site is leaving):** the project manager and admin
  fix the assignment first; do not leave the account open "for a few days".
- **The person returns:** a new invitation or onboarding, with fresh checks; do not re-enable old keys.

## Open points for the owner

- Decided on 26 November 2026: personal files stay; mailboxes are shared, so nothing is redirected.
- Still open: who may open a leaver's personal files afterwards, and for how long they are kept.
- Still open: whether the admin's checklist lives on the Frappe HR separation record (proposal above).

## Private companion

The admin screens and names of the groups, mailboxes and spaces, and each app's own steps, are in the private
operations repository.
