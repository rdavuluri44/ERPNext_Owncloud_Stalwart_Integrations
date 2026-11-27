# Mobile push

## Purpose

Alerts to the mobile app while it is closed (owner, 26 November 2026), the way large Indian apps do it: ERPNext
sends a **data-only, high-priority message directly to Google's Firebase Cloud Messaging (FCM)**; the app on the
phone writes the visible text itself and, for approvals, shows the full-page ringing alert. No other relay.

**What alerts** (owner): something new **waits for your approval or check** (any ERPNext workflow approval, and
attendance to approve or verify), and your entry was **returned** to you. Approved entries and other
notifications send nothing.

**What leaves the server:** the kind (`approval`, `verify`, `returned`), the document type, the document ID, and
for attendance the site and its name. Never a person's name, an amount or other business data. The phone opens the
details only after the app lock, from ERPNext, as the signed-in person.

## Contents

- `Mobile Device` (DocType, System Manager only): one row per phone: person, platform, push address (hidden),
  on/off, registered. **One phone per person**: registering a new phone removes the older one; the same push
  address signed in by someone else moves to them; a disabled user's phones are removed.
- `api.register_device(token, platform)`, `api.unregister_device(token)`: POST only, for the signed-in person only.
- `events.py`: `Notification Log` after insert (custom_hr's attendance notices, by the entry's state) and
  `Workflow Action` after insert (Open: people holding one of its roles who have a phone and may read the
  document; never the person who moved it there).
- `sender.py`: queued after commit on the `short` queue; Google token signed with the service-account key (RS256,
  PyJWT), cached until a minute before expiry. A 404 / `UNREGISTERED` answer switches that phone off; a 400 never
  does (a bad message must not switch off every phone). No retry: a missed alert still shows in the app.
- `rules.py`: the rules without Frappe.

## Requirements

Frappe / ERPNext as for the rest of this app; `PyJWT[crypto]` and `requests` (already dependencies). Outbound
HTTPS from the workers to `oauth2.googleapis.com` and `fcm.googleapis.com`. A Firebase project (free plan).

## Reuse

Any Frappe site can use it: the triggers are standard `Workflow Action` and `Notification Log` events; only the
attendance part reads `Field Attendance Entry` (custom-hr) and does nothing when that DocType is absent from a
notice. The phone side is `mobile/` (mobile-app module).

## Configuration

Maintainers, test site first:

1. A Firebase project with the app's Android package (`APP_ID`) added; the app build gets its
   `google-services.json` (see `mobile/README.md`).
2. In Firebase: Project settings, Service accounts, **Generate new private key**. Place the JSON file on the
   server, readable only by the Frappe user and **outside the site folder** (site files go into backups and test
   refreshes), for example `/home/frappe/secrets/fcm-key.json`, mounted read-only. The test site and production
   each get their own file; never put it in the repository, chat or a ticket.
3. `bench --site <site> set-config mobile_push_fcm_key_file /home/frappe/secrets/fcm-key.json`
4. `bench --site <site> migrate` (creates `Mobile Device`), restart web and workers.

Without `mobile_push_fcm_key_file` nothing is sent and nothing fails. Switch the whole feature off with
`cloud_features: {"mobile_push": false}`. iPhone (Apple APNs) comes later with the Apple Developer account;
`register_device` accepts Android only until then.

## Tests

`python tests/test_mobile_push.py`: the rules on the real module (data only, no text for Google, dead addresses
only on 404 / `UNREGISTERED`), the triggers on the real `events` module with a fake frappe (role holders with a
phone who may read the document; attendance only when waiting or returned), and the surface (POST only, own
records only, sending after commit, nothing secret in logs, the device list for System Managers only).

## Licenses

Our code: as `LICENSE`. Frappe Framework (MIT). FCM is a Google service used over HTTPS; no Google code is included.

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
