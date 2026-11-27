# Our changes to upstream apps, and what to redo on an upgrade

This register lists every place where we change, patch, overlay or rely on the
internals of software we did not write. It is the list to walk before and after
upgrading any of them (P89, `AGENTS.md` "Our changes to upstream apps").

- **Re-apply:** our patch or copy of their file must be redone against the new
  upstream version (rebase, then rebuild).
- **Re-check:** it relies on their internals (function names, fields, page
  structure, routes, settings); confirm on the test site that it still works.
- **None:** nothing to do on an upgrade; listed so nobody wonders.

**Loud** means an upgrade that breaks it fails visibly (build error, migrate
error, crash). **Silent** means it stops working without an error: these are the
ones that need a deliberate check.

Details that cannot be public (host names, live object names, manual settings on
the live servers, the client brand) are in the private companion,
`docs/upstream-customizations-private.md` in the operations repository. It uses
the same entry IDs.

First version 26 November 2026, at `main` `fa4f28e`, built from the code, the
decision log, the retained record and the private records. Items marked
**to verify** were not confirmed from those sources.

## Upgrade checklist

Use this for every pull request that changes a version in
`deployment/upstream-lock.json` or `deployment/build-lock.json`, or an image pin
in `deployment/upstream-watch.json`.

1. **Before:** read the release notes and advisories (the security rule in
   `AGENTS.md`), then read this register's section for the app, plus
   "Several apps" and the private companion's section for it.
2. **Re-apply** every re-apply entry against the new version, in the same pull
   request. A patch whose anchor no longer matches must fail the build; never
   loosen the anchor to make it pass.
3. **Build and deploy the branch to the test site.**
4. **Re-check** every re-check entry, the silent ones first. Use the listed test
   where there is one, and a browser check where there is not.
5. **Record** in the pull request one line per entry: re-applied, checked and
   working, not affected, or broken and fixed. Note the new upstream version on
   each entry you touched in this file.
6. **Retire** workarounds that upstream has fixed: remove our code, update the
   entry and the `workaround` note in `deployment/upstream-watch.json`, and say
   so on the upstream issue.
7. **After promotion:** the release record names the entries checked, and the
   ones the test site could not cover.

Lessons from earlier upgrades and incidents are at the end of this file. Read
them before an upgrade of Frappe, authentik, Drive, Coolify or the host.

## Contents

