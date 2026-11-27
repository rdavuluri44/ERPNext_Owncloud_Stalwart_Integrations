# Custom HR (`custom-hr`)

Our additions to Frappe HR, in the one app `erpnext_drive_integrations`: field sites and their members, worker
assignments and their events, shift allocation, team attendance with photo and location, engineer verification, approval
by the site's approvers (the project manager), checkout, the field team web page, and the functions the mobile app
uses for HR. Frappe HR's own features (leave, expenses, payslips, requests) are used as they are; whatever they lack
is built here. Formerly the field-attendance part (`field/`, module "Cloud Field"; renamed 22 November 2026).

## Purpose

Attendance for people who work under a supervisor and have no ERP login. Their supervisor or assigned engineer captures
a photo and location inside the site’s fence. The module also provides HR functions that Frappe HR does not offer.

## Contents

- `erpnext_drive_integrations/custom_hr/**` (code, DocTypes, the desk page `field-attendance`, the rename patch)
- `erpnext_drive_integrations/public/custom_hr/**` (the field team web page's script and style)
- `erpnext_drive_integrations/www/field_team.*` (the web page at `/field-team`)
- `tests/test_custom_hr.py`

Open the field team web page at `/field-team` or the Desk page at `field-attendance`.

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

### Engineer verification

1. Grant the engineer **Field Attendance Verifier**. On the Field Site, add them as an enabled **Verifier** member.
2. On each applicable **Supervisor** member row, set **Attendance Engineer** to that engineer.
3. Keep **Attendance needs approval** enabled and configure a separate project manager as an **Approver** member
   with **Field Attendance Approver**. Workers use Field Worker Assignments and can remain ERP employees without logins.

A supervisor's submission waits in **Pending Verification** until their assigned engineer verifies it or returns it
with a reason. The engineer can also capture attendance for workers whose effective supervisor for that site,
date and shift is assigned to them. On submit, this capture is marked **Verified** automatically and enters the
project manager's approval queue. Both paths record the verifier, timestamp and method. The project manager's
approval creates the official HR Attendance. The recorder and verifier cannot issue final approval for that entry.

The field team page shows **Verification** for assigned engineers. API consumers use `bootstrap.sites[].verifier`,
the worker-level `team` action flags, `verifications(site)`, and the POST-only `verify(name, decision, remarks)`
with **Verify** or **Return**. `entry` returns `can_verify` and verification audit fields. `approvals` includes
verified entries and direct submissions. Sites or teams without an engineer assignment keep their existing flow,
as do self check-ins. An in-progress capture that already requires verification continues to require it if the
engineer assignment changes.

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
- **Project manager's own check-in** (owner, 25 November 2026): when an **Approver** member of a site checks in
  themselves at that site, online and with no clash, the entry becomes HR attendance at once (remark "Own check-in
  of the site approver"). Selfie and fence rules are unchanged. Offline check-ins and clashes still go to another
  approver or a Field Attendance Manager. Team entries the approver records still need another approver.
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
  `entry`, `entry_photo`, `review`, `review_many`. Writes are POST only. `entry_photo` returns an entry's photo to
  anyone `entry` allows: the private file URL itself applies ERPNext's Employee user permissions, which would stop a
  project manager from seeing another employee's photo.

**Upgrading a site from the former name:** `bench migrate` runs `custom_hr/patches/rename_module.py` before the
DocTypes are synced; it renames "Cloud Field" to "Custom HR". When Frappe has already registered
the new module for this app, the patch merges the old module's links into that record. Records and
tables are not touched. The scheduled checkout job moves to its new name during the same migrate.

### Face attendance for field teams (P95, in progress)

The supervisor photographs each worker without choosing them first; the server recognises the face among the
workers that supervisor may record on that site and shift. Decided by the owner on 26 November 2026 (P95).

- **Switched off unless the site says so** (owner, 27 November 2026): face attendance runs only where the site config
  has `custom_hr_face` -> `enabled: true`. Without it, enrolment, identification, the capture queue (sending a
  photograph, both lists and deciding a capture) refuse with "Face attendance is switched off on this site." before
  anything is read or stored. Naming an engine does not switch it on. **Withdrawal, the deletion of a leaver's or
  deleted employee's face data and the daily removal of rejected photographs always work.** Production stays off
  until the legal opinion and the owner's decision (P95); the test site has it on.
- **Enrolment** (`api.face_enrol(employee, photos, consent)`, POST): HR, a Field Attendance Manager, an approver of
  the worker's site, or the worker's own team (owner, 27 November 2026: the responsible supervisor on the worker's
  Field Worker Assignment, or the engineer assigned to that supervisor on the site's member list) enrols the worker
  from several angles (at least 3) after checking their identity document. Another team's supervisor or engineer is
  refused; withdrawal (`api.face_withdraw`) follows the same rule. The consent (`accepted`, `agreement_version`,
  `language` the worker read: English by default, or the translation they chose; `identity_checked`) is stored as a
  **Biometric Consent** record, with who recorded it. Only encrypted templates are kept, in **Field Face Enrolment** (site encryption key; the templates field
  is readable by no role and keeps no version history). The photographs are not stored.
- **Identification** (`api.face_identify(site, shift, photo)`, POST): for a supervisor or assigned engineer of the
  site. Returns `decision` (`match`, `uncertain` or `none`), the `employee` for a match, up to three `candidates`
  with scores, and how many rostered workers are not enrolled or need re-enrolment (templates of another model).
  A match needs the threshold and a clear margin over the next worker, so look-alikes are never decided alone.
- **Withdrawal and leavers** (`api.face_withdraw(employee, reason)`, POST; and automatically when an employee is no
  longer Active or is deleted): the templates are deleted permanently (not kept in Deleted Documents); the consent
  record stays as evidence, marked Withdrawn or Ended.
- **Face model:** OpenCV Zoo's YuNet detector and SFace recogniser (`custom_hr/face_sface.py`), adopted on 26
  November 2026. The ERP add-on image fetches them at a pinned commit with checksums into `/opt/face-models`
  (`deployment/face-models.json`, `tools/fetch_face_models.py`, register BUILD-11); OpenCV is already in the image.
  The engine stays **off** until a site names it in site config `custom_hr_face` -> `engine`:
  `erpnext_drive_integrations.custom_hr.face_sface.SFaceEngine`. A photograph must hold exactly one clear face
  (detection confidence 0.8, at least 80 pixels); otherwise it is refused and retaken. Thresholds can be set in
  `custom_hr_face` -> `thresholds` (`match`, `margin`, `floor`, `candidates`, `minimum_angles`, `same_person`),
  within fixed bounds. Engine test (26 November 2026, OpenCV 5.0.0): the same face mirrored, smaller or darker
  scored 0.93 to 0.97, a different person 0.18 (match threshold 0.363). Before production: the legal opinion and
  the SFace training-data question (P95).
- **Capture without choosing the worker, and the project manager's queue** (`custom_hr/face_queue.py`):
  - `api.face_capture(payload)` (POST; `site`, `shift`, `capture_id`, `photo`, `latitude`, `longitude`, `accuracy_m`,
    `gps_captured_at`, and for offline captures `offline`, `device_captured_at`, `clock_offset_s`): for a supervisor
    or assigned engineer. The place and time are validated once, on arrival, under the same rules as a normal
    capture. A confident match is recorded and submitted at once **in the supervisor's name** and goes to
    Approvals as usual. Anything else waits as **Needs review**: an uncertain match, nobody recognised, no clear
    face, face recognition off, or a rule that needs a person (for example a machine allocation). A retry with the
    same `capture_id` returns the same capture.
  - **Face queue** screen on the field team page (approvers only) and `api.face_queue_pending(site)`,
    `api.face_queue_resolve(name, employee, work_mode, asset, remarks)`, `api.face_queue_reject(name, reason)`:
    the project manager picks the worker (the closest matches are offered) or rejects with a reason. The chosen
    worker must be one the capturing supervisor may record on that shift; an approver cannot decide their own
    capture or record themselves. `api.face_queue_mine(site)` shows a supervisor what became of their captures of
    the last three days.
  - **Photographs:** private; only the site's approvers and the capturing supervisor can read a queued capture.
    The queue's copy is deleted as soon as the capture is recorded (the attendance entry keeps its own). A rejected
    capture keeps its photograph for 30 days (owner, 26 November 2026), then only the record and the reason remain.
  - The roster used for matching is the supervisor's team at the time of upload.
- **Not yet built:** the capture screen in the mobile app (take the photograph, call `face_identify` when
  online or `face_capture` when offline), liveness on the phone (needs a phone), and a trial on the test site.

## Tests

- `tests/test_custom_hr.py` (offline)
- `tests/test_custom_hr_face.py` (offline: face matching rules, consent, engine slot, stored records)
- `tests/test_custom_hr_face_queue.py` (offline: who the queue acts for, who decides, photographs, the web screen)
- `tests/test_custom_hr_face_switch.py` (offline: the off switch, where it applies and where it never does)
- `tests/test_custom_hr_face_enrolers.py` (offline: who may enrol or remove a face)
- `erpnext_drive_integrations/custom_hr/face_queue_integration_tests.py` (needs a live test site; rollback only)
- `tests/test_custom_hr_face_engine.py` (model pins and fetch; the live engine part runs in the ERP image)
- `erpnext_drive_integrations/custom_hr/test_checkout.py`
- `erpnext_drive_integrations/custom_hr/integration_tests.py` (needs a live test site)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- ERPNext — GPL-3.0 — https://github.com/frappe/erpnext
- Frappe HR — GPL-3.0 — https://github.com/frappe/hrms
- OpenCV — Apache-2.0 — https://github.com/opencv/opencv
- OpenCV Zoo SFace (Apache-2.0) and YuNet (MIT) models — https://github.com/opencv/opencv_zoo (licence files
  copied with the models into `/opt/face-models`)

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md). This module's own code: open-source license not yet chosen by the owner (P35).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
