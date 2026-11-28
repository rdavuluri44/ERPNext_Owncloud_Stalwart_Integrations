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


### The Desk's top bar (P111, P112)

The Desk has one always-visible bar. From the left: the brand icon (full screen), the applications (a strip that
scrolls inside its own space; Home first), on the test site the refresh button, search, notifications, and the
person's button with About, font size, mode and Sign out.

- **Search and notifications are universal.** The Desk asks the business system itself
  (`frappe.utils.global_search.search`, `portal.desk.notifications`) and sends every other application a
  message (`{source:'cloud-desk', type:'search', text, round}` or `type:'notifications?'`); the application
  answers from its own page with `{source:'cloud-session', type:'search-results'|'notifications', items}`,
  where an item is a title, a detail and a path. The Desk opens a path only inside the application that named
  it (`type:'open'`). Other messages: `look` (font size and mode), and the sign-out ones below.
- **About** (`portal.desk.about`): our application's name, version and repository; the installed Frappe
  applications; the other applications from `portal/components.json`, written by `tools/about_components.py`.
  Run that tool after a pinned image changes; a test fails otherwise.
- **Addresses:** `/place_holder#drive` shows an application, `/place_holder#drive:/files/...` a place inside it,
  `/place_holder#open:/desk/...` a page of the business system. The proxy sends a person's page visit to an
  application's own address there (P112, register PROXY-7).

### Sign-out on the Desk (P53)

Sign out is the last item of the menu of the person's button in the top bar. The bar shows on the Desk
home only and is hidden while an application is open. It asks every open
application for unsaved work (`{source:'cloud-desk', type:'unsaved?'}`), warns the person, tells each application to
end its own session (`type:'signout'`), waits at most 2.5 seconds for their `{source:'cloud-session', type:'logout'}`
answers, then calls `finish_logout`. Inside the Desk each application's own sign-out item is hidden by that
application's script (`session.js` here; Drive, DMS and webmail in their modules). Opened on its own, an application
shows "Back to home" instead. Messages are accepted only between the Desk's address and its own frames.
`tests/test_desk_signout.py` pins both sides.

### Isolated test identity

A marked test copy can set `cloud_test_identity_origin` to its dedicated Authentik HTTPS origin. Its
`cloud_oidc_issuer` and Authentik Social Login Key must use the same origin. The ERP logout then ends the
session at that test issuer. The test provider can use Authentik’s session invalidation flow for account switching,
and send back-channel logout tokens to the ERP test site.
