# Sign-in: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 27 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Sign-in: P items

authentik single sign-on: passkeys, invitations and recovery, global logout, sign-in pages and templates, the identity stack.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P08 — Latest global logout and fresh passkey sign-in

**App:** signin · **Also touches:** portal, erp, drive, mail, dms · **State:** in progress

**Status:** earlier ERP-initiated cross-app logout passed; latest hardening is deployed but not fully accepted end to end.

Verify the final outpost/full-user logout flow ends ERP, Drive, Mail and DMS sessions, reaches the clear signed-out page, and requires a fresh passkey when Sign in is selected. Repeat with each independent app as logout initiator, including multiple open app tabs. Preserve drafts and do not remove authentication protections to make a test pass.

### P25 — Invitation, passkey enrollment and recovery acceptance

**App:** signin · **Also touches:** none · **State:** open

**Status:** native invitation/recovery adapters are retained. Complete real SMTP
and supported-device ceremonies for a fresh user, single-email enrollment,
duplicate/expired invitations, lost-device recovery and account revocation.
Preserve native identity APIs; source tests and an existing administrator's
working passkey do not prove fresh-user enrollment or recovery.

### P49 — Bring production's sign-in pages and templates into the repository

**App:** signin · **Also touches:** none · **State:** open

**Found 20 November 2026:** production's ERP provider mapping sent the legacy
claim `unformat_approved` while the repository ERP requires `cloud_approved`;
new ERP sign-ins failed for days. Emergency fix: the mapping now sends both.
When moving sign-in to the repository build, make the claim name one setting,
add a test that the ERP's required claim is in the provider's mappings, and a
browser sign-in check after every ERP or sign-in deployment.

