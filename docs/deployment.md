# Deployment and reconstruction

## Inputs kept outside Git

Prepare a domain, Linux Docker host, private administrator network, DNS/TLS control, company branding, an authentik administrator and fresh per-application credentials. Business records, native settings, session encryption keys and API tokens are not source code. Keep them in persistent volumes/native secret stores and back them up separately. Example addresses in this repository are reserved examples.

Use `erp.example.com` for the portal, `sso` for authentik, `drive` for oCIS, `office` for ONLYOFFICE Docs, `mail` for authenticated web/JMAP/DAV, `dms` for Paperless and `respond` for restricted private-link forms. The editor hostname remains necessary even without a separate launcher. Keep the Coolify UI and mail administration on the private administrator network.

## Frappe prerequisite image

The prerequisite image can now be built from this checkout and pinned public
sources. It does not require an image copied from an existing deployment:

```sh
python3 tools/prepare_erp_image.py --output /srv/build/erp-core
docker build --secret id=apps_json,src=/srv/build/erp-core/apps.json \
  -t cloud-integrations/erp-core:16.60.2 /srv/build/erp-core
docker build --build-arg ERP_BASE_IMAGE=cloud-integrations/erp-core:16.60.2 \
  -f deployment/erp/Dockerfile.addon -t cloud-integrations/erp:0.1.0 .
```

`build-lock.json` pins the official Docker recipe and Python base image;
`upstream-lock.json` pins all nine app repositories. The preparer fetches exact
commits, checks them, and gives the official builder local Git sources. Python
constraints pin the reviewed environment; Node, Yarn and Bench versions are
locked separately. Public dependency downloads require network access during
the build. An AMD64 build of the core and addon completed on 15 November 2026.
That build result is distinct from the complete service acceptance checks below.

Install Frappe/ERPNext v16 with Python 3.14 and their supported MariaDB/Redis/Node dependencies using the official Frappe Docker build process. Install HRMS, India Compliance, Insights, Payment Integration Utils, RazorpayX Integration and India Payroll from their upstream repositories. Pin the revisions in the upstream lock rather than following moving branches on production. Their source, licenses and migrations remain upstream responsibilities.

Persist the Frappe sites, uploaded files, logs and custom session registry. Use one identical app image for backend, websocket, short/long workers and scheduler. The frontend must serve assets from that same release. Never let a sites/assets symlink point to an older image's manifest. Rebuild all required upstream assets and verify every manifest entry is present.

For a fresh installation:

1. Render this addon into a separate build directory using `tools/render_runtime.py` and private runtime configuration.
2. Build `deployment/erp/Dockerfile.addon` with `ERP_BASE_IMAGE` set to the prepared upstream image. The build context is the rendered directory. This installs the single editable package into the existing bench environment.
3. Add `erpnext_drive_integrations` to the bench's apps.txt, mount the persistent session registry writable by the bench user, and run `bench --site SITE install-app erpnext_drive_integrations`.
4. Configure the enabled features in site_config.json, then migrate/build assets and restart all app services together. The field feature requires HRMS. Turning off a feature is not a data-removal operation.

Do not install the three former packages alongside it on a fresh site.

## Existing-site consolidation

Never run `uninstall-app` on the source packages: it can remove owned DocTypes and data. Back up database, files, site configuration, session registry, native Coolify Compose and all source mounts first. Rehearse on a disposable isolated database with no external network and no scheduler.

Prepare a private migration-plan JSON with `source_apps` (the three existing technical IDs) and `module_names` mapping the three existing Module Def names to `Cloud Integrations`, `Cloud Field`, and `Onboarding`. Call `erpnext_drive_integrations.migration.consolidate(plan_path, apply=False)` to inventory ownership and business record counts. The applying mode renames module metadata and replaces installed-app membership without dropping tables. Commit only after receipt validation; run the native site migration afterward. A schema change after commit requires restoring the matched database/files/config/image snapshot for rollback.

Pause scheduler and queues and drain running jobs before production cutover. Replace all three source registrations in apps.txt, update persisted RPC/config references, synchronize scheduled jobs, and verify record counts after migration. `cloud_legacy_rpc_aliases` may privately map former whitelisted RPC names to their new names during phased rollout. It does not add permissions or allow arbitrary methods. Remove aliases only after all clients/configuration have migrated. Run tools/migrate_asset_references.py in the bench environment with a private explicit old-to-new asset-prefix mapping, inspect its dry run, and apply it to Website/Navbar/Portal settings so saved branding does not point at retired addon paths. This tool deliberately excludes business records.

