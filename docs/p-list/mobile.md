# Mobile: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 27 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# Mobile: P items

The native mobile app, push notifications, offline behaviour and phone clients.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P14 — Retained mobile/browser push acceptance

**App:** mobile · **Also touches:** erp, raven · **State:** open

**Status:** approved-session OAuth/PKCE binding, refresh/revocation and push modules are retained; current-stack native Raven and fresh-device acceptance remain incomplete. Earlier ERP/HR notification receipt is recorded at its earlier deployment checkpoint, not re-certified on the current portal.

Verify the new portal's per-device opt-in controls, ERP/HR notification receipt and tapping, and Raven background delivery from another user on actual devices. (Owner, 27 November 2026: the Raven parts fall away with P108.) Native relay credentials and registrations stay private. Mocked tests and a provider HTTP success do not prove device delivery. No notification test or business approval message was sent during consolidation.

Recheck native Raven login/chat/refresh and revoked-token refusal, and coordinate realtime recovery with P01. Preserve exact validated callbacks and existing workers/drafts. See [push and Raven scope](../roadmap.md#1-push-and-session-bound-native-raven).

### P50 — Native mobile app for phones and tablets (modules `mobile-app` and `mobile-native`)

**App:** mobile · **Also touches:** none · **State:** open

**Status:** opened 19 November 2026. The Expo app (module `mobile-app`) is the app in use on test. The native
Android rebuild (module `mobile-native`, Kotlin with Jetpack Compose) is under way: Phase 0 (foundation, no
sign-in, no server calls) in the colleague's draft PR #114, review fixes added 27 November 2026.
**Test-site request (27 November 2026):** the developer asked for the five-phone test preparation (PR #114,
issuecomment-7214300268). The owner said "go for rest of all"; the answers were posted (issuecomment-7214761500): Part D
decided (P95, PR #131); A5 and B4 answered from the code; B1 not needed (two bootstrap calls exist); B2 and B3 opened as
P103 and P104; the test-site preparation as P105 (blocked on the testers' mail addresses and the test build's signing
fingerprint).
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
  "waiting to send" state. This replaces the web-app (PWA) offline work: P23
  closed as superseded (owner, 26 November 2026).
- Layout: four bottom tabs on the phone (Work = the person's own module,
  opening with a Today dashboard; Chat; Mail; Drive); floating "+" for quick
  capture; module switcher only for the few multi-module users; project
  selector limited to assigned projects. Tablet: permanent side rail with the
  same four areas and list/detail panes. Separate layout per ERP module.
- Pilot module: HR attendance and checkout (sets the shared look and
  components).
- Distribution: Android signed APK hosted by us; iOS needs an Apple Developer
  account (TestFlight or Ad Hoc); no store listing.
- Framework (owner, 27 November 2026, confirming the agreement with the
  colleague on 26 November; replaces the earlier Expo recommendation): the
  Android app is rebuilt natively in Kotlin with Jetpack Compose (module
  `mobile-native`), because the P82 trial showed the sign-in key, the
  fingerprint lock and the computer sign-in need native code anyway. The Expo
  app stays in use until the native one does everything it does and passes
  the same checks. The rules live in a plain Kotlin module so an iPhone app,
  which follows after Android, can share them.

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

**Branding per server (owner, 25 November 2026; replaces the single universal name above):**
one build per brand, same code, built automatically from a small brand file (name, icon,
colours, server address). The home-screen name and icon come from the build, because phones
cannot reliably rename an app or swap its icon while it runs; inside the app the logo and
colours also come from the server it connects to. For now there is one brand, **unformat**
with the **UN** icon, for the test site, demo sites and production. The first client
(<tenant company>; production holds its assets) gets its own build from the same
script when it goes live. Demo sites use the unformat build. Record the change in the decision
log with the first pull request.

**Passkeys in the app (owner, 25 November 2026):** ERP Mobile becomes the phone's passkey
provider and holds each person's sign-in key; Android first. Scope, decisions and the decision
path are in **P82** (sign-in list).

**Update (27 November 2026): native rebuild, Phase 0 review.** Draft PR #114 (colleague's fork, branch
`native/phase-0`) reviewed; the owner confirmed the native rebuild (above) and gave the go to fix the review
points on the colleague's branch: CI now runs the app's own checks (`gradle checkAll`, P100) with Gradle 9.9.2
(older Gradle has one critical and seven high advisories), the checksum list gained the Linux and Mac copies of
the Android build tool, and the calling layer treats a redirect as signed out, shows only readable server
sentences and no longer crashes on sign-out during a save. Still open in Phase 0 (the colleague's list): picture
comparison, texts in one file, a real tablet, vibration, icon and start screen, detekt, crash reports. Not for
merging yet; nothing to deploy (no server stack).

**Incident reports go to Matrix (owner, 27 November 2026, evening):** the person picks one or more rooms, as the
22 November design did with Raven threads; the photos (and later clips, P106) still go to the project's Drive
through ERPNext (P74) and the room message links to them. Reason: the long-term plan is not to use ERPNext for
everything; modules stay separate and replaceable. The agent had proposed ERPNext records; it noted that chat
does not track whether an incident is open or closed, so a small separate incident tracker can be added later
if that is needed.

**Today, Inbox and alerts: the developer's plan and the owner's answers (27 November 2026, night; public #114,
issuecomment-7220894102):**
- **Every approval rings, round the clock** (owner; the agent had recommended 07:00 to 21:00 only).
- **Reminders every 4 hours, only between 07:00 and 21:00** (owner); the server applies the hours.
- Agreed as proposed: no decision without a connection; no amounts on Today; every thing has one home (Today,
  Inbox, Notices, Chat, Mail); alerts carry no content; the numbers on the places come from the server.
- **Server side owes the app (P108 part 2 unless noted):** one "what waits for me" call for everything ERPNext
  knows (count, longest wait, nearest deadline per kind); a content-free "remove this alert" signal; the reminder;
  a per-site summary for people who look after sites. Chat and mail unread are asked from their own servers, not
  through ERPNext.
- **Open for the owner, later:** who decides while someone is on leave.

**The developer's screen plan and the owner's answers (27 November 2026; public #114, issuecomment-7219041831 and
issuecomment-7219386949):**
- **Bottom bar: Today, Inbox, Chat, Mail, More** (owner; replaces Today, Inbox, My HR, Menu of 22 November; "Inbox"
  stays the approvals place, not renamed "To do").
- **Chat kept on the phone for 7 days** (the developer proposed 14), locked with the fingerprint key.
- **"Save to phone" for mail attachments is a setting, off by default** (the developer proposed it for everyone): a
  saved file leaves the app's locked store.
- Agreed as proposed: the "Outside" pill on mail from outside, remote pictures only after a tap, links show their
  address first; alerts say only "New message" or "New mail"; separate badges for Inbox, Chat and Mail.
- **Server side owes the app:** rooms made by the server per site and team (P73); a read-only "Notices" room, and
  every message marked "inform" or "needs a decision" by the notification service (P108); a yes/no "has a mailbox"
  in the bootstrap answer (P109); client IDs, return paths and addresses for three token issuers (ERPNext, the
  sign-in service for mail, Matrix's authentication service for chat); the design of mail alerts.
- The developer posted the test build's signing fingerprint on #114 (issuecomment-7216179275), for P105.

**Chat and mail in the app now (owner, 27 November 2026, evening; replaces "for now" below):** Matrix chat (P73) and
the light mail client (P109) are built now, in parallel with Phase 1. **Sign-in design for Phase 1 part 4:** one
passkey sign-in in the browser gives the app every token it needs: ERPNext's now, and later the sign-in service's
tokens for mail and for Matrix (through the same browser session, so no second passkey). Build the safe and the
connection layer to hold several tokens from the start.

**No chat and no mail in the app for now (owner, 27 November 2026, afternoon; replaced above):** the key the app holds cannot be shared with
Raven's or a mail app's own phone apps, and Raven is being removed (P108). Later the app gets Matrix chat (P73) and a
light mail client (P109). This replaces "Chat, Mail and Drive stay separate apps" of 22 November for chat and mail.

**Phase 1 plan and owner decisions (27 November 2026; the colleague's plan of five parts: the lock, the safe, the
connection, sign-in, home):**
- Parts 4 (sign-in: browser, passkey, tokens straight into the encrypted store) and 5 (home: name, roles, sign out):
  agreed. Part 4 waits for P105's sign-in client on the test site.
- **Fingerprint again after 3 minutes away** (another app opened or the screen off).
- **Without a connection the app still opens for 12 hours** (one site shift, 07:00 to 19:00 or 19:00 to 07:00), then
  it needs a connection. The owner first said 5 hours; the agent pointed out that a supervisor without signal could
  not mark the afternoon's attendance, and the owner accepted 12 hours. A switched-off person is refused at the
  next connection; the 3-minute fingerprint lock covers a lost phone meanwhile.
- **Photos offline:** see P74 (cache decision of 27 November).

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

### P74 — Document and photo store in the mobile app (Drive / oCIS)

**App:** mobile · **Also touches:** drive, erp, signin · **State:** in progress

**Status:** proposed in public issue #53 (owner decisions 23 November 2026), design revised by the owner on
24 November 2026. Server part public PR #65, app part PR #66 (builds on #64).
- **Owner decisions (23 and 24 November 2026):** no Drive app on phones; no separate photo server (Immich and
  PhotoPrism compared and set aside); site photos go straight to the project's Drive space, tagged (project, site,
  type, time, GPS, who, "From gallery", "Captured offline"); nobody deletes a work photo; phone storage only for the
  encrypted offline queue (at most 1 day); receipts, bills and scans stay with the DMS; phone scanning to Paperless
  later. **Everything through ERPNext with one sign-in:** the phone talks only to ERPNext, which checks site
  membership (the attendance rule); a dedicated Drive account (`erp-photo-service`, Space Admin) owned by the server
  writes and reads one project space per ERPNext Project; no member sync, no TUS.
- **Review fixes (24 November 2026, on #65):** full photo id in the Drive path (no upload can replace a photo);
  project browsing limited to the person's own site folders; Drive thumbnail sizes gain `256x256` (owner chose
  option A; oCIS served 1080 px for the 256 px preview).
- **Test site (24 November 2026):** #65 head `db3969c` deployed; 30 of 31 live API checks passed, the failed one
  (preview size) fixed by the Drive setting. Receipts `p74-test-*`.
- **Merged 24 November 2026:** #65 at `059f8bf` (tree identical to tested `db3969c`). Production held: it needs the
  main ERP release with PR #40 and #51 (owner decision).
- **Production 25 November 2026:** Drive preview size, ERP main `059f8bf` (with #40 and #51), the
  `erp-photo-service` account and `drive_store` config are live (release log, receipts `p74-production-*`). No
  production test photo (owner).
- **26 November 2026:** owner browser checks on production working; first nightly renewal run without failure.
  Phone test started on the test site (owner: colleague's Android development build of #66 head `f195a2d`, which
  contains #64 head `5c7c3b5`; the owner's test administrator; site Mobile Attendance QA, project PROJ-0002, no
  new test data: the account is a System Manager, so it counts as a member of every enabled site).
- **Phone test, first part (25 November, found 26 November):** two camera photos from the app on test passed the
  server checks (folder, tags, no EXIF, 256 px preview, no duplicate). Gallery, offline, list, project files and
  sign-out still to test.
- **Open:** the rest of the phone test with #64 and #66 (checklist on #66); backups and disk growth with P72 (about 1 MB per photo
  before compression; the app sends about 200 KB); privacy (photos show workers and the public: project access only,
  no public links); the daily token renewal needs the scheduler (test has none).
- **Viewing photos without a connection (owner, 27 November 2026; amends "phone storage only for the encrypted offline
  queue" of 24 November):** the app also keeps previews and the photos the person has opened, of their own sites
  only, inside the app's encrypted store; at most **200 MB** and **7 days**; wiped at sign-out, when the key is lost,
  and for a site the person no longer belongs to. The send queue stays as before (at most 1 day).
- **Short videos for incidents:** P106.

### P86 — Personal business files in the app, with a quota per user

**App:** mobile · **Also touches:** drive, erp, signin · **State:** open

**Why (owner, 26 November 2026):** besides the project files of P74, each person needs a place for their own work
files: business documents they are not ready to share in a project folder yet. Every person has a storage quota
and cannot use more than it.

**What:**
- **Personal files in the app:** browse, open, upload from the camera or the phone's files, rename, delete, and
  **move or copy a file into a project folder** when the person is ready to share it (the step this feature is for).
  Viewing PDFs and office files on the phone is part of this item (P74 shows "opens in Drive on a computer" for
  everything except images).
- **Same files on the computer:** they are the person's personal space in Drive (oCIS gives every user one), so
  they also appear in Drive on the web.
- **Quota per user:** a default for everyone and a different amount per person where needed, set by an
  administrator; the app shows used and free space and refuses an upload over the quota with a clear message
  (also for uploads waiting in the offline queue). Where the quota is managed (in ERPNext, synced to Drive, or in
  Drive only) is decided at design.
- **Privacy:** only the person sees their personal files. The server's photo account of P74 (`erp-photo-service`)
  must not get access; the app reaches the personal space with the person's own sign-in. Whether the phone talks
  to Drive directly or through ERPNext (the P74 rule) is decided at design.

**To check at design (26 November 2026, from public sources, not yet verified on our version):** oCIS sets a default
quota for new spaces (`GRAPH_SPACES_DEFAULT_QUOTA`) and a maximum (`OCIS_SPACES_MAX_QUOTA`); a forum report says a
personal quota can only be set after the user's first sign-in; check against the oCIS release we pin.

**Owner (26 November 2026): a leaver's personal files stay in place; nothing is deleted.** Still open: who may open
them afterwards and for how long they are kept.
**Owner decisions needed:** the default quota and who may change it; whether
sharing from the personal space to other people (not only to a project folder) is allowed.

**Acceptance (test site):** two test users, each sees only their own files; upload, open (image, PDF, office file),
move to a project folder; an upload over the quota is refused in the app and in Drive on the web; backup and disk
growth counted with P72.

**Related:** P74 (project files and photos, same screens), P50 (Drive tab), P72 (backups and disk growth), P10.

### P87 — Camera videos in the mobile app (Frigate)

**App:** mobile · **Also touches:** general, signin · **State:** open

**Why (owner, 26 November 2026):** Frigate on the TrueNAS server records the cameras (P46); people need to watch live
views, alerts and recordings on their phones, inside ERP Mobile.

**Where P46 stands (record, 26 November 2026):** a one-camera trial on the local network; Frigate 0.18.3, web page
with its own login on the local and private networks only; the camera is installed later; remote sites are not in
the trial. This item builds on the trial's result.

**Recommendation (agent, 26 November 2026), in two steps:**
1. **First, Frigate's own web page inside the app.** A "Cameras" entry opens Frigate's mobile web page (live, review,
   recordings) in the in-app browser, signed in through authentik: Frigate does not do single sign-on itself but
   accepts the user and role from an authenticating proxy (`role_map`). Since 0.17 a viewer role can be limited to
   chosen cameras, so each person sees only their sites' cameras. Quick, and the full Frigate feature set.
2. **Then native screens in the app, through our gateway:** an alerts list with thumbnails (Frigate review items),
   clip and timeline playback (Frigate's recordings API as HLS, played with the app's video player), live view
   through Frigate's go2rtc (HLS first; low-latency WebRTC needs a native module), and alerts as push messages
   (Frigate events to our notification service, P14; tapping opens the clip). Who may see which camera comes from
   ERPNext (site membership, the P74 rule), mapped to Frigate's camera roles.
- **Not recommended:** the Home Assistant app with a Frigate add-on (a whole extra system to run), or Frigate open to
  the internet.

**Security (checked 26 November 2026, public sources):** Frigate 0.17.2 fixed ways to reach other cameras' recordings
despite camera limits; CVE-2026-75608 (a viewer reaching the internal go2rtc API) is fixed in 0.18.0. Keep Frigate
behind the gateway, the viewer roles camera-limited, and Frigate in the daily upstream watch.

**To decide:** who sees which cameras (by site, by role); mobile data use (live in low resolution, recordings on
request); how long alerts and clips stay available; whether the app may download clips (evidence) or only play them.

**Acceptance (test site, after P46):** a viewer sees only their cameras in the app (and is refused another camera's
recording through the API); live view, an alert, and a recording play on Android and iPhone over mobile data.

**Related:** P46 (recorder), P14 (push), P50 (app), P82 (sign-in), P72 (monitoring).

### P100 — Mobile app checks in CI, and the app's dependencies in the daily watch

**App:** mobile · **Also touches:** general · **State:** open

**Why (found 26 November 2026; owner go to open it):** the developers' build loop for every screen (adopted the
same day, `mobile/BUILD-GUIDE.md` section 3) relies on automatic checks: build, all tests, code scanners, security
advisories, secret scan. The repository's CI (`.github/workflows/check.yml`) checks only the Python and server
parts. For `mobile/` it runs no install, typecheck, lint or tests, and there is no secret scan or code scanner for
any part. The app's npm dependencies are not in the daily upstream watch (found by P35 on 26 November). So a pull
request cannot prove the checks ran; today they run only on the developer's own computer.

**What (proposal, owner to confirm before work):**
1. A CI job for `mobile/`, on every push and pull request that touches it: `pnpm install --frozen-lockfile` (install
   scripts stay blocked), `pnpm typecheck`, `pnpm lint`, `pnpm test`, `npx expo-doctor` (pinned), and an export
   build (`expo export`) so a broken bundle fails. Pinned action versions by commit.
2. A secret scan for the whole repository on every pull request (including forks), with the findings kept out of
   public logs.
3. A code scanner for the app's TypeScript (and the repository's Python and JavaScript where it is free for
   public repositories), results visible in the pull request.
4. Dependency advisories: `pnpm audit` (or OSV-Scanner on `pnpm-lock.yaml`) in CI, failing on high and critical;
   and the app's direct dependencies added to the daily upstream watch (P62), so new flaws reach us without a pull
   request.
5. The mobile build guide and the pull request template updated to point at these checks instead of local runs.

**Not decided:** which secret scanner and code scanner (licence, maintenance, how fixes are published, and that
they run on forks without secrets; adoption check before choosing); whether the export build runs on every pull
request or only when `mobile/` changes; whether a failed advisory check blocks a merge or only warns at first.

**Overlap:** PR #75 (Maestro robot tests and a roles table in the pull request template) touches the template;
take both together or rebase. P71 (GitHub Actions deployments) uses the same workflows folder.

**Acceptance:** a pull request that breaks the app's types, lint, tests or bundle fails CI; a committed test
secret is caught; a dependency with a known high advisory fails the check; the daily watch lists the app's
direct dependencies.

**Related:** P50 (native app), P62 (daily watch), P35 (open-source list), P71, P96 (SOPs), the build loop in
`mobile/BUILD-GUIDE.md` section 3.

**Owner (26 November 2026):** ranked in tier 1 (row 5a, next to P62). The second review by a different AI model stays
for sensitive screens only (sign-in, security, payments, personal or biometric data); the guide says so.

### P106 — Short video clips with site incidents

**App:** mobile · **Also touches:** drive, erp · **State:** open

**Why (owner, 27 November 2026):** people reporting an incident in the app attach photos; a short video often shows
what happened better.

**What:**
- Clips of **at most 60 seconds**, with Incident photos (P74); the same tags, site check and Drive folder.
- **Compressed on the phone** before upload; the server does not re-encode. **Owner, 27 November 2026: HEVC (H.265)
  when the phone can record it, otherwise H.264**, at 720p with mono AAC sound. HEVC is about 40% smaller (about 9
  MB a minute against about 15 MB for H.264 at 2 Mbit/s). Consequence: a browser that cannot play HEVC (older
  computers, some Firefox set-ups) offers the clip as a download instead of playing it in Drive. The app checks
  the phone's hardware encoder before recording. Android's Media3 Transformer does the conversion (licence and
  advisory check before adoption).
- **New upload path:** today's photo upload takes files under 3 MB in one request; clips need an upload that resumes
  after a dropped connection, and a size limit on the server.
- Offline: a clip waits in the encrypted send queue like a photo (at most 1 day); the queue's size limit needs a
  decision.

**Acceptance (test site):** a 60-second clip recorded on a mid-range phone is under 16 MB, uploads over a poor
connection after an interruption, plays in Drive in a browser (H.264 everywhere; HEVC where the browser supports
it, otherwise offered as a download), and is refused for a site the person does not belong to.

**Related:** P74, P50 (Phase 2 or later, not Phase 1), P72 (disk growth and backups).

### P109 — A light mail client in the phone app (JMAP)

**App:** mobile · **Also touches:** mail, signin · **State:** open · **Category:** now

**Owner, 27 November 2026, evening: all at once and now.** Production is not in real use yet, so there are no live
chats to move. Raven's removal with the notification service (P108), Matrix chat (P73) and the light mail client
(P109) start now, in parallel. The agent had recommended deciding all together but building the app parts after
attendance and approvals, because the same app developer builds Phase 1 to 3; the owner chose parallel work and
accepts that risk.

**Why (owner, 27 November 2026):** mail on the phone without sharing the app's key with another mail app.

**What (agent's proposal for the owner to confirm when it starts):**
- **Read and reply first:** inbox, open a mail, reply, see attachments; everything else in webmail in the phone's
  browser. More features only when people ask for them.
- **Through JMAP,** the mail server's modern interface that our webmail already uses, signed in with the same sign-in
  service (to prove on the test site first).
- **Mail from strangers is shown safely:** a locked-down view, remote images blocked until the person allows them.
- **Reuse:** **Ltt.rs** (Android JMAP client, Apache-2.0) is the best candidate: borrow its mail-server code (its
  JMAP library), not its screens (older Android style; ours are Compose). It calls itself a proof of concept and its
  last release was March 2026, so check its code and upkeep before copying; copied files keep their notices and go
  into the open-source list as `borrowed`. Thunderbird for Android plans JMAP only for 2027.
- **Sign-in:** the mail server already accepts the sign-in service's tokens (that is how webmail works); add the app
  as an accepted client.
- **With it, decide P18:** whether other mail apps (the external mail provider, Outlook) are refused once mail works in our app (agent
  recommends refusing them).

**Related:** P108, P73, P18, P50, P82.

