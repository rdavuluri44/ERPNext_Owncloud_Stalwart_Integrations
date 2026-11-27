# authentik identity configuration (`authentik-identity`)

Retained authentik blueprint (providers, applications, scope mappings), test client creation, invitation recovery service and identity-support adapters.

## Purpose

Reproducible authentik setup: a retained blueprint of providers, applications and scope mappings, test client creation that never edits production providers, an invitation recovery service and identity-support helpers.

## Contents

- `integrations/authentik/**`
- `deployment/stacks/identity.compose.json`
- `deployment/stacks/identity-support.compose.json`
- `deployment/scope-mappings.example.json`
- `tools/authentik_blueprint.py`
- `tests/test_invitation_configuration.py`
- `tests/test_first_admin.py`
- `tests/test_passkey_providers.py`
- `tools/sync_passkey_providers.py`
- `archive-reader/` and `tests/test_archive_reader_signin.py` (P69 mail archive reader)

## Requirements

Modules: none.

authentik (existing instance); run tools under the native `ak shell`.

## Reuse

The approved passkey providers are one setting, [`passkey-providers.json`](passkey-providers.json); after changing it run
`tools/sync_passkey_providers.py` (P79). Choose the first administrator of a fresh instance and switch off `akadmin` with
[`first-admin/`](first-admin/README.md). Apply `configuration.json` through `tools/authentik_blueprint.py`; reuse `invite-recovery/` on its own for single-email invitation recovery (see its README).

The default Brand in the blueprint gives stacked sign-in flows a plain white background and
uses Authentik's light theme by default. Use the deployment's own logo through the existing
branding URL. After applying the Brand on a fresh build, verify the sign-in page against the
logo on desktop and at phone width. For an existing instance, apply the appearance fields
through the Brand settings without reimporting the full identity graph.

## Configuration

Private inputs: template slugs, exact callbacks, approved group and gateway for `configure_test_clients.py`; `deployment/scope-mappings.example.json` for custom scopes. Client secrets stay in authentik.

### Settings that must agree with the ERP (P49)

- **Approval claim.** The ERP admits a sign-in only when the ID token carries the approval claim as a literal
  `true`. Its name is one setting: `APPROVED_CLAIM` in `erpnext_drive_integrations/portal/sso.py`
  (`cloud_approved`), overridable per site with `cloud_approved_claim` in site config. The ERP provider's scope
  mapping ("Workspace approved identity" in `configuration.json` and `deployment/scope-mappings.example.json`)
  must send exactly that name, and so must the test clients (`approved_claim` in their profile, same default).
  `tests/test_signin_settings.py` fails when they differ. On 20 November 2026 production's mapping sent a legacy
  name and new ERP sign-ins failed for days; production's mapping now sends both names until sign-in moves onto
  this build. **After every ERP or sign-in deployment, sign in once in a browser with a passkey** (a fresh
  session, not one already open): the unit tests cannot see the live mapping.
- **Brand and template names** of the invitation pages and e-mails: profile settings `identity_brand` (default
  `Cloud`) and `identity_template_prefix` (default `cloud-`), applied by `tools/prepare_runtime.py` when it copies
  `invite-recovery/templates` and `invite-recovery/public` into the stacks. authentik's database refers to e-mail
  templates by file name, so an installation that already has its own names sets the prefix to keep them. The
  defaults leave every file unchanged.
- **Webmail product name:** `CI_MAIL_WEBMAIL_APP_NAME` in the profile's `settings`; without it webmail shows "Mail".

### Mail archive reader (P69)

The mail archive (see `integrations/mail/README.md`) is read through one dedicated account, `archive-reader`, never
a staff account. It signs in with a passkey like staff, but reaches only the mail application:

- Group **Mail Archive Readers** (no administrator rights, no parents). The passkey sign-in gate
  (`<namespace>-passkey-approved-account`) admits active administrators, the staff group and this group. Every
  other check is unchanged: an approved passkey provider is still required.
- The mail application admits the staff group **or** this group (policy engine mode "any"). Mode "any" is only
  used where every binding is a plain group binding, so it cannot weaken a policy binding. No other application
  binds the group, so the reader is refused everywhere else.
- The reader is not in the test group either, so it does not reach the other test applications. Self-service
  passkey recovery stays staff-only: an administrator re-enrols the reader's passkey by impersonating it.
- On a test client, `also_groups` in `configure_test_clients.py`'s profile admits the group (e.g. on the test
  webmail). A rerun keeps a group added earlier, so test mail never ends up requiring both groups.
- On an existing instance use `archive-reader/archive_reader_access.py` in `ak shell`: `plan`, `apply` (writes the
  before-state receipt first, refuses a gate that was edited by hand), `check` and `rollback`.
  `archive-reader/test_native.py` tests it on a throwaway authentik of the release in use; everything rolls back.

### Identity stack tuning (P49, carried over from production, 20 November 2026)

- PostgreSQL runs with `jit = off` (one sign-in step went from 1.2 s to 0.3 s on production).
- The authentik server may use 3 GB (was 2 GB); a server worker grew to 1.46 GB over five days there.
- Web worker lifetime: `CI_IDENTITY_SERVER_AUTHENTIK_WEB__MAX_REQUESTS` (default 1000, the pinned authentik's own
  default, now explicit): each web worker is replaced after about that many requests. Growth like the one seen
  there therefore happened within one worker's requests or outside the web workers; lower the value only after
  measuring.
- Memory alert: a server that reaches its limit is restarted by Docker, which the P57 restart watch reports;
  sending alerts to people is P72.
- `AUTHENTIK_CACHE__TIMEOUT_POLICIES` stays `0` (policy results are not cached), as production has run it since
  the move of 14 November 2026. Its origin is unknown; changing it is a separate, measured decision.
- When sign-in moves onto this stack, compare the running environment of the old and new containers (lesson of
  the Mail move, `docs/production-moves.md` step 3).

Not in this repository yet: production's newer invitation pages (stylesheet, admin navigation) and e-mail
templates. They are exported from production without secrets, imported into `invite-recovery/` and wired to the
settings above in a follow-up.

## Tests

- `tests/test_invitation_configuration.py`
- `tests/test_signin_settings.py` (approval claim agreement, branding, identity stack tuning)
- `integrations/authentik/invite-recovery/test_native.py`
- `integrations/authentik/invite-recovery/test_recovery_guard.py` and `test_invitations.mjs` (run in CI)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- authentik — MIT (core; enterprise features separately licensed) — https://github.com/goauthentik/authentik

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