- [Several apps: build and packaging of the ERP image](#several-apps-build-and-packaging-of-the-erp-image)
- [Frappe](#frappe)
- [ERPNext](#erpnext)
- [HRMS (Frappe HR)](#hrms-frappe-hr)
- [India Compliance](#india-compliance)
- [Chat (Synapse and the Matrix Authentication Service)](#chat-synapse-and-the-matrix-authentication-service)
- [Insights](#insights)
- [Payment apps and India Payroll](#payment-apps-and-india-payroll)
- [authentik](#authentik)
- [ownCloud oCIS and ownCloud Web (Drive)](#owncloud-ocis-and-owncloud-web-drive)
- [ONLYOFFICE Docs (office editor)](#onlyoffice-docs-office-editor)
- [Stalwart mail](#stalwart-mail)
- [Bulwark webmail](#bulwark-webmail)
- [Paperless-ngx (documents)](#paperless-ngx-documents)
- [Processing, databases and small components](#processing-databases-and-small-components)
- [Traefik (Coolify's proxy)](#traefik-coolifys-proxy)
- [Coolify](#coolify)
- [Host: Docker, Tailscale, TrueNAS, RustFS](#host-docker-tailscale-truenas-rustfs)
- [Mobile app (Expo, React Native)](#mobile-app-expo-react-native)
- [Retired](#retired)
- [Lessons from earlier upgrades](#lessons-from-earlier-upgrades)
- [Open questions found while building this register](#open-questions-found-while-building-this-register)

## Several apps: build and packaging of the ERP image

Made against: frappe_docker `0ad1a11`, bench 5.31.1, Node 24.22.1, Yarn 1.22.22
(`deployment/build-lock.json`).

### BUILD-1 We rewrite frappe_docker's official Containerfile

- **What and why:** pins the Python base image by digest, Node, Yarn and bench to
  `deployment/build-lock.json`; adds our app sources, the Python constraints and
  the Node heap; clones Frappe from our pinned local copy. Reason: a
  reproducible build from public pins (`docs/deployment.md`).
- **How:** text replacement on upstream's file in `tools/prepare_erp_image.py`
  (around lines 41-59); `tools/build_erp_core.py`.
- **Upgrade:** **re-check** on every frappe_docker bump. **Loud** since P91: each of
  the seven changes must find its upstream line exactly once, or the build stops
  (`replace_once`), so a reworded line can no longer silently drop our pins. Still
  compare the generated `Dockerfile` with upstream's Containerfile for new lines
  that need a pin.
- **Tests:** `tests/test_prepare_erp_image.py` (each changed line stops the build).

### BUILD-2 Our copy of Frappe's nginx template

- **What and why:** a full copy of the official template with two changes: Origin
  is filled in only when the browser leaves it out, and the socket.io location
  passes it on. Reason: Frappe 16 rejects a realtime socket whose Origin differs
  from Host, and upstream's template forced Origin to the internal site name
  ("Invalid origin", `docs/idle-navigation.md`). (`absolute_redirect off` is
  upstream's own line, added in frappe_docker `eccae39`, not ours: checked
  26 November 2026.)
- **How:** `deployment/erp/frappe.conf.template`, copied over
  `resources/core/nginx/nginx-template.conf` at build and mounted at runtime
  (`deployment/stacks/erp.compose.json`).
- **Upgrade:** **re-apply** on every frappe_docker bump: rebase our two changes onto
  the new upstream template. **Silent:** new upstream directives are lost because
  our copy replaces theirs; upstream `main` has already changed this template
  since our pin, so the next bump must start from upstream's new file. Our fix
  has only static tests; "Invalid origin" is still listed as open in
  `docs/rebuild-verification.md`, so check realtime on test after any change.
- **Upstream security fixes carried by hand:** because our copy replaces theirs,
  a fix upstream makes in this template does not reach us through a
  frappe_docker bump. Carried so far: the forced-download rule for `/files/`
  (advisory GHSA-94mh-qq29-qwrf, high: the old rule matched lower-case
  extensions only, so an uploaded `poc.SVG` or `poc.HTML` opened in the browser
  and could run script in another user's session). Our copy has upstream's
  v4.3.0 rule word for word since 26 November 2026 (P97): any case, 14 file
  types. **Re-check** on every bump and whenever the daily watch reports a
  frappe_docker advisory: compare this rule and the rest of the file with
  upstream's. Also carried (P98, 26 November 2026): upstream's clearing of
  `X-Forwarded-SSL` and `X-Forwarded-Protocol` in the socket.io and backend
  locations, so the backend sees only the `X-Forwarded-Proto` this template sets.
- **Not carried yet, re-apply at the next frappe_docker bump (P98):** upstream's
  trusted-forwarding map (`TRUST_UPSTREAM_FORWARDED_PROTO`, frappe_docker
  `280fc962eb`). The nginx entrypoint in our pinned image does not fill in that
  variable, so the map would stay literal and every request would look like plain
  http. At the bump: take upstream's map together with their newer entrypoint, set
  `TRUST_UPSTREAM_FORWARDED_PROTO=on` for the frontend in `deployment/stacks/`,
  and change the test that guards this
  (`tests/test_realtime_origin.py`, `ForwardedHeaderTests`). Until then our map
  trusts `X-Forwarded-Proto: https` as upstream's "on" does; that is safe here
  because the public proxy trusts no forwarded headers from outside on its https
  entry point, the frontend is published only on the server's loopback address,
  and Gunicorn trusts only the frontend's own address.
- **Tests:** `tests/test_realtime_origin.py` (Origin; forwarded headers, P98), `tests/test_files_forced_download.py`.
- **Upstream:** reported privately to frappe_docker on 26 November 2026 (the Origin
  overwrite also switches off Frappe's own Origin check). Workaround to retire if
  upstream stops overwriting Origin.

### BUILD-3 Python constraints for the whole bench

- **What and why:** about 280 exact pins applied to every pip/uv install, so the
  reviewed environment is reproducible. `sqlglot` was raised to 30.22.0 for
  Insights 3.50.3 (commit `9ec7d2a`).
- **How:** `deployment/python-constraints.txt`, `tools/prepare_erp_image.py`.
- **Upgrade:** **re-check** on every app bump. **Loud:** resolver conflict at build time.
  No single pin has a recorded reason.

### BUILD-4 Node heap for frontend builds

- **What and why:** `NODE_OPTIONS=--max-old-space-size=3072`; the Insights frontend
  build ran out of memory on an 8 GB host with the default.
- **How:** `deployment/erp/Dockerfile.addon`, `tools/prepare_erp_image.py`.
- **Upgrade:** **re-check**. **Loud:** out-of-memory build failure if bundles outgrow it.
- **Tests:** `tests/test_rebuild_templates.py::test_addon_frontend_build_has_explicit_node_heap`.

### BUILD-5 Hand-made asset link for our add-on

- **What and why:** our app's `public` folder is linked into the bench `assets`
  folder instead of being built with `bench build`; our hooks reference those
  unbundled paths.
- **How:** `deployment/erp/Dockerfile.addon` (`ln -s`).
- **Upgrade:** **re-check** with `tools/verify_erp_assets.py`. **Silent:** 404s if bench
  moves the assets folder.

### BUILD-6 Asset manifest check

- **What and why:** fails when a file named in Frappe's `assets.json` or in any
  app's include hooks is missing. Reason: after a core upgrade, manifest entries
  pointed at files from the old image and Desk apps broke (`docs/retained.md`).
- **How:** `tools/verify_erp_assets.py` (reads Frappe's manifest format).
- **Upgrade:** **re-check:** run it after every upgrade; confirm it still finds the
  manifest (a changed format could make it pass falsely).

### BUILD-7 Payment assets manifest merged at backend start

- **What:** if `/opt/cloud-payment-assets.json` exists, it is merged into the
  bench `assets.json` before gunicorn starts.
- **How:** `deployment/erp/backend_start.py`.
- **Upgrade:** **re-check** whether it is still needed. **To verify:** nothing in the
  repository mounts that file and its purpose is not written down; probably a
  remnant of the manifest repair, and a candidate for removal.

### BUILD-8 PYTHONPATH for the payment apps and our app

- **What:** every ERP role puts the two payment apps and our app on PYTHONPATH.
- **How:** `CI_ERP_*_PYTHONPATH` in `deployment/stacks/inputs.json`;
  `deployment/stacks/erp.compose.json`.
- **Upgrade:** **re-check** whether still required. **Loud:** ImportError. The reason is
  not written down (**to verify**).

### BUILD-9 App list and site creation through a private Frappe function

- **What:** the configurator writes `sites/apps.txt`; `tools/initialize_erp.py` calls
  Frappe's private `frappe.installer._new_site(...)`.
- **Upgrade:** **re-check**. **Loud** (TypeError), but only when a fresh site is created.

### BUILD-10 Two apps pinned to commits on `develop`

- **What:** payment_integration_utils and razorpayx_integration publish no release
  tags, so they are pinned by commit (`deployment/upstream-lock.json`).
- **Upgrade:** **re-check:** move to tags when upstream publishes them; review the
  commit range by hand, because no release notes exist.


### BUILD-11 Face models fetched into the ERP add-on image (P95)

- **What:** OpenCV Zoo's SFace recogniser (fp32, `face_recognition_sface_2021dec.onnx`) and YuNet detector
  (`face_detection_yunet_2023mar.onnx`) with their licence files, at commit `48b10fa`, each checked against its
  SHA-256 in `deployment/face-models.json`; written to `/opt/face-models` with a `model-id` file. Run by the
  `opencv-python-headless` 5.0.0.93 already in the image (pinned in `deployment/python-constraints.txt` through an
  upstream app).
- **How:** `tools/fetch_face_models.py` in `deployment/erp/Dockerfile.addon`; the build stops on any checksum
  difference.
- **Relies on:** with OpenCV 5's graph engine, `FaceDetectorYN.setInputSize` after creation has no effect, so the
  engine creates one detector per photo size (`custom_hr/face_sface.py`, found in the engine test).
- **Upgrade:** **re-check**. A new model pin changes `model-id`, and every enrolled worker must enrol again (the
  service reports them as "needs re-enrolment"). An OpenCV upgrade (through an upstream app) re-runs the live engine
  test (`tests/test_custom_hr_face_engine.py`) in the new image. Training data of the SFace weights is unverified
  (opencv/opencv_zoo#313).
- **Test:** `tests/test_custom_hr_face_engine.py` (pins, fetch refusal, image wiring; live part in the image).
- **Workaround to retire:** the per-size detector, once `setInputSize` works again in OpenCV 5.
## Frappe

Made against: v16.60.2 (`2df0425`).

### FRAPPE-1 Sign-in callback replaced (high priority)

- **What and why:** overrides `frappe.integrations.oauth2_logins.custom` with our
  callback, which re-implements the login flow with Frappe's internal
  `frappe.utils.oauth` functions and adds ID-token checks, the passkey approval
  claim and a freshness window. Reason: sign-in through authentik with passkey
  approval only. Falls back to upstream when single sign-on is not enforced.
- **How:** `override_whitelisted_methods` in `erpnext_drive_integrations/portal/hooks.py`;
  `erpnext_drive_integrations/portal/sso.py`.
- **Upgrade:** **re-check:** a fresh browser passkey sign-in on the test site (not a
  long-lived session). Loud if signatures change; **silent, and possibly a
  security regression,** if the meaning of the OAuth state changes. Read the diff
  of `frappe/utils/oauth.py` and `frappe/integrations/oauth2_logins.py`.
- **Tests:** `tests/test_logout_and_signin.py`, `tests/test_signin_settings.py`
  (fake Frappe, not real Frappe).

### FRAPPE-2 Request rewriting: portal redirects, logout, injected session script

- **What:** `before_request` sends `/desk`, `/login?logged_out`, `/signed-out` and
  deep Desk and Insights page loads into the portal, and logs out revoked
  sessions; `after_request` injects `session.js` into every HTML page (replacing
  `</head>`) and sets `Clear-Site-Data` and `Cache-Control: no-store`.
- **How:** `erpnext_drive_integrations/portal/sso.py`, `portal/hooks.py`.
- **Upgrade:** **re-check:** **silent** if Desk, login or logout routes change.
- **Tests:** `tests/test_portal_deep_link.py`, `tests/test_logout_and_signin.py`.

### FRAPPE-3 Legacy `?cmd=` calls refused on every path

- **What and why:** Frappe 16 runs `?cmd=<guest method>` on any path (audit AUTH-01,
  11 November 2026); we refuse any request with `cmd`.
- **How:** `erpnext_drive_integrations/portal/guard.py`; the same rule in
  `onboarding/respond.py`.
- **Upgrade:** **re-check** whether upstream still dispatches `cmd`; retire the guard if
  not. Nothing breaks if it stays.
- **Tests:** `tests/test_hook_composition.py`, `tests/onboarding/test_respond.py`.
- **Upstream:** frappe/frappe#48437 drops `cmd` dispatch in v17 (not backported);
  we asked there for an opt-in v16 setting (26 November 2026). Workaround until v17.

### FRAPPE-4 Desk logout replaced and idle sessions recovered in the browser

- **What and why:** replaces `frappe.app.logout` (shared-computer logout), checks
  `frappe.auth.get_logged_user` without following redirects, reconnects
  `frappe.realtime.socket` and renews the proxy session in a hidden frame after
  idle time. Reason: the sign-in proxy session (8 h) ends long before the Frappe
  session (170 h), and expired background requests failed silently
  (`docs/idle-navigation.md`, P01). Also draws the test-site marker.
- **How:** `erpnext_drive_integrations/public/session.js`, included through
  `app_include_js` / `web_include_js` and FRAPPE-2.
- **Upgrade:** **re-check** idle return, logout and realtime in the browser. **Silent** if
  `frappe.app.logout` or `frappe.realtime.socket` is renamed.
- **Tests:** static only (`tests/test_portal_deep_link.py`, `tests/test_logout_and_signin.py`).
- **Upstream:** frappe/frappe#39831 (historical, closed; not proven to be the same
  problem).

### FRAPPE-5 Module header and menus drawn over the Desk sidebar

- **What and why:** hides upstream's dock, sidebar header, standard items band and
  Home row, restyles the sidebar, and adds our logo, module picker and fixed
  Edit Sidebar / Help / Search / Notification rows (`docs/retained.md` "Frappe Desk
  menus"). Also removes the "All apps" item: that was once done by editing
  upstream files on the server, and the next build brought it back
  (`docs/decisions.md`). Uses Desk internals such as
  `frappe.app.sidebar.current_module`, `get_sidebar_app()`, `open_module()`,
  `sidebar_header.menu_items()`, `frappe.boot.module_sidebars` and the `page-change`
  and `sidebar-expand` events.
- **How:** `erpnext_drive_integrations/public/module-header-20261115.js`, included
  from `portal/hooks.py`. Affects the ERPNext, HRMS, India Compliance, onboarding
  and Framework Desk screens.
- **Upgrade:** **re-check** visually in every Desk app after every Frappe upgrade.
  **Silent:** it returns early when an internal is missing, leaving a broken or
  duplicated header.
- **Tests:** `tests/test_app_menu_link.py` (static text checks only).

### FRAPPE-6 Boot information rewritten (menus, dock, apps by role)

- **What:** relabels `bootinfo.module_sidebars[*].app` for our modules; filters
  `module_sidebars`, `dock` and `app_data` by role, rebuilding Desktop entries with
  the internal `frappe.desk.doctype.dock.dock.get_app_entry_set` and re-implementing
  `frappe.boot.get_app_data`; reads `DocPerm`, `Custom DocPerm` and `Has Role`
  directly; drops legacy `app_data` entries. The mobile API uses
  `frappe.boot.get_module_sidebars()`.
- **How:** `boot_session` in `erpnext_drive_integrations/hooks.py`; `bootstrap.py`,
  `onboarding/access.py`, `onboarding/api.py`, `custom_hr/web.py`.
- **Upgrade:** **re-check (high priority):** sign in as a limited role and as an
  administrator and compare the menus. **Silent** if bootinfo shapes change (menus
  show everything or nothing); **loud** (Desk does not load) if an internal moves.
- **Tests:** `tests/onboarding/test_access.py`, `tests/onboarding/test_api.py` (fake
  bootinfo shape).

### FRAPPE-7 Portal home built from Frappe's app list

- **What:** the launcher uses the internal `frappe.boot.get_app_data()` and hard-coded
  fallback routes `/desk/setup/home`, `/desk/hr-setup`, `/desk/build`.
- **How:** `erpnext_drive_integrations/www/place_holder.py`.
- **Upgrade:** **re-check** every tile opens. **Silent** (missing tiles, 404s).

### FRAPPE-8 Items added to upstream sidebars at migrate

- **What:** "Field Attendance" in HRMS "Shift and Attendance", "Construction
  Schedule" in ERPNext "Projects", "Vendor Onboarding" and "KYC Amendment" in
  ERPNext "Buying", and an edit to the "HR Setup" custom sidebar, through the
  internal `add_site_sidebar_item`.
- **How:** `after_migrate` in `custom_hr/setup.py`, `onboarding/setup.py`.
- **Upgrade:** **re-check** the items appear. **Loud** (migrate fails) if the function
  moves; **silent** if upstream renames a sidebar.
- **Tests:** none.

### FRAPPE-9 Website Settings written on every migrate

- **What:** `home_page=place_holder`, `disable_signup=1`, favicon and app logo, with
  versioned addresses. Any change made in the settings screen is reverted at the
  next migrate (by design).
- **How:** `erpnext_drive_integrations/bootstrap.py`, `portal/combined.py`.
- **Upgrade:** **re-check:** **silent** if field names change.
- **Tests:** `tests/test_brand_assets.py`.

### FRAPPE-10 Sign-in key, site settings and OAuth clients written by the configure step

- **What:** creates the authentik Social Login Key, writes scheduler, mail-mute and
  host-name site settings, and on test copies rewrites OAuth Client redirect
  addresses or creates public clients.
- **How:** `erpnext_drive_integrations/operations/bootstrap.py` (run by bench, not on
  migrate).
- **Upgrade:** **re-check** field names.
- **Tests:** `tests/test_test_oauth_clients.py`.

### FRAPPE-11 Native-app OAuth codes and tokens bound to the browser session

- **What:** `after_insert` on `OAuth Authorization Code` and `OAuth Bearer Token`
  reads their fields and `frappe.form_dict` during the token request; an
  `auth_hooks` validator and a minutely cleanup revoke tokens. Used by our phone
  apps (Raven's phone app, the first client, went with Raven in P108).
- **How:** `erpnext_drive_integrations/portal/mobile.py`, `portal/hooks.py`.
- **Upgrade:** **re-check** a native-app sign-in on test. Loud (sign-in refused) or
  **silent** (binding skipped) if Frappe's OAuth provider changes how it saves these.
- **Tests:** `tests/portal/test_mobile.py` (fake Frappe).

### FRAPPE-12 Approval push uses workflow internals

- **What:** imports `get_workflow_name`, `get_doc_workflow_state`,
  `get_next_possible_transitions` and `get_users_next_action_data` from Frappe's
  workflow action module; `after_insert` on `Notification Log` and `Workflow Action`.
- **How:** `erpnext_drive_integrations/portal/push.py`.
- **Upgrade:** **re-check** an approval push on test. Fails only in the background job,
  so users **silently** get no pushes.
- **Tests:** none.

### FRAPPE-13 Push through the Frappe push relay

- **What:** posts to the relay's `notification_relay.api.*` as project `hrms`, using
  `Push Notification Settings`; the browser loads Firebase SDK 10.8.0.
- **How:** `erpnext_drive_integrations/portal/push.py`, `public/push-client.js`.
- **Upgrade:** **re-check** when Frappe or HRMS change their push setup. **Silent.**

### FRAPPE-14 Proxy routes that name Frappe endpoints

- **What:** routes that bypass or forward-authenticate
  `/api/method/frappe.integrations.oauth2.get_token`,
  `/api/method/frappe.push_notification.auth_webhook`, Bearer `/api/`,
  `/private/files/` and `/socket.io`.
- **How:** `deployment/config/proxy/cloud-native-clients.yaml` (was `cloud-raven-native.yaml` until P108),
  `cloud-push-registration.yaml`.
- **Upgrade:** **re-check:** **silent** if an endpoint is renamed (it falls behind the
  sign-in gate, which breaks mobile sign-in and push registration).
- **Tests:** `tests/test_rebuild_templates.py::test_test_ingress_has_production_native_app_routes`
  (structure only).

### FRAPPE-15 Realtime server: Node preload that wraps Frappe's code (high priority)

- **What and why:** a `--require` preload replaces `Module._load` to wrap
  `frappe/realtime/middlewares/authenticate.js` and `socket.frappe_request`, and
  overrides `fetch` so callbacks to the backend carry the verified ingress
  identity and the public Host ("Frappe 16 realtime adapter").
- **How:** `deployment/erp/netbird_realtime.cjs`, `deployment/stacks/erp.compose.json`.
- **Upgrade:** **re-check** realtime (live list updates, notifications) on test after
  every Frappe upgrade. **Silent** if the middleware path or `frappe_request` changes.
- **Tests:** none. **To verify:** nothing in the repository reads the headers it adds
  or the `netbird_auth_trusted_proxies` site setting; the consumer may be private
  or left over.

### FRAPPE-16 Backend start wrapper

- **What:** writes `netbird_auth_trusted_proxies` into the site config, sets
  `FORWARDED_ALLOW_IPS`, then starts upstream's `/usr/local/bin/start.sh`.
- **How:** `deployment/erp/backend_start.py`.
- **Upgrade:** **re-check** on frappe_docker bumps. **Loud** (no start) if `start.sh` moves.

### FRAPPE-17 Frappe's bundled Gantt library loaded by path

- **What:** the construction schedule page loads
  `assets/frappe/node_modules/frappe-gantt/dist/...` and uses its API.
- **How:** `erpnext_drive_integrations/onboarding/page/construction_schedule/construction_schedule.js`.
- **Upgrade:** **re-check** the page draws. **Silent** (blank page) if Frappe moves or
  upgrades the library.

### FRAPPE-18 Our own permission rows on Project and Task

- **What:** adds Custom DocPerm rows for Project Coordinator and Projects Manager.
  Once such rows exist, Frappe ignores the standard permissions for that
  doctype, so **upstream permission changes to Project and Task stop applying.**
- **How:** `erpnext_drive_integrations/onboarding/setup.py`.
- **Upgrade:** **re-check:** compare upstream's standard permissions for Task and
  Project on each ERPNext upgrade and carry over what is new.
- **Tests:** none.

### FRAPPE-19 Test-copy quarantine relies on Frappe's tables

- **What:** relies on Frappe 16.60 storing only a hash of the session id; deletes
  from `tabSessions` and `__Auth`; switches off `Email Account`, `Webhook`,
  `Notification`, `Auto Email Report` and `Scheduled Job Type` by field name.
- **How:** `erpnext_drive_integrations/operations/quarantine.py` (test copies only).
- **Upgrade:** **re-check:** **silent** if an upgrade adds a new kind of outgoing
  message or job that is not switched off. **To verify:** whether payment payouts
  and Insights alerts are covered.
- **Tests:** `tests/test_logout_and_signin.py`.

### FRAPPE-20 Minimum Frappe version

- **What:** Frappe must stay at 16.60.1 or newer (GHSA-vwqr-4mjv-ffrm, exploited
  mail-sender flaw).
- **Upgrade:** none while versions move forward; a test fails on a downgrade
  (`tests/test_logout_and_signin.py`).

### FRAPPE-21 Mail health check uses an Email Account internal

- **What:** `Email Account.get_smtp_server().session.noop()`, plus queries on `Error
  Log` and `Email Queue`.
- **How:** `erpnext_drive_integrations/onboarding/monitor.py`.
- **Upgrade:** **re-check:** a change turns into a false "mail server does not answer"
  alert.
- **Tests:** `tests/onboarding/test_monitor.py`.

### FRAPPE-22 One-time module rename patches

- **What:** set `Module Def.custom=1` briefly so Frappe allows the rename; rewrite
  the `installed_apps` global. Only our own modules.
- **How:** `custom_hr/patches/rename_module.py`, `migration.py`, `patches.txt`.
- **Upgrade:** none once applied everywhere. Lesson: after Frappe 16.60.2, module
  sync ran before `pre_model_sync` patches (see Lessons).
- **Tests:** `tests/test_custom_hr.py`.

### FRAPPE-23 Our checks on User, File and Contact

- **What:** `User.validate` / `on_trash`, `File.validate` / `on_trash` (evidence
  protection), `Contact.validate` (changing mail or mobile clears verification;
  relies on the Contact controller syncing primary values before our hook).
- **How:** `portal/hooks.py`, `custom_hr/hooks.py`, `onboarding/hooks.py`.
- **Upgrade:** **re-check.**
- **Tests:** `tests/test_hook_composition.py`.

### FRAPPE-24 Test-data scrambler names upstream doctypes

- **What:** lists of Frappe, ERPNext, HRMS and India Payroll doctypes and
  fields to wipe or rename on test copies. The Raven names stay in the lists (harmless
  when the tables are absent) until no production snapshot holds Raven tables (P108).
- **How:** `tools/cripple_snapshot.py`.
- **Upgrade:** **re-check** the schema changes of every upgrade. **Silent:** new personal
  data fields would not be scrubbed on test.
- **Tests:** `tests/test_cripple_snapshot.py`.

### FRAPPE-25 Native settings set by hand

- **What:** the no-reply Email Account, the Social Login Key, `session_expiry` 170 h,
  `deny_multiple_sessions=0` (`docs/mail-smtp.md`, `docs/deployment.md`,
  `docs/idle-navigation.md`). Production also has more custom fields than a fresh
  install and legacy File-field property setters that were never reconciled
  (`docs/rebuild-verification.md`). Live values are in the private companion.
- **Upgrade:** **re-check** these settings survive the migrate.

### FRAPPE-26 Never uninstall our app with bench

- **What:** `bench uninstall-app` drops the doctypes the app owns (`docs/deployment.md`).
- **Upgrade:** none; a standing rule.

### FRAPPE-27 Face templates rely on Frappe's encryption, field levels and permanent deletion (P95)

- **What:** face templates of field workers are stored encrypted with `frappe.utils.password.encrypt` (the site's
  `encryption_key`), in a field at permission level 1 that no role is granted, with `track_changes` off; they are
  deleted with `frappe.delete_doc(..., delete_permanently=True)` so no copy goes to Deleted Documents.
- **How:** our code and DocType definitions (`custom_hr/face_service.py`, `field_face_enrolment.json`); nothing
  of Frappe's is patched.
- **Files:** `erpnext_drive_integrations/custom_hr/face_service.py`, `custom_hr/doctype/field_face_enrolment/`.
- **Upgrade:** **re-check** that `encrypt`/`decrypt` keep their signature and key, that level-1 fields stay out of
  the form, the list, reports and the REST API for every role, that versions are not written with
  `track_changes` off, and that `delete_permanently` still skips Deleted Documents. Losing the site's
  `encryption_key` makes every template unreadable (workers must enrol again).
- **Test:** `tests/test_custom_hr_face.py` (definitions); on the test site, read a Field Face Enrolment as HR
  Manager through the form and `/api/resource` and confirm `templates` is absent; delete one and confirm no Deleted
  Document row.
- **Workaround to retire:** no.

## ERPNext

Made against: v16.60.0 (`886ab6a`). See also FRAPPE-5, -7, -8, -18.

### ERPNEXT-1 Custom fields on Task, Supplier and Contact

- **What:** `hov_baseline_*` after Task `exp_end_date`; the KYC and vendor
  onboarding fields after Supplier `pan`; `hov_*` after Contact `designation`.
- **How:** `create_custom_fields(update=True)` on every migrate,
  `erpnext_drive_integrations/onboarding/setup.py`.
- **Upgrade:** **re-check** the anchor fields still exist. **Silent:** fields move to the
  end of the form.

### ERPNEXT-2 Supplier, address, contact and bank records rely on naming rules

- **What:** relies on ERPNext naming a Bank Account "`<account_name> - <bank>`" and on
  the fields `branch_code`, `party_type`, `is_company_account`.
- **How:** `onboarding/vendor.py`, `onboarding/kyc.py`.
- **Upgrade:** **re-check** a vendor approval on test. **Loud** at approval time.
- **Tests:** `tests/onboarding/test_onboarding.py`, `tests/onboarding/test_kyc.py`.

### ERPNEXT-3 "Request response" button on Purchase Order

- **What:** a `doctype_js` script that reads `supplier_name`, `supplier`,
  `contact_email`.
- **How:** `onboarding/hooks.py`, `onboarding/client/request_response.js`.
- **Upgrade:** **re-check** the button works.

## HRMS (Frappe HR)

Made against: v16.60.0 (`1b2d7e0`). See also FRAPPE-5, -7, -8.

### HRMS-1 Custom fields on Employee, HR Settings and Attendance

- **What:** placed after `attendance_device_id`, `allow_geolocation_tracking`, `shift`.
- **How:** `custom_hr/setup.py`, on every migrate.
- **Upgrade:** **re-check** the anchors.
- **Tests:** `tests/test_custom_hr.py`.

### HRMS-2 One attendance path: HRMS check-in switched off

- **What and why:** sets `HR Settings.allow_employee_checkin_from_mobile_app=0` (only
  if the field exists), switches off auto attendance on our field-site shifts,
  and blocks `Employee Checkin` (owner decision 22 November 2026, `docs/decisions.md`).
- **How:** `custom_hr/setup.py`, `custom_hr/guards.py`, `custom_hr/hooks.py`.
- **Upgrade:** **re-check:** **silent** if HRMS renames the field (the setting is then
  skipped) or adds a check-in route that does not create `Employee Checkin`.
- **Tests:** `tests/test_custom_hr.py`.

### HRMS-3 Attendance guards and our own attendance

- **What:** `Attendance.validate` lets HRMS leave attendance through and blocks other
  direct edits; cancelling attendance with evidence is blocked; we create and
  submit Attendance ourselves; Employee hooks.
- **How:** `custom_hr/guards.py`, `custom_hr/service.py`, `custom_hr/hooks.py`.
- **Upgrade:** **re-check** a leave approval on test. **Loud** if HRMS changes how leave
  creates attendance.
- **Tests:** `tests/test_custom_hr.py`, `custom_hr/integration_tests.py` (live site).

### HRMS-4 "Request response" button on Job Offer

- **What:** a `doctype_js` script reading `applicant_name`, `applicant_email`.
- **How:** `onboarding/hooks.py` loads `onboarding/client/request_response.js`, the
  same script as Purchase Order. The button shows only when a response rule for
  Job Offer is enabled.
- **Upgrade:** **re-check** the button on a Job Offer.
- **Tests:** `tests/test_hook_asset_paths.py` (every script a hook names must exist);
  `tests/test_js_call_methods.py` (every browser call uses an HTTP method its function accepts).
- **Fixed in P93:** the hook pointed at `client/request_response.js`, which does not
  exist, and Frappe skips a missing file without an error, so the button never
  loaded.
- **Fixed in P93 (27 November 2026):** the script asked `rule_status` with
  `frappe.xcall`, which sends POST by default; `rule_status` accepts GET only, so
  Frappe answered "Not permitted" and the button never showed, on Job Offer and on
  Purchase Order. The script now asks with GET. **Relies on** Frappe's `xcall`
  default (POST) and its refusal of a method the whitelist does not allow.

### HRMS-5 Script injected into the HRMS mobile pages

- **What:** `after_request` injects `launcher.js` into `/hrms*` pages and sets
  `no-store`; the script now only removes a retired launcher.
- **How:** `custom_hr/web.py`, `public/custom_hr/launcher.js`.
- **Upgrade:** none; a candidate for removal.

## India Compliance

Made against: v16.11.1 (`6898239`).

### INDIA-COMPLIANCE-1 Private GSTIN lookup function (high priority)

- **What:** imports the underscore-private
  `india_compliance.gst_india.utils.gstin_info._get_gstin_info` and reads its result
  keys.
- **How:** `erpnext_drive_integrations/onboarding/vendor.py`.
- **Upgrade:** **re-check.** **Silent:** a change shows only "GST lookup is not
  available". The live lookup has never been accepted (no API secret,
  `docs/retained.md`).
- **Tests:** `tests/onboarding/test_onboarding.py` (faked).

### INDIA-COMPLIANCE-2 India Compliance fields on Supplier and Address

- **What:** records are created with `gstin` and `gst_category`; our fields are
  anchored after Supplier `pan`.
- **How:** `onboarding/kyc.py`, `onboarding/setup.py`.
- **Upgrade:** **re-check.**

## Chat (Synapse and the Matrix Authentication Service)

Made against: Synapse v1.166.0, Matrix Authentication Service v1.30.0. Both run unmodified; everything here is
configuration we write (`integrations/chat/configure.py`).

### CHAT-1 Sign-in delegated to the authentication service, which uses only the sign-in service

- **What and why:** Synapse's `matrix_authentication_service` block; passwords and registration off on both sides;
  one upstream OAuth2 provider; people cannot change name or mail address or deactivate their account. One passkey
  sign-in for everything (P73).
- **How:** `integrations/chat/configure.py` (`homeserver`, `mas`), `deployment/stacks/chat.compose.json`.
- **Upgrade:** **re-check:** **loud** if a key is renamed (the service refuses to start); **silent** if a new
  sign-in or registration path is added upstream with a default of "on". Read both release notes for new
  account, registration and login options.
- **Tests:** `tests/test_chat_stack.py`.

### CHAT-2 No federation; rooms not encrypted by default

- **What and why:** `federation_domain_whitelist: []`, no trusted key servers, no federation listener;
  `encryption_enabled_by_default_for_room_type: off`, so the company can keep and search rooms.
- **How:** `integrations/chat/configure.py` (`homeserver`).
- **Upgrade:** **re-check:** **silent** if a default changes. People can still switch encryption on in a room
  they manage until the room rules made by the server side forbid it (P73, not built).
- **Tests:** `tests/test_chat_stack.py`.

### CHAT-4 The business system's bot; invitations accepted automatically

- **What and why:** an application service registration (`bridge.yaml`) for one user, `@erp`, with the aliases
  `#site-…` and `#team-…`, and no call-back address; `auto_accept_invites` for invitations from this server. The
  bot puts people into rooms by inviting them, so nothing holds an admin token. (A client of the authentication
  service cannot get Synapse's admin scope; tried on the test site, 27 November 2026.)
- **How:** `integrations/chat/configure.py` (`bridge`, `homeserver`).
- **Upgrade:** **re-check:** **silent** if `auto_accept_invites` changes its meaning or default (people would
  stop appearing in their rooms); **loud** if the registration format changes (Synapse refuses to start). The room
  rules the bot sets depend on the default room version (12 on the test site: the creator is not listed in the
  power levels).
- **Tests:** `tests/test_chat_stack.py`; live: create, invite, post, remove on the test site.

### CHAT-3 Proxy paths that name Matrix endpoints

- **What:** `/_matrix`, `/_synapse/client` and `/_synapse/mas` go to Synapse; `/_matrix/client/*/login`, `logout`
  and `refresh` go to the authentication service; `/_synapse/admin` is not routed.
- **How:** `tools/prepare_ingress.py` (test site). Production route file: not written yet.
- **Upgrade:** **re-check:** **silent** if upstream adds a delegated path (sign-in from an app then fails).
- **Tests:** `tests/test_chat_stack.py`.

## Insights

Made against: v3.50.3 (`d733108`).

### INSIGHTS-1 Patch on the Insights frontend source

- **What and why:** `frontend/src2/session.ts` takes identity from Insights' own
  signed-in user API instead of a presentation cookie shared with the parent
  domain (production and test cookies collided); `frontend/src2/router.ts` and
  `components/AppSidebar.vue` keep the sidebar visible in workbooks
  (`integrations/insights/README.md`, `docs/source-review.md`).
- **How:** `integrations/insights/patch_session.py`, run and compiled in
  `deployment/erp/Dockerfile.addon`. No compiled bundle is copied.
- **Upgrade:** **re-apply** on every Insights upgrade; it was rewritten once already for
  3.15.1 to 3.50.3 (commit `edf508c`). Every line it changes must appear exactly
  once upstream, or the build stops (since P91; before, a changed `vue` import line
  left `useRoute` undefined at runtime without a build error). Then open a
  workbook on test.
- **Tests:** `tests/test_insights_patch.py`.
- **Upstream:** not reported. Workaround (`deployment/upstream-watch.json`).

### INSIGHTS-2 Insights opens inside the portal

- **What:** top-level `/insights*` loads are sent into the portal and get `session.js`; the
  browser also checks `window.top`, because a single-page app's service worker can fetch
  navigations without `Sec-Fetch-Dest` (`docs/decisions.md` "Portal deep links").
- **Upgrade:** **re-check.**

### INSIGHTS-3 `sqlglot` pinned to Insights' version

- **What:** `sqlglot==30.22.0` for Insights 3.50.3 (BUILD-3).
- **Upgrade:** **re-check** on every Insights upgrade.

## Payment apps and India Payroll

Made against: payment_integration_utils `71ab8cc`, razorpayx_integration `047864d`
(both `develop`), india_payroll v16.1.0 (`495f020`).

- **PAYMENT-1:** PYTHONPATH (BUILD-8), assets manifest (BUILD-7), `develop` pins
  (BUILD-10). **Re-check.**
- **PAYMENT-2:** **to verify:** the test-copy quarantine (FRAPPE-19) names no payout
  or payment doctype, so it is not known whether a restored test copy could
  start outgoing payment actions. **Re-check** before the payment apps are used.
- **INDIA-PAYROLL-1:** only the install list and the test-data scrambler
  (FRAPPE-24). **Re-check** FRAPPE-24.

## authentik

Made against: 2026.8.7. **Production still runs its own sign-in objects made by
hand until P49 is imported: see the private companion (AUTHENTIK-P1 to P11) on
every authentik upgrade.**

### AUTHENTIK-1 Invitation, recovery and sign-in gate inside authentik policies (high priority)

- **What and why:** single-mail invitation; passkey recovery that keeps old keys
  until a fresh approved key is verified; a sign-in gate that admits approved
  passkey providers only (`integrations/authentik/invite-recovery/README.md`);
  P78 multi-attempt links because authentik uses up a single-use link as soon as
  it is opened (`docs/decisions.md`). Works around authentik internals: stage
  re-evaluation gets a copy of the plan context, so we write `flow_plan.context`
  explicitly; the single-use invitation stage clears the invitation's key, so the
  ledger is keyed by name; attempt and recovery ledgers live in
  `Token.description`.
- **How:** objects created through the `ak shell` Django ORM (flow
  `cloud-passkey-recovery-invitation`, its stages, `cloud-invite-*` policies bound
  negated; existing policies rewritten by text replacement; **every** WebAuthn
  setup stage forced to required user verification and resident keys with the
  approved provider list; a gate before login in `cloud-passkey-login`; mail
  stage bindings removed). Relies on `request.context` keys (`flow_plan`,
  `invitation`, `invitation_in_effect`, `pending_user`, `auth_method_args`) and
  model fields of `Invitation`, `Token`, `WebAuthnDevice`, `WebAuthnDeviceType`.
  Files: `integrations/authentik/invite-recovery/` (`native_recovery.py`,
  `install_native.py`, `install_single_email.py`, `provider_policy.py`,
  `recovery_guard.py`, ...), copies in `integrations/authentik/configuration.json`.
- **Upgrade:** **re-check** by running `test_native.py` on a throwaway authentik of the
  new release before touching test. A renamed context key or field **fails closed:
  every passkey sign-in and recovery is refused** (loud, but a lock-out). A
  changed invitation-consumption rule could break attempt counting **silently**.
- **Tests:** `integrations/authentik/invite-recovery/test_native.py` (real authentik,
  rolled back), `test_recovery_guard.py`, `smoke_single_email.py`,
  `tests/test_invitation_configuration.py`.
- **Upstream:** none filed. Partly a workaround (P78 attempts, plan-context copy):
  retire if authentik adds invitation attempt limits.

### AUTHENTIK-2 Admin page template override and "Invite users" entry

- **What and why:** keeps native Invitations and adds an "Invite users" entry beside
  it (`docs/invitation-configuration.md`; the decision says to check both after an
  authentik upgrade).
- **How:** `templates/if/admin.html` extends upstream's template and injects
  `admin-navigation.mjs` in `{% block head %}`; the script walks the admin shadow
  DOM (`ak-sidebar-item`, `#/flow/stages/invitations`, `pf-c-nav__link`). Templates
  mounted at `/templates` (`deployment/stacks/identity.compose.json`).
- **Upgrade:** **re-apply / re-check** in the real admin console. **Silent** if the block,
  route or classes change; loud if upstream removes `if/admin.html`.
- **Tests:** `tests/test_invitation_configuration.py` (static).

### AUTHENTIK-3 Invitation companion app on the sign-in host

- **What:** a router at priority 2000 takes `/admin-invitations/`; nginx
  `auth_request` against `/api/v3/core/users/?page_size=1` is the admin gate; the
  page calls API v3 (`core/users/me/`, `flows/instances/`,
  `authenticators/admin/webauthn/`, `stages/invitation/invitations/` and
  `send_email/`) with the `authentik_csrf` cookie.
- **How:** `integrations/authentik/invite-recovery/` (`nginx.conf`, `traefik.yaml`,
  `public/invitations.mjs`), `deployment/config/proxy/cloud-invitations.yaml`.
- **Upgrade:** **re-check.** API changes show as errors in the form; if authentik ever
  lets non-admins list users, the nginx gate weakens **silently** (authentik's own
  checks stay in force).
- **Tests:** `invite-recovery/test_invitations.mjs`, `tests/test_invitation_page.py`.

### AUTHENTIK-4 Our mail templates

- **What:** `invite-recovery/templates/email/cloud-*.{html,txt}`, chosen by file name,
  using authentik's send-mail context (`url`, `username`); file names can be renamed
  by profile settings. The recovery stage uses upstream's
  `email/account_confirmation.html`.
- **Upgrade:** **re-check** with a test send. **Silent:** a changed context gives broken
  links nobody sees until a mail arrives. Production runs newer pages and templates
  than the repository (`integrations/authentik/README.md`; private AUTHENTIK-P1).
- **Tests:** `test_native.py`, `tests/test_signin_settings.py`.

### AUTHENTIK-5 Brand CSS and look

- **What:** white sign-in background, logo size, rounded card, light theme, through
  `branding_custom_css` with PatternFly 4 classes, `:host(ak-flow-executor)` and
  `[part="locale-select"]` (`integrations/authentik/configuration.json`).
- **Upgrade:** **re-check** on a computer and at phone width. **Silent** (cosmetic) if
  authentik moves to new components.
- **Tests:** `tests/test_authentik_card_corners.py` (static).

### AUTHENTIK-6 Our blueprint carries edited copies of upstream default objects

- **What:** `configuration.json` (rendered by `tools/authentik_blueprint.py`) holds
  edited copies of `default-provider-authorization-implicit-consent`,
  `default-invalidation-flow`, `default-user-settings-flow`, `default-request`,
  `default-user-settings-authorization` and the default OAuth scope mappings, plus
  our own flows, proxy provider (access 5 min, refresh 8 h) and mappings.
- **Upgrade:** **re-check:** authentik's worker re-applies its own default blueprints and
  may **silently** reset those objects; a fresh install from our copy could also
  bring back older defaults. Compare the live objects after the worker restarts.
- **Tests:** `tests/test_rebuild_templates.py`, `tests/test_signin_settings.py`.

### AUTHENTIK-7 Approved passkey providers (AAGUID list)

- **What:** one list, `integrations/authentik/passkey-providers.json`, written into the
  policies, installer and blueprint by `tools/sync_passkey_providers.py`; needs
  authentik's `WebAuthnDeviceType` metadata rows.
- **Upgrade:** **re-check.** Loud if rows disappear (installer asserts); links to deleted
  rows are lost **silently**.
- **Tests:** `tests/test_passkey_providers.py`.

### AUTHENTIK-8 First administrator by passkey; `akadmin` switched off

- **What and why:** upstream's setup page opens when `akadmin` is missing or has no
  usable password, and its bootstrap blueprint recreates `akadmin`
  (`integrations/authentik/first-admin/README.md`, `docs/decisions.md` P77).
- **How:** `integrations/authentik/first-admin/` (`first_admin.py`, `first-admin.sh
  --akadmin-only`).
- **Upgrade:** **re-check** after every upgrade that `akadmin` is inactive and the setup
  page is closed. **Silent** security exposure if upstream changes that logic.
- **Tests:** `tests/test_first_admin.py`.

### AUTHENTIK-9 Mail archive reader access (P69)

- **What:** edits the gate policy expression and binds a group with policy mode "any";
  writes a before-state receipt; refuses a gate edited by hand.
- **How:** `integrations/authentik/archive-reader/archive_reader_access.py`.
- **Upgrade:** **re-check** with its `check` command.
- **Tests:** `tests/test_archive_reader_signin.py`, `archive-reader/test_native.py`.

### AUTHENTIK-10 Test client setup imports authentik internals

- **What:** `integrations/authentik/configure_test_clients.py` imports
  `authentik.blueprints.v1.common.get_attrs`, provider serializers and `Outpost`.
- **Upgrade:** **re-check.** Loud (ImportError).
- **Tests:** `tests/test_test_oauth_clients.py`.

### AUTHENTIK-11 Settings that pin or override upstream defaults

- **What:** `AUTHENTIK_CACHE__TIMEOUT_POLICIES=0` (origin not written down; the
  recovery code needs policy caching off, **to verify**), `AUTHENTIK_WEB__MAX_REQUESTS=1000`
  (freezes today's default), server memory 3 GB, worker as root (reason **to
  verify**), PostgreSQL `jit=off`.
- **How:** `deployment/stacks/identity.compose.json`, `deployment/stacks/inputs.json`.
- **Upgrade:** **re-check** against the new release's defaults.
- **Tests:** `tests/test_signin_settings.py`.

### AUTHENTIK-12 Forward-auth behaviour the apps rely on

- **What:** forward-auth to `/outpost.goauthentik.io/auth/traefik` and its `X-authentik-*`
  headers; every route that bypasses the gate strips those headers (only the
  onboarding route also strips `X-authentik-name`); the 8 h proxy refresh is why
  FRAPPE-4 exists.
- **How:** `deployment/config/proxy/*.yaml`, `tools/prepare_ingress.py`.
- **Upgrade:** **re-check.** **Silent** if authentik adds new identity headers (the strip
  lists become incomplete).
- **Tests:** `tests/test_rebuild_templates.py`, `tests/test_logout_and_signin.py`.

### AUTHENTIK-13 Root sign-in discovery rewritten to one application

- **What:** the sign-in host's `/.well-known/openid-configuration` is rewritten to the
  `office` application's discovery document, for Drive clients that use the root
  issuer (`integrations/drive/config/web-with-picker.json`). Test uses the
  per-application path.
- **How:** `deployment/config/proxy/office-shared-oidc-discovery.yml`.
- **Upgrade:** **re-check** Drive and desktop-client sign-in. Loud if authentik changes
  its provider address layout.
- **Tests:** none.

### AUTHENTIK-14 Other behaviour relied on

- Back-channel logout to the ERP on every OAuth provider, through the relay gateway
  `integrations/authentik/identity-support/nginx.conf`.
- User identifiers are derived from `AUTHENTIK_SECRET_KEY`, so a rebuild must reuse
  the key (`tools/restore_identity.py`, `tests/test_restore_identity.py`).
- Since 2026.8.7 a policy that errors makes its stage fail closed (`docs/decisions.md`
  P83); our gates rely on that.
- Production logs `property_mapping_exception` once or twice a day; not investigated.
- **Upgrade:** **re-check.**

## ownCloud oCIS and ownCloud Web (Drive)

Made against: oCIS 8.2.3, ownCloud Web 12.5.0.

### DRIVE-1 Our script inside ownCloud Web (`workspace.js`)

- **What and why:** hides Drive's bar inside the editor and folds it into ONLYOFFICE,
  hides the app switcher, logo and feedback link, and passes logout to the other
  apps and revokes the refresh token; draws the test-site marker.
- **How:** copied into oCIS web assets and loaded by `scripts` in
  `integrations/drive/config/web-with-picker.json`. Relies on element IDs
  (`#oc-topbar`, `#applications-menu`, `#app-top-bar-close`,
  `#oc-topbar-account-logout`, `#external-onlyoffice`, ...), `aria-label` texts,
  tippy internals, the `/external-onlyoffice/` and `/text-editor/` routes and the token
  storage key `oc_oAuth.user:<authority>:<client>`.
- **Upgrade:** **re-apply / re-check** in the browser. **Silent and security-relevant:**
  if the logout element or storage key changes, logout stops passing on and the
  refresh token is not revoked.
- **Tests:** static only (`tests/test_onlyoffice_editor.py`, `tests/test_logout_and_signin.py`).

### DRIVE-2 Mail attachment picker

- **What:** `integrations/drive/mail-picker.js` ("for ownCloud Web 12.5.0"): Web's embed
  messages `owncloud-embed:file-pick` / `owncloud-embed:cancel`, `resource.webDavPath`,
  `/config.json`, downloads over `/dav/`.
- **Upgrade:** **re-check** attaching a Drive file in webmail. Loud (error in the picker).
- **Tests:** none.

### DRIVE-3 Our copies of oCIS configuration files

- **What:** `integrations/drive/config/`: `web-with-picker.json`, `csp.yaml` (a full copy
  of upstream's default CSP plus our addresses), `app-registry.yaml` (ONLYOFFICE as
  default, DOCX/XLSX/PPTX creation on, ODF off), `apps.yaml`.
- **Upgrade:** **re-apply:** compare each with the new release's defaults and carry over
  new directives and file types. **Silent:** new upstream entries are missing.
- **Tests:** `tools/verify_test_collaboration.py` checks the creation flags on test.

### DRIVE-4 Our Web theme

- **What:** `integrations/drive/theme/theme.json`, derived from upstream's
  `themes/owncloud/theme.json`, selected by `WEB_UI_THEME_PATH`. The Drive tab icon is
  still ownCloud's (open item).
- **Upgrade:** **re-apply** if the theme format changes (likely **silent** fall-back).

### DRIVE-5 Editor bridge registration workarounds (temporary)

- **What and why:** oCIS advertised one of its network addresses at random, and the
  editor bridge (collaboration) learns which editors exist only when it starts itself
  (`docs/decisions.md` P57; P80 and P81 open). Restarting or recreating oCIS alone
  leaves Drive without an editor until the bridge restarts (outages 19, 20 and 25
  November 2026).
- **How:** the bridge joins every oCIS network (`NETWORK_PEERS` in
  `tools/prepare_runtime.py`); the boot check restarts it once on `AddAppProvider failed`
  / `i/o timeout` (`tools/host_check.py`); restarted after a test restore
  (`tools/verify_test_collaboration.py`); `depends_on: service_healthy`. Manual rule
  until P80/P81 are built: **after any oCIS restart, restart collaboration and open a
  document.**
- **Upgrade:** **re-check** by opening a document after every oCIS upgrade or restart.
  **Silent** (Drive offers download instead of editing) if the log text changes.
- **Tests:** `tests/test_reboot_resilience.py`, `tests/test_host_checks.py`.
- **Upstream:** added to owncloud/ocis#3832 (registration refresh, open) on 26 November
  2026; the OpenCloud fork fixed it with periodic re-registration
  (opencloud-eu/opencloud#1035). Retire when oCIS re-registers itself.

### DRIVE-6 Test-copy scrambler rewrites oCIS storage directly

- **What:** `tools/cripple_snapshot.py` reads and writes decomposedfs node metadata
  (`.mpk`, `user.ocis.*` keys) and walks the spaces, blobs, trash and uploads folders.
- **Upgrade:** **re-check** with a real snapshot on a throwaway host. **Silent:** a format
  change can leave personal data unscrambled or the test copy corrupt.
- **Tests:** `tests/test_cripple_snapshot.py` (synthetic data only).

### DRIVE-7 oCIS APIs our code calls

- **What:** app tokens at `/auth-app/tokens` (needs `OCIS_ADD_RUN_SERVICES=auth-app` and
  `PROXY_ENABLE_APP_AUTH`) in `integrations/document-worker/document-worker.py`,
  `erpnext_drive_integrations/drive_store/drive.py`, `tools/enroll_worker.py`; Graph
  `/graph/v1.0/me`, `/me/drives`, tags; WebDAV; `/app/list`.
- **Upgrade:** **re-check.** Loud (errors in worker logs).
- **Tests:** `tests/test_drive_store.py`, `tests/test_retarget_worker.py` (mocked).

### DRIVE-8 Settings that override oCIS defaults

- **What:** start command `ocis init || true; exec ocis server`;
  `OCIS_EXCLUDE_RUN_SERVICES=idp`, `PROXY_OIDC_REWRITE_WELLKNOWN=true`, the secure-view
  app address tied to `COLLABORATION_APP_NAME`, auto-provisioning and role settings;
  thumbnail sizes = **a copy of upstream's default list** plus 256x256 (P74).
- **How:** `deployment/stacks/drive.compose.json`, `deployment/stacks/inputs.json`.
- **Upgrade:** **re-apply** the thumbnail list from the new release's default; **re-check**
  the rest. **Silent:** our copy hides upstream changes to the default list.
- **Tests:** `tests/test_drive_store.py`.

### DRIVE-9 Desktop and iOS client registration constants

- **What:** the client identifiers compiled into ocis-konnectd, pinned in
  `deployment/native-clients-lock.json` with a checksum and used by
  `tools/prepare_native_drive_clients.py`.
- **Upgrade:** **re-check** when a client release changes them. Loud (client sign-in fails).

## ONLYOFFICE Docs (office editor)

Made against: 10.0.0 build 169 (package `onlyoffice-documentserver` 10.0.0-169, checked
on the pinned image 26 November 2026).

### OFFICE-1 Patched WOPI start page over the image's own file (re-apply every upgrade)

- **What and why:** ONLYOFFICE Community ignores the official layout options. Our
  page carries the agreed layout, the always-light theme, private sheet views, the
  view cap, the retry keeper, the AGPL "modified version" notice and the test marker
  (`integrations/onlyoffice/README.md`, `docs/decisions.md` P42).
- **How:** `integrations/onlyoffice/editor-wopi.ejs` (and the unmodified
  `editor-wopi.original.ejs`), mounted read-only over
  `/var/www/onlyoffice/documentserver/web-apps/apps/api/wopi/editor-wopi.ejs`. Injects
  CSS and DOM changes into the editor frame by element ID and uses `Asc` sheet-view
  APIs.
- **Upgrade:** **re-apply** with the README procedure: `tools/refresh_editor_original.py`
  copies the new image's own start page (without starting the image) and records
  image and checksum in `integrations/onlyoffice/upstream.json`; then re-apply our
  marked parts. **Loud** since P91: the tests fail unless the stored original, that
  record and the image in the stack agree, so a digest bump alone fails CI. The
  record was checked against the pinned image on 26 November 2026.
- **Tests:** `tests/test_onlyoffice_editor.py`, `tests/test_refresh_editor_original.py`,
  `tests/test_onlyoffice_private_views.py` (headless Chrome).

### OFFICE-2 Sheet-view empty-filter crash guard (temporary)

- **What and why:** in 10.0.0 build 169, an empty column filter makes
  `CT_NsvFilter.IU()` throw and the workbook goes blank.
- **How:** in `editor-wopi.ejs`, a patch of **minified** methods (`IU`, `zq`, `Eh`, ...)
  that applies only while the unsafe method is detected; repair tool
  `integrations/onlyoffice/sheetview_sanitize.py`.
- **Upgrade:** **re-check;** minified names change in every build, so the guard switches
  itself off **silently** (safe if upstream fixed it, unsafe if not). Test whether the
  new build still crashes; remove the guard once it does not.
- **Tests:** `tests/test_onlyoffice_sheetview_filter.py`.
- **Upstream:** ONLYOFFICE/DocumentServer#3954 (26 November 2026). The throwing code is
  unchanged in sdkjs `v10.0.0.176` and master.

### OFFICE-3 Start command removes a stale supervisor PID file

- **What and why:** a reused PID made the image skip supervisord and the editor
  returned 502 (`docs/decisions.md`).
- **How:** `deployment/stacks/editor-onlyoffice.compose.json` runs
  `rm -f /var/run/supervisord.pid; exec /app/ds/run-document-server.sh`.
- **Upgrade:** **re-check.** Loud if the script moves. Retire if upstream cleans it up.
- **Tests:** `tests/test_onlyoffice_editor.py::test_stale_supervisor_pid_removed_on_start`.

### OFFICE-4 Our `local-production-linux.json`

- **What:** save every 2 minutes instead of only after everyone closes (P61);
  `request-filtering-agent.allowPrivateIPAddress: true` (overrides an upstream security
  default so the private WOPI host is reachable); `ipfilter` naming the bridge
  (ONLYOFFICE 10 calls only WOPI hosts in its ipfilter); `wopi.enable`. Environment:
  `GENERATE_FONTS=false` (reason **to verify**), JWT and WOPI settings.
- **How:** `deployment/config/onlyoffice-local-production-linux.json`.
- **Upgrade:** **re-check** key names. **Silent** if a key is renamed (saves only on close).

### OFFICE-5 Shutdown, cache and internal command API relied on

- **What:** 5 minutes stop grace so the image's `documentserver-prepare4shutdown` saves
  open documents; upstream cache expiry defaults; `tools/editor_safety.py` uses the
  internal `http://localhost/command` (`getForgottenList`, `getForgotten`, `forcesave`,
  `drop`), the log paths and log line format (`PutFile`, `storeForgotten`,
  `changesError`) and the cache path.
- **Upgrade:** **re-check.** **Silent:** a changed log format makes the safety watch blind.
- **Tests:** `tests/test_editor_safety.py`.

### OFFICE-6 Free edition's touch editor is view-only

- **What:** phones use the desktop editor (`docs/decisions.md` P42).
- **Upgrade:** **re-check** on a phone.

### OFFICE-7 The editor's status page and internal interface stay private at the proxy

- **What and why:** ONLYOFFICE 10 has no admin panel. Its status page (`/info`) and
  cluster interface (`/internal`), also under a `/<version>/` prefix, are allowed to
  localhost only by its own nginx rules, which do not trust forwarded addresses, so
  they are refused through the proxy (checked on test 26 November 2026: 403). The
  test ingress also keeps them private (P92), so they stay closed even if the
  info page is turned on as ONLYOFFICE's documentation describes. This replaced a
  rule for Collabora's admin paths, which ONLYOFFICE does not have. Production has
  no such proxy rule and relies on ONLYOFFICE's own.
- **How:** `office-admin` in `tools/prepare_ingress.py`; ONLYOFFICE's
  `/etc/onlyoffice/documentserver/nginx/includes/ds-docservice.conf`.
- **Upgrade:** **re-check** the paths ONLYOFFICE restricts in that file (new private
  interfaces), and that `/info/` returns 403 through the proxy.
- **Tests:** `tests/test_rebuild_templates.py::test_ingress_references_and_narrow_public_response_routes`.

## Stalwart mail

Made against: 1.1.1. Mail retention (P69) is on draft PR #69 and is not on `main`;
it adds its entries when it merges.

### MAIL-1 Set-up through Stalwart's admin JMAP API

- **What:** `integrations/mail/stalwart_bootstrap.py` ("native Stalwart v1.1 JMAP") calls
  `x:Directory`, `x:Bootstrap`, `x:Domain`, `x:Account`, `x:Authentication`,
  `x:SystemSettings`, `x:NetworkListener`. Workarounds: bootstrap mode is detected
  by the error text `'bootstrap mode'`; a container restart activates bootstrap;
  another restart because the running server caches session advertisements.
- **Upgrade:** **re-check** on an isolated server. Loud. 1.2.0 needs a manual role
  permission step and adds protocols retention would have to cover (`docs/decisions.md`
  P75), so it is not adopted yet.
- **Tests:** none (runs during test refresh, `tools/restore_test_data.py`).

### MAIL-2 Sender-only service accounts

- **What:** `integrations/mail/smtp_senders.py`: `x:Account` with a custom role allowing
  only sign-in and sending, and `x:AppPassword` with allowed addresses
  (`docs/mail-smtp.md`).
- **Upgrade:** **re-check.** **Silent** if the permission model changes and the accounts
  get wider rights.

### MAIL-3 Routes and certificates

- **What:** `/jmap`, `/dav`, `/.well-known/{jmap,caldav,carddav}` go to Stalwart and it
  answers the certificate challenge for the mail host
  (`deployment/production/mail.traefik.yaml`, `deployment/config/proxy/office-acme.yml`);
  the set-up turns off Stalwart's own certificate request.
- **Upgrade:** **re-check** certificate renewal dates.
- **Tests:** `tests/test_rebuild_templates.py`.

### MAIL-4 Stalwart behaviour to check after restarts

- **What:** after a reboot, settings held in memory went stale (JMAP 500) until
  `ReloadSettings` (P57 item 7, not built); the image's log folder did not exist, so
  Stalwart wrote no logs (fix on the P69 branch). `dnsZoneFile` regenerates itself;
  ignore it in settings comparisons.
- **Upgrade:** **re-check** sign-in and logs after every restart or upgrade.

### MAIL-5 Mail store backed up as an opaque database

- **What:** stopped and copied for backup and export; not scrambled on test.
- **Upgrade:** **re-check** the restore drill.
- **Tests:** `tests/backup/test_backup.py`.

## Bulwark webmail

Made against: commit `933bc18` (1.21.2), `integrations/mail/upstream.json`.

### WEBMAIL-1 Whole-file overlay on upstream's source (re-apply every upgrade)

- **What:** replaces whole upstream files: login page, sign-in callback, main layout,
  mail composer (Drive attach button), auth store (logout hook) and the `Dockerfile`
  (`SENTRYCLI_SKIP_DOWNLOAD=1`); adds the session guard, test marker, Drive attach
  button and `lib/cloud-session.ts`.
- **How:** `integrations/mail/overlay/`, applied by `tools/prepare_mail.py`, which also
  packs the matching source for the AGPL.
- **Upgrade:** **re-apply** by a three-way merge of each file against the new commit:
  `tools/refresh_webmail_overlay_base.py --checkout <clone>` lists the files upstream
  changed, then `--write` records the new base. **Loud** since P91:
  `overlay_base` in `integrations/mail/upstream.json` holds the upstream checksum of
  every file we replace, `tools/prepare_mail.py` stops when the clone differs, and
  the tests fail when the commit changes without it. Checked against a clone of the
  pinned commit on 26 November 2026.
- **Tests:** `tests/test_webmail_overlay_base.py`; constants in
  `tests/test_logout_and_signin.py`, `tests/test_rebuild_templates.py`.

### WEBMAIL-2 Admin policy and blocked admin routes

- **What:** `/app/data/admin/policy.json` with `filesEnabled: false`; public `/admin`,
  `/api/admin` and `/setup` blocked except `GET /api/admin/policy`;
  `STALWART_ADMIN_ACCESS=off`, `BULWARK_TELEMETRY=off`, `AUTO_SSO_ENABLED=true`.
- **Upgrade:** **re-check.** **Silent** if the policy format or admin paths change (Files
  could come back on, or admin could be exposed).
- **Tests:** `tests/test_rebuild_templates.py`.

### WEBMAIL-3 Framing settings must come from compose `environment`

- **What:** frame ancestors and the parent origin are set in `environment`, not
  `env_file`; Mail framing was lost once when they were carried over the wrong way.
- **Upgrade:** **re-check** webmail opens inside the portal.

## Paperless-ngx (documents)

Made against: 3.4.2.

### DMS-1 Our Django app inside Paperless

- **What and why:** the documents app follows portal sign-in and logout
  (`integrations/dms/README.md`). `cloud_session` is added through `PAPERLESS_APPS` and
  `PYTHONPATH`, appends a middleware in `ready()`, serves `/cloud-session.js`, logs out
  on a session mismatch and **injects a script before `</body>`** of HTML responses.
- **How:** `integrations/dms/cloud_session/`, `deployment/stacks/dms.compose.json`.
- **Upgrade:** **re-check** sign-in and logout. **Silent** if Paperless or Django builds
  the middleware earlier or changes how pages are served.
- **Tests:** static (`tests/test_rebuild_templates.py`, `tests/test_logout_and_signin.py`).

### DMS-2 Set-up through the Django shell

- **What:** `integrations/dms/bootstrap.py` uses permission codenames of the `documents`
  models and the DRF token.
- **Upgrade:** **re-check.** **Silent:** a renamed model gives groups narrower or wider rights.

### DMS-3 Test-copy scrambler writes SQL against Paperless tables

- **What:** `tools/cripple_snapshot.py` scrubs documents, correspondents, tags, notes,
  custom fields, mail accounts, social accounts, users, audit log and share links;
  `tools/export_snapshot.py` skips sessions and tokens.
- **Upgrade:** **re-check** the schema changes. **Silent:** new personal-data tables or
  columns stay unscrubbed on test.
- **Tests:** `tests/test_cripple_snapshot.py` (synthetic).

### DMS-4 Paperless API used by the document worker

- **What:** tags, documents (`full_perms`, `set_permissions`), notes, tasks (accepts two
  response shapes) in `integrations/document-worker/document-worker.py`.
- **Upgrade:** **re-check.** Loud.

### DMS-5 Sign-in settings and framing

- **What:** OIDC settings, regular login off, `CONSUMER_DELETE_DUPLICATES=false`; at the
  proxy, X-Frame-Options is removed and the CSP is **replaced** with `frame-ancestors`
  (`deployment/config/proxy/place-holder-frames.yaml`, `deployment/production/dms.traefik.yaml`).
- **Upgrade:** **re-check.** **Silent:** CSP directives Paperless adds are dropped by ours.

## Processing, databases and small components

- **TIKA-1** Apache Tika 3.2.3: plain image. **None.**
- **GOTENBERG-1** Gotenberg 8.40.0: `--chromium-disable-javascript=true`,
  `--chromium-allow-list=file:///tmp/.*` (hardening). **Re-check** flag names (loud).
- **COREDNS-1** CoreDNS 1.15.0: the Corefile is kept by the operator outside the
  repository. **Re-check** it.
- **MARIADB-1** MariaDB 11.8.9: character-set flags, `MARIADB_AUTO_UPGRADE=1`, the image's
  `healthcheck.sh`, tools call `mariadb` / `mariadb-dump`. **Re-check** (loud).
- **POSTGRES-1** PostgreSQL 16.16 / 17.12: identity runs with `jit=off`; a major version
  needs dump and restore; the documents health check hard-codes `-U paperless`.
  **Re-check.**
- **REDIS-1** Redis: broker with `--appendonly yes`; restore runs `FLUSHALL`. **None.**
- **NGINX-1** nginx: our own full `nginx.conf` for the identity gateway and invitation
  companion (Docker DNS `127.0.0.11`) and the website `default.conf`. **Re-check** (low).
- **MONITORING-1** Prometheus, Grafana, Loki, Alloy, node_exporter, cAdvisor
  (`integrations/monitoring/observability/compose.yml`): pinned and, since P91, in
  `deployment/upstream-watch.json` (the watch now reads the module compose files).
  **Re-check** at upgrade.

## Traefik (Coolify's proxy)

### PROXY-1 Response headers rewritten so apps open inside the portal

- **What:** X-Frame-Options removed for Drive, ONLYOFFICE and Mail; the DMS CSP replaced
  (DMS-5). `deployment/config/proxy/place-holder-frames.yaml`, `tools/prepare_ingress.py`.
- **Upgrade:** **re-check** each app opens in the portal.

### PROXY-2 Routes that bypass the sign-in gate

- **What:** push, native phone-app, onboarding response and invitation routes at higher
  priority, each stripping identity headers (AUTHENTIK-12, FRAPPE-14).
- **Upgrade:** **re-check.**

### PROXY-3 HTTP/3 off and `Alt-Svc: clear` for the relayed test host (temporary)

- **What and why:** browsers reused an open production connection, and HTTP/3 reached
  production's 503 page (`docs/decisions.md`). `tools/prepare_ingress.py`,
  `tools/coolify_proxy_hosts.py`, `tools/coolify_proxy_http3.py`.
- **Upgrade:** **re-check.** Retire when test is no longer relayed.
- **Tests:** `tests/test_rebuild_templates.py`.

### PROXY-4 Forwarded headers trusted on the private entry point only

- **What and why:** without it the proxy dropped `X-Forwarded-Uri` and sign-in landed on
  the landing page; the auth bridge exists because a second HTTPS proxy replaced
  `X-Forwarded-Host`. `tools/sso_proxy_trust.py`, `tools/prepare_auth_bridge.py`.
- **Upgrade:** **re-apply** if Coolify resets the proxy (private PROXY-P2).
- **Tests:** `tests/test_sso_proxy_trust.py`, `tests/test_rebuild_templates.py`.

### PROXY-5 Traefik v3 syntax and internal services

- **What:** `ipAllowList`, `HeaderRegexp`, `PathRegexp`, `noop@internal`,
  `acme-http@internal`; a HostSNI rule cannot list several host names, and the relay
  router needs an explicit priority (`tools/prepare_test_relay.py`).
- **Upgrade:** **re-check** on a major Traefik upgrade (loud: configuration refused).

### PROXY-6 Own certificate per name; two Let's Encrypt resolvers (P11)

- **What:** every public name gets a Let's Encrypt certificate from Traefik.
  - **Production names:** HTTP challenge (`acme-http@internal`), with challenge routes
    above all other port-80 routes for those names (`own-certificate-acme-validation`
    in `deployment/config/proxy/office-acme.yml`).
  - **Relayed test names:** a second resolver `letsencrypt-tls` with the TLS-ALPN
    challenge (proxy flags from `tools/coolify_proxy_tls_resolver.py`; it shares the
    ACME storage), so their port-80 challenges keep reaching the test host.
  - **Relies on:** Traefik skips any name that a loaded certificate covers, without
    checking its expiry date (`getUncheckedDomains` in 3.7.20). So no copied
    certificate may be loaded for these names. The challenge handler answers only its
    own tokens.
  - The manual live item, removing the copied wildcard from production, is in the
    private companion.
- **Upgrade:** **re-check** on a Traefik upgrade: certificates renew (dates in the
  HTTPS probe), each production name's port-80 challenge path still reaches Traefik,
  and the running proxy still has the second resolver (`--check`). **Re-apply** if
  Coolify resets the proxy configuration.
- **Tests:** `tests/test_rebuild_templates.py::test_every_certificate_name_answers_its_http_challenge`,
  `test_test_relay_terminates_and_forwards_only_test_hosts`,
  `test_tls_resolver_flags_are_added_once_and_keep_the_rest`.

## Coolify

### COOLIFY-1 Services registered through Coolify's internals

- **What:** `tools/coolify_native.py` runs PHP in the Coolify container with
  `App\Models\Server/Project/Service`, `->parse(isNew:)`, `new_public_id()`,
  `connect_to_docker_network` and `/data/coolify/services/<uuid>`. Workaround:
  Coolify's parser writes an empty `ports` list as null and empty `volumes` as `{}`,
  which Compose rejects, so empty fields are dropped first.
- **Upgrade:** **re-check.** Loud. Retire the workaround when Coolify fixes its parser
  (reported as coollabsio/coolify#12667, 26 November 2026).
- **Tests:** `tests/test_rebuild_templates.py::test_coolify_registration_drops_empty_ports_and_volumes`.

### COOLIFY-2 Direct edits of Coolify's stored proxy configuration

- **What and why:** Coolify rebuilds the proxy from its stored copy at boot, and a
  proxy restart from its dashboard drops service networks. Our tools update
  `servers.proxy` (`last_saved_proxy_configuration`, `last_saved_settings`) in
  `coolify-db` and the proxy compose file (`tools/coolify_proxy_hosts.py`,
  `tools/coolify_proxy_http3.py`, `tools/sso_proxy_trust.py`).
- **Upgrade:** **re-check** after every Coolify upgrade and reboot. **Silent** if Coolify
  regenerates the proxy without our settings.
- **Tests:** `tests/test_rebuild_templates.py`.

### COOLIFY-3 Other reliance on Coolify storage

- **What:** `tools/drift_check.py` reads `services.description`; `tools/restore_identity.py`
  reads the backed-up service compose; production uses route files instead of
  container labels because a Coolify redeploy can silently restore old settings
  (`docs/production-moves.md`). A re-render can bring back an older stored image.
- **Upgrade:** **re-check.**
- **Tests:** `tests/test_promotion_plan.py`, `tests/test_restore_identity.py`.

### COOLIFY-4 Nightly Docker cleanup deletes the ERP core image (temporary)

- **What:** the forced cleanup removes unused images, including the ERP core and
  images built the evening before; about 20 minutes of rebuild per release until P71.
  Switched off by hand on the test VM (private PROXY-P4).
- **Upgrade:** **re-check** which cleanup the new Coolify runs (`docs/production-moves.md`).

## Host: Docker, Tailscale, TrueNAS, RustFS

- **DOCKER-1** `tools/test_egress.py` inserts rules into the `DOCKER-USER` chain and needs
  IPv6 off on that network. **Re-check.**
- **TAILSCALE-1** Docker starts after `tailscaled` and waits for the tailnet address (a
  drop-in from `tools/render_host_checks.py`); the trusted PROXY-protocol source is the
  Docker gateway because Tailscale masquerades forwarded traffic. **Re-check** unit names
  (**silent** if ordering is lost). Tests: `tests/test_host_checks.py`.
- **TRUENAS-1** TrueNAS snapshot tasks refuse internal app storage, so a root cron job
  runs `integrations/backup/zfs-snapshot-guard.sh` (temporary; TrueNAS does not list
  these snapshots). **Re-check** after TrueNAS upgrades. Tests:
  `tests/backup/test_backup.py`.
- **RUSTFS-1** `integrations/backup/harden_storage.py` uses S3 versioning and lifecycle;
  RustFS rejected the `s3:PutLifecycleConfiguration` action name, so the tool was
  changed, and the key policy was attached by hand. **Re-check** with `verify`.
- **HOST-1** systemd units and cron entries installed by hand from rendered templates:
  see private HOST-P1. **Re-check** after OS or Docker upgrades.

## Mobile app (Expo, React Native)

- **MOBILE-1** Windows Android build: short worktree folder (260-character path limit in
  the SQLCipher C++ build), `pnpm install --config.node-linker=hoisted`, undo
  `expo prebuild`'s `package.json` change, CMake 3.31.6, JDK 17, arm64 only
  (`mobile/README.md`). **Re-check** on SDK upgrades.
- **MOBILE-2** Jest maps `lucide-react-native` to its CommonJS bundle
  (`mobile/package.json`; reason **to verify**). **Re-check.**
- **MOBILE-3** `predictiveBackGestureEnabled: false` (reason **to verify**),
  `useSQLCipher: true`, React Compiler experiment (`mobile/app.json`). **Re-check.**
- **MOBILE-4** Planned Android package `in.unformat.erp`: Kotlin files need backticks
  around `in` (expo#26910), and an open SDK 58 bug means always prebuild with
  `--clean` (expo#53158). From P82 research, **to verify** when the trial starts.
- pnpm supply-chain settings (`mobile/pnpm-workspace.yaml`) are our policy, not a
  workaround. **None.**

## Retired

- **Collabora** was retired with P42 (the upstream comment was posted on
  CollaboraOnline/online#16276). **None.** Its deployment instructions and ingress
  rule were removed in P92; older records mention it as history.

## Lessons from earlier upgrades

1. Restarting or recreating oCIS alone silently drops the editor until the bridge
   restarts; health checks do not see it. Open a document after every Drive or editor
   change (25 November 2026 outage).
2. Coolify's nightly cleanup deletes unused images, including the ERP core and images
   built the evening before. Keep the core outside Docker and build on the morning of
   the release.
3. Coolify rebuilds the proxy from its stored copy at boot: a change made only to the
   file vanishes after a reboot. Save it through Coolify (COOLIFY-2).
4. Recreating the proxy drops Coolify's service networks; use the tool that re-attaches
   them.
5. Compose `environment` overrides `env_file`; when carrying settings over, compare
   with the running container (Mail framing lost on 19 November 2026).
6. A claim name can move: the ERP required a new claim, the live mapping sent the old
   one, and new sign-ins failed for days while long sessions hid it. Do a fresh
   browser passkey sign-in after every ERP or identity deploy.
7. After the Frappe 16.60.2 upgrade, module sync ran before `pre_model_sync` patches.
   Rehearse migrations on test with real data.
8. Version labels can lie (an app's branch tip differed from the tag in production).
   Compare source trees, not labels.
9. After a core upgrade, asset manifest entries pointed at the old image and broke
   Desk apps. Run `tools/verify_erp_assets.py`.
10. A Stalwart reboot left stale settings and no logs. Reload settings and check
    sign-in after a restart.
11. Files written by root with umask 077 inside the identity and webmail containers
    broke sign-in (HTTP 500) and webmail (crash loop). Make rendered files readable.
12. An advisory check was skipped once and Frappe stayed on a version with a known
    high advisory. Check advisories before every promotion.
13. Rendering from a stale checkout wrote a wrong commit into the profile. Use one
    public checkout per host.
14. Container logs vanish on recreate. Archive them first (P61).
15. The Insights build depends on the host's memory; keep the Node heap pinned.
16. Renders without the live inputs changed live names (public mail client name,
    webmail display name). Seed renders with the live inputs.
17. Database and Redis stop-grace settings apply only when those containers are
    recreated, not on an image-only restart.
18. The reboot drill on test caught ordering problems. Repeat it after host or Docker
    changes.
19. Removing the "All apps" item by editing upstream files on the server lasted only
    until the next build. Change upstream behaviour only in this repository.

## Open questions found while building this register

Found on 26 November 2026 and reported to the owner; none of them is changed by P89.

- **HRMS-4:** fixed in P93.
- **OFFICE-1, WEBMAIL-1, BUILD-1, INSIGHTS-1:** fixed in P91 (each check now fails
  loudly on a changed upstream file, image or commit).
- **Upstream watch:** fixed in P91 (`workaround` notes for every app with entries here;
  monitoring images watched).
- **Collabora leftovers:** fixed in P92 (READMEs; the ingress rule now guards
  ONLYOFFICE's own private paths, OFFICE-7).
- **ONLYOFFICE version:** fixed in P91 (10.0.0 build 169 everywhere).
- **Left-over or unexplained code:** BUILD-7 (payment assets manifest), BUILD-8
  (PYTHONPATH), FRAPPE-15/16 (the NetBird names: nothing reads those headers; NetBird
  is not pinned or watched), HRMS-5 (retired launcher script).
- **WhatsApp:** fixed in P92 (correction note in `docs/decisions.md`: the wrapper is
  planned under P04, not built; WhatsApp is not installed).
- **Upstream reports** (now tracked with every check and follow-up in `docs/upstream-posts.md`): filed 26 November 2026: owncloud/ocis#3832 (comment),
  ONLYOFFICE/DocumentServer#3954, coollabsio/coolify#12667, frappe/frappe#48437
  (comment), shridarpatil/frappe_whatsapp#257 (comment on the open signature-check
  fix), goauthentik/authentik#16049 and #14304 (comments), #28187 and #28188 (new
  requests), and a private report to frappe_docker (Origin overwrite).
