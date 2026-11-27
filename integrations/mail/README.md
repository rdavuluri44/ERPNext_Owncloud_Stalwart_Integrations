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

## Tests

- `tests/test_rebuild_templates.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Bulwark Webmail — AGPL-3.0-only (see integrations/mail/LICENSE.upstream and NOTICE.upstream) — https://github.com/bulwarkmail/webmail
- Stalwart Mail Server — AGPL-3.0 (or commercial SEL) — https://github.com/stalwartlabs/stalwart

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Mail: `components/cloud-test-marker.tsx` in the main layout (image rebuild needed).
