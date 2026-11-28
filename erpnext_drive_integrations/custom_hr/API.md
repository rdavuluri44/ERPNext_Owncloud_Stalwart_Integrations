# Custom HR: what each call takes and answers

For people building a client (the phone app, the field team web page) against the attendance functions of this
module. It covers the person's own check-in and check-out, team attendance, verification and approval, and the face
functions. The rules behind them are in the [module README](README.md).

Written from the code (`custom_hr/api.py`, `service.py`, `access.py`, `domain.py`, `face_service.py`,
`face_queue.py`) by the owner's AI agent (Claude). The code is the authority: a change to a call updates this page in
the same pull request.

## How to call

- **Address:** `/api/method/erpnext_drive_integrations.custom_hr.api.<name>`, as the signed-in person.
- **Method:** given per call. "POST" means POST only; "GET" means GET only; "any" accepts both.
- **Answer:** Frappe wraps every answer as `{"message": <answer>}`. The tables below show `<answer>`.
- **Lists and objects as arguments** (`payload`, `names`, `photos`, `consent`) may be sent as JSON or as a JSON string.
- **Times** are strings on the server's clock, `YYYY-MM-DD HH:MM:SS` (some with fractions of a second).

### Who a person is, in these calls

- **A user** (the sign-in ID) names the person who acts: `user`, `captured_by`, `responsible_supervisor`,
  `verified_by`, `supervisor`, `supervisors[].user`.
- **An Employee ID** names the person whose attendance it is: `employee`.
- The sender of an attendance entry is `captured_by`, a user. A worker recorded by a supervisor usually has no user.

### How a call refuses

Frappe's standard answers, by the kind of refusal:

| Status | When | Examples |
|---|---|---|
| 401 | Not signed in, or the user is disabled | "Please sign in again." |
| 403 | Signed in, but not allowed | no access to the site; not the person's own submission; face attendance switched off |
| 404 | The record named does not exist | an unknown entry name; an entry with no photo |
| 417 | A rule refused the request | outside the fence; location too old; already submitted; record changed |

The sentence is in the answer's `_server_messages` (and `exception`). There are no separate refusal codes yet: a
client can tell the kinds apart by status only, and the cases within 417 only by their sentence.

### Parts shared by several calls

**A photograph** is a data URL string: `data:image/jpeg;base64,…` (also `png`, `webp`). The whole string is at most
4,000,000 characters; the picture at least 100 pixels on its shorter side and at most 20 megapixels. The server
stores a JPEG of at most 1280 pixels.

**A place** is `latitude`, `longitude` and `accuracy_m` (numbers). `accuracy_m` must not exceed the site's
`maximum_accuracy_m` (200 when not set). When the site has a radius, the place must lie inside it.

**A time.** Every capture sends `gps_captured_at`, the time the location was fetched. It must lie within 5 minutes of
the capture time.