**Status:** open, found by P45 on 19 November 2026; blocks moving sign-in
(authentik and its support service) onto the repository build. Production's
invitation pages (`<legacy mount: unformat-invitations/public>`, with a stylesheet and
newer admin navigation) and e-mail templates (`unformat-*` names, referenced
by name in authentik's database) are newer than the repository's (`cloud-*`
names, generic branding). Import them into
`integrations/authentik/invite-recovery/`, make the brand name and template
file names profile settings, rehearse on the test site, then switch sign-in
(P45). Also make the webmail product name a setting (production showed
"Unformat Mail"; the repository build shows "Mail").

**24 November progress.** Deployed both administrator entries on the
isolated Test Authentik issuer from public revision `a0541d4`. The test
build takes the companion, stylesheet, admin template and test email template
from the public release commit and requires them at startup. The six
production enrollment and recovery template files match the existing public
templates after applying the deployment brand and template prefix. Production
identity migration and performance settings remain open.

The test companion lists eligible synthetic accounts and links signed-in
administrators to their own native WebAuthn setup. Test invitation email is
disabled because the test sender's SMTP connection closes during authentication.
Browser acceptance intercepts email submission and checks real invitation
creation, listing and cancellation on the isolated issuer.

**Invitation mail follow-up.** The owner approved adding the TrueNAS VM's
single tailnet IP to the dedicated Stalwart test sender. Test Authentik now
submits via a private, recipient-restricted SMTP relay. The live companion
has Send enabled at public revision `7088f51`. Stalwart accepted all three
requested enrollment messages. The owner's external mailbox visibly showed the
supervisor invitation. The other two messages were accepted, with no mail
for the mailbox remaining on the Stalwart queue. The existing single-use
links were retained and expire at 19:44 IST on 24 November.

**PR #63 merged.** The public invitation module and future build checks are
on `main` at `5db9a66`. The merge tree matches the tested TrueNAS revision
`7088f51`. A clean stage from merged `main` included the approved favicon set
and the test invitation mail setting. Production identity reconciliation
and promotion remain open under P49.

**Production cutover preflight.** [PR #67](https://github.com/rdavuluri44/ERPNext_Owncloud_Stalwart_Integrations/pull/67)
updates the affected identity pins and renders both gateway configs. All
GitHub checks and the isolated PostgreSQL 16.15 to 16.16 upgrade rehearsal
passed. A production scratch render preserved the running environment and
external peers, and a verified root-only rollback backup was captured.
Production SMTP already fails authentication from the current Authentik
worker. Resolve its source-IP restriction during the authorized cutover.
See the private cutover runbook (private record).

**PR #67 merged.** Public `main` is `288993c` with the exact tested tree.
The live SMTP connection reaches Stalwart from a shared bridge address
different from the exact address on the production credential. The merge is
complete. A dedicated SMTP route and production cutover still require approval.

**Production deployed.** Both identity stacks are at public `288993c`. A
dedicated worker SMTP route authenticated before and after recreation.
The initial native sign-in and admin HTTP 500 was traced to restrictive
asset file permissions, corrected in the private renderer and verified
over HTTPS and in Chrome. PostgreSQL is 16.16 with JIT off, both companions
are on NGINX 1.30.8, and the server's 3 GB cap and memory alert are active.
Production issuer discovery, signing keys, existing ERP session, both
invitation controls, and JWT rejection at the ERP logout endpoint passed.
P59 marks both identity stacks clean. A fresh physical passkey ceremony
and delivery of a new production invitation were outside this check.

**Carry into the repository identity stack (found 20 November 2026):**
PostgreSQL `jit = off` for authentik's database (sign-in step 1.2 s to 0.3 s);
a higher memory limit for the authentik server (3 GB; the host has about 7.5 GB
spare) and a cap on gunicorn worker lifetime/memory, because a worker grew to
1.46 GB over five days; a memory alert; check `AUTHENTIK_CACHE__TIMEOUT_POLICIES=0`
(policy caching is off in the legacy stack since the 14 November move, origin
unknown) and decide whether to keep it. Compare the running environment of old
and new containers when switching (lesson of the Mail move).

### P76 — Owner's passkey sign-in on the test site

**App:** signin · **Also touches:** test-site · **State:** in progress

**Found 24 November 2026:** after the owner's account
became a native Test Authentik administrator without a production link, its
test passkey (Bitwarden) passed on the normal test sign-in page, but the final
login step admitted only the synthetic accounts, so no session was created.

**Objective:** the owner signs in on test.example.com with the test passkey
alone, as on production. **Scope:** only the `mobile-attendance-qa-eligible`
login policy in `deployment/test-identity/configure.py`. Synthetic accounts,
linked staff, the passkey stage, applications, test ERP and test Drive are
unchanged. **Acceptance:** a policy dry run on test covers the owner with an
approved and a disallowed provider, without a passkey, synthetic, bootstrap
admin and linked staff accounts; then the owner completes a real passkey
sign-in on test.example.com and reaches the ERP.

**Status 25 November 2026:** applied to test; the owner signed in on
test.example.com with the passkey and reached the ERP. The provider list moves
to one setting in P79. Released together with P77 to P79; merged to public `main` 25 Nov (PR #72, `f4a3f37`).

### P77 — First administrator chosen at setup; built-in `akadmin` switched off

**App:** signin · **Also touches:** test-site · **State:** in progress

**Why:** a fresh Authentik setup creates the built-in `akadmin` account with a
generated password nobody uses, and nothing asks who should administer the
system. Upstream's first-time setup page reopens whenever `akadmin` is missing
or has no usable password, so deleting it would expose that page.

**What (owner decisions, 25 November 2026):** the setup asks the person setting
it up for the administrator's email and name (no password). It creates that
administrator and shows a single 24-hour link, only on the operator's terminal,
to register a passkey from an approved provider (P79). The administrator signs
in with the passkey only (no password) and manages other users. Rerunning the
same command on the server issues a new link when the passkey is lost. `akadmin`
is switched off, not deleted: inactive, a random password nobody knows, out of
the admin group, and the bootstrap password file removed. The test invitation
helper uses the configured administrator instead of `akadmin`. On test, the
owner's account becomes passkey-only.

**How it is tested:** a throwaway Authentik from scratch on the test VM (setup
prompt, link, passkey sign-in, setup page stays closed, rerun link, `akadmin`
cannot sign in), then the real test instance with the owner's sign-in checked
again. Production is not touched; whether production has an `akadmin` is a
separate step with its own go.

**Production (25 Nov):** done. `akadmin` recreated switched off via `--akadmin-only`
(PR #73, `0ed08d4`), and the owner's production administrator is passkey-only.
The owner's browser sign-in check passed (owner, 25 Nov afternoon: "working").

**Status 25 November 2026:** on test. Public draft PR #72 (module `6586c38`,
CI green), throwaway test passed, Test Authentik switched over (the owner's
account is the passkey-only administrator, `akadmin` off). Merged to public
`main` 25 Nov (PR #72, `f4a3f37`, tree equal to tested `f5b4f89`); production pending.

### P78 — Invitation link attempts chosen by the administrator

**App:** signin · **Also touches:** none · **State:** in progress

**Why:** the invitation form creates single-use links, which Authentik consumes
as soon as the link is opened, even if passkey setup then fails.

**What (owner decisions, 25 November 2026):** the Invite users form asks how
many attempts the link allows, 1 to 5, default 5. Each opening of the link counts
as one attempt. A successful passkey setup ends the link immediately, whatever
attempts remain. The same choice applies to recovery invitations for a lost
passkey. **Tests:** attempts counted per opening, link refused after the last
attempt and after success, existing single-use behaviour at 1.

**Status 25 November 2026:** on test from public `2530a3f` (draft PR #72 with
P77 and P79, CI green). Live links on the test enrollment flow and the shared
policy logic passed; production recovery and first-time flows are not on test.
Merged 25 Nov (PR #72, `f4a3f37`); production needs a separate go.

### P79 — Approved passkey providers as one setting

**App:** signin · **Also touches:** test-site · **State:** in progress

**Why:** the approved-provider list (Apple Passwords and Bitwarden) is copied in
five places, and phones running Android 13 or older cannot use a third-party
passkey app, so their users need Google Password Manager.

**What (owner decisions, 25 November 2026):** one setting lists the approved
providers: Apple Passwords, Bitwarden (also used with Vaultwarden), Google
Password Manager and Chrome's own Mac store. Everything else is refused, including
providers that report no identity. Every check reads that setting, including the
test passkey stage for the synthetic accounts. Chrome's Mac store keeps the passkey
on one Mac only, so a lost Mac needs a recovery invitation. Test first;
production only with a separate go after the upstream advisory check.

**Production (25 Nov):** done with `tools/identity_passkeys_p79.sh` (7 stages, 6
production policies). Rollback point `<rollback folder>`.
Production email wording and P78 on production wait for P49.

**Status 25 November 2026:** on test from public `2530a3f`
(`passkey-providers.json`, `tools/sync_passkey_providers.py`); every Test
Authentik passkey step uses the five providers. Not merged; production needs a
separate go.

### P82 — ERP Mobile holds the passkeys; one phone and one computer session per user

**App:** signin · **Also touches:** mobile, portal, erp, test-site · **State:** open

**Why:** passkeys in Apple Passwords, Google Password Manager or Bitwarden travel with the
person's account: whoever is given the account login gets the key on their own devices, and a
key saved on a shared office computer can be used by the next person. The owner wants sign-ins
that cannot be shared or left behind on a shared computer, enforced in authentik so it holds for
every service behind it (not in ERPNext).

**What (owner decisions, 25 November 2026):**
- **ERP Mobile holds the keys.** The app becomes a passkey provider on the phone. Each key is
  created in the phone's secure hardware, never synced or exported, and locked to the
  fingerprints/face enrolled at sign-up (adding one destroys the key; removing one does not, as the P82 trial
  found on two phones, wording corrected with the owner's yes on 26 November 2026; Android
  `setInvalidatedByBiometricEnrollment`, iOS `biometryCurrentSet`); no PIN fallback for the key.
- **Computers sign in only by QR from the phone** (standard WebAuthn cross-device sign-in: the
  phone scans, Bluetooth checks it is nearby). Because ERP Mobile keys exist only on phones, a
  computer can use them only this way; no change to authentik's code is needed. Office
  computers have Bluetooth (owner).
- **Sign-up from the phone:** "Request access" in the app, the admin approves (invite page),
  the key is created in the app. A new or replacement phone needs the admin's approval.
- **One phone per person** and **at most 1 phone and 1 computer session per user**; the newest
  sign-in ends the older session of the same kind and the person gets a notice.
- **Exception group in authentik** (admin adds/removes people): members may sign up and sign in
  with **Apple Passwords only**, directly on their MacBook, iPad or iPhone, without a phone scan.
  Members get an extra **tablet** session (1 phone + 1 computer + 1 tablet). The owner is a
  member. Accepted risk: their keys can be shared through their Apple account.
- **Everyone else:** only ERP Mobile keys are accepted (the approved-provider setting of P79
  shrinks to ERP Mobile plus Apple Passwords for the exception group). Chrome's own Mac store
  is removed.
- **Proof of the genuine app:** Android key attestation (and Apple App Attest later) checked at
  sign-up by our own sign-up service (the invitations companion), because authentik does not
  check it.
- **Device binding:** phones are bound by their key (the admin sees model, sign-up date, last
  use and can remove one). Computers are bound too, now, not later (owner: do not wait):
  first evaluate authentik's Endpoint Devices on test (its docs call it an early preview, not
  for production, with Enterprise parts; check licence and maturity), and report a fallback
  design if it is not usable.
- **Sessions:** the sign-in service session ends when the browser closes, on sign-out, or after
  **30 minutes** of inactivity; same for the ERP (its `session_expiry` is 170 hours today).
  Chrome/Edge "continue where you left off" can revive session cookies, so the inactivity
  limit is the safety net.
- **Sign-out from the app signs the person out of the Desk and all apps** (moved here from
  P53): the app revokes its own tokens and ends all of the person's authentik sessions;
  authentik (2025.10 and later) sends back-channel logout to connected apps; the ERP through our
  portal code (P56/P08 global logout). Check each app's back-channel support one by one.
- **Android first;** the Apple part follows later and this item stays open until it is done
  (needs an Apple Developer account).
- **Upstream:** post the authentik feature request (validation stage: require or expose the
  reported authenticator attachment) and share the link with the owner for review (working
  agreements, upstream rule).

**Decision path (discussion 25 November 2026, owner and agent):**
1. Owner proposal: store user passkeys in the app; request access on the phone, approve in
   authentik, key stored on the device; desktop sign-in by scanning a QR. Agent: QR sign-in
   already exists in the standard (cross-device); the new part is the app as a passkey
   provider. Three options: (A) app as passkey provider (large, about 6–10 weeks), (B) our own
   QR approval like WhatsApp Web (refused: a fake site can show a real QR code and the victim
   signs the attacker in; no proximity check), (C) keep the standard providers and tighten.
2. Owner alternative: face or fingerprint matched against copies on the server, cached for
   offline sign-in, and TOTP for the desktop. Agent: phones never give apps fingerprints; a
   server face store is spoofable without liveness and cannot be rotated if leaked (privacy
   law); TOTP is phishable, so only as a backup. Owner: a fingerprint change must be noticed;
   agent: the signature does not carry the fingerprint, but the key can be locked to the
   current fingerprint set (adopted above). Offline sign-in: a locally unlocked session,
   time-limited and checked again when back online (P50).
3. Owner chose C at first with (i) sign-up only from a phone and (ii) computers only by QR.
   Agent found authentik drops the browser's "where the key came from" report before policies
   run, so (ii) needed a small authentik code change and an own image (option B of that step);
   phone-mode/desktop-mode browsers can fake the device type, so the rule must not rely on it.
4. Owner: give Apple users a free way (Macs are not shared; iPad users must not need a phone);
   and found that synced passkeys can be shared with the account, so the passkey use case was
   compromised. Agent: only a non-copyable key that needs the person's own finger stops sharing,
   which is option A; it also makes the authentik code change unnecessary.
5. Owner: go for A without intermediate solutions, with the admin exception group in authentik,
   device binding, the session limits and the app sign-out above.

**Code from other projects (checked 25 November 2026):** borrow with credits and licence notices.
- Google `android/identity-samples` (`CredentialProvider/MyVault`): Apache-2.0, active.
- KeePassDX (Kunzisoft, passkey provider on Android 14+): GPL-3.0, active.
- Password Store, Passkey Edition (pando85 fork; the original Android-Password-Store is archived):
  GPL-3.0, active.
- Commercial use is allowed by all three. GPL-3.0 code may be combined with our AGPL-3.0 public
  repository (GPL-3.0 section 13); it must therefore stay in the public `mobile-app` module, never
  in the private repository (all rights reserved), and every app build we hand out must offer its
  source. Prefer the Apache-2.0 sample where it covers the need. Record each borrowed file and its
  origin in the module's notices.

**To settle in the first step (trial on one Android phone):** Credential Manager provider support
on the phone brands we use (some Android 14 builds lack third-party providers; some Xiaomi/Oppo
phones reject the fingerprint-lock flag, which must refuse rather than continue silently); the
app's link to the sign-in site (`assetlinks.json` on the sign-in host); authentik accepting the
app's identity (AAGUID) in our existing rules; key attestation from an app installed outside the
Play Store; Expo native module for the provider service; Endpoint Devices on test.

**Order:** trial on Android; phone sign-up with admin approval; computers by QR and the
authentik rules (ERP Mobile keys only, Apple for the exception group); sessions and the app
sign-out; moving existing users (the 9 current passkeys are removed after everyone has signed up
again, except the exception group's; the owner's emergency link stays); production after test,
merge and a rollback point; then the Apple part.

**Related:** P50 (the app, per-brand builds), P53 (Desk sign-out icons stay there), P56 and P08
(global logout), P78 (invitation attempts), P79 (approved providers), P14 (push for approvals).

**Started (owner, 25 November 2026, evening):** go for research, a trial branch
`p82/android-passkey-trial` in the public `mobile/` module, the upstream feature requests and these records.
Trial phone: Android 14 or newer (model not yet named). Builds: Expo's cloud build (EAS), APK profile.
Android ID: owner chose `in.unformat.erp` (the app's web address written reversed, as Android requires).

**Research results (25 November 2026, read-only, public sources; agent research, partly unverified):**
- *Android:* third-party passkey providers work from Android 14 (`androidx.credentials` 1.6.0 stable,
  its credential provider service class in `androidx.credentials.provider`); the service, activities and XML go in a local Expo module, no config plugin
  needed; EAS builds an installable APK. `in.unformat.erp` works: Expo writes ``package `in`.unformat.erp``
  since SDK 51 (expo#26910); our own Kotlin files must use the backticks; open SDK 58 bug expo#53158, so
  always prebuild with `--clean`. No security advisories (OSV) for `androidx.credentials`,
  `androidx.biometric`, `expo-modules-core`.
- *Biggest unknown:* Google publishes no statement that the computer QR sign-in offers a third-party
  provider's keys; community reports (OneKeePass, Bitwarden) say it works on phones with Google Play
  services, and it fails on microG. The trial tests this first.
- *Phone makers:* some Android 14 builds have no third-party provider setting; Xiaomi/Oppo reportedly reject
  the fingerprint-lock flag (single source); Samsung Pass conflicts reported. Pixel or recent Samsung for the trial.
- *Google MyVault sample* (Apache-2.0, active): demonstration only; it stores private keys in its database,
  allows PIN fallback and gives no attestation, so only its structure is borrowed; key handling is our own
  (Keystore, StrongBox when present, fingerprint/face only, invalidated on enrolment change).
- *Website link:* a provider serving websites through the browser gets the origin from the browser
  (`CallingAppInfo.getOrigin` with Google's privileged-browser list); `assetlinks.json` on the sign-in host is
  not needed for that (only when a native app calls). The earlier "to settle" point is answered.
- *Attestation:* the app can give Android key attestation (package name and signing-certificate digest in the
  certificate). authentik 2026.8.5 checks `android-key` signatures against Google's roots and stores the
  certificate, but also accepts "none". Whether attestation survives the QR route: unverified, trial.
- *authentik 2026.8.5 gaps:* (1) our app's AAGUID cannot be added to the device-type list (read-only, not in
  blueprints); only "Unknown devices" (opens every unlisted one). Plan: an expression policy after the passkey
  stages checks the key's AAGUID and attestation certificate. (2) authentik never sees whether the QR route
  was used (`authenticatorAttachment` is not sent; confirmed in source); keys that exist only in the phone app
  achieve the "computers only by QR" rule in practice. (3) No per-user session limit, no idle timeout (absolute
  duration only), and browser-close and a fixed duration cannot both be set in one login stage. Plan: a small
  service of ours, fed by login events, using `/api/v3/core/authenticated_sessions/` to end the older session
  of the same kind; deleting a session sends back-channel logout (OIDC since 2025.8, SAML since 2025.10).
  (4) App sign-out of everything: `bulk_delete` of the user's sessions plus revoking refresh tokens; works.
  (5) Endpoint Devices: early preview, "not recommended for production", needs the authentik Agent on every
  computer and a browser extension; local device login and advanced compliance are Enterprise (paid in
  production); checks the device only at sign-in. Owner decision pending (see handover 25 Nov).
- *Upstream:* existing requests to add to: authentik #16049 (AAGUID management), discussion #10104, #14304
  (session refresh/idle). New requests needed: expose `authenticatorAttachment`/transports to policies;
  per-user concurrent session limits. Not yet posted.
- *Conflict with an owner decision:* the app's minimum is Android 9 (build guide, 22 Nov); passkeys in the app
  need Android 14. Answered by the owner on 26 November (older phones, below): the minimum stays Android 9.

**Owner decisions, 26 November 2026 (discussion with the agent; they amend the points above where they differ):**
- **Onboarding in the app:** the person enters their mail address, mobile number and a face photo and sends
  "Request access". The **project manager approves the person's identity** (in person, against an ID), then the
  **admin approves** in authentik (invite). The app then creates the key in the phone's secure hardware; authentik
  stores only its public half; the person is signed into the app automatically. The face photo serves only the
  project manager's identity check and is not kept after the request is decided (owner: the face is not stored in
  our database). A new key (new or replacement phone, or after an erase) goes through both approvals again; the
  old key is removed in authentik at the same time.
- **Biometrics stay with the phone:** fingerprints and face are enrolled in the phone's own settings and held by
  its secure hardware; the app only learns "matched / not matched"; nothing biometric goes into the app's storage
  or to our server. The key accepts **every** fingerprint enrolled on that phone, so at onboarding the project
  manager asks, and the person confirms in writing, that only their own fingerprints and face are enrolled
  (removing family members' first; SOP in P96). Enrolling another one afterwards destroys the key (unchanged).
- **Strong sensors only:** the key unlocks only with Android's "strong" (Class 3) biometrics. Weak camera face
  unlock, which most Android phones have, is never offered, so on those phones only the fingerprint works. Strong
  face unlock (for example recent Pixels) is accepted: Android does not let an app choose fingerprint over a strong
  face. A phone with neither is refused at onboarding with a clear message.
- **Every sign-in needs the biometric,** no PIN fallback (unchanged). Signing in to the ERP and the other services
  needs internet, because authentik checks the signature; without internet the app opens with the biometric for a
  limited time and queues its captures (P50 offline). Computer sign-in by QR needs internet on both devices and
  Bluetooth.
- **Wrong attempts:** the app counts misses **in a row** (reset after a successful sign-in), shows how many tries
  are left and makes the wait grow between tries; after **5** misses in a row it erases the key, and the person
  onboards again (project manager, then admin). The phone's own 30-second sensor pause after 5 misses still
  applies. Reason for counting only misses in a row: wet, dusty or cut fingers on site fail often, and every erase
  costs a project manager visit and an admin approval.
- **Self check-in without a selfie:** the biometric at each check-in plus the site's location fence proves the
  person was there; this replaces the selfie of the 22 November decision (decision log, 26 November). The location
  check is already built and free (our own server compares the distance and GPS accuracy; the app refuses
  fake-location apps); nothing is paid unless the app shows Google maps. Field team attendance by face: **P95**.
- **Older phones (Android 9–13):** owner: Android's limits must not lock these users out. The fingerprint-locked
  key works from Android 9, and signing in to the app itself is done by the app. Only computer sign-in by QR
  normally goes through Android 14's passkey-provider service; the trial tests whether the app can run the
  QR-and-Bluetooth step (FIDO hybrid) itself on Android 9–13. Unverified until the trial. **Decided later the same
  day: our own route on all phones (below).**
- **Apple exception group:** forcing Face ID does not close the gap: Apple passkeys copy to every device on the
  same Apple ID, where that person's own Face ID unlocks them, and a website cannot demand Face ID over the phone's
  passcode. The real fix is the Apple version of ERP Mobile (key kept in one iPhone, not copied), the Apple part of
  this item. Until then the group stays small and the risk stays accepted (owner, 25 November).
- **Computer sign-in by QR: our own route for all phones (owner, 26 November 2026, late evening).** The colleague's
  P82 work set out three options for phones below Android 14: (1) older phones use the app only, and computer
  sign-in needs Android 14 or newer; (2) build our own QR route for all phones, about 4 to 6 weeks plus the review;
  (3) count first how many staff need a computer and have an older phone. **Owner chose (2).** ERP Mobile carries out
  the standard QR-and-Bluetooth computer sign-in (FIDO "hybrid": the computer's browser shows the QR, the phone
  scans it, a Bluetooth advertisement proves it is nearby, and the signed answer travels through the standard tunnel
  service) **itself on every phone**, instead of through Android 14's passkey-provider service. One route on every
  Android version. **Must stay:** the Bluetooth nearness check and the browser's own origin check. Those are what
  separate it from the WhatsApp-style QR approval refused on 25 November (decision path, step 1), where a fake site
  could show a real QR code. To verify in the trial: which tunnel service the browsers accept for a third-party
  authenticator, Bluetooth advertising on the phone brands we use, and attestation through this route.
- **Our QR route is a temporary add-on, retired when no phone below Android 14 is left (owner, 26 November 2026,
  late evening).** Few people still use Android 13 or older, and in about a year there will probably be none.
  - **Track Android versions:** the app reports its Android version at onboarding and at each sign-in. The server
    keeps it with the phone's binding (next to model, sign-up date and last use), and the admin sees how many active
    phones are below Android 14 (device list; alerts and exceptions widget, P53).
  - **Retire:** when the count of active phones below Android 14 reaches zero and new onboardings no longer bring
    any, open a work item to retire our QR route. Phones then use Android's own passkey-provider route for computer
    sign-in.
  - **So that retiring is a switch, not a new project (agent):** keep our QR route a separate, removable part of the
    app. Have the Android trial prove Android's own route on an Android 14 phone as well, so it is known to work
    when the add-on goes.
- **Relay for our QR route: Google's public relay, for the trial and until the add-on is retired (owner,
  26 November 2026, late evening).** The phone and the computer meet through a relay on the internet (the "tunnel
  service" of the FIDO hybrid standard). The relay sees only encrypted data and cannot read or change the sign-in.
  The colleague's trial code uses the public relay the standard names, run by Google (the same one every Android
  phone uses for QR sign-in). The colleague asked whether to use it for the trial. **Owner:** yes, and keep it for
  real sign-ins too until the add-on is retired (about a year, when no phone below Android 14 is left). No relay of
  our own is built.
  - **Accepted risks (owner):** we have no agreement with Google for this use. Google can change, limit or stop it
    for third-party apps at any time, and then computer sign-in from older phones stops until a fix. The relay also
    learns that a sign-in is taking place (not its content).
  - **Watch:** a failure through the relay goes into the admin's alerts (P53, P72). If Google stops it, the fallback
    is our own relay (an option the colleague described) or app-only use on older phones.
  - **Still a gate (from the colleague's report):** the trial code has never talked to a real computer and is
    encryption code written in one sitting. It is fit for a trial with a test passkey on a demo website only.
  - **Security review (owner, 26 November 2026, late evening):** instead of an outside expert, an AI agent in the
    role of a senior security analyst reviews and verifies the route before any real sign-in uses it; **the owner
    deploys Codex (OpenAI's coding agent) for this job**, a different model from the Claude agent that wrote the
    code, which answers the concern about shared blind spots. **Accepted by the owner:** no independent human
    review. Setting Codex up under the working agreements: its entry point must load the working agreements and this
    project's `AGENTS.md` (verify on that computer); Claude Code's hooks and secret guard do not apply to Codex, so
    it gets no production keys or secrets for this job; it reviews the public mobile module and the standard only.
    **How the review is done (agent's recommendation, confirmed by the owner's "ok"):**
    1. A separate session, not the one that wrote the code, reviews it from the code and the standard alone, with
       the task of breaking it.
    2. Evidence beyond reading: the standard's published test cases pass; a real Chrome on a computer completes
       sign-ins and refuses tampered ones; the encryption uses well-reviewed libraries wherever possible instead of
       our own code.
    3. A written report in the pull request (what was checked, found and fixed) and the owner's written acceptance
       of the remaining risk. Fixes go back through the usual branch and review; Codex checks the fixes too.
    **Open: Codex review planned for next week, the week of 30 November 2026 (owner, 26 November 2026).** This
    item stays open until the review report, the fixes and the owner's written acceptance are recorded here; no real
    sign-in uses the QR route before then.
- **microG (being evaluated by the colleague, 26 November 2026):** listed as "evaluating" in public
  `docs/open-source.json` (P35). Record the adoption check here (licence: Apache-2.0 per its repository; maintenance;
  security history; how fixes are published) and in the decision log, whether adopted or not; if adopted, credit
  and track it in the same pull request (working agreements).
- **Unused keys expire after 7 days** (owner, 26 November 2026, evening, from the P82 discussion with the
  colleague's agent): the **sign-in server** removes a person's ERP Mobile key when it has not been used for 7 days
  (the server knows the last use; a phone that is switched off cannot delete its own key). The person then onboards
  again (project manager, then admin). Accepted cost: anyone away for more than 7 days (leave, illness, a site with
  no signal) must onboard again; if that happens too often the period can be lengthened (14 or 30 days). The app
  tells the person when the server has removed their key and deletes its own copy. Not built; to verify: that
  authentik records each passkey's last use, and that the small sessions service of ours (above) can remove
  unused keys on a schedule. **Grace days per group (owner, 26 November 2026, late evening):** the admin decides
  how many unused days each authentik group gets (a group setting; 7 when a group has none), including the Apple
  exception group. SOP: the onboarding SOP (P96) covers re-onboarding.
- **Leavers (owner, 26 November 2026, late evening):** the exit procedure in Frappe HR (the employee's separation,
  status Left) triggers removal of the person's keys, devices and sessions in authentik and purges all their data
  in the app on the phone; the face templates go too (P95). SOP A14 (P96).
- **Lost passkey or replacement phone (owner, 26 November 2026, night):** the project manager verifies the
  person's phone in person and confirms the request **in their own app**; only then is a key issued again (the admin's
  approval follows as for onboarding). Nothing is re-issued on a message, mail or call. Until the app does this, the
  project manager confirms to the admin themselves before a recovery invitation (SOP: invite a user).
- **Usual places and unusual sign-ins (owner, 26 November 2026, late evening):** the sign-in server learns where
  each person usually signs in from: their usual IP addresses and networks, and the approximate location an IP
  address gives (city and country, not GPS). A sign-in from somewhere unusual (a new country or city, a new
  network, or two sign-ins too far apart for the time between them) sends an alert to the admin: on the Desk
  widget (P53), by mail, or both (P72).
  - **Free tools, to verify on test:** authentik already records the client address, location and network operator
    with every sign-in event, and has a free GeoIP policy (country, distance and "impossible travel" checks) and
    notification rules that can send mail or call a webhook for our widget. Location needs a free IP database:
    MaxMind GeoLite2 (free account, its own licence) or DB-IP Lite (CC BY 4.0); to choose, and to list in the
    open-source file (P35).
  - **Alert only, at first:** an unusual sign-in is reported, not blocked, until the rules have proven themselves
    on real use. Blocking or asking for an extra check can follow as a separate owner decision.
  - **Personal data (DPDP):** sign-in addresses and approximate locations of employees are personal data. They go in
    the staff notice, are kept for a fixed period (**owner, 26 November 2026: 90 days of history**, then only the
    learned usual places),
    and are shown only to the sign-in admin. The SOP inventory (P96) gets the admin's handling of these alerts.
  - **Office and site networks:** the admin can mark known office and site addresses as usual for everyone, so
    shared office connections do not raise alerts.
- **Alerts and exceptions to the admin (owner, same evening):** the sign-in admin receives the alerts and exceptions
  of this item (keys removed for no use, erases after wrong attempts, refused or pending onboardings, unknown
  computers, failed certificate checks), and the person with authentik admin rights sees them in a widget on their
  Desk (scope added to P53).
- **Daily face check of the phone owner** (owner question): not taken up; the biometric at every sign-in covers
  most of it (agent).
- **SOPs:** every manual step of this item (identity check, fingerprint confirmation, re-onboarding after an erase,
  new or lost phone, exception group membership, admin approvals) gets an SOP under **P96**, written alongside the
  build.

**Binding office computers with free tools (owner, 26 November 2026: no paid or preview parts; build the missing
piece or find another free tool). Agent research, primary sources; decided below:**
- authentik's own client-certificate stage is Enterprise; Endpoint Devices is a preview (Agent and compliance)
  with Enterprise connectors. Free authentik can read the client address and request in expression policies and can
  restrict a passkey step to certain authenticator types.
- **Recommended: company certificates.** Our own certificate authority (smallstep step-ca, Apache-2.0) issues a
  certificate per computer (on Windows the key in the TPM, not exportable; Mac Keychain); Traefik requires it on
  the host names computers use and passes it on; a free authentik expression policy checks it against an
  admin-managed allow-list (list and remove computers). Binds every request, not only the sign-in. Effort medium.
  **Owner chose this (26 November 2026, late evening): build it.**
  To verify on test: Traefik must strip a forged certificate header; the app's and the QR sign-in's host names
  stay certificate-free; shared PCs (machine or per-user certificate); renewal; browsers; no revocation list in
  Traefik (the allow-list does the removal); advisories of step-ca and our Traefik.
- **Complement later:** Headscale (BSD-3, already planned): apps reachable only over the mesh from admin-approved
  computers (binds the network path, not the browser).
- **Rejected:** a second Windows Hello passkey step (self-reported type, Windows can now sync passkeys, nothing
  dependable on Mac); Pomerium Core (device approval is Enterprise); Teleport device trust and NetBird peer approval
  (paid); our own browser extension (rebuilds the preview Agent).

**Onboarding details (owner, 27 November 2026):**
- **Full name** at onboarding, as on the identity document the project manager checks: first name (required) and
  surname (optional; many people use an initial and one name).
- **The user name is the full mail address**, in the sign-in service and in ERPNext (ERPNext's user ID is the mail
  address anyway). The agent's alternatives (firstname.initial with a number on collision; the part before @) were
  set aside. Consequences to keep in mind: a person's mail address is their identity, so a changed address needs an
  admin rename; colleagues see each other's addresses in lists.
- **Chat name** (owner, 27 November 2026, night): the sign-up service also makes each person's chat name,
  `firstname.initial` with a number on a clash, and stores it as the attribute `chat_name` (P73).
- **Mail address verified** with a **6-digit code** sent by **our own mail server** (not Firebase, which only sends
  sign-in links). The code expires after 10 minutes, allows 5 tries, and a new one can be asked after 60 seconds.
- **Mobile number verified** with a 6-digit code **over WhatsApp** (P04), same limits; no SMS and no Firebase.
  So onboarding with a verified number waits for P04.

**Status:** in progress; research done, decisions amended 26 November; trial code by the colleague (not yet in
this repository). Open before real sign-ins: the Codex security review of the QR route (planned for the week of 30
November 2026). A local branch
`p82/android-trial` (no commits, not pushed) exists in a worktree on the owner's PC; the colleague taking up P82
picks the trial branch name.
