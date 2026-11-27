# Permanent test site and one-way refresh (`test-refresh`)

Restricted production snapshot export, test-side restore with quarantine of outbound integrations and credentials, the refresh control and progress, test profiles, egress policy and the verification tools used for acceptance.

## Purpose

Keeps a permanent test site that mirrors production data one way only: a restricted export on production, a root-only worker on test that validates, restores and quarantines (outbound email, webhooks, schedulers, API keys, sessions, provider credentials), the refresh control with progress, test profiles, egress policy and the verification tools used for acceptance.

### Test refresh and code reset

**Refresh data** replaces test data with a crippled production copy. It uses
production resources, so it is meant for occasional use.

GitHub Actions takes care of test code. When a PR is closed without merging,
the reset workflow restores the approved main build if the PR head is still
deployed. Test data stays in place.

### Crippled data

Produced on production by `tools/cripple_snapshot.py` before anything leaves
it (the exporter runs it after production has resumed, on copies only):

- **Strictly the last 60 days**, ERP included: older transactions, logs and
  attachments are dropped; old customers, suppliers, contacts, addresses and
  employees are dropped unless a remaining transaction refers to them. Numbers
  and balances do not add up, by design.
- **All personal information replaced**: names, e-mail addresses, phone
  numbers, addresses, PAN, GSTIN, Aadhaar, bank accounts and IFSC, payroll
  amounts, free text and comments. Fakes are deterministic within one export
  (links keep working) and derived from a key discarded afterwards, so they
  cannot be reversed. Customer, supplier, contact, employee and user record
  names are renamed everywhere they are referenced.
- **Documents become placeholders** of the same type with scrambled names:
  ERP attachments, DMS documents (originals, archive versions, thumbnails,
  OCR text) and Drive files. Drive revisions, trash, search index, thumbnails
  and event history are dropped.
- **Mail is not exported**: Stalwart keeps its mail in a database that cannot
  be scrambled offline, so test mailboxes start empty.
- **Kept accounts**: the logins listed in `keep_accounts` (the members of the
  authentik group **"Testers"**, which gates the test site) keep **only their
  login identity**: e-mail, username and name. Every other profile field
  (mobile number, phone, birth date, bio, location, API keys, reset keys, last
  IP, provider ids of other people) is scrambled or cleared like anyone
  else's. A kept account keeps its provider id so it can sign in.
- **Names of accounts that are not kept**: a person's full name is also
  replaced wherever it still appears in free text (comments, messages,
  descriptions, other records), with the same fake the person's own record
  got. A kept account's own identity fields are never swept, so if a kept
  account shares its name with a non-kept (for example disabled duplicate)
  account, that name remains in the kept account only, by design. Single
  words are never swept (too common); the rehearsal audit excludes kept
  identity rows and technical tables.
- Outbound e-mail, WhatsApp and payments stay switched off on test by the
  existing quarantine and egress policy.

Run `tools/rehearse_cripple.py --config <test worker profile> --keep <login>`
on the test host to prove the scrambling against copies of the test site's own
data; it prints counts of surviving identifiers per table, never values. Its
e-mail audit counts addresses at the public mail providers, at the profile's
`domain` and `mail_domain`, and at the domains listed in the worker profile's
optional `audit_mail_domains` (for example a client's own domain, which never
appears in this repository).

## Contents

- `erpnext_drive_integrations/operations/**`
- `erpnext_drive_integrations/portal/test_refresh.py`
- `erpnext_drive_integrations/public/test-refresh.*`
- `deployment/test-refresh-worker.*`
- `deployment/test-runtime.example.json`
- `tools/export_snapshot.py`
- `tools/cripple_snapshot.py`
- `tools/rehearse_cripple.py`
- `tools/snapshot_archive.py`
- `tools/test_refresh_worker.py`
- `tools/restore_test_data.py`
- `tools/activate_test_refresh.py`
- `tools/prepare_test_profiles.py`
- `tools/rehearse_empty_test.py`
- `tools/test_egress.py`
- `tools/verify_test_collaboration.py`
- `tools/verify_test_queues.py`
- `tools/verify_test_processing.py`
- `tests/test_cripple_snapshot.py`
- `tests/test_refresh_boundary.py`
- `tests/test_refresh_status_files.py`
- `tests/test_restore_boundaries.py`
- `tests/test_snapshot_archive.py`

## Requirements

Modules: `deployment`, `erp-addon-shell`.

Module `deployment`; SSH from test to production limited by a forced command and source address; a test host with Docker.

## Reuse

Install `tools/export_snapshot.py` on the source host and `tools/test_refresh_worker.py` on the test host with root-private profiles; activate with `tools/activate_test_refresh.py` after a verified first restore. See docs/test-rebuild-runbook.md.

## Configuration

Profiles: `deployment/test-runtime.example.json`; systemd examples `deployment/test-refresh-worker.*`. Site config on test: `cloud_test_copy`, `cloud_test_refresh_enabled`, `cloud_test_refresh_users`. Never restore test data into production.

Private settings for crippled data:

- production exporter profile: `"cripple": {"enabled": true, "days": 60,
  "keep_accounts": ["<login of each member of Testers>"]}` and
  `"require_cripple": true` (refuse any uncrippled export);
- test worker profile: `"require_crippled": true` (restore refuses an
  uncrippled snapshot).

## Tests

- `tests/test_cripple_snapshot.py`
- `tests/test_refresh_boundary.py`
- `tests/test_restore_boundaries.py`
- `tests/test_snapshot_archive.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- No upstream product is bundled or adapted.

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: AGPL-3.0-or-later (see `LICENSE`).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
