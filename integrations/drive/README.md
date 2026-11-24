# Drive (ownCloud Infinite Scale) adapters (`drive`)

Workspace adapter for the ownCloud web client (editor chrome, theme, outside-click), Mail attachment picker, Drive configuration templates and native desktop/mobile client registrations.

## Purpose

Integrates ownCloud Infinite Scale as the office Drive: an editor workspace adapter (chrome, theme from the editor, outside-click), the Mail attachment picker, configuration templates and native client registrations.

## Contents

- `integrations/drive/**`
- `deployment/stacks/drive.compose.json`
- `deployment/drive-clients.example.json`
- `deployment/native-clients-lock.json`
- `tools/prepare_native_drive_clients.py`

## Requirements

Modules: `authentik-identity`.

ownCloud Infinite Scale and Web at the versions noted below; module `authentik-identity` for sign-in; module `onlyoffice-editor` for the editor start page.

## Reuse

Serve `workspace.js` and `mail-picker.js` as oCIS Web external assets and mount the `config/` files; register native clients with `tools/prepare_native_drive_clients.py`.

## Configuration

The config directory contains sanitized retained examples for oCIS 8.2.3 / Web 12.5.0. Initialize oCIS with its native `ocis init` to generate private service secrets; those generated secrets are deliberately absent here. Keep native storage, service configuration and proof keys persistent outside Git.

Render the example domain and deploy these public files through the native oCIS configuration mounts:

| Source | Deployment purpose |
| --- | --- |
| config/web-with-picker.json | Web config: server/issuer, scripts and empty external_apps |
| config/app-registry.yaml | Office MIME registry (default app ONLYOFFICE); DOCX/XLSX/PPTX creation enabled, ODF creation disabled |
| config/csp.yaml | Native Web CSP; only the retained portal origin is included in the example |
| config/apps.yaml | Native external-app registry |
| workspace.js | Serve as `/assets/apps/cloud-workspace/workspace-20261115-editor3.js` |
| mail-picker.js | Serve as `/assets/apps/office-mail-picker/bridge.js` |

The native oCIS Web config and app-registry environment variables must point to these mounted files. Preserve upstream CSP directives when adapting hosts; frame ancestors, WOPI hosts and cross-window message origins must match the intended installation.

Create the Drive web provider with public client ID `office-web`, global issuer mode and the two exact HTTPS callbacks in deployment/drive-clients.example.json. Desktop and iOS use separate native client IDs/callbacks while every display name remains **Drive**. Their non-secret registration examples are included; match credentials privately to the selected ownCloud client release. Never put a confidential secret in Web config.

Deploy Collabora on `office.example.com` and the oCIS collaboration service with matching WOPI trust/proof configuration. Keep native tabbed mode and initially closed editor sidebars. Append integrations/collabora/theme.css to the matching upstream CSS, and load header-ui.js and private-sheet-views.js (P34 automatic private Calc sheet views) as same-origin external scripts from that exact editor build's HTML. Regenerate this small adaptation on upgrades; do not freeze an entire vendor browser bundle in Git.

The workspace adapter hides duplicate Drive chrome in editors, retains filename/actions, slims TXT/Markdown headers and checks exact editor origins before processing messages. The attachment bridge never transfers an OIDC token to Mail. The native Office hostname remains required for WOPI/editing even without an Office launcher.

Preview sizes: oCIS makes thumbnails only in the sizes listed in `THUMBNAILS_RESOLUTIONS` and serves the next larger one for any other request. The stack setting `CI_DRIVE_OCIS_THUMBNAILS_RESOLUTIONS` keeps the upstream default list and adds `256x256` for the photo store's previews (P74); without it a 256 px request returns a 1080 px image.

Per-owner worker credentials and application data remain private. Editing-format policies affect creation choices; they do not convert existing documents or prohibit uploads.

## Tests

- `tests/test_rebuild_templates.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- ownCloud Infinite Scale — Apache-2.0 — https://github.com/owncloud/ocis
- ownCloud Web — AGPL-3.0 — https://github.com/owncloud/web

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).

Test-site marker: on hostnames starting with `test.` or `test-` (enforced by the renderer) this module shows the shared TEST SITE marker, a 3px striped top line with a small tab, top window only, no layout space. Drive: in `workspace.js`.

## Web theme

`theme/` is a tenant-neutral theme for the web client: the sign-in and callback page ("Logging you in...") is white without the upstream logo. The renderer copies it to Drive's web assets (`web/assets/themes/cloud/`) and `config/web-with-picker.json` plus the stack's `WEB_UI_THEME_PATH` select it (oCIS overrides the file's theme with that setting). Switching themes needs an oCIS restart, then a collaboration restart (keep its networks). Derived from ownCloud web's theme (Apache-2.0); see `theme/README.md`.
