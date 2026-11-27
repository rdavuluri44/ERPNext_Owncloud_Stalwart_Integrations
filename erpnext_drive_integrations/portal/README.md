# ERP portal, SSO session and mobile (`portal-sso`)

Portal home, authentik SSO sign-in and global logout, shared-browser logout guard, idle proxy-session recovery (P01), native mobile login binding, web push, module header and placeholder/signed-out pages.

## Purpose

Turns ERPNext into the office portal behind authentik SSO: sign-in and global logout across apps, a shared-browser logout guard, recovery of menus after the SSO proxy session lapses while idle (P01), native mobile login binding, web push and the portal module header.

## Contents

- `erpnext_drive_integrations/portal/*`
- `erpnext_drive_integrations/public/session.js`
- `erpnext_drive_integrations/public/push-client.js`
- `erpnext_drive_integrations/public/push-worker.js`
- `erpnext_drive_integrations/public/module-header-*.js`
- `erpnext_drive_integrations/www/signed_out.*`
- `erpnext_drive_integrations/www/place_holder.*`
- `erpnext_drive_integrations/www/__init__.py`
- `tests/portal/**`

Excluded (owned by another module): `erpnext_drive_integrations/portal/test_refresh.py`

## Requirements

Modules: `erp-addon-shell`, `authentik-identity`.

authentik with an ERP proxy provider (forward auth) and an OIDC provider; Frappe Social Login Key for authentik.

## Reuse

Reusable for any Frappe 16 site behind an authentik forward-auth proxy: keep `portal/` plus `public/session.js` and `public/module-header-*.js`, and enable the `portal` feature.

## Configuration

Site config keys: `cloud_sso_enforced`, `cloud_sso_auto_provision`, `cloud_oidc_issuer`, `cloud_combined_site`, `cloud_dashboard_host`, `cloud_default_app`, `cloud_cookie_host_only`, `cloud_native_mobile_clients`, `cloud_native_mobile_enabled` (the old name `cloud_raven_mobile_enabled` is still read when the new one is absent), `cloud_push_enabled`, `push_relay_server_url`, `host_name`. A site's own portal look (unset = production's page): `cloud_portal_hide_entity_name` (no company name beside the logo), `cloud_portal_logo_height` (40 to 100 px), `cloud_portal_logo_position` (`{"top": px, "left": px}`, 0 to 80), `cloud_portal_clean_root_address` (show `/` instead of `/place_holder` where the host serves the portal at its root). Asset URLs are versioned by the runtime renderer.

## Tests

- `tests/portal/test_mobile.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Frappe Framework — MIT — https://github.com/frappe/frappe
- authentik — MIT (core) — https://github.com/goauthentik/authentik

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Portal and Frappe apps: `session.js` (Desk, Raven, Insights) and `www/place_holder.html`.

## Branding

The portal page keeps its name (title and the company name beside the logo). The logo and favicons come from the tenant's private runtime profile (`company_logo`, `company_favicon_dir`); the repository ships neutral placeholders. The same logo is used in the menu's home button. With more than five apps the left-edge menu shows two balanced vertical columns (the home button is not counted); with five or fewer it stays one column (P58).

## Logout and sign-in

Every logout ends on the company website: `sso.LANDING`, rendered from the private profile's `landing_url` (default `https://www.<domain>/`). Apps hand over to the ERP's `/login?logged_out=1` or `/signed-out`. Sign-in asks for the passkey once: `max_age=600` instead of `prompt=login` with `max_age=0`; the callback accepts an authentication from the last ten minutes. `tests/test_logout_and_signin.py` pins both.

Signed-out hand-over (P56 follow-up): `/login?logged_out=1` and `/signed-out` forward to the landing page for top-level navigations only. A request made from an iframe (`Sec-Fetch-Dest: iframe`, for example a portal app frame that discovers the sign-out) gets the ERP's own frameable sign-out page, whose Sign in button opens in the whole tab, because the landing page refuses to be framed.


### Isolated test identity

A marked test copy can set `cloud_test_identity_origin` to its dedicated Authentik HTTPS origin. Its
`cloud_oidc_issuer` and Authentik Social Login Key must use the same origin. The ERP logout then ends the
session at that test issuer. The test provider can use Authentik’s session invalidation flow for account switching,
and send back-channel logout tokens to the ERP test site.
