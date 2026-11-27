# Mail (Stalwart and Bulwark Webmail) (`mail`)

Bulwark Webmail overlay (SSO login, Drive picker, policy), Stalwart bootstrap and SMTP sender definitions, mail build preparation, and the ERP mailbox administration DocType and access report.

## Purpose

Single sign-on webmail with Drive attachments: a source overlay for Bulwark Webmail (SSO callback, session guard, Drive picker, policy), Stalwart bootstrap and SMTP sender definitions, and ERP-side mailbox administration with an access matrix report.

## Contents

- `integrations/mail/**`
- `erpnext_drive_integrations/cloud_integrations/**`
- `deployment/stacks/mail.compose.json`
- `tools/prepare_mail.py`
- `tools/refresh_webmail_overlay_base.py`

## Requirements

Modules: `authentik-identity`, `drive`.

Stalwart Mail Server and Bulwark Webmail at the commit in `integrations/mail/upstream.json`; authentik OIDC client for webmail; module `drive` for the picker.

## Reuse

Run `tools/prepare_mail.py` to apply the overlay to the pinned Bulwark commit and build it; the modified source is shipped with the build as the AGPL requires. The overlay replaces whole upstream files, so `overlay_base` in `upstream.json` records the upstream checksum of each file it replaces at that commit: the build stops when the clone differs, and the tests fail when the commit changes without it (P91). To move to a new Bulwark commit, run `tools/refresh_webmail_overlay_base.py --checkout <clone at the new commit>`: it lists the files to merge (old upstream, new upstream, ours); after merging, run it again with `--write` (register entries WEBMAIL-1 to -3 in `docs/upstream-customizations.md`). The ERP mailbox administration DocType can be reused without the webmail overlay.

## Configuration

Webmail OIDC settings are rendered by the runtime renderer into the mail stack; Stalwart is initialised with `integrations/mail/stalwart_bootstrap.py`. Credentials stay in Stalwart's native store.

## Mail retention (P69)

Company mail is kept and users cannot delete it for good. This uses Stalwart Community only; the
Enterprise "deleted items" archive is not used. `integrations/mail/retention.py` runs on the mail host
with a private profile and does the following:

- **Journal copy:** a system Sieve script copies every message that passes the SMTP DATA stage to an
  archive account. That covers inbound mail, authenticated submission and webmail (JMAP) submission.
  The archive account has no sign-in and may only receive mail.
- **No permanent deletion:** the built-in User and Group roles lose IMAP `EXPUNGE`/`DELETE`, JMAP
  destroy and POP3 `DELE`, and Trash and Junk are no longer emptied automatically. A delete only moves
  mail to Trash. The administrator role is unchanged, because the purge needs it.
- **Read access:** one reader account gets read-only access to the archive Inbox. Its sign-ins
  (`auth.success` with the account name) are the access log. The log tracer is moved to
  `/var/lib/stalwart/logs/` on the data volume, as plain text, so the log is kept and backed up. The
  default `/var/log/stalwart/` does not exist in the image, so nothing was logged before.
- **Restart:** Stalwart applies a changed DATA stage and tracer only after a restart. `apply`
  restarts the container and then verifies every setting.
- **Backfill:** `backfill` copies mail received before the journal started into the archive once
  (resumable and idempotent).
- **Purge:** `purge` counts mail older than `retention_days` (default seven years) in every account,
  the archive included. `purge --apply` removes it; see `deployment/mail-retention-purge.*.example`
  for a daily timer, to be enabled only after a counting run has been reviewed.
- **Status:** `status` lists any setting that is not in place and the stored sizes in bytes.
- **Rollback:** `apply` writes the settings it replaces to a receipt first; `rollback` restores them
  and switches the journal off. It keeps the archive, its mail and the reader's access.

Webmail matches the policy:

- `tools/prepare_runtime.py` locks the delete action to "move to Trash" and hides the Enterprise-only
  "Recover deleted items" page.
- `tools/prepare_mail.py` replaces the English texts that promise a permanent delete with
  `integrations/mail/locale-overrides.json`. It changes only those texts in place and fails the build
  if upstream changed one of them.

## Tests

- `tests/test_rebuild_templates.py`
- `tests/test_mail_retention.py` (retention tool against a fake server, webmail texts and policy)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Bulwark Webmail — AGPL-3.0-only (see integrations/mail/LICENSE.upstream and NOTICE.upstream) — https://github.com/bulwarkmail/webmail
- Stalwart Mail Server — AGPL-3.0 (or commercial SEL) — https://github.com/stalwartlabs/stalwart

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Mail: `components/cloud-test-marker.tsx` in the main layout (image rebuild needed).
