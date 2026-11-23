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

## Requirements

Modules: none.

authentik (existing instance); run tools under the native `ak shell`.

## Reuse

Apply `configuration.json` through `tools/authentik_blueprint.py`; reuse `invite-recovery/` on its own for single-email invitation recovery (see its README).

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
