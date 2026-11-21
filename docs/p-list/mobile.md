# Mobile: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Mobile: P items

The native mobile app, push notifications, offline behaviour and phone clients.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P14 — Retained mobile/browser push acceptance

**App:** mobile · **Also touches:** erp, raven · **State:** open

**Status:** approved-session OAuth/PKCE binding, refresh/revocation and push modules are retained; current-stack native Raven and fresh-device acceptance remain incomplete. Earlier ERP/HR notification receipt is recorded at its earlier deployment checkpoint, not re-certified on the current portal.

Verify the new portal's per-device opt-in controls, ERP/HR notification receipt and tapping, and Raven background delivery from another user on actual devices. Native relay credentials and registrations stay private. Mocked tests and a provider HTTP success do not prove device delivery. No notification test or business approval message was sent during consolidation.

Recheck native Raven login/chat/refresh and revoked-token refusal, and coordinate realtime recovery with P01. Preserve exact validated callbacks and existing workers/drafts. See [push and Raven scope](../roadmap.md#1-push-and-session-bound-native-raven).

### P23 — PWA offline and poor-connectivity behavior

**App:** mobile · **Also touches:** portal · **State:** open

**Status:** planned. Audit retained drafts and existing service workers before
adding any caching or queue. Design user-isolated caches, safe logout/wipe,
idempotent retries, conflict/error visibility and bounded storage. Test browser
and installed iOS behavior, airplane mode and reconnect; do not cache sensitive
business data or replay consequential actions by default.

### P50 — Native mobile app for phones and tablets (module `mobile-app`)

**App:** mobile · **Also touches:** none · **State:** open

**Status:** planning with the owner (opened 19 November 2026); nothing built.
Own app (not the colleague's P38 app), native on Android and iOS, one codebase
for phones and tablets, in this repository as a self-contained module. No
Supabase: ERPNext is the data backend, authentik the sign-in (native-client
login already exists).

**Decided so far (owner):**
- Users: office staff, field workers, management; menus from each person's
  ERPNext roles and project access, enforced by the server (the app never
  decides permissions).
- Data capture happens mainly on the app; the experience must be intuitive,
  fast and engaging. Same work possible on phone and tablet (parity); no
  special desktop-handoff feature.
- Version 1 scope: attendance and checkout, site reports and photos, vendor
  onboarding and KYC capture, approvals and requests; Drive, Mail and DMS
  access; chat and alerts.
- Screens: hybrid. Hand-designed screens for the top daily tasks per module,
  automatic forms generated from ERPNext's definitions for everything else.
- Offline: capture works without a signal and syncs later, with a visible
  "waiting to send" state.
- Layout: four bottom tabs on the phone (Work = the person's own module,
  opening with a Today dashboard; Chat; Mail; Drive); floating "+" for quick
  capture; module switcher only for the few multi-module users; project
  selector limited to assigned projects. Tablet: permanent side rail with the
  same four areas and list/detail panes. Separate layout per ERP module.
- Pilot module: HR attendance and checkout (sets the shared look and
  components).
- Distribution: Android signed APK hosted by us; iOS needs an Apple Developer
  account (TestFlight or Ad Hoc); no store listing. Framework recommended:
  React Native with Expo (TypeScript); Flutter is the runner-up, final choice
  after asking what the colleague and owner can maintain.

**Still to decide:** look and feel (logo, colours, languages, light/dark),
sign-in and security details (biometrics, session length, lost-device wipe),
notifications, the module list and each module's layout, delivery and update
method, build order after the pilot.

**Update (21 November 2026): native sign-in on the test site.** PR #15 (module `mobile-app`, from the
colleague's fork) was reviewed and deployed to the test site: the test gateway has production's native app
routes, the app's OAuth client is created on test from the private profile ("ERP Mobile", public PKCE client),
native sign-in is on for that client only. The colleague tests on a real phone. **Open (owner decision):** the first
sign-in via the relayed test host returns to the front page because the production proxy's private entry point
drops `X-Forwarded-Uri`; fix = trust forwarded headers on that entry point for the bridge sources only (a production
proxy setting). His own SSH access (forced-command deploy key plus a tailnet share) follows P54. **Later the same day:** the app's 500 after sign-in was a server
bug (`portal/mobile.py` imported a non-existent `before_request`); fixed in PR #15 (`4d28354`), installed on test,
app requests now succeed. The same line is latent on production: promote it with PR #15 (ERP release). **Naming (owner, 21 November 2026):** one universal app name with no company name, **"ERP Mobile"**,
for the app title, its sign-in record and its link scheme (`erpmobile`); on test the client id is `erpmobiletest1`.

### P64 — Native app sign-in on production: latent auth-hook crash and a stale client list

**App:** mobile · **Also touches:** signin, erp · **State:** in progress

**Status:** open, found 21 November 2026 while connecting the mobile app (PR #15) to the test site.
- **Flaw:** `portal/mobile.py` (the `auth_hooks` entry) imported `before_request` from `portal/combined.py`, a
  function that never existed in this repository (a leftover of the retired pre-repository Suite role guard). Every
  Bearer request from an approved native client failed with ImportError (HTTP 500) before reaching the app's API.
  The existing test replaced `combined` with a fake module that still had the function, so it could not catch this.
- **Fixed on test:** colleague's commit `4d28354` (PR #15) removes the call and makes the test import the real module;
  installed on the test site 21 November 10:19 UTC; app requests succeed since (check_access and the app's bootstrap 200).
- **Production:** the same line is live, native sign-in is on (`cloud_raven_mobile_enabled`), but the native client
  list (`cloud_native_mobile_clients` and the legacy `unformat_native_mobile_clients`) names `psvrvmandb`, the
  colleague's old client that was deleted from production on 20 November (P38). So nothing can trigger it today, and
  the setting is stale. Only "Raven Mobile" exists as an OAuth client on production, and it is not in the native list.
- **To do (normal order):** merge PR #15, ERP release with a rollback point; when the app goes to production (P50),
  create its client and set the native list to it (drop the stale id and the legacy key); browser and phone check after
  promotion. Decide whether Raven Mobile should be a native client.

**Progress (21 November 2026):** the fix is **live on production** (ERP `4a5151f`, merged via PR #15 and #18): a Bearer request
no longer raises the ImportError. **Remaining:** the stale native client list on production (`psvrvmandb`) is corrected
when the app goes to production (P50), and whether Raven Mobile should be a native client is decided then.


