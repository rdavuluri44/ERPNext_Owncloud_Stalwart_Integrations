# Tools

Every tool belongs to one module (modules.json). Tools stay in this directory so the
paths used by running servers (for example the production snapshot export and the test
refresh worker) do not change; this index groups them by module.

## Reboot resilience (`deployment`)

- `host_check.py` — Post-boot check, crash-loop watch and tailnet wait for a Docker host (P57).
- `render_host_checks.py` — Render its config, systemd units and the Docker start-after-Tailscale drop-in from the private profile.

## Upstream watch (`deployment`)

- `open_source.py` — One list of every open-source project we use, borrow from or evaluate; renders the README acknowledgements and `docs/open-source.md` and checks them against the upstream watch and `modules.json` (P35).
- `upstream_posts.py` — The list of our posts on other projects and a read-only check for replies, state changes and unlisted posts; `check --gh --record` at every session start (P35).
- `upstream_watch.py` — Daily digest of new releases, security advisories, end of life and licence changes for every pinned component, from public sources only; never upgrades anything (P62).

## Drive (ownCloud Infinite Scale) adapters (`drive`)

- `prepare_native_drive_clients.py` — Populate private fresh-identity inputs from pinned official native defaults.

## Mail (Stalwart and Bulwark Webmail) (`mail`)

- `prepare_mail.py` — Prepare pinned upstream Mail plus the selected overlay and corresponding source; stops when the upstream files differ from the overlay's recorded base (P91).
- `refresh_webmail_overlay_base.py` — Move the webmail overlay to a new upstream commit: lists the files to merge, then records the new base (P91).

## Drive to DMS document worker (`document-worker`)

- `enroll_worker.py` — Enroll revocable, owner-scoped TEST/production document worker credentials.
- `retarget_worker.py` — Retarget only worker-generated links after a TEST data refresh.

## authentik identity configuration (`authentik-identity`)

- `authentik_blueprint.py` — Render the retained native authentik graph, without exporting any users/keys.

## ONLYOFFICE editor (`onlyoffice-editor`)

- `editor_safety.py` — Editor file safety (P61): list and rescue parked edits, unstick a document, and a five-minute watch for failed saves, disk and cache; never deletes a document.
- `refresh_editor_original.py` — On an image change, copy the new image's own start page to `editor-wopi.original.ejs` without starting it, and record image and checksum in `integrations/onlyoffice/upstream.json` (P91).

## Reproducible build and deployment (`deployment`)

- `build_erp_core.py` — Build the prepared public ERP core with the pinned official apps_json input.
- `check_repository.py` — Offline syntax, schema, import (P68: imports of our own modules and names must exist) and publication checks. Never reads a live site.
- `coolify_native.py` — Register a prepared Compose service through local Coolify's native models.
- `initialize_erp.py` — Initialize one empty ERP site using the pinned native installer.
- `migrate_asset_references.py` — Rewrite retired addon asset prefixes in system settings, never business text.
- `prepare_auth_bridge.py` — Render a source-IP-limited forward-auth bridge on an existing SSO host (one or more public test addresses; optional separate private-entry-point router).
- `sso_proxy_trust.py` — On the SSO host, trust forwarded headers on the private (tailnet) entry point used by the test sign-in bridge, from exact addresses only (normally the test VM; `prepare_auth_bridge.py --print-forwarded-trust`), so the sign-in gateway returns to the requested page (P65). Writes the proxy compose file and Coolify's saved proxy configuration; never touches public entry points; the proxy restart is a separate step.
- `prepare_test_relay.py` — Render a pass-through relay (SNI, PROXY protocol, port 80) for the six test hostnames on another Traefik host, for a test host without a public address.
- `coolify_proxy_http3.py` — Switch HTTP/3 off on a relay host's Coolify proxy (saved configuration and compose file).
- `coolify_proxy_tls_resolver.py` — Add the TLS-ALPN Let's Encrypt resolver (`letsencrypt-tls`) to a relay host's Coolify proxy, for the relayed test names (P11); `--restart`, `--check`.
- `coolify_proxy_hosts.py` — Persist the proxy's workspace network/aliases and optional private (tailnet) host pins in Coolify's saved proxy configuration and compose file.
- `prepare_erp_image.py` — Prepare an ERP build entirely from pinned public sources, with no private image; every change to frappe_docker's Containerfile must find its upstream line exactly once (P91).
- `prepare_ingress.py` — Render complete workspace ingress for a controller's existing Traefik proxy.
- `prepare_runtime.py` — Prepare portable native service mounts/configuration from a Git checkout.
- `promotion_plan.py` — List the stacks, steps, live settings and restarts a change reaches, and what test cannot cover (P59).
- `drift_check.py` — Read-only check on production that every stack runs what `main` says, that the mounted runtime files equal main or their deployment record (P99), and that served pages match (P59).
- `runtime_mounts.py` — Which runtime mount is made from which repository file; the record of what was mounted, and `record` for a one-file promotion (P99).
- `render_runtime.py` — Render public deployment URLs into a build tree; never edit the Git checkout.
- `run_unit_tests.py` — Run mock-based rules/security suites in separate processes, without a live site.
- `test_host_aliases.py` — Resolve this test host's own HTTPS services locally, retaining TLS checks.
- `verify_erp_assets.py` — Read-only native-bench asset manifest/hook check; run inside the ERP image.

## Permanent test site and one-way refresh (`test-refresh`)

- `activate_test_refresh.py` — Enable the test-only button/timer after a verified production snapshot restore.
- `export_snapshot.py` — Restricted production -> test data export. There is no restore/import path.
- `prepare_test_profiles.py` — Derive root-private test refresh/bootstrap profiles from native receipts. `erp_site_settings` in the private profile sets the test site's own portal look (allow list: `cloud_portal_hide_entity_name`, `cloud_portal_logo_height`, `cloud_portal_logo_position`, `cloud_portal_clean_root_address`).
- `rehearse_empty_test.py` — Rehearse four-app restore ONLY on a fresh test without business documents.
- `restore_test_data.py` — Restore a verified four-app data snapshot into one explicit TEST runtime.
- `snapshot_archive.py` — Validate data-only refresh archives before touching any test service.
- `test_egress.py` — Restrict the isolated test workspace to local apps and its existing SSO.
- `test_refresh_worker.py` — Consume fixed test refresh requests; all privileged configuration is host-only.
- `verify_test_collaboration.py` — Activate and verify native test Drive office registration after cold restore.
- `verify_test_processing.py` — Create one synthetic personal PDF on test and verify Drive -> DMS processing.
- `verify_test_queues.py` — Run a timestamp-only job through each test ERP queue, without business writes.

Development of these tools is assisted by AI agents (Anthropic's Claude); see AGENTS.md.
