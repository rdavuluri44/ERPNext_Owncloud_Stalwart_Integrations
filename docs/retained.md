> Sanitized final operating record. Production identities, secrets and private configuration remain outside Git.

# Workspace — retained deployment and changes

Updated **15 November 2026 (Asia/Kolkata)**. Scope: the final retained changes from **14–15 November**, reconciled against the conversation, deployment receipts, browser checks and a fresh read-only production audit. This is the current handover; the separate the maintainers' task list (private operations repository) records incomplete work and acceptance checks.

## Deployment and addresses

Production ERPNext and authentik now run with the workspace services on the new VPS at the hosting provider, **203.0.113.10**, managed by its own Coolify instance. The old controller remains independent and has no active application projects or test deployment. Its management services, retained data volumes and rollback archives remain.

| Address | Retained purpose |
|---|---|
| https://erp.example.com/ | place-holder portal and ERPNext entry point |
| https://sso.example.com/ | authentik authentication |
| https://drive.example.com/ | ownCloud oCIS files, sharing, Spaces and sync |
| https://office.example.com/ | ONLYOFFICE editing endpoints used by Drive |
| https://mail.example.com/ | Webmail, authenticated JMAP, calendar/contact access |
| https://dms.example.com/ | Paperless-ngx document management |
| https://respond.example.com/ | Restricted private-link vendor/response forms |
| http://100.64.0.10:8000/ | New Coolify, tailnet access only |
| http://100.64.0.20:8000/ | Old independent Coolify, tailnet access only |

All seven public service names above resolved to the new VPS in the final audit. HTTPS certificate validation passed. Public application access remains authenticated except the explicitly approved restricted response-link routes and required discovery/login endpoints. Mail administration stays private. Off-server backups remain deferred.

## Portal and navigation

- The root ERP address is the launchpad. Direct top-level `/desk` and `/desk/` visits redirect to the portal root; embedded Desk and deeper native ERP routes remain available.
- Normal app clicks open inside the same page. Cached app frames preserve the open app while switching. Real links retain right-click and Ctrl/Cmd opening in another tab.
- Home shows the company logo and smaller, regular-weight blue company name. The logo is configured as the fullscreen toggle. Manual fullscreen acceptance remains pending.
- The portal uses the company favicon. The compact icon menu has larger icons, hover labels, a translucent/glass appearance and left-edge reveal on Home and inside apps. Outside clicks/Escape dismiss it; keyboard and touch access remain available.
- Inside apps, Home is the first separate menu row with the company logo; it no longer overlaps ERPNext. The menu scrolls when the viewport cannot fit all entries.
- The portal launches the installed Frappe apps plus Drive, Mail and DMS. The editor is reached by opening a document in Drive, without a duplicate Office launcher.

### Frappe Desk menus

The final shared adapter applies to native Desk pages in ERPNext, HR, Onboarding, India Compliance and Framework:

1. App logo followed by the selected first-level module name and a chevron dropdown.
2. First permitted module selected on a fresh portal app launch.
3. ERPNext has fixed **Edit Sidebar, Help, Search and Notification** rows above the module submenu. Other Desk apps have only **Edit Sidebar** in that group.
4. Edit Sidebar/Help use the same 13px label size, weight, left alignment, 16px icons and 28px row height as native Search/Notification.
5. A divider separates the fixed group from the selected module's submenu. Changing modules leaves the fixed group in place.
6. Native Home submenu rows are hidden. The independent portal Home shortcut remains.

Native permission-filtered module data, submenu actions, sidebar editor and Help are used. Custom navigation is supplied by the integration add-on rather than vendor source edits. Raven and Insights have separate SPA interfaces; their native navigation remains, with coverage review listed as pending.

## Authentication and sign-out

- Authentik's **Workspace Users** group contains the existing ten ERP users and gates workspace sign-in. Administrator rights and app-local document, Space and mailbox access remain separate.
- Its user dashboard presents ERPNext, Drive, Mail and DMS in one group. Native desktop/iOS client registrations remain available without separate dashboard tiles.
- Web, desktop and iPhone ownCloud sign-in screens all display **Drive**. Separate technical clients preserve their required callbacks. Approved office-client refresh-token validity is 30 days; this does not make every application session last 30 days.
- The sign-out integration propagates a shared-browser logout signal across ERP, Drive, DMS and Mail. Earlier ERP-initiated cross-app logout passed. Mail protects offline drafts during remote logout.
- The retained hardening sends ERP through the native authentik outpost sign-out and full user-logout flow, ending at a clear `/signed-out` page. Explicit sign-in requests fresh authentication and validates the returned authentication time.
- Final acceptance of this latest hardened logout flow, including every app as initiator, remains pending. It is not described as completely verified.
- Passkey authentication remains enabled. The temporary browser diagnostic was removed; the user previously confirmed successful sign-in after correcting the browser-extension issue.

## Drive, ONLYOFFICE and document processing

