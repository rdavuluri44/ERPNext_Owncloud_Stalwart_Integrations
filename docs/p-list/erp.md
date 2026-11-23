# ERP: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 22 November 2026
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

Set up the provider/business number, deploy/configure the connector, prepare approved message templates and webhooks, and implement authenticated reply-to-record mapping. Verify sending onboarding links and recording vendor yes/no responses against the intended response request or PO with an audit trail. No live sending is currently established.

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
- **Channels (owner decision): Raven inside the company, WhatsApp for outside vendors.** Activepieces can post to
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