## Authentik and application sessions

Create a single ordinary-users sign-in group. Administrator rights remain separate. Bind each app/provider to this group; document/mailbox permissions are still app-local. Preserve signed email/sub/approval checks and require a fresh passkey after central logout.

- ERP: confidential OIDC provider, exact native Frappe callback, signed approved-user claim, trusted issuer/JWKS, and the addon's backchannel logout endpoint. Configure the native Social Login Key and private `cloud_oidc_issuer`; enable `cloud_sso_enforced`. Persist the shared registry and encryption key across releases.
- Drive: separate web, desktop and iOS OIDC clients with identical display title **Drive**. Web uses its exact HTTPS callback; desktop uses loopback callbacks; iOS uses its exact registered URI. Keep the Web public client secret-free and PKCE enabled. Match the desktop/iOS client type and native registration requirements to the actual client release; configure their matching credentials privately. See deployment/drive-clients.example.json for observed non-secret IDs/callback constraints. Refresh-token lifetime is an explicit policy setting, not a source default.
- DMS: configure native Paperless OIDC, least-privilege office-group permissions and the matching owner/sharing model. Mount `integrations/dms/cloud_session` through Django's additional-app mechanism and include its session middleware/assets as documented in the source.
- Mail: configure Stalwart's restricted OIDC directory and Webmail's matching client. Shared-mailbox membership/send-as and SMTP-only integration credentials are separate native settings. Do not expose administrator pages with the public authenticated UI/API.

Enrollment/recovery source and the administrator companion are under `integrations/authentik/invite-recovery`. Read its deployment notes before executing installers: inventory native flows/provider metadata and supply an existing approved administrator and baseline enrollment flow. Retain native invitation backend APIs. Source tests are not proof of completed physical-device registration.

## Phone apps, notification and private ingress

`portal/mobile.py` binds selected native OAuth clients to an approved browser session and requires PKCE S256. Enable it only for the exact configured native client IDs. At ingress, strip caller-supplied identity headers, retain the validating forward-auth check and restrict preflight to exact native origins/methods. A Bearer header alone never grants access. Preserve Frappe's native token validation and document permissions.

Push needs native provider registration and per-device opt-in. Configure secrets only in native encrypted fields. The addon's dedicated push worker has no fetch/cache handler and must not replace other apps' offline workers. Preserve exact static-worker and secret-challenge callback routes. See source-review.md for the boundary between retained ERP/Raven functionality and retired callbacks.

## Separate workspace applications

Use separate Coolify projects. Apply the matching source overlays to pinned upstream releases, not arbitrary latest builds:

- **Drive:** load `integrations/drive/workspace.js` and `mail-picker.js` as Web extensions, configure trusted frame origins and WOPI collaboration, and set ODF creation actions off while retaining DOCX/XLSX/PPTX. This is a creation-menu policy, not an upload ban.
- **ONLYOFFICE Docs:** layout, private sheet views and Drive integration come from the patched WOPI start page (`integrations/onlyoffice/`); keep the WOPI `ipfilter`, JWT and frame/message origin checks. Collabora was retired in November 2026 (P42).
- **Mail:** start from integrations/mail/upstream.json, copy the overlay to the corresponding paths, build with the upstream lockfile and include corresponding modified source in the distributed build. Store company branding in runtime configuration; Files/storage is disabled in the native Webmail policy. Keep the Drive picker and session bridge together.
- **DMS worker:** deploy `integrations/document-worker/document-worker.py` as its own service, with persistent private state and a read-only mounted secret configuration. Enroll users individually with revocable Files/Paperless tokens. The worker maps owner permissions; shared-space copies may be shared with the ordinary-users group. Never put user tokens in this repository or browser code.

## Verification and updating

Run offline syntax/security/domain tests before building. Verify fresh passkey sign-in, central logout from every initiating app, anonymous/fake-token rejection, native desktop/iOS redirects, each app's permissions, editor opening/saving, shared mailbox send-as, worker ownership and business record counts. Test a real device separately for native sync and push; a successful mocked relay request is not device delivery.

Commit source/config templates, build a versioned immutable image from the selected commit, back up, migrate, and deploy that image to every ERP role. Do not pull mutable source directly into a running bench. Retain the previous image plus matching data/config backup until acceptance passes. Never publish rendered production source, native configuration backups or migration receipts containing private data.

Outstanding acceptance and provider-dependent work remains in the maintainers' task list (private operations repository). Off-server backup destination/restore testing and long-idle recovery are explicitly deferred; they are not silently enabled by installation.
