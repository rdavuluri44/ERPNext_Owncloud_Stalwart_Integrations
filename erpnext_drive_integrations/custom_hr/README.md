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

### Self check-in, offline captures and approval (owner decisions of 22 November 2026)

- **Who checks in themselves:** employees with a login who are listed on a Field Site with the member role
  **Staff** (Supervisors and Approvers of a site may also check in there). People recorded by a supervisor (a Field
  Worker Assignment) cannot check in themselves.
- **Self check-in** (`api.self_check_in`): a **selfie** is required; the location must lie inside the site's fence
  and be accurate enough (`radius_m`, `maximum_accuracy_m`); the time is the server's. The entry is a Field
  Attendance Entry with **entry type "Self"**, submitted straight to the site's approvers. One check-in per person
  and shift; a retry with the same request ID returns the same entry.
- **Self check-out** (`api.self_check_out`): inside the fence, no selfie, before the automatic 12-hour check-out.
- **Offline** (self and team captures): the phone sends `offline`, its own clock reading `device_captured_at` and
  `clock_offset_s` (server minus phone, measured at its last connection, for example from `bootstrap`'s
  `server_now`). The server uses the corrected time, accepts it only within the last day and not in the future, and
  marks the entry **"Captured offline"** for the approver. A later development build will add an exact native clock.
- **Approval:** every entry, team or self, is approved by the site's approvers (the project manager); nobody approves
  their own attendance or their own submission. `api.review_many` approves or returns up to 200 entries, each under
  all the rules, and reports per entry what happened. Approval creates the HR Attendance, as before.
- **Sites without approval** (for example head office): each Field Site has the box **"Attendance needs
  approval"**, ticked by default and for every existing site. Where an administrator unticks it, an online entry
  (self or team) becomes HR attendance as soon as it is submitted. Offline entries still go to the site's
  approvers, and so does a clash with HR attendance created elsewhere; so such a site also keeps an approver.
- **One attendance path, the administrator's choice:** HR Settings has **"Block Frappe HR check-ins (use the
  company app)"** (ticked on first install) and **"Roles that may still create check-ins"** (first "System
  Manager"; one role per line, for example for an attendance machine). While ticked:
  - the server refuses any new or changed Employee Checkin from users without a listed role, whatever screen or
    route it comes from (background jobs running as Administrator pass);
  - on install and every migrate, Frappe HR's check-in button ("Allow Employee Checkin from Mobile App") and
    automatic attendance on the Shift Types our sites use are switched off.
  Unticked, this module leaves Frappe HR's check-in settings alone; the administrator manages them.
- **For the mobile app:** `bootstrap` (now also `check_in_sites` with each site's fence and shifts, and
  `server_now`), `self_check_in`, `self_check_out`, `my_attendance`, `save_capture`, `submit`, `approvals`,
  `entry`, `review`, `review_many`. Writes are POST only.

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