- Online, the capture time is the server's clock at arrival; the phone's clock is not used.
- Offline, the capture also sends `offline: true`, `device_captured_at` (the phone's clock when it was taken) and
  `clock_offset_s` (server minus phone, in seconds, measured at the last connection, for example from `bootstrap`'s
  `server_now`). The server adds the difference to both times. The corrected time must lie within the last day and
  not more than 2 minutes in the future.

**Identifiers the client makes:** `request_id` and `capture_id` are 16 to 80 characters from `A-Z a-z 0-9 _ -`.

**States of an attendance entry:** `Draft`, `Pending Verification`, `Submitted`, `Verified`, `Approved`, `Returned`.
In `team`, a worker with no entry has the state `Not recorded`.

**Versions:** a team capture carries the entry's `revision`, and the server refuses an edit made from an older one.
`verify`, `review` and `review_many` take no version today.

## Start

### `bootstrap` (any)

Takes nothing. Answers who the person is and what they may do.

| Field | Meaning |
|---|---|
| `user`, `full_name` | The signed-in person |
| `employee` | Their Employee ID, or null when no active employee record is linked |
| `manager` | true for a Field Attendance Manager or System Manager |
| `server_now` | The server's clock |
| `version` | The version of these calls (`0.2.0`) |
| `sites[]` | Sites where the person has a team role (all enabled sites for a manager) |
| `check_in_sites[]` | Sites where the person may check in themselves; empty when they have no employee record or a supervisor records them |

Each of `sites[]`: `name`, `label`, `project`, `project_name`, `company`, `supervisor`, `approver`, `verifier`
(true or false, what the person is there), `shifts[]`, `supervisors[]` (`user`, `label`), `assets[]` (`name`,
`label`).

Each of `check_in_sites[]`: `name`, `label`, `project`, `latitude`, `longitude`, `radius_m`, `maximum_accuracy_m`,
`shifts[]`. The fence is there so the client can warn before sending; the server decides.

Each of `shifts[]`: `name`, `label` (`Day` or `Night`), `start`, `end` (`HH:MM`), `attendance_date` (the date an
entry made now would belong to; a night shift belongs to the date it starts).

## The person's own attendance

### `self_check_in` (POST)

Takes `payload`:

| Field | Needed | Meaning |
|---|---|---|
| `site`, `shift` | yes | One of `check_in_sites[]` and one of its shifts |
| `request_id` | yes | Made by the client; the same one on a retry |
| `photo` | yes | The selfie |
| `latitude`, `longitude`, `accuracy_m`, `gps_captured_at` | yes | The place and its time |
| `remarks` | no | At most 2,000 characters |
| `offline`, `device_captured_at`, `clock_offset_s` | offline only | See "A time" |

Answers `name`, `state`, `check_in_time`, `captured_offline`. The state is `Submitted`, or `Approved` at once at a
site that needs no approval or for the site's own approver (online only).

A retry with the same `request_id` answers `name` and `state` only, and changes nothing. A second check-in for the
same shift and day is refused.

### `self_check_out` (POST)

Takes `payload`: `name` (the check-in's entry), `latitude`, `longitude`, `accuracy_m`, `gps_captured_at`, and the
offline fields when offline. No photograph.

Answers `name`, `check_out_time`, `checkout_method` (`Self check-out` or `Self check-out (offline)`). A repeat
answers the check-out already recorded. It is refused before the check-in time and after the automatic check-out
12 hours later.

### `my_attendance` (GET)

Takes nothing. Answers the person's own check-ins, newest first, at most 100; an empty list when no employee record
is linked. Each: `name`, `site`, `shift`, `attendance_date`, `state`, `check_in_time`, `check_out_time`,
`checkout_method`, `captured_offline`, `review_remarks`, `attendance` (the HR Attendance, once approved).

## Team attendance

### `team` (any)

Takes `site`, `shift`, and optionally `search` (part of a name or an Employee ID). `offset` is accepted but not used.

Who: anyone with a team role at the site. A supervisor or engineer sees their own workers; an approver sees all.

Answers `workers[]` (at most 500, by name), `total`, `truncated` (true when more than 500), `attendance_date`,
`missing` (workers with no entry, a draft or a returned one).

Each worker: `employee`, `employee_name`, `designation`, `machine_required`, `supervisor`, `locked` (an approver
fixed this assignment), `assignment_source`, `entry` (the entry's name, or null when there is none or the person may
not open it), `state`, `revision`, and what the person may do: `can_capture`, `can_edit`, `can_transfer`.

### `save_capture` (POST)

Records or corrects one worker's attendance as a draft. Takes `payload`:

| Field | Needed | Meaning |
|---|---|---|
| `site`, `shift`, `employee` | yes | The worker must be on the person's team for that shift |
| `request_id` | yes | Names the entry; unique per entry |
| `capture_id` | yes | Names this attempt; the same one, with the same payload, on a retry |
| `attendance_status` | no | `Present` (default) or `Absent` |
| `photo` | when Present | Not needed again when the entry already has one |
| `latitude`, `longitude`, `accuracy_m`, `gps_captured_at` | for a new entry, and whenever a photo is sent | The place and its time |
| `work_mode`, `asset` | when the worker needs a machine | `Operating` with an `asset` of the site, or `Standby`; otherwise `Not applicable` (default) and no asset |
| `remarks` | when Absent | At most 2,000 characters |
| `name`, `revision` | when correcting | The entry and the revision the client last saw |
| `offline`, `device_captured_at`, `clock_offset_s` | offline only | See "A time" |

Answers `name`, `state` (`Draft`), `revision`.

- A retry with the same `capture_id` and the same payload answers the same; with a changed payload it is refused.
- When the entry is already submitted, the same `request_id` answers `name` and `state`; another one is refused.
- A correction from an older `revision` is refused ("This record changed. Refresh before editing.").
- One entry per worker, date and shift; an entry made by another supervisor is refused.

### `submit` (POST)

Takes `name`. Only the person who captured the entry; not for self check-ins.

Answers `name`, `state`: `Pending Verification` (the supervisor has an engineer), `Verified` (the engineer captured
it), `Submitted`, or `Approved` (a site that needs no approval, online). A repeat answers the current state.

### `my_records` (any)

Takes nothing. Answers the entries the person captured at their sites, last changed first, at most 100: `name`,
`employee`, `employee_name`, `site`, `shift`, `attendance_date`, `state`, `review_remarks`.

## Looking at one entry

### `entry` (any)

Takes `name`. Who: the person who captured it, the engineer of its supervisor and the site's approvers (both once it
is no longer a draft), the person themselves for a self check-in, and managers.

Answers `name`, `employee`, `employee_name`, `site`, `project`, `attendance_date`, `shift`, `attendance_status`,
`state`, `work_mode`, `asset`, `machine_required`, `remarks`, `review_remarks`, `photo` (a private file address;
use `entry_photo`), `latitude`, `longitude`, `accuracy_m`, `captured_at`, `captured_by`, `responsible_supervisor`,
`check_in_time`, `auto_checkout_at`, `check_out_time`, `checkout_method`, `verified_by`, `verified_at`,
`verification_method`, `revision`, `request_id`, `attendance`, and what the person may do now: `can_review`,
`can_verify`.

### `entry_photo` (GET)

Takes `name`. Same people as `entry`. Answers the photograph itself (`image/jpeg`), not JSON; 404 when the entry has
none.

## Verification (the engineer)

### `verifications` (any)

Takes `site`. Who: a verifier at the site. Answers the entries waiting for this engineer, oldest first, at most 200:
`name`, `employee_name`, `attendance_date`, `shift`, `attendance_status`, `captured_by`. An empty list when no
supervisor is assigned to them.

### `verify` (POST)

Takes `name`, `decision` (`Verify` or `Return`), `remarks` (needed for `Return`; at most 2,000 characters).

Who: the engineer assigned to the entry's supervisor; never the person who captured it, never the person whose
attendance it is, never a self check-in.

Answers `name`, `state` (`Verified` or `Returned`). A repeat of `Verify` by the same person answers the same.

## Approval (the site's approvers)

### `approvals` (any)

Takes `site`, and optionally `shift` (then only that shift's current attendance date). Who: an approver at the site.

Answers the entries ready for approval, oldest first, at most 200: `name`, `site`, `employee`, `employee_name`,
`attendance_date`, `shift`, `attendance_status`, `state`, `work_mode`, `asset`, `captured_by`, `submitted_at`,
`entry_type` (`Self` for a self check-in), `captured_offline`, `check_in_time`, `accuracy_m`,
`verification_required`, `verified_by`, `verification_method`, and `can_review` (false for the person's own
submission, own attendance, or an entry they verified).

### `review` and `review_many` (POST)

`review` takes `name`, `decision` (`Approve` or `Return`), `remarks` (needed for `Return`; at most 2,000
characters). It answers `name`, `state` (`Approved` or `Returned`), `attendance` (the HR Attendance made by the
approval).

`review_many` takes `names` (a list of 1 to 200) with the same `decision` and `remarks` for all. Each entry is
reviewed on its own; one refusal does not stop the rest. It answers a list, one per entry: `name`, `state`,
`attendance`, `ok: true`; or `name`, `ok: false`, `error` (the sentence).

Who: an approver of the entry's site; never the person who captured it, the person whose attendance it is, or the
person who verified it. A repeat of `Approve` on an approved entry answers the same. An approval is refused when HR
attendance for that worker, date and shift already exists; nothing is overwritten.

## Face attendance

Every call here except `face_withdraw` answers 403 ("Face attendance is switched off on this site.") unless the
site's configuration switches face attendance on.

### `face_enrol` (POST)

Takes `employee`, `photos` (a list of 1 to 10 photographs, several angles) and `consent`: `accepted: true`,
`identity_checked: true`, `agreement_version`, `language` (each at most 40 characters).

Who: HR, a manager, an approver of the worker's site, or the worker's own supervisor or engineer.

Answers `employee`, `angles`, `consent` (the consent record). Enrolling again replaces the earlier templates. The
photographs are not kept.

### `face_identify` (POST)

Takes `site`, `shift`, `photo`. Who: a supervisor or engineer at the site. The photograph is compared only with the
workers that person may record on that shift.

Answers `decision` (`match`, `uncertain` or `none`), `employee` (on a match), `candidates[]` (`employee`,
`employee_name`, `score`), `not_enrolled` and `needs_re_enrolment` (counts among those workers).

### `face_withdraw` (POST)

Takes `employee`, `reason` (needed). Same people as `face_enrol`. Works whether face attendance is on or off.
Answers `employee`, `templates_deleted` (true or false).

### `face_capture` (POST)

A team photograph sent without choosing the worker. Takes `payload`: `site`, `shift`, `capture_id`, `photo`,
`latitude`, `longitude`, `accuracy_m`, `gps_captured_at`, and the offline fields when offline.

Answers the capture: `name`, `state`, `decision`, `employee`, `entry`, `note`.

- `Matched`: recognised, recorded and submitted in the supervisor's name; `entry` names the attendance entry.
- `Needs review`: waits for the site's approvers; `note` says why when there is a reason.

A retry with the same `capture_id` answers the same capture.

### `face_queue_pending` and `face_queue_mine` (any)

Both take `site`. `face_queue_pending` (approvers) answers the captures that need review; `face_queue_mine` answers
the person's own captures of the last three days. Oldest first, at most 200.

Each: `name`, `state` (`Needs review`, `Matched`, `Resolved` or `Rejected`), `site`, `shift`, `attendance_date`,
`captured_by`, `captured_at`, `captured_offline`, `accuracy_m`, `photo` (a private file address), `decision`,
`candidates[]`, `note`, `employee`, `entry`, `remarks`.

### `face_queue_resolve` and `face_queue_reject` (POST)

`face_queue_resolve` takes `name`, `employee`, and optionally `work_mode`, `asset`, `remarks`; it records and submits
the attendance for that worker under the same rules as `save_capture` and `submit`. `face_queue_reject` takes `name`
and `reason` (needed).

Who: an approver of the site; never the person who took the capture, and nobody for their own attendance. A capture
already decided is refused.

Both answer the capture as `face_capture` does, with the state `Resolved` or `Rejected`.

## Not on this page

Moving workers between supervisors (`move`) and the manager's setup calls (`setup_options`, `create_shifts`,
`save_site`, `unassigned`, `enroll`) are in `api.py`. Other ERPNext approvals use Frappe's own
`frappe.model.workflow.get_transitions` and `apply_workflow`.
