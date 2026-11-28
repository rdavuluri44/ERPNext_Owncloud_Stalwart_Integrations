# Notification service

## Purpose

One function through which the business system tells a person something (P108; owner, 27 November 2026). Every
message has a **kind**:

- **decide**: something waits for this person's decision. It alerts the phone, round the clock. While it still
  waits, the person is reminded every 4 hours, but only between 07:00 and 21:00 (the site's time).
- **inform**: the person only needs to know. It goes to their read-only Notices room in chat. It never rings.

Mail is the fallback when the person cannot be reached otherwise. Each event is sent once per person. When
something is decided, by anyone and anywhere, its alert is removed from the phones.

**What leaves the server** (owner, 28 November 2026): to the phone, a reason (`approval`, `verify`, `returned`),
whether it needs a decision, a short code for the sort of thing (`about`: `attendance`, `payment`, `purchase`,
`leave`, `petty_cash`, `store`; none for other document types) and a **mark**. The mark stands for the thing
without saying what it is: only this server can compute it, and it is different for every person. A reminder
carries a count and the oldest wait in hours. A removal carries the mark alone. Never a document type, a document
ID, a site, a person's name, an amount or a text. The phone learns what a mark stands for from "what waits for me",
as the signed-in person. The mail for a decision says only that something waits, with the link. A notice's text
goes to the company's own chat or mail.

## Contents

- `service.py`
  - `notify(users, kind, doctype, name, reason, state, site, deadline, text)`: the one function. It writes one
    `Notification Record` per person and thing and sends after the save commits (`short` queue).
  - `resolve(doctype, name, current_state)`: closes the waiting records of a thing that left the state they were
    made for, and sends the content-free "remove this alert" message (`kind: remove`, with each phone's own
    mark) to the phones that got one, the deciding person's included.
  - `remind` (hourly): closes what the events missed, then sends one reminder per person (`kind: reminder`).
  - `purge` (daily): removes closed records after 90 days. What still waits is never removed.
- `events.py`: what makes the service speak. `Workflow Action` after insert (any ERPNext approval: every enabled
  person who holds one of its roles and may read the document, never the person who moved it there);
  `Notification Log` after insert (custom-hr's attendance notices: to approve, to verify, or returned). Any saved or
  deleted document closes its own waiting records; document types without a workflow return at once.
- `api.waiting` (GET, for the signed-in person only): "what waits for me". How many decisions wait, since when the
  oldest waits and the nearest known deadline: in total, per kind of thing and per site. Then the things
  themselves (`items`, oldest first): `mark`, `reason`, `about`, `doctype`, `docname`, `site`, `waiting_since`,
  `deadline`. With them the app opens the thing an alert's mark stands for, and sets its own list right when a
  removal was lost: an alert whose mark is not in `items` is no longer waiting. Chat and mail unread counts are
  not in it: the app asks those servers.
- `Notification Record` (DocType, System Manager, read only): who, kind, why, about what, the state it was in,
  since when, how it was sent (`phone`, `chat`, `mail`, `workflow mail`), reminders, when it was closed. It holds
  no text.
- `rules.py`: the decisions without Frappe (channels, one record per person and thing, reminder hours, 90 days,
  the numbers of "what waits for me", the `about` codes and the mark).

**The mark:** the first 32 hex characters of HMAC-SHA-256 over the person, the document type and the document ID,
keyed with the site's own encryption key (`encryption_key` in the site's configuration, which Frappe creates). A
site restored with another key computes other marks; the phones then set their lists right from `items`.

**Choices (owner, 28 November 2026):**

- The phone channel (`mobile_push`) keeps the phone list and the sending; its own triggers moved here, so an
  event has one trigger and a phone rings once.
- A returned attendance entry counts as `decide`: it waits for the person who made it.
- Nothing sends `inform` yet. `notify` accepts it for the modules that will (admin alerts, document notices).
- A person without a phone gets one mail when the decision starts to wait and no reminders. Where the document's
  workflow already mails its approvers (`Send Email Alert`), the service sends no second mail and records
  `workflow mail`.
- Whether Google accepted a phone message is recorded; whether the phone showed it is not known to the server.
- The portal's older opt-in browser alerts (`portal/push.py`, `cloud_push_enabled`) are unchanged and still have
  their own triggers.

## Requirements

Frappe / ERPNext as for the rest of this app. For phone alerts the `mobile-push` module with its key; for notices
the `chat-rooms` module with a chat server; outgoing mail for the fallback.

## Reuse

Any Frappe site can use it. The approval trigger is the standard `Workflow Action`; only the attendance part reads
`Field Attendance Entry` (custom-hr) and does nothing where that DocType is absent. Another module calls
`service.notify(...)` and, for a decision of its own, `service.resolve(...)` when it is decided.

## Configuration

`bench --site <site> migrate` creates `Notification Record`. Nothing else is needed: without the phone key
decisions go by mail, without chat notices go by mail. Switch the service off with
`cloud_features: {"notifications": false}`; then nothing triggers a phone alert either.

On a test site, mail follows the test site's own rules for outgoing mail (see the work list, test-site items).

## Tests

`python tests/test_notifications.py`: the rules. `python tests/test_notification_service.py`: the real service and
triggers on a fake site. They fail if an event could be sent twice, if a decision's alert or mail could carry
content, if a document, a site or its name could go to a phone, if a phone could ring for information, if a reminder could go out at night or more often than every
4 hours per person, if a decided thing could stay on a phone, or if a waiting record could be removed.

## Licenses

Our code: as `LICENSE`. Frappe Framework (MIT).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
