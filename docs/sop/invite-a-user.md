# Invite a new user to sign in

**Status:** in use · **Owner of this SOP:** admin · **Last reviewed:** 26 November 2026

P82 will replace this procedure for staff who use ERP Mobile (see
[onboarding to ERP Mobile](onboarding-identity-and-biometrics.md)); until that is built, this is how a person gets
access.

## Purpose

A person can sign in only with a passkey that was created through an invitation. The system fixes the mail address
and checks the passkey provider, but only a person can check that the invitation goes to the right human being. A
link sent to the wrong person, or forwarded, gives that person the account.

## Who

- **Admin** (sign-in administrator): creates and sends the invitation.
- **The person's manager or HR:** confirms who the person is and which mail address is theirs.
- **New user:** opens the link and creates the passkey.

## When

A new employee or collaborator needs access. For a lost device or passkey, use the recovery invitation (same
screen); see "When it goes wrong".

## Steps

1. Get the request from the person's manager or HR, with the person's full name and work mail address. Do not act
   on a request that comes only from the person themselves.
2. Check that the person is in the approved-user group's intended audience (staff or an agreed collaborator) and
   that the mail address is theirs and not shared.
3. In the sign-in service's admin screens, open **Flows and Stages → Invite users**. Choose the person and the
   approved-user group (the group's name is in the private companion).
4. Choose how many times the link may be opened (1 to 5 where the site offers it; otherwise it is single use).
   Use the smallest number that is practical; more than one only for people who are likely to start on the wrong
   device.
5. Send the link to the person's own work mail address only. Never paste it into a chat group, a ticket or a
   shared mailbox.
6. Tell the person, by another channel (phone or in person): open the link on the device they will use, create the
   passkey in an approved provider (the list is in the private companion; the sign-in page refuses others), and
   then sign in from the portal, not through the link again.
7. Confirm with the person that they signed in. Then give the app access they need (ERP roles, site membership,
   mailbox, Drive): the joiner procedure (inventory A7).

## Checks

- The request came from the manager or HR, and names the person and the address.
- The invitation shows as used (or removed after its last attempt) under **Invitations**.
- The person signed in from the portal with their passkey.

## Record

The sign-in service records who created the invitation and when it was used. Note the request (who asked, for
whom, date) where the private companion says.

## When it goes wrong

- **The link expired or the attempts are used up:** create a new invitation; do not extend an old one.
- **The person opened it on the wrong device or saved the passkey in the wrong place:** use a **recovery**
  invitation. The old passkey is removed only after the new one works.
- **Lost device or passkey** (owner's rule, 26 November 2026): the **project manager meets the person, checks
  their phone in person** and confirms the request. Only then does the admin send a recovery invitation. A message,
  mail or call asking for recovery is never enough. When ERP Mobile holds the keys (P82), the project manager
  confirms the request in their own app instead of telling the admin; until then they confirm it to the admin
  themselves, and the admin notes who confirmed and when.
- **The invitation reached the wrong person:** delete it at once under **Invitations**; if a passkey was already
  created, remove it from the account, end the account's sessions and tell the owner.
- **The mail did not arrive:** check the sender account (inventory D1) before sending again.

## Private companion

The group names, the approved passkey providers, the admin address of the sign-in service and where requests are
noted are in the private operations repository.
