# Reproducible build and deployment (`deployment`)

Pinned upstream and build locks, ERP core and add-on builds, runtime rendering, native Coolify registration, ingress, ERP initialisation, asset checks, offline checks and CI.

## Purpose

Rebuilds the whole system from this repository and pinned public sources: ERP core and add-on images, runtime rendering of every stack, native Coolify registration, ingress, ERP initialisation, asset verification, offline checks and CI.

## Contents

- `deployment/**`
- `tools/build_erp_core.py`
- `tools/prepare_erp_image.py`
- `tools/prepare_runtime.py`
- `tools/render_runtime.py`
- `tools/prepare_ingress.py`
- `tools/prepare_auth_bridge.py`
- `tools/test_host_aliases.py`
- `tools/coolify_native.py`
- `tools/initialize_erp.py`
- `tools/migrate_asset_references.py`
- `tools/verify_erp_assets.py`
- `tools/check_repository.py`
- `tools/run_unit_tests.py`
- `tools/README.md`
- `tests/test_rebuild_templates.py`
- `tests/test_realtime_origin.py`
- `tests/test_module_manifest.py`
- `.github/**`

Excluded (owned by other modules): `deployment/stacks/drive.compose.json`, `deployment/stacks/mail.compose.json`, `deployment/stacks/dms.compose.json`, `deployment/stacks/processing.compose.json`, `deployment/stacks/identity.compose.json`, `deployment/stacks/identity-support.compose.json`, `deployment/drive-clients.example.json`, `deployment/native-clients-lock.json`, `deployment/scope-mappings.example.json`, `deployment/test-refresh-worker.*`, `deployment/test-runtime.example.json`

## Requirements

Modules: none.

A Linux Docker host with Coolify; Python 3.14 in the ERP image for the tools; network access to the pinned upstream sources during builds.

## Reuse

Use `tools/prepare_erp_image.py` + `tools/build_erp_core.py` for a reproducible Frappe/ERPNext image from `upstream-lock.json`, or `tools/prepare_runtime.py` + `tools/coolify_native.py` to render and register stacks on any Coolify host. See tools/README.md for every tool by module.

## Configuration

Read docs/deployment.md first. This directory and integrations contain source/configuration examples, not production secrets or business backups.

- `runtime.example.json`: public domain/branding/protocol rendering input. Store the actual file outside the checkout. Do not put secrets in public_replacements.
- `erp/site-config.example.json`: addon feature switches and host/issuer settings. Merge deliberately with a newly created site's native DB/encryption settings. Finish native Social Login Key/provider setup before turning on enforced SSO. Never replace a live site_config wholesale with this example.
- `drive-clients.example.json`: observed public native-client IDs, exact callback constraints, global issuer and token lifetimes. The desktop/iOS registrations have their own credential requirements; credentials are not exported. Client changes require renewed compatibility testing.
- `scope-mappings.example.json`: generic custom verified-email, approved-identity, Files-group and mailbox mapping expressions. Native standard profile/email scopes, signing keys and provider settings remain necessary. Replace the example identity/mailbox mapping and preserve the single-email verification attributes written by the invitation flow. Do not make every arbitrary email verified.
- `upstream-lock.json`: public upstream revision pins for reconstructing the nine prerequisite products. These pin source inputs; native data/configuration and build dependencies still have to be supplied.
- `erp/Dockerfile.addon`: layer this single addon on the prepared ERP image. Deploy the same image to all ERP roles; keep a curated apps.txt rather than listing every unused directory in an image.
- `erp/frappe.conf.template`, backend_start.py and netbird_realtime.cjs: retained frontend/startup/realtime adapters. Preserve private ingress boundaries. The separately deferred idle/realtime defect is not fixed by these files.
- `integrations/authentik/identity-support`: optional private TLS/backchannel gateway and invitation companion composition. Adapt Docker aliases/networks and supply certificates privately; it publishes no host ports. Its internal ERP backchannel still validates signed logout tokens in the addon. The invitation companion source is in its own sibling directory.

