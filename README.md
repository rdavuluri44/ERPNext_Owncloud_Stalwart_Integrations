# ERPNext_drive_integrations 0.1.0

A modular Frappe v16 addon plus separate adapters for an ERP portal, authentik SSO, phone-app sign-in and push, field operations, onboarding, ownCloud Drive, ONLYOFFICE, Mail and Paperless.

## Mandatory release workflow

**Repository first → permanent test environment → validated production promotion.**
Every development change must follow this sequence without bypasses. See
[AGENTS.md](AGENTS.md) for the nonnegotiable contributor and automation rules.

## Modules

The repository is one installable Frappe app plus deployment tooling, organised as
self-contained modules (owner principle 6). [modules.json](modules.json) assigns every file to
exactly one module and records its dependencies, tests and upstream licenses;
`tests/test_module_manifest.py` enforces it. Each module README explains how to reuse that
module on its own.

| Module | What it does | README |
| --- | --- | --- |
| `erp-addon-shell` | The single installed Frappe app: hook composition with per-feature switches (cloud_features), bootstrap, migration, shared role fixtures and app logos. | [erpnext_drive_integrations/README.md](erpnext_drive_integrations/README.md) |
| `portal-sso` | Portal home, authentik SSO sign-in and global logout, shared-browser logout guard, idle proxy-session recovery (P01), native mobile login binding, web push, module header and placeholder/signed-out pages. | [erpnext_drive_integrations/portal/README.md](erpnext_drive_integrations/portal/README.md) |
| `custom-hr` | Our HR additions to Frappe HR: field sites, supervisor-recorded team attendance with photo and location, PM approval, checkout, and the mobile app's HR functions. | [erpnext_drive_integrations/custom_hr/README.md](erpnext_drive_integrations/custom_hr/README.md) |
| `onboarding` | Vendor onboarding with KYC and amendments, single-use device-bound response links (yes/no, documents) with audit trail, WhatsApp consent capture, construction schedule page and monitoring. | [erpnext_drive_integrations/onboarding/README.md](erpnext_drive_integrations/onboarding/README.md) |
| `onlyoffice-editor` | ONLYOFFICE Docs start page for Drive (WOPI): space-saving layout, single side strip with menu button, automatic private sheet views, light theme, About with modification notice. | [integrations/onlyoffice/README.md](integrations/onlyoffice/README.md) |
| `drive` | Workspace adapter for the ownCloud web client (editor chrome, theme, outside-click), Mail attachment picker, Drive configuration templates and native desktop/mobile client registrations. | [integrations/drive/README.md](integrations/drive/README.md) |
| `mail` | Bulwark Webmail overlay (SSO login, Drive picker, policy), Stalwart bootstrap and SMTP sender definitions, mail build preparation, and the ERP mailbox administration DocType and access report. | [integrations/mail/README.md](integrations/mail/README.md) |
| `dms` | Paperless-ngx session adapter for portal SSO and the Django-shell bootstrap for approved roles and worker enrollment. | [integrations/dms/README.md](integrations/dms/README.md) |
| `document-worker` | Moves new Drive uploads into Paperless with owner-preserving permissions and generated links; enrollment and link retargeting tools. | [integrations/document-worker/README.md](integrations/document-worker/README.md) |
| `authentik-identity` | Retained authentik blueprint (providers, applications, scope mappings), test client creation, invitation recovery service and identity-support adapters. | [integrations/authentik/README.md](integrations/authentik/README.md) |
| `insights-adapter` | Patches the pinned Insights frontend to take identity from the native authenticated API before it is compiled. | [integrations/insights/README.md](integrations/insights/README.md) |
| `deployment` | Pinned upstream and build locks, ERP core and add-on builds, runtime rendering, native Coolify registration, ingress, ERP initialisation, asset checks, offline checks and CI. | [deployment/README.md](deployment/README.md) |
| `website` | Company front page: static, tenant-neutral page with an original pencil tunnel-construction drawing drawn in batches, typed launch text and an Employee Zone link; pinned read-only nginx stack, production routes for `www` and the bare domain, and the test front-page route. | [integrations/website/README.md](integrations/website/README.md) |
| `test-refresh` | Restricted production snapshot export, test-side restore with quarantine of outbound integrations and credentials, refresh button and progress, test profiles, egress policy and the verification tools used for acceptance. | [docs/modules/test-refresh.md](docs/modules/test-refresh.md) |
| `mobile-app` | Native iOS and Android app (Expo): passkey sign-in bound to the browser session, role-filtered menus, read-only lists and records, app lock, tablet split view and sunlight mode. | [mobile/README.md](mobile/README.md) |

One Frappe app is installed: **erpnext_drive_integrations**. Logical navigation entries do not create extra installed apps. Features can be selected through site configuration cloud_features; disabling a feature does not delete its data.

Start with docs/source-review.md, docs/deployment.md, docs/retained.md and docs/production-moves.md. Upstream products, DNS, provider accounts and private runtime secrets are external prerequisites. Cloning supplies source and instructions; it cannot reproduce credentials or business data.

