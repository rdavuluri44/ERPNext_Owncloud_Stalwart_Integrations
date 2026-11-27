# Insights session adapter (`insights-adapter`)

Patches the pinned Insights frontend to take identity from the native authenticated API before it is compiled.

## Purpose

Makes Frappe Insights take its identity from the native authenticated API rather than shared parent-domain cookies, which can collide between production and test. Keeps the main Insights sidebar visible in signed-in workbook routes and marks Workbooks as active while editing queries, charts, or dashboards.

## Contents

- `integrations/insights/**`

## Requirements

Modules: `erp-addon-shell`.

Frappe Insights at the version pinned in `deployment/upstream-lock.json`.

## Reuse

Run `integrations/insights/patch_session.py <insights app dir>` before compiling the Insights frontend (the ERP add-on Dockerfile does this). Every line it changes must appear exactly once upstream, or it stops the build: on an Insights upgrade, re-apply the patch to the new source (register entry INSIGHTS-1 in `docs/upstream-customizations.md`).

## Configuration

None.

## Tests

- `tests/test_insights_patch.py`
- `tests/test_rebuild_templates.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Frappe Insights — AGPL-3.0 — https://github.com/frappe/insights

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