Create separate native Coolify projects for ERP, authentik/identity helpers, Drive/collaboration, Collabora, Mail, DMS and the document worker. Create and retain their native database/storage volumes and private application networks. Configure public DNS/TLS for the documented host map, with Coolify/mail administration private. Native product configuration is explicit setup work: clone cannot manufacture provider accounts, signing keys, mailbox credentials, API credits or data.

Rebuild order: prerequisite ERP image and native site → authentik/passkey flows and app providers → addon/native migration → Drive/editor → Mail and DMS → owner-bound worker enrollment → acceptance checks. Configure SMTP-only senders and shared-mailbox membership through native Stalwart settings. Retain only the selected integration sender; don't copy mailbox credentials from an old installation.

For later code updates: fetch/review the chosen Git commit, render outside Git, build an immutable image, pause/drain processing and back up, run the native migration, save the matched image in the existing Coolify service definitions and deploy all ERP roles. Verify the record/app/SSO/UI checks before resuming work. Do not edit core vendor files or overwrite running source with an unreviewed git pull. Keep image/data/config rollback together.

## Tests

- `tests/test_promotion_plan.py`
- `tests/test_rebuild_templates.py`
- `tests/test_realtime_origin.py`
- `tests/test_module_manifest.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- frappe_docker (official build recipe) — MIT — https://github.com/frappe/frappe_docker
- Coolify — Apache-2.0 — https://github.com/coollabsio/coolify
- Traefik — MIT — https://github.com/traefik/traefik
- nginx — BSD-2-Clause — https://nginx.org

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## Promotion plan and drift check (P59)

No stack is left behind at a release (on 21 November 2026 the website stack missed a fix
because production stacks are promoted one by one and nothing listed what a merge reached).

- **`deployment/promotion-map.json`** says, for every tracked file, which stacks, setup
  steps, live settings (authentik) and restarts it reaches when it changes, and what the
  test site cannot cover (production-only route files; sign-in, which test shares with
  production). A test fails when a file matches no rule, and checks the map against the
  files `tools/prepare_runtime.py` mounts into each stack.
- **`tools/promotion_plan.py FROM TO`** (or `--files ...`) prints that list as Markdown for
  the pull request (template section "Promotion plan") and the release record; exit 1 when
  a file is unclassified.
- **`tools/drift_check.py --config ...`** on production, read-only: for each stack it finds
  the commit it runs (Coolify's "Source commit" record written by `tools/coolify_native.py`,
  a profile or receipt with a `commit`, or a container's image tag or revision label) and
  reports the stack as **behind** when a file it owns changed between that commit and
  `main`, **not on main** when it runs another branch, and **unknown** when its commit
  cannot be read. It also compares served pages with local files (for example the landing
  page script and the ERP favicon). Signals: exit 0 clean, 1 a check could not run, 2 drift;
  `/var/lib/cloud-drift-check/status.json`; one journal line. Settings example:
  `deployment/drift-check.example.json`; nightly timer `deployment/drift-check.*.example`;
  also run it by hand after every promotion (`AGENTS.md`).
- Not compared yet: Coolify's stored compose definition against the rendered one (Coolify
  adds its own labels, so they are never equal byte for byte).

## Reboot resilience (P57)

A reboot or restart must bring every stack back without manual repair.
`tools/prepare_runtime.py` keeps the Drive editor bridge on every network
oCIS is on (`NETWORK_PEERS`; oCIS advertises one of its own addresses at
random at each start) and the stacks give the databases `stop_grace_period`
of 60 s and Redis 30 s. `tools/render_host_checks.py` renders a Docker drop-in
(start after Tailscale, wait up to a minute for the tailnet address), a boot
check (`tools/host_check.py boot`: containers, hosts over HTTP, tailnet ports,
and a one-time restart of the editor bridge if it cannot register) and a
five-minute watch for containers that keep restarting. Checklist, planned
reboot procedure and install commands: `docs/production-moves.md`; private
section example: `deployment/host-checks.example.json`; tests:
`tests/test_reboot_resilience.py`, `tests/test_host_checks.py`.

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