- Drive is the file workspace; ONLYOFFICE Docs (which replaced Collabora in November 2026, P42) keeps its own hostname for editor traffic. Drive's own app-switcher, ownCloud header link/logo and feedback controls are hidden. Its browsing search/account controls remain available.
- The agreed editor layout (one header row with Drive's close and file menu at the left, one side strip opened from a menu button, automatic private sheet views, light theme) is recorded in `integrations/onlyoffice/README.md`.
- File-action menus dismiss on outside clicks, including clicks inside the editor.
- TXT and Markdown use a compact 34px filename/action row with native Save, menu and Close controls instead of the full global bar.
- The native creation menu offers DOCX, XLSX and PPTX, with ODT/ODS/ODP creation disabled. This is a creation-menu policy, not an upload/conversion restriction; existing OpenDocument files remain usable.
- The independent document worker continues to copy eligible Drive uploads into Paperless for processing, with owner-aware access, sharing, tags and adjacent DMS Links shortcuts. Personal documents stay owner-only; shared Office Space copies receive group sharing. Document-worker enrollment is currently verified for the existing enrolled user and shared Space, not all twenty intended users.
- Mail's Drive attachment picker remains installed and uses interactive Drive authentication. It copies selected file bytes into ordinary email attachments, up to 25 × 1024 × 1024 bytes; earlier attachment verification passed and the hostname was updated to Drive. Automatic expiring links for attachments over 200 KB are not implemented; see P17 in the the maintainers' task list (private operations repository).

## Mail and integration senders

- Mail now opens directly inside the portal using authenticated public HTTPS, without the old local-network permission/Connect screen. JMAP and DAV data operations require authentication; administrative paths remain private.
- Automatic authentik-backed Mail sign-in is configured. Earlier fresh portal/Mail acceptance passed. Mail keeps the company favicon/login branding but no company-logo sidebar tile.
- Webmail's separate file-storage feature is disabled. Email folders, archives and attachments remain available.
- **noreply@example.com** is the sole integration sender. **alex@example.com** remains the personal mailbox. Retired integration-mailbox contents were archived.
- Production ERP has one enabled outgoing Email Account, noreply; the final audit confirmed this. Authentik has its own restricted SMTP-only noreply credential. Application SMTP runs over restricted private-network TLS connections; public SMTP reception remains separate.
- Onboarding's sender monitor is enabled. Earlier native SMTP authentication/envelope checks passed without sending test messages in this audit.

## Onboarding and business extensions

- The retained package is **Onboarding**, with the **O** icon. It contains Vendor Onboarding, KYC Amendment, Response Request/Rule and Construction Schedule features.
- The production migration preserved the vendor forms, response-link flows, existing approval rules and business integrations. Response rules cover vendor onboarding, KYC amendment, purchase orders and job offers.
- Public response routes are restricted to approved private-link forms/methods rather than exposing arbitrary ERP APIs. Existing expiry, device-lock and different-person approval protections remain.
- The active Onboarding and portal add-on source/name audit passed for Python/JS/HTML/JSON files. No retired business-module registration or old-name scheduled job is active.
- GSTIN lookup/prefill code calls India Compliance and maps returned identity/address facts into the form. GSTIN syntax/check-digit checks and PAN extraction already exist. Live lookup acceptance is pending: API use is enabled but the GST API secret is absent.
- PAN syntax, GSTIN/PAN consistency and selected-constitution/type-letter checks already exist. These are not live PAN verification. Automatic constitution deduction and live PAN verification remain pending.
- Existing field operations, Onboarding, India Payroll and payment integrations remain. The three custom packages are consolidated into **ERPNext_drive_integrations 0.1.0**; logical app menus remain independent.

## Retained installed versions

The core upgrade completed with database/files rollback copies and preserved installed-app membership. A subsequent asset-manifest correction restored missing core JavaScript/CSS references. Onboarding, India Compliance and Framework render successfully again.

| Installed app | Verified version |
|---|---|
| Frappe | 16.56.0 |
| ERPNext | 16.55.0 |
| HRMS | 16.53.2 |
| India Compliance | 16.11.0 |
| Raven | 3.2.0 |
| Insights | 3.15.1 |
| ERPNext_drive_integrations | 0.1.0 |
| India Payroll | 16.1.0 |
| Payment Integration Utils | 16.0.0-dev |
| RazorpayX Integration | 16.0.0-dev |

These are the running versions checked in this audit, not a claim that every third-party app is on its newest upstream release. eKYC India and WhatsApp are not installed.

## Operator handover and verification limits

- Native NEW Coolify service definitions retain the deployments; the old controller is not the central controller.
- The ERP roles use the versioned consolidated addon image, built on the audited upgraded core image. See migration-record.md and deployment.md.
- Portal/SSO, field and Onboarding source now live under `erpnext_drive_integrations/` in this repository. Final menu asset: `public/module-header-20261115.js?v=4`.
- Drive, ONLYOFFICE, Mail and DMS adapters are under `integrations/`; preserve their matching native configuration and mounted assets on upgrades.
- Native Compose, database/files, site configuration and session-state rollback snapshots are retained privately on the VPS; they are not source files.
- Local rollback archives are not off-server backup protection. No credentials are included in this handover.
- Browser menu/editor checks passed, but idle/resume reliability has a confirmed real-time connectivity defect and remains deferred. See the [investigation](idle-navigation.md).
- Current certificates validate. ERP, SSO, Drive and Respond still present certificates expiring **30 January 2027**; renewal/individual issuance acceptance remains due. Office, Mail and DMS certificates expire in February 2027.

The the maintainers' task list (private operations repository) is the authoritative list of remaining implementation and acceptance work. Older deployment reports are historical evidence, not current instructions.
