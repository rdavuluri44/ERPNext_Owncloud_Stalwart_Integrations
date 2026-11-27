# ERP: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# ERP: P items

ERPNext and Frappe with HRMS, India Compliance, onboarding, field operations, banking and payroll apps, the correspondence register, the AI assistant, WhatsApp and eKYC.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P03 — Employee eKYC India

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** official source staged; app not installed in production. No Digio account is ready.

Confirm compatibility with the running Frappe/ERP versions, install and configure eKYC India, establish the provider account/credentials and any required commercial approval, then verify the employee identity workflow and access controls. Do not describe staged source as an installed or usable integration.

### P04 — WhatsApp onboarding and vendor/PO replies

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** official source staged; WhatsApp app/connector not installed. No Meta WhatsApp Business account or business number is ready.

Set up the provider/business number, deploy/configure the connector, prepare approved message templates and webhooks, and implement authenticated reply-to-record mapping.

**Also (owner, 27 November 2026):** a WhatsApp verification flow for onboarding (P82): a 6-digit code to the mobile number the person gave, valid 10 minutes, 5 tries, a new code after 60 seconds; an authentication message template approved by Meta. No SMS and no Firebase for phone checks; mail codes stay on our own mail server.

**Official API only (owner, 27 November 2026, evening):** the owner asked whether a Matrix-WhatsApp bridge could replace Meta's API now that Matrix is the chat. No: the usual bridge (mautrix-whatsapp) acts as an unofficial WhatsApp Web client on an ordinary number, which WhatsApp's terms forbid for automated messages, and such numbers get banned, sometimes for good (agent's reading of public sources, not of Meta's current terms text). P04 stays on Meta's WhatsApp Business API; mail is the fallback until the Meta number exists. A bridge between Matrix rooms and WhatsApp for staff-to-vendor chats could come later, and then on the official API. Verify sending onboarding links and recording vendor yes/no responses against the intended response request or PO with an audit trail. No live sending is currently established.

### P05 — Live GSTIN lookup and form prefill

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** lookup/prefill code exists and calls India Compliance; end-to-end acceptance is incomplete.

- GST API use is enabled, but the configured API secret is absent in the final audit.
- Configure the India Compliance account/API secret and required credits/usage approval.
- Verify successful and invalid GSTIN cases, legal/trade name and address mapping, PAN extraction, error/fallback behavior and lookup limits on an actual vendor form.
- Existing GSTIN format/check-digit validation is not a completed live-lookup acceptance test.

### P06 — PAN verification and automatic constitution deduction

**App:** erp · **Also touches:** none · **State:** open

**Status:** partly implemented, partly outstanding.

Existing checks cover PAN syntax, GSTIN/PAN consistency, and whether the PAN type character matches the selected constitution. Still due:

- Deduce/prefill constitution from the PAN type character, with handling for ambiguous categories and controlled correction.
- Choose/configure an authorized live PAN verification mechanism and test valid/invalid cases.
- Keep local format/type checks visibly distinct from verified identity/status.

### P21 — Client/project correspondence register and DMS integration

**App:** erp · **Also touches:** dms · **State:** open

**Status:** Paperless product selection/deployment is complete; the ERP correspondence register and its integration remain planned. No correspondence DocType was found in the read-only schema audit.

