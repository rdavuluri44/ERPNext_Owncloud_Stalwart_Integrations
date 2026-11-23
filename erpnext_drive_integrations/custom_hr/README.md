# Custom HR (`custom-hr`)

Our additions to Frappe HR, in the one app `erpnext_drive_integrations`: field sites and their members, worker
assignments and their events, shift allocation, supervisor-recorded team attendance with photo and location, approval
by the site's approvers (the project manager), checkout, the field team web page, and the functions the mobile app
uses for HR. Frappe HR's own features (leave, expenses, payslips, requests) are used as they are; whatever they lack
is built here. Formerly the field-attendance part (`field/`, module "Cloud Field"; renamed 22 November 2026).

## Purpose

Attendance for people who work under a supervisor and have no ERP login (recorded by their supervisor with a photo
and location inside the site's fence), approved by the site's approvers before HR attendance is created; plus the
HR functions that Frappe HR does not offer.

## Contents

- `erpnext_drive_integrations/custom_hr/**` (code, DocTypes, the desk page `field-attendance`, the rename patch)
- `erpnext_drive_integrations/public/custom_hr/**` (the field team web page's script and style)
- `erpnext_drive_integrations/www/field_team.*` (the web page at `/field-team`)
- `tests/test_custom_hr.py`

DocType names (Field Site, Field Attendance Entry and the others), role names (Field Supervisor, Field Attendance
Approver, Field Attendance Manager) and the page addresses `/field-team` and `field-attendance` are unchanged.

## Requirements

Modules: `erp-addon-shell`.

ERPNext and Frappe HR (employees, projects, shift types, attendance).

## Reuse

Keep the paths above, leave the `custom_hr` feature on, and migrate to create the DocTypes. The module adds **no
desk app icon**: it declares no `add_to_apps_screen` entry and ships no workspace (tested); its desk page is reached
from the HR "Shift and Attendance" sidebar.

## Configuration

Site config `cloud_features` key `custom_hr` (the former key `field` is still honoured); no other keys. Roles are
created on install. Permissions are enforced on the server in `custom_hr/permissions.py`, `custom_hr/access.py` and
`custom_hr/guards.py`.

**Upgrading a site from the former name:** `bench migrate` runs `custom_hr/patches/rename_module.py` before the
DocTypes are synced; it renames "Cloud Field" to "Custom HR". When Frappe has already registered
the new module for this app, the patch merges the old module's links into that record. Records and
tables are not touched. The scheduled checkout job moves to its new name during the same migrate.

## Tests

- `tests/test_custom_hr.py` (offline)
- `erpnext_drive_integrations/custom_hr/test_checkout.py`
- `erpnext_drive_integrations/custom_hr/integration_tests.py` (needs a live test site)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- ERPNext — GPL-3.0 — https://github.com/frappe/erpnext
- Frappe HR — GPL-3.0 — https://github.com/frappe/hrms

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