The [carried-forward roadmap](docs/roadmap.md) reconciles the eight selected earlier plans with the current stack. The [P list](docs/p-list.md) is the project's full work list, organised by app ([ERP](docs/p-list/erp.md), [portal](docs/p-list/portal.md), [sign-in](docs/p-list/signin.md), [Drive](docs/p-list/drive.md), [editor](docs/p-list/editor.md), [mail](docs/p-list/mail.md), [DMS](docs/p-list/dms.md), [Raven](docs/p-list/raven.md), [mobile](docs/p-list/mobile.md), [test site](docs/p-list/test-site.md), [general](docs/p-list/general.md)) (every P number in commits, pull requests and READMEs): scope, status, priority order and dependencies, published from the maintainers' private list with only names, addresses, paths and similar identifiers replaced. Dated operations records (release log, migration runbooks with real addresses, handovers) are kept in a private operations repository.

The [persistent test rebuild runbook](docs/test-rebuild-runbook.md) covers native
Coolify registration, isolated app builds, shared SSO and one-way four-app refresh.
The [dated acceptance record](docs/test-acceptance.md) distinguishes the tested
replica from the provider/device and future-feature work.

## Offline validation

Use Python 3.14 in the matching ERP image:

    python tools/check_repository.py
    python tools/check_client_identity.py
    python tools/run_unit_tests.py

Never run invitation/native migration smoke scripts against production without their documented rollback/mock requirements. Feature and permission tests are separate from actual-device acceptance.

## Runtime rendering

Keep a private JSON file outside Git with domain, optional company_logo, session_state_path and any public protocol compatibility replacements. Run:

    python tools/render_runtime.py --config /etc/cloud-integrations/runtime.json --output /srv/cloud-integrations/build

Only public values belong in public_replacements. Store OAuth secrets, registry keys and app tokens in the application's native secret stores or private mounted files. Build directories are disposable; persistent data is not.

## Acknowledgements

<!-- OPEN-SOURCE:START (generated by tools/open_source.py) -->
This small-office system is built on open-source projects, used, integrated or configured here: Frappe
Framework, ERPNext, Frappe HR, India Compliance, India Payroll, Frappe Insights, Payment Integration Utils,
RazorpayX Integration, Frappe Bench, frappe_docker (official build recipe), Frappe Suite (app icons),
authentik, ownCloud Infinite Scale, ownCloud Web, ocis-konnectd, ONLYOFFICE Docs, Stalwart Mail Server,
Bulwark Webmail, Paperless-ngx, Apache Tika, Gotenberg, Coolify, Traefik, nginx, Docker Engine (Moby),
MariaDB, PostgreSQL, Redis, Python, Node.js, CoreDNS, Tailscale, Linux kernel, Ubuntu, TrueNAS, restic,
RustFS, Grafana, Loki, Alloy, Prometheus, node_exporter, cAdvisor, Expo and Expo Router, React Native, React,
OpenCV (opencv-python-headless), OpenCV Zoo: SFace and YuNet, Synapse, Matrix Authentication Service, Sygnal
and Element Web. Used before: Raven (removed from the ERP image in P108 (owner, 27 November 2026); Matrix
replaces it as the internal chat (P73)), Collabora Online (used until November 2026, replaced by ONLYOFFICE
Docs, P42). Thank you to their communities. Each remains under its own licence; the full list with licences,
where each is used, how we track it and what we are evaluating is in
[docs/open-source.md](docs/open-source.md) (see also LICENSES.md).
<!-- OPEN-SOURCE:END -->

## AI-assisted development

Development of this repository is assisted by AI agents (Anthropic's Claude).
Every change follows the repository → test → production workflow and is
reviewed and accepted by the owner, but users and contributors should be aware
of the AI assistance.

## License

Copyright © 2026 unformat.in. This repository is free software
under the **GNU Affero General Public License v3.0 or later**
([LICENSE](LICENSE)): if you run a modified version as a network service, you
must offer its users the modified source. Upstream products, the app icons
from frappe/suite and the Bulwark and ONLYOFFICE derived files keep their own
notices; see [LICENSES.md](LICENSES.md).

Names such as ERPNext, Frappe, ownCloud, ONLYOFFICE, Stalwart, authentik and
Paperless-ngx are trademarks of their owners and are used here only to say
what this repository integrates with; it is not affiliated with or endorsed
by them.

## Contributing

Fork, branch from `main`, open a pull request; see [CONTRIBUTING.md](CONTRIBUTING.md).
No production upgrade or destructive removal is implied by a source checkout.

See [docs/decisions.md](docs/decisions.md) for the decisions behind this setup, [docs/upstream-customizations.md](docs/upstream-customizations.md) for our changes to upstream apps and what to redo when they are upgraded, and [docs/disaster-recovery.md](docs/disaster-recovery.md) for recovery and ransomware protection.