Agree client/project, incoming/outgoing direction, reference/date/subject, responsible employee, response deadline/status, reply chains, transaction/DMS links and physical-original location fields, numbering, workflow and roles. Coordinate with P20, preserve privacy and test an incoming letter/outgoing reply and outstanding-response pilot. Existing vendor response forms and OCR search are not a completed correspondence register. See [register scope](../roadmap.md#7-clientproject-correspondence-register).

### P22 — Permission-controlled ERP AI assistant and business automation (Activepieces)

**App:** erp · **Also touches:** raven, mail, drive, dms, general · **State:** open

**Status:** planned read-only-first evaluation/development; no model, provider data sharing, public tool endpoint or write authority is selected/enabled.

Agree pilot project reports, approvals and attendance summaries; evaluate installed native Frappe tool interfaces; enforce caller-bound native roles/document/field access and a server-side tool allowlist. Require source links, audit/revocation and untrusted-content protections. No shared Administrator, unrestricted database/SQL/shell or arbitrary RPC access. Decide provider/data/cost policy before sending business data. Drafts and consequential writes are later separately controlled phases; DMS/Drive retrieval depends on validated connectors. See [assistant scope](../roadmap.md#8-permission-controlled-erp-ai-assistant).

**Scope added (owner, 22 November 2026): business automation and notifications.**
- **Tool: Activepieces** (owner's preference over n8n): MIT-licensed core (a paid enterprise folder aside), visual
  workflows with AI steps; n8n was set aside because its Sustainable Use License is not open source and restricts
  offering it to other organisations (future tenants). Single sign-on is paid in both, so the Activepieces admin screen
  sits behind the authentik gateway instead.
- **Changed by the owner, 27 November 2026:** Raven is removed (P108); messages inside the company go through our
  own notification service (in the app, mail, WhatsApp, SMS) instead of Raven, and later Matrix chat (P73). The
  vendor part below stays.
- **Channels (owner decision, 22 November; superseded inside the company):** Raven inside the company, WhatsApp for outside vendors. Activepieces can post to
  Raven through Raven's incoming webhook / REST API (generic HTTP step) and to WhatsApp through the WhatsApp Business
  Cloud API; WhatsApp needs the Meta business number (P04's blocker), approved templates for messages vendors did not
  start, and has per-conversation charges. One sender per event, so vendors never get duplicates (Activepieces or the
  ERP's own WhatsApp connector from P04, chosen per event).
- **Step 1, no new tool:** ERP-native notifications for events inside the ERP: Raven document notifications (for
  example a Purchase Order submitted, posted to a channel with the document linked) and ERPNext Notifications (for
  example a Payment Entry to a vendor: mail now, WhatsApp once P04 is live). Through the test site first.
- **Step 2, pilot Activepieces on the test site** for work that crosses systems or runs on a schedule: supplier
  invoices from mail read by AI, filed in the DMS and drafted in the ERP; weekly overdue-payment summaries; GSTIN checks
  when a vendor is created; Drive folder processing; routing monitoring alerts (P72) to Raven or the phone; human
  approval steps.
- **Rules:** workflows exported to git and promoted test to production like every other change; credentials in the
  secrets manager (P71) and never in workflow exports; AI steps only under the provider and data policy decided in this
  item (business data must not go to an AI provider before that); test-site messages follow the demo safeguards
  (allow list and test marker); every workflow names an owner and has a way to switch it off.

### P24 — Field attendance pilot and correction acceptance

**App:** erp · **Also touches:** none · **State:** open

**Status:** retained field source is packaged; real-worker acceptance remains.
Exercise device/location/geofence behavior, submitted and returned corrections,
void/cancel rules, supervisor roles and payroll/report effects using test workers.
The earlier approved cancellation path remains blocked; a returned correction
path is not proof of cancellation. Agree business rules before changing them.

### P26 — Banking and payroll provider sandbox acceptance

**App:** erp · **Also touches:** none · **State:** blocked

**Status:** upstream integration apps are pinned and installed; provider sandbox
end-to-end acceptance is pending. Configure approved sandbox accounts privately,
test permissions, callbacks/signatures, reconciliation, retries/idempotency and
payroll effects. Do not initiate live transfers, payroll payments or provider
account changes as part of rebuild acceptance.

### P28 — Dual approval for ERP super-administrator access

**App:** erp · **Also touches:** general · **State:** open

**Status:** planned assessment/design; owner deferred the choice of approval
model until implementation. No authentication or privilege changes authorized
by this planning entry.

Investigate passkey-based independent approval by two named people before ERP
super-administrator access or sensitive modifications. Decide whether approval
is required once for a short-lived privileged session, whether both people must
remain signed in, or whether selected actions require individual approval.
Two open sessions or two authenticators on one identity do not establish
independent two-person approval.

At implementation, agree eligible requesters/approvers, self-approval prevention,
request binding, reason/audit records, session duration, expiry/revocation,
recovery/emergency access and concurrent-request handling. Assess direct
Administrator login, API tokens, impersonation and existing sessions, plus the
separate authority of Coolify/SSH/database administrators. Do not claim an
ERP-only gate controls infrastructure administrators. Preserve ordinary named
user access and validate bypass/denial/recovery cases on the permanent test
site before any production promotion. Final scope and design require the
owner's decision at that time.

### P31 — Keyboard-first navigation to nested ERP/Frappe menus

**App:** erp · **Also touches:** portal · **State:** open

**Status:** planned usability work. Owner reports mouse navigation through two
menu levels is slow; provide direct keyboard access to nested destinations.

Audit installed Frappe v16 Awesomebar/Global Search shortcuts and the retained
portal/Desk adapters first. Prefer native permission-filtered navigation search
rather than duplicating a global command engine. Current upstream documentation
distinguishes Ctrl/Cmd+K (Awesomebar menus/actions) from Ctrl/Cmd+G (Global Search);
verify actual installed behavior before choosing bindings.

Provide discoverable shortcut hints, keyboard access to module dropdown and
second-level items (arrows, Enter, Escape and correct focus return), and direct
searchable destinations with their module/path labels. Assess optional user
favorites/recent destinations and configurable direct shortcuts for frequent
screens during design. Exact key assignments remain to be agreed after checking
browser, OS, native Frappe and editor conflicts.

Respect effective user permissions; navigation shortcuts never grant additional
access. Preserve text-entry shortcuts, form edits and unsaved work, and ensure
portal iframe focus/app switching does not swallow keys or invoke commands in
an inactive app. Validate ERP, other native Desk apps, Windows/macOS browsers,
logout/session expiry and keyboard accessibility on permanent test before
production promotion. This improves navigation effort; backend/network latency
and P01's idle freeze remain separate issues.
References: https://docs.frappe.io/framework/keyboard-shortcuts and
https://frappe.io/blog/product-updates/product-updates-for-may-2026

#### P31 extension — Transaction-code navigation

Evaluate an SAP-like transaction-code entry window as an alternative/complement
to keyboard shortcuts and native Awesomebar search. A user types a memorable
code and optional validated record/field argument to navigate directly to an
allowed list, new form, existing document, report, section or field.
Illustrative syntax only (not selected bindings): PO = Purchase Order list;
PO.NEW = unsaved Purchase Order form; PO <record> = existing permitted order;
PO <record> supplier = reveal its section and focus the permitted Supplier field.

Use a versioned, modular allowlisted registry of codes/aliases and native Frappe
routing/new-document APIs. No arbitrary JavaScript, SQL, Python or RPC execution
from the command window. Provide autocomplete, descriptive destination/path
labels, discoverable code hints and clear unknown/ambiguous-code errors. Decide
shared versus personal aliases and registry editing rights during design.

Enforce native create/read/report permissions and document/field restrictions;
never reveal inaccessible record titles or hidden fields through suggestions.
Field targeting needs a loaded form and a selected document or new-form context;
handle collapsed tabs/sections, read-only fields and child tables explicitly.
Navigation must not save, submit, approve, cancel or delete automatically.
Preserve unsaved-change prompts and portal iframe focus. Compare usability with
native Awesomebar before choosing the minimum custom implementation. Keep exact
codes, activation keys and command grammar undecided until the test pilot.
References: https://docs.frappe.io/framework/user/en/api/js-utils and
https://docs.frappe.io/framework/user/en/api/dialog

### P32 — Native-module integration and reversible add-on navigation

**App:** erp · **Also touches:** none · **State:** open

**Status:** planned architecture/navigation policy and Onboarding refactor.
Prefer Frappe add-ons that extend native forms/modules without a standalone
portal/apps-screen icon, wherever functionally appropriate. Installed package
registration/dependencies remain distinct from user-facing launcher visibility.
Do not assume every marketplace app can safely adopt this without review.

First application: retain Onboarding inside erpnext_drive_integrations but
remove its standalone launcher from the portal, apps screen and equivalent
navigation. Integrate its relevant links/forms/actions into CRM and HR as
requested. Inventory all existing onboarding/vendor/KYC/response/schedule pages
and agree the destination of each; flag procurement-specific or cross-functional
items for placement decisions rather than silently dropping them. Preserve
existing URLs or compatible redirects, records, permissions, APIs and guest
response links. Coordinate permission-filtered menu/Tcode discovery with P31.

Source audit found explicit Onboarding add_to_apps_screen hooks plus custom
access/boot handling, so removing one visible icon alone is insufficient.
Use supported native workspaces/sidebar/form hooks and addon-owned idempotent
migrations rather than editing upstream ERP/HR files. Future installations,
upgrades and migrations must preserve the selected integrated presentation.

Provide an ownership/change ledger for added menu rows, field/property changes,
fixtures and other configuration. On feature removal, detach only owned entries,
restore prior values only if they still match the addon's applied value, and
report later user/third-party edits for review instead of overwriting them.
Preserve shared links, unrelated customizations and business records. Test
install/repeat-migrate/upgrade/disable/re-enable/remove cycles and rollback.

Non-destructive removal requires a supported feature-disable/detach operation
and documented data retention/export/dependency handling. Native bench
uninstall can delete app-owned DocTypes and records: do not represent it as
safe data-preserving removal or run it as the default cleanup path. Full package
uninstall needs a separately tested preservation/migration plan; disabling
Onboarding must not uninstall the consolidated app's other features. Returning
the navigation/configuration to its previous state must not undo legitimate
business transactions or later independent changes. Validate on permanent test
before promoting the same revision to production.
Reference: https://docs.frappe.io/framework/user/en/python-api/hooks

### P93 — "Request response" button missing on Job Offer

**App:** erp · **Also touches:** general · **State:** in progress

**Why (found 26 November 2026, P89):** `onboarding/hooks.py` loads the "Request response" script on Job Offer from
`client/request_response.js`, which does not exist; Purchase Order uses the real path
`onboarding/client/request_response.js`. Frappe skips a missing file without an error, so the Job Offer button
probably never loads. The script itself already handles Job Offer.

**What (owner go 26 November 2026):** point Job Offer at the real file; add a unit test that fails when any
`doctype_js`, `doctype_list_js` or include hook names a file that does not exist; update the register (HRMS-4).

**Release:** ERP app change: branch, rebuild, test site, owner's browser check (open a Job Offer, the button is
there and opens the request), merge, production. Waits for a free test-site slot (the owner decides when).

**Acceptance:** the button shows on Job Offer on test and production; the new test fails on a wrong path.

**Related:** P89 (register entry HRMS-4).

**Number (26 November 2026):** opened as P90 in this session, but another session had already
recorded P90 (Traefik) on `main`; renumbered P93. Public PR #89, its branch `p90/job-offer-button` and its first
commit still carry the old number.

**Progress (26 November 2026):** public PR #89 (`p90/job-offer-button`), CI passed; the new test fails on the old path.
Waiting for a test-site slot (test ERP runs #77, used by the P74 phone test; owner decides).

**Progress (27 November 2026): second fix merged, not deployed.** The owner's browser check on test found the
button still missing: the script asked `rule_status` (GET only) with `frappe.xcall`, which sends POST, so Frappe
answered "Not permitted" on Job Offer and Purchase Order. Public PR #123 asks with GET and adds
`tests/test_js_call_methods.py`; tested on test at `b5f9c5d`, the owner saw the button on a Job Offer; merged at
`086552f` (owner's go). **Merged, not deployed:** goes to production with the prepared ERP release (image rebuilt
from main first).

### P95 — Face recognition for field team attendance

**App:** erp · **Also touches:** mobile, signin, test-site · **State:** in progress

**Why (owner, 26 November 2026):** field workers often have no phone or app account of their own. The supervisor
should mark the team's attendance just by photographing each person: no selecting the employee first; the app
recognises the face, clears that person's attendance and the supervisor moves on to the next one. Self check-in by
people with the app uses the fingerprint instead (P82), so this item covers only team attendance.

**What (owner decisions, 26 November 2026):**
- **No team faces on the supervisor's phone.** Face data lives on our server only.
- **Bulk onboarding:** HR (or the project manager) enrols each field worker with one good phone, checked against the
  worker's ID: several angles (front, left, right, up, down) on video. True 3D needs a depth sensor, which only
  iPhones have; on Android it is several 2D views. The server keeps encrypted face templates (numbers), not the
  photos (agent recommendation; a model change then needs re-enrolment).
- **Liveness on the phone, matching on the server:** on the supervisor's phone, offline and free, MediaPipe Face
  Landmarker follows the head turn and a blink (its 3D is estimated from the picture, not measured) and a photo and
  screen check (Silent-Face) catches paper and screens on the spot; the phone holds no one's face data. The server
  matches each capture with SFace against the workers rostered on that site and shift only (more accurate than the
  whole company) and re-checks the uploaded frames in case a tampered app fakes the liveness result.
- **Uncertain matches:** with connection, the supervisor picks from the 2–3 closest names on the spot, marked for
  the project manager. **Offline:** the app saves each capture encrypted with GPS and the phone's time and shows
  "queued"; the server recognises it when the phone is back online; uncertain or unmatched captures go to the
  project manager, who clears the offline queue. The existing approval of all attendance by the site's approvers
  (decision of 22 November) stays.
- **Consent:** an agreement is shown and accepted at onboarding: a separate tick box, in a language the worker can
  read, with withdrawal possible. Workers who refuse or withdraw keep an attendance path without a face (the
  supervisor marks them and the project manager approves). Face data is deleted when a worker leaves.
- **Legal:** development goes ahead; a lawyer's opinion under India's DPDP Act (consent, or the employment
  "legitimate use" of section 7; notice; retention; protection) is obtained **before launch**. Build so the face
  store can be moved or switched off if the opinion asks for it. Until launch, test only with synthetic data or
  staff who have signed consent.

**Before adoption (working agreements):** check licence, maintenance and security history of MediaPipe
(reported Apache-2.0), SFace (OpenCV Zoo, reported Apache-2.0) and Silent-Face-Anti-Spoofing (reported Apache-2.0,
not updated for a few years). The best-known free face models (InsightFace) are for non-commercial use only and are
not used. Record the results in the decision log.

**First step:** the licence and maintenance checks above, then a trial on test with synthetic faces: enrolment,
liveness on two phone models, server matching against a small roster, online pick and offline queue.

**Related:** P24 (field attendance pilot), P50 (the app, offline captures), P82 (onboarding, biometric sign-in,
self check-in without a selfie), P96 (SOPs: bulk onboarding, consent, leavers, offline queue).

**Owner, 26 November 2026 (evening):** build now; do not wait for the lawyer's opinion. **Late evening:** the legal
opinion is needed **before the app is connected to production** (that is the gate, not the development).

**SFace (owner, 26 November 2026, late evening):** build on SFace now and ask OpenCV about its training data. Asked
by adding to the existing upstream issue (opencv/opencv_zoo#313, comment https://github.com/opencv/opencv_zoo/issues/313#issuecomment-7193191907; four open issues ask the same, a
maintainer has only answered that the Apache-2.0 licence should be enough). The residual risk is decided before
production, with the legal opinion.

**Adoption check (26 November 2026, agent research, primary sources):**

| Tool | Verdict | Code / weights licence | Version | Note |
|---|---|---|---|---|
| MediaPipe Face Landmarker (Android Tasks) | adopt | Apache-2.0 / Apache-2.0 | tasks-vision 1.2.3 (11 Nov 2026) | blink and head pose for liveness; no advisories |
| Expo wrapper for it | reject | MIT | 1.4.0 | one-person project for an old camera library; write our own Kotlin plugin |
| OpenCV Zoo SFace (fp32) | adopt with caution | Apache-2.0 / Apache-2.0 | model 2021dec | **training data unverified** (paper used research-only datasets); owner decision |
| OpenCV Zoo YuNet face detector | adopt | MIT / MIT | 2023mar | |
| Silent-Face anti-spoofing | adopt with caution | Apache-2.0 | last commit 2020 | unmaintained; one signal only, the head turn and blink are primary |
| UniFace (packages those weights) | adopt with caution | MIT; weights from Silent-Face | 4.3.0 | maintained packaging |
| opencv-python-headless | adopt | Apache-2.0 (+ FFmpeg LGPL-2.1) | 5.1.0, wheel build 95 (17 Nov 2026) | no open advisories |
| onnxruntime | adopt if needed | MIT | 1.32.0 | not needed on the server (OpenCV runs the models); source repo not reachable on the check date |
| InsightFace models | reject | MIT code / **non-commercial** weights | | |

**Progress (26 November 2026):** public PR #94 (`p95/face-attendance-server`): matching rules, encrypted templates
(readable by no role, no history, permanent deletion), consent records, enrol / identify / withdraw, leaver hooks, the
model slot (off); 21 new tests, CI passed. Not yet: the face model (waits for the SFace decision), capture screen and
PM queue, phone liveness (needs a phone), a test-site migrate (needs a slot).

**Face engine (owner's go, 26 November 2026, late evening):** public PR on branch `p95/sface-engine`.
- YuNet and SFace fp32 from OpenCV Zoo at commit `48b10fa`, fetched into the ERP add-on image with a SHA-256 check
  per file (`deployment/face-models.json`, `tools/fetch_face_models.py`, register BUILD-11), run by the OpenCV
  already in the image (version 5.0.0, wheel build 93; OSV: no advisories, also numpy 2.5.4).
- The engine is off until a site names it in site config. The daily watch follows the model pin. The open-source
  list moves OpenCV and OpenCV Zoo to "adopted".
- Engine test here, on OpenCV's sample photos with the image's exact OpenCV version:
  - the same face mirrored, smaller or darker scored 0.93 to 0.97;
  - a different person scored 0.18 (threshold 0.363);
  - a blank photo and a photo with two faces were refused;
  - identification picked the right worker.
- Found: OpenCV 5 ignores `setInputSize` after the detector is made, so the engine makes one per photo size.
  Detection confidence is 0.8, because 0.9 refused a smaller copy of a clear face.
- Not done:
  - an ERP image build with the models (next release build);
  - a trial on the test site with synthetic or consenting faces (needs a test-site slot, owner);
  - tuning on real field photos.

**Capture without choosing the worker, and the project manager's queue (owner's go, 26 November 2026, night):**
public PR #101 (`p95/pm-queue`).
- `face_capture`: a team photograph without a chosen worker is validated once on arrival (place, time, photograph).
  A confident match is recorded and submitted at once in the supervisor's name; everything else waits as "Needs
  review" (uncertain, nobody recognised, no clear face, recognition off, or a rule that needs a person such as a
  machine allocation).
- The project manager's "Face queue" tab on the field team page: pick the worker or reject with a reason. Only
  another approver of the site decides; the chosen worker must be on the capturing supervisor's team.
- Photographs are private; the queue's copy is deleted once recorded; a rejected capture keeps its photograph for 30
  days (confirmed by the owner, 26 November 2026).
- It works with recognition off: every such capture then waits for the project manager.
- Tests: 12 new offline tests; 57 with the HR and face suites pass; CI passed.
- **Live run on the test site (26 November 2026, owner's go, option A; receipt `test-erp-main-4412593-20261126`):**
  `main` `4412593` (with #77, #100, #101, #105) deployed to the test ERP and migrated (the three new DocTypes exist).
  - Image: 67 suites / 531 tests; face engine on sample photographs 8/8.
  - Live: field attendance 79/79 and #77's checks 12/12.
  - Face queue 22/22 and the real face engine end to end 9/9 (enrolled worker recognised at 0.96 and recorded at
    once; a stranger and a blank photograph wait for the project manager). Both ran with the fix of PR #109
    loaded for the check.
  - Found: a queued photograph kept one File record after the capture was recorded (Frappe keeps two per photo
    field), and the live checks used shift times HRMS refuses. Both fixed in public PR #109, merged at `73b6da4`
    and deployed to the test ERP the same night (receipt `test-erp-main-73b6da4-20261126`): face queue 22/22 and
    the real face engine 9/9 against the deployed code.
  - Also found earlier in this slot: the build context lacked the model files (fixed in #105, merged).
- Not built: the mobile app's capture screen and the liveness check on the phone.

**Off switch (owner's go, 27 November 2026; public PR #121, `9c0d183`):**
- Found by the other session: releasing main for P93 and #77 would also ship a working face-photo intake
  (`face_capture` stored photographs for manual review even without face settings) before the legal opinion.
- Every face function that takes in or uses a face refuses unless the site config has `custom_hr_face` ->
  `enabled: true`. Withdrawal, deletion for leavers and the photo clean-up always work. Production has no
  `custom_hr_face`, so it is off; the test site has `{"enabled": true}` with no engine, as it behaved before.
- On the test ERP since 26 November 20:17 UTC (receipt `p95-test-erp-face-switch-9c0d183`): 69 suites in the image,
  face queue live 29/29 (7 new switched-off checks: nothing stored, withdrawal works), field attendance 79/79.
- **Next:** owner merges #121; one ERP release from main (P93, #77, P95 present but off) at a quiet moment, after the
  owner's P93 browser check on the test ERP. **Switching P95 on in production waits for the legal opinion and the
  owner's decision.**

**Owner decisions, 27 November 2026 (Part D of the native app's request on public PR #114):**
- **Who may enrol:** also the supervisor and the engineer, besides HR and the project manager. Built as: the worker's
  responsible supervisor, or the engineer assigned to that supervisor at that site; another team's supervisor or
  engineer is refused; withdrawal follows the same rule.
- **Consent text:** English by default; the worker may choose to read a translation in the language of their choice;
  the language read is recorded (agreement draft 2). **If a translation and the English differ, the English version
  governs** (owner, 27 November 2026; in #131 at `777a5fd`, documentation only). **Ticking "I agree" also confirms
  that the person enrolling the worker explained the terms in a language they understand** (owner, 27 November; the
  owner chose "whoever enrols" over "HR only", so the Part D decision stands; `0cf7865`, documentation only). For
  the lawyer: whether this acknowledgement, with the record of who enrolled and the language, is enough when the
  worker cannot read the text.
- **Public PR #131** (`p95/enrol-by-team`, tested at `5ae5cd0`, head `0cf7865` adds only the English-governs and
  explained-in-your-language text in `docs/`, CI passed, ready for the owner). On the test ERP since
  09:27 UTC (receipt `p95-test-erp-enrol-by-team-5ae5cd0`): 71 suites in the image; face queue live 36/36 (7 new);
  field attendance 79/79. Not covered: a phone (the enrolment and agreement screens are not built).
- **Merged, not deployed:** #131 merged at `de1feaf` (10:28 UTC, 27 November; head `0cf7865`, tested image
  `5ae5cd0`, later commits `docs/` only). Joins the next ERP release from main (P95 stays off in production).

**Status:** in progress.

### P103 — Request ID on every app action, and "what happened to my request"

**App:** erp · **Also touches:** mobile · **State:** open

**Why (owner, 27 November 2026: "go" on Part B of the native app's request on public PR #114):** the native app's
data-flow tracker (P50, Phase 0) can follow a save only as far as the gateway. Nothing on the server returns or stores a
request or correlation ID (checked 27 November: no such header; `request_id` exists only as the attendance retry key on
Field Attendance Entry). A failed save cannot be pinned to one point without someone reading server logs.

**What:**
1. The app sends one request ID with every save; the server returns it in the answer and writes it on the record
   created (reuse the existing unique client ID fields: `request_id`/`capture_id` on Field Attendance Entry,
   `client_id` on Drive Photo, `capture_id` on Field Face Capture).
2. The same ID on the calls that have none today and are repeat-safe only by the record's state: `self_check_out`,
   `submit`, `review_many`, `verify`, `apply_workflow` (B4 of the request).
3. A read-only function "what happened to my request ID": for the signed-in person's own IDs only, it answers the
   record, its state and which notices were made; never other people's values.

**Acceptance (test site):** every app save carries an ID that is returned and found on the record; the lookup answers
for one's own IDs and refuses others'; repeating a call with the same ID returns the first result.

**Related:** P50 (native app), P104 (version handshake), P105 (five-phone test round).

### P104 — Version handshake between the server and the mobile apps

**App:** erp · **Also touches:** mobile · **State:** open

**Why (owner, 27 November 2026: "go" on Part B of the request on public PR #114):** an app that is older than the
server's functions should say "update needed" instead of showing strange errors.

**What:** `custom_hr.api.bootstrap` already returns `version` (`0.2.0`); add a short fingerprint of the fields and
functions the mobile apps depend on (generated from the code, checked by a test so it cannot drift), and the oldest app
version the server accepts. The apps compare at sign-in and on resume.

**Acceptance:** a test fails when a mobile-facing function or field changes without the fingerprint changing; an app
below the minimum shows "update needed" on the test site.

**Related:** P50, P103, P105.
