# Decision log

What we decided and why, for anyone building a similar setup from scratch.
Newest first. Each entry: **decision**, **why**, and where it lives. The
discussion that led to a decision is not repeated here.

## 2026-11-28

### A chat screen for browsers: Element Web, under its own name, from the Desk menu (P73)

- **Decision (owner, 28 November 2026):** chat gets a screen for browsers now, with a "Chat" entry in the Desk's
  menu. The phone app's chat continues separately. The screen is Element Web, unchanged, with our configuration.
  - It has a host name of its own (`chat-web`), not the chat server's, as its makers advise: uploaded files are
    served from the server's name.
  - It names only our server and switches off what would call an outside service.
  - The menu entry opens it in its own tab. The sign-in pages refuse to be shown inside another page, so it is
    not put into the Desk's frame. Signing out of the Desk does not sign out of it yet.
- **Adoption check (28 November 2026; GitHub repository and its Security Advisories):** element-hq/element-web,
  AGPL-3.0 (also offered under GPL-3.0 and a commercial licence). A release about every two weeks (v1.12.36 on
  24 November 2026). 5 advisories in the last 12 months (1 high, of 16 October 2026), each published with its fixed
  version; the newest fix is in 1.12.32, so none is open at 1.12.36. Verdict: adopt, pinned by version and digest,
  in the daily upstream watch (exposure: public).
- **Alternatives on record:** Cinny and FluffyChat (other Matrix web clients; not checked in detail); no browser
  screen at all (chat only in the phone app).
- **Where:** `integrations/chat/element-config.json`, `deployment/stacks/chat.compose.json`,
  `tools/prepare_ingress.py`, `erpnext_drive_integrations/www/place_holder.*`; register entry CHAT-7.

### The phone app is named "UNformat ERP" (P85, P50)

- **Decision:** the phone app's name is **UNformat ERP**, replacing "ERP Mobile". It is the default brand's app name
  (`branding/unformat/brand.json`, `mobile_app.name`), with the app ID `in.unformat.erp`, which test builds use
  from now on as well. A deployment that ships the app as its own product replaces both through its brand settings.
- **Why:** owner, 28 November 2026. The earlier rule (22 November) was one universal, neutral app name; since P85 our
  own brand is the public default and is replaceable, so the app carries the brand's name like the rest.
- **Not changed:** earlier entries of this log and of the work list keep "ERP Mobile", the name in use when they
  were written. The Expo app's tests keep their sample name: that app is being replaced by the native one, and
  three open pull requests touch those files. The native app's own texts are changed in its pull request (#114).
- **Where:** `branding/unformat/brand.json`, `docs/sop/` (five procedures), `mobile/BUILD-GUIDE.md`,
  `mobile/README.md`, `deployment/test-runtime.example.json`, `tests/test_test_oauth_clients.py`.

### Chat alerts: the gateway runs inside the chat stack, optional and private (P73)

- **Decision:**
  - The alert gateway (Sygnal v0.17.0) is a service of the chat stack. It starts only where an operator has
    placed Google's service-account key and asked for the `alerts` profile.
  - It has no port on the host and no public route. Synapse reaches it inside the stack's own network, which has
    a fixed range that Synapse is told it may call.
  - It is the only service on a second network of the stack, `outbound`, its way to Google. It is not on the
    workspace network, so a test site's block on outbound connections from that network stays whole.
  - The key lives in a root-only folder on the host. The one-time `configure` service copies it into the
    gateway's own volume and writes the gateway's configuration for one app ID.
  - The app asks for alerts that carry only the event's ID.
- **Why:**
  - Owner, 27 and 28 November 2026: alerts carry no content, and the Firebase project `unformat-erp` with the app
    `in.unformat.erp` exists.
  - A public gateway address would let anyone who learned a phone's address send it alerts; an address inside the
    stack cannot be reached from outside.
  - Without the key nothing is written and nothing starts, so a site without phone alerts is unaffected.
- **Where:** `integrations/chat/configure.py`, `deployment/stacks/chat.compose.json`, register CHAT-5, the chat README.

## 2026-11-27

### Chat rooms follow the sites, and the business system stores nothing about them (P73)

- **Decision:**
  - The bot keeps three kinds of room: one per enabled Field Site (every enabled member), one per supervisor's
    team at a site (the supervisor, the engineer assigned to them, the site's approvers), and a read-only Notices
    room per person.
  - A room is found by a fixed address made from the site's record name (and the supervisor's chat name), and its
    members are read from the chat server at every run. There is no room table in ERPNext.
  - Rooms are brought in step after every saved change of a Field Site or of a person's chat name, and once an
    hour for everything.
  - A person takes part only with a chat name on their User record; people without one are counted and left out.
    The chat name cannot be changed once set.
  - A failure of the chat server never stops a save; it is logged and tried again.
- **Why:** owner, 27 November 2026: rooms are made by the server side, people join and leave with their site
  assignment, and ERPNext is not to hold what another system already holds (modules stay separate and
  replaceable). A team is the supervisor's team because attendance is organised that way. Reading members from
  the chat server each time makes every run a repair, so a missed run or a manual change heals itself.
- **Where:** `erpnext_drive_integrations/chat_rooms/` (`rules.py`, `matrix.py`, `sync.py`, `hooks.py`),
  `tests/test_chat_rooms.py`, `integrations/chat/configure.py` (the bot also owns `#notices-…` addresses).

### Chat: the business system acts through a bot that invites; nothing holds an admin token (P73)

- **Decision:** the business system has one chat identity, the bot `@erp`, with its own token. It creates the site
  and team rooms and each person's read-only Notices room, invites people, posts, and removes people whose
  assignment ended. Synapse accepts invitations from this server automatically, so people are in their rooms
  without a tap. There is no admin client and no admin user for this.
- **Why:** tried on the test site on 27 November 2026: the authentication service gives a client its own admin
  scope but not Synapse's, which needs an admin person's token. Inviting needs no such right, and one credential
  less with full power over every room is safer. With no federation, only people on this server can invite, so
  automatic acceptance cannot be used from outside. Synapse's own "server notices" need the admin interface too,
  so the Notices room is an ordinary room in which only the bot may write.
- **Where:** `integrations/chat/configure.py` (`bridge`, `auto_accept_invites`), register CHAT-4, the chat README.

### The chat stack: two settings files written by a one-time service; the server name is `chat.<domain>` (P73)

- **Decision:**
  - The server name is `chat.<domain>`, so addresses are `@name:chat.<domain>`. It can never be changed, so
    production starts on the domain people keep.
  - The stack is Synapse, the Matrix Authentication Service and one PostgreSQL each. A `configure` service runs
    once before them, in the Synapse image, and writes both configuration files from the stack's settings; it makes
    the authentication service's signing key the first time and keeps it afterwards.
  - Fixed in that script: sign-in only through the sign-in service, no federation at first, rooms not encrypted by
    default, and people cannot change the name or mail address the sign-in service gives.
  - The stack is opt-in (`chat` in the profile's `projects`) and needs two host names, `chat` and `chat-auth`.
- **Why:**
  - Owner, 27 November 2026: `chat.<domain>` over the bare domain, which would tie chat to the website serving two
    files for ever. The chat server stands on its own address, separate and replaceable.
  - Neither service reads secrets from environment variables, and the authentication service's image has no shell.
    The renderer only fills values into stack files, so a service that turns its environment into the two files
    keeps every secret where the other stacks keep theirs, with no new mechanism in the renderer.
  - The configuration is written as JSON, which both services read as YAML, so the script needs no YAML library
    and is tested offline.
- **Where:** `deployment/stacks/chat.compose.json`, `integrations/chat/configure.py`, `tools/prepare_ingress.py`
  (test routes), `tools/prepare_runtime.py` (the two host names), `tests/test_chat_stack.py`, register CHAT-1 to -3.

### Raven leaves ERPNext; Matrix chat and a light mail client in the phone app, all now (P108, P73, P109)

- **Decision (owner, 27 November 2026), all started now and in parallel:**
  1. **Raven is removed from ERPNext.** System messages to people go through one notification service in our add-on,
     which picks the channel for each person and message: in the app, mail, or WhatsApp. SMS is used only where those
     don't reach. Outside the company: mail, forms (the Respond app and ERPNext web forms) and WhatsApp.
  2. **Matrix is the internal chat, built into the phone app.** The server is Synapse, with the Matrix Authentication
     Service signing in through authentik. The app uses Matrix's Rust SDK through its Kotlin bindings. Company rooms
     are unencrypted so the company can keep and search them.
  3. **A light JMAP mail client in the phone app**, read and reply first. It borrows the mail-server code of Ltt.rs
     (Apache-2.0); the screens are our own.
  4. **The app's sign-in** (Phase 1) is built so one passkey sign-in gives every token: ERPNext's, and the sign-in
     service's for mail and Matrix.

  This replaces three earlier decisions: "Chat, Mail and Drive stay separate apps" (22 November) for chat and mail;
  "incidents go to Raven threads"; and "Raven inside the company" (P22).
- **Why:**
  - The app holds each person's key in the phone's secure hardware, and Android cannot share it with another app. So
    chat and mail must be inside our app, whichever server they use.
  - Matrix over Raven: an open standard, independent of ERPNext's uptime, able to connect separate companies later,
    with a maintained Android library and calls. The costs are a new server (with monitoring, backups and a test
    copy), an ERPNext bot for document messages, and about three months of work.
  - Synapse because the Matrix Authentication Service supports only Synapse today. The lighter Tuwunel and
    continuwuity are on record as alternatives.
  - Production is not in real use, so no live chats need moving.
  - The owner chose parallel work over the agent's suggestion to build the app parts after attendance and approvals.
- **Kept:** the phone sign-in check (`portal/mobile.py`). It was written for Raven's app but signs in every phone app
  now, so its settings are renamed, not removed.
- **Adoption check (27 November 2026; GitHub and Codeberg repositories and GitHub Security Advisories):**
  - **Synapse** (element-hq/synapse): AGPL-3.0, a release every one to two weeks (v1.166.0 on 24 November 2026).
    13 advisories in the last 12 months (7 high), published in two batches with the fixed versions (1.152.1 and
    1.157.2); none open at 1.166.0. Verdict: adopt, pinned by version and digest, in the daily upstream watch.
  - **Matrix Authentication Service** (element-hq/matrix-authentication-service): AGPL-3.0, v1.30.0 on 24 November
    2026, no advisories in the last 12 months. Verdict: adopt.
  - **matrix-rust-sdk** (matrix-org/matrix-rust-sdk): Apache-2.0, v0.20.0 on 25 November 2026. 4 advisories in the
    last 12 months (1 high), all fixed by 0.19.0. Verdict: adopt at 0.20.0 or later.
  - **Sygnal**, the push gateway: the matrix-org repository is archived; it continues at element-hq/sygnal
    (AGPL-3.0, v0.17.0 of 5 November 2025, commits in November 2026, no advisories). Verdict: adopt from element-hq
    when the app's chat alerts are built.
  - **Ltt.rs** and its JMAP library (codeberg.org/iNPUTmice): Apache-2.0. Little upkeep: the library's last commit
    was April 2025, the app's last code change October 2025. Verdict: borrow the JMAP library code with caution and
    maintain our copy ourselves; do not depend on upstream fixes.
  - All stay `evaluating` in the open-source list until each is deployed or copied.
  - **Room on the test VM:** 8 GB memory with about 3.5 GB available, 3 CPUs, 120 GB disk free: enough for Synapse,
    its database and the authentication service on test. Production's room is checked before promotion.
- **Where:** P108, P73, P109, P50, P04.

### Removing Raven: the phone sign-in keeps working under a neutral name; uninstall before the new image (P108)

- **Decision:** Raven leaves the ERP build (the app list, the version lock, the daily watch), the portal's app
  frames, onboarding's app rules, the phone menu and the proxy (its discovery route and its preflight route). The
  phone sign-in check stays: its switch is now `cloud_native_mobile_enabled`, the old name
  `cloud_raven_mobile_enabled` is still read when the new one is absent, and the single-client setting
  `cloud_raven_mobile_client` approves nothing any more. The proxy file is `cloud-native-clients.yaml`
  (routers `cloud-native-token` and `cloud-native-bearer`, middleware `cloud-native-auth`).
- **Order on each site (it matters):** (1) with the **old** image still running, `bench --site <site> uninstall-app
  raven` after a database backup (this deletes Raven's messages and channels); (2) deploy the new image, built on a
  core without Raven; (3) set `cloud_native_mobile_enabled` in the site config and remove the two old keys;
  (4) install the renamed proxy file and remove the two old ones. An image without Raven's code on a site that
  still lists Raven as installed does not start.
- **Why:** owner, 27 November 2026 (see the decision on Matrix and the notification service). The sign-in check
  was written for Raven's phone app but signs in every phone app; reading the old switch name keeps a site working
  between the image and the config change.
- **Where:** `portal/mobile.py` (`enabled`, `clients`), `deployment/config/proxy/cloud-native-clients.yaml`,
  `tools/prepare_ingress.py`, `deployment/upstream-lock.json`, `deployment/stacks/erp.compose.json`,
  `tools/initialize_erp.py`, `portal/sso.py`, `public/session.js`, `www/place_holder.html`, `onboarding/access.py`,
  `tests/portal/test_mobile.py`, `tests/test_portal_deep_link.py`, the register (Raven section removed).

### Native app Phase 1 and sign-up: lock, offline window, photo cache, user name, verification codes, video (P50, P74, P82, P04, P106)

- **Decision:**
  - The app asks for the fingerprint again after **3 minutes** away (another app opened or the screen off).
  - Without a connection it still opens for **12 hours**, then it needs a connection.
  - **Photos offline:** the app keeps previews and the photos a person has opened, of their own sites only, in its
    encrypted store: at most 200 MB and 7 days. They are wiped at sign-out, when the key is lost, and for a site the
    person no longer belongs to.
  - **Sign-up:** full name (first name required, surname optional). The **user name is the full mail address**. The
    mail address is verified with a **6-digit code from our own mail server**, the mobile number with a **6-digit
    code over WhatsApp**. Each code expires after 10 minutes, allows 5 tries, and a new one can be asked after 60
    seconds.
  - **Incident videos:** clips of up to 60 seconds, compressed on the phone at 720p, **HEVC where the phone records
    it, otherwise H.264**.
- **Why:** owner, 27 November 2026.
  - 12 hours covers one site shift. Offline attendance must work for a whole shift without signal, and a switched-off
    person is refused at the next connection.
  - The mail address is already ERPNext's user ID, so one identity runs through every app.
  - Six digits suit a phone's number pad. The expiry and the try limit, not the alphabet, protect the code.
  - Our mail server sends codes for free, while Firebase only sends sign-in links by mail and charges for SMS.
    WhatsApp replaces SMS later as well.
  - HEVC is about 40% smaller than H.264. H.264 remains as the fallback, and a browser without HEVC offers the clip
    as a download.
- **Where:** the native app (`mobile-native`, PR #114) for the lock, offline window and cache; P82 sign-up; P04
  (WhatsApp); P106 (video upload, to build).

### Face enrolment: also the worker's own supervisor or engineer; the agreement in English, other languages on choice (P95)

- **Decision:** besides HR, a Field Attendance Manager and the project manager of the worker's site, the worker's own
  supervisor (the responsible supervisor on their Field Worker Assignment) and the engineer assigned to that
  supervisor at that site may enrol a face and record a withdrawal. Another team's supervisor or engineer is refused.
  The face attendance agreement opens in English; the worker may choose to read a translation in the language of
  their choice, and the language they read is recorded with their consent (as before, every acceptance records the
  agreement version and language). If a translation and the English differ, the English version governs, and the
  agreement tells the worker so. By ticking "I agree" the worker also confirms that the person enrolling them
  explained the terms in a language they understand; the consent record names that person and the language.
- **Why:** owner, 27 November 2026, answering the native app's request on PR #114. Supervisors and engineers are the
  ones at the site with the team, so enrolment does not wait for HR or the project manager to visit. Limiting it to
  the worker's own team keeps it to people who know the worker; the consent record names who recorded it, and the
  project manager looks over new enrolments (SOP). English as the default with a free choice of translation keeps one
  reference text and still lets every worker read it in a language they understand.
- **Where:** `custom_hr/face_service.py` (`may_enrol`, `require_enroller`), `tests/test_custom_hr_face_enrolers.py`,
  `custom_hr/face_queue_integration_tests.py` (part 6), the module README, `docs/sop/field-face-enrolment-and-consent.md`,
  `docs/sop/face-attendance-agreement.md` (draft 2), `docs/sop/README.md`.

### Face attendance has an off switch, and it is off unless the site turns it on (P95)

- **Decision:** every face function that takes in or uses a face (enrolment, identification, the capture queue's
  intake, its lists and its decisions) refuses unless the site config has `custom_hr_face` -> `enabled: true`. The
  check is the first line, so nothing is read or stored while off. Withdrawing consent, deleting face data when an
  employee leaves or is deleted, and the daily removal of rejected photographs never depend on it.
- **Why:** owner, 27 November 2026. The ERP ships as one image, so a release of main for other merged changes (P93,
  #77) also ships P95. Without face settings, matching and enrolment already refused, but the capture queue still took
  in photographs for manual review: a working face-photo intake on production before the legal opinion. An
  explicit switch, off by default, lets the code be released while nothing can use it.
- **Where:** `custom_hr/face_service.py` (`enabled`, `require_enabled`), `custom_hr/face_queue.py`,
  `custom_hr/face_queue_integration_tests.py`, `tests/test_custom_hr_face_switch.py`, the module README.

### The boot check's alert mail may connect to the mail server's private address (P57)

- **Decision:** the alert sender's settings take an optional `address` (an IP address). The boot check then connects
  there instead of to `smtp_host`, and still verifies the server certificate for `smtp_host`; certificate checks are
  never switched off. Without `address` nothing changes.
- **Why:** owner, 27 November 2026. On the production server the mail server's public name resolves to the public
  address, where the submission port is closed; it answers only on the server's tailnet address, whose certificate
  carries the public name. The options were a line in the server's hosts file (a hand patch outside the
  repository that also changes the name for everything else on the server) or this setting; the owner chose the
  setting. The onboarding form mail already uses the same pattern (`address` in `test_form_smtp`).
- **Where:** `tools/host_check.py` (`verified_smtp`), `tools/render_host_checks.py`,
  `deployment/host-checks.example.json`, `docs/production-moves.md`, `tests/test_host_checks.py`.

## 2026-11-26

### Unformat is the default brand, public and replaceable (P85)

- **Decision:** our own brand, Unformat (the "UN / format" logo, favicons, name and colours), is published in
  `branding/unformat/` and is the default look: the ERP's logo and favicons and the front page's title and name.
  A deployment replaces it through its private profile (`company_logo`, `company_favicon_dir`, `website_title`,
  `website_name`), as before. The copyright notice reads "Copyright © 2026 unformat.in"; the name and logo are
  trademarks of unformat.in, free to use to run, test and show the software, replaced by anyone shipping it as
  their own product. The mobile app's name, app ID and icons follow in a later step with the app's maintainers.
- **Why:** the owner aims to keep about 95% of the work public; our brand is part of it, and users always keep the
  choice of replacing it. Clients' brands stay private (P84). Deployments that supply their own branding, such as
  production and the test site, see no change.
- **Where:** `branding/`, `erpnext_drive_integrations/public/company-*`, `tools/prepare_runtime.py`, `README.md`,
  `LICENSES.md`, `tests/test_branding.py`.

### After a reboot every container that ran before must run again; the admin is mailed (P57)

- **Decision:** the boot check compares the running containers with the list the five-minute watch saved before
  the reboot. A container with restart policy `always` or `unless-stopped` that is not running a minute after
  Docker started is started once; anything still down fails the check. When the check repaired or failed
  something it mails the admin through a dedicated alert sender, independent of Prometheus. The monitoring stack
  uses `restart: always`; exporter-only hosts remove the central containers instead of keeping them stopped.
- **Why:** owner, 26 November 2026. After a production reboot Prometheus stayed down for 26 minutes (exit 0,
  `unless-stopped`) and nobody knew, because no alert leaves a server yet. A reboot of the test VM did not
  reproduce it: a fast-stopping copy of Prometheus with the same policy came back. So the exact cause is still
  open, and the fix does not depend on it. Starting a missing container once is the same pattern the check
  already uses for the editor bridge; the cost is that a container stopped on purpose in the few minutes before a
  reboot is started again (the list is at most five minutes old, and the start is reported).
- **Where:** `tools/host_check.py`, `tools/render_host_checks.py`, `deployment/host-checks.example.json`,
  `integrations/monitoring/observability/compose.yml` and README, `docs/production-moves.md`,
  `tests/test_host_checks.py`.

### The ERP web server clears two forwarded headers now; trusted forwarding waits for the frappe_docker bump (P98)

- **Decision:** our ERP web server template clears `X-Forwarded-SSL` and `X-Forwarded-Protocol` before requests go
  to the backend and to realtime, as upstream does. Upstream's switch for trusting `X-Forwarded-Proto`
  (`TRUST_UPSTREAM_FORWARDED_PROTO`) is taken at the next frappe_docker bump, set to "on"; until then our existing
  map, which behaves like "on", stays.
- **Why:** a browser's copy of those two headers reached Gunicorn, which trusts the frontend and reads them, so the
  backend could see two protocol indications. The switch needs upstream's newer nginx entrypoint: with our pinned
  image the variable would stay unfilled and every request would look like plain http, which can break sign-in
  redirects. Our current behaviour is safe because the public proxy replaces forwarded headers from outside, the
  frontend is published only on the server's loopback address, and Gunicorn trusts only the frontend (owner,
  26 November 2026: the recommended options).
- **Where:** `deployment/erp/frappe.conf.template`, register entry BUILD-2, `tests/test_realtime_origin.py`.

### The drift check compares mounted runtime files, and runs its own code from main (P99)

- **Decision:** the drift check also compares every read-only runtime file the containers mount from the
  repository. A mount counts as equal to main when its bytes equal main's file, or when it matches the record
  written at deployment and its source has not changed on main since; it is behind when its source changed, and
  changed by hand when it differs from its record (both drift); with no record it is listed as not compared,
  without failing the run. Records are written by every full render and by a `record` command after a one-file
  promotion. The nightly run first moves its own checkout to `main`.
- **Why:** after P97 the ERP web server template on production equalled main, yet the check reported it as behind
  because it reads only the image tag; a file changed by hand on a server was never noticed at all. The check's
  own code on production was still from 24 November, so improvements to it never ran. Existing production files
  have no record and are listed as not compared until their next release (owner, 26 November 2026: the
  recommended options).
- **Where:** `tools/drift_check.py`, `tools/runtime_mounts.py` (shared with `tools/prepare_runtime.py`),
  `deployment/drift-check.service.example`, `deployment/README.md`, `docs/sop/production-release.md`,
  `tests/test_drift_mounts.py`.

### The Android app is rebuilt natively; Phase 0 lays the foundation (P50)

- **Decision:** the Android app is rebuilt in Kotlin with Jetpack Compose in `mobile-native/`, beside the Expo app,
  which stays the app in use until the native one does everything it does and passes the same checks; the iPhone
  app follows after Android. The rules live in a pure Kotlin module without Android, so they can be shared with an
  iPhone app later without choosing a cross-platform framework now. Built in from the first day: a data-flow
  tracker (one tracking number per action, a mark at each of eight points, a read-back comparison after every
  save), building blocks that cannot show an action word without an action, no backup or screenshot of app data,
  one command that runs every check, and a pinned checksum for every library.
- **Why:** developer's decision with the owner's agreement, 26 November 2026 (confirmed by the owner on 27 November), after the P82 trial showed the
  sign-in key, the fingerprint lock and the computer sign-in must be native code anyway. Testing the Expo app
  showed taps that led nowhere and failures without a reason; the tracker and the building blocks make those two
  faults visible or impossible. Crash reports will use Google's free service (developer's choice, not added yet).
- **Dependency review:** on 26 November 2026, Kotlin 2.2.10, the Android Gradle plugin 9.2.1, Compose BOM
  2026.09.00 (UI, Material 3, adaptive navigation suite), AndroidX Activity 1.12.4 and Biometric 1.1.0
  (Apache-2.0) and JUnit 4.13.2 (EPL-1.0, tests) were checked in OSV: none open (the two Kotlin standard-library
  entries were fixed before 1.6; JUnit's was fixed in 4.13.1). detekt is not added yet: its stable release does not
  support this Kotlin version; Android lint runs with warnings as errors meanwhile. Added for the screen tests
  (tests only, not in the app): Robolectric 4.18 (MIT, active, released 13 November 2026) and Compose's UI test
  library; OSV, 26 November 2026: none open.
- **Checked in CI (owner's go after review, 27 November 2026; P100):** `gradle checkAll` runs in the `native-app`
  job of `.github/workflows/check.yml` on every push and pull request, so the app's tests, lint and checksum check
  no longer run only on the developer's computer. Gradle is downloaded at 9.9.2 and checked against its published
  SHA-256. GitHub Security Advisories for Gradle, checked 27 November 2026: one critical (GHSA-3cfg-jpcr-gfp3) and
  seven high (GHSA-7f7r-77ff-fr6f, GHSA-99wf-vhq9-wm2x, GHSA-4mf6-7pm2-6wm8, GHSA-35pj-rg5r-8rpv, GHSA-gqrr-4j89-5267,
  GHSA-pcp8-98xm-c6pr, GHSA-j5m7-59rp-24f5) affect versions before 9.9.2 (released 19 November 2026), which fixes them all; the README now asks for 9.9.2 or newer.
  The checksum list gains the Linux and Mac copies of the Android build tool aapt2 (from Google Maven; the Windows
  copy matched the existing entry), which a list made on Windows lacks.
- **Review fixes (27 November 2026):** the calling layer treats a redirect as signed out (the sign-in service in
  front sends an expired session to its login page), shows the server's refusal sentence only when it is readable
  text (no error dump, code or page; the original stays in the test-build detail), and no longer crashes when
  sign-out clears the tracker while a save waits.
- **Where:** `mobile-native/` (README), `tests/test_mobile_native.py`. AI-assisted by Claude Code.


### One build loop for every screen of the mobile app (P100)

- **Decision:** every screen of ERP Mobile goes through one loop: a tap and state list (loading, empty, offline,
  refused, error); a mock-up approved before code; tests for the rules first; screen tests in every state at phone
  and tablet size; automatic checks (build, tests, code scanner, dependency advisories, secret scan); own review
  against a checklist; a second review in a fresh session, by a different AI model for sign-in, security, payments
  and personal data; a tap-through on a real phone; a small pull request saying what was and was not tested; the
  maintainers test on the test site; the owner merges. A fault found late returns to the start with a new test.
  The project rules are added to it: a P item first, advisories and the open-source list for new packages, the
  promotion plan, SOP and register updates in the same pull request. The review by a different model is kept to
  sensitive screens only (owner, 26 November 2026); P100 is ranked in tier 1.
- **Why:** the developers' own loop (26 November 2026) was stricter than the guide: it covers every state of a
  screen, real phones and an independent review, and stops a fixed fault from returning. CI did not check the app
  at all, so the automatic checks become their own item (P100) and are run by hand until then.
- **Where:** `mobile/BUILD-GUIDE.md` sections 3 and 10; P100 in the work list.

### A project manager's own online check-in needs no approval; attendance photos served after our own check (25 November 2026)

- **Decision:** when an Approver member of a site checks in themselves at that site, online and without a clash with
  HR attendance made elsewhere, the entry becomes HR attendance at once (remark "Own check-in of the site approver:
  no approval required"). Offline check-ins and clashes still go to another approver or a Field Attendance Manager,
  and team entries the approver records still need another approver. A new read-only call `entry_photo(name)`
  returns an entry's photograph to anyone the existing `entry` call allows, and only the private file attached to
  that entry.
- **Why:** owner, 25 November 2026: a project manager should not wait for someone else to approve their own day.
  The photo problem: `/private/files` applies ERPNext's user permissions on Employee, so a project manager could not
  open another employee's attendance photograph; answering from our own site rules keeps those permissions as they
  are.
- **Where:** `custom_hr/domain.py` (`skips_approval`), `service.py` (`approve_without_review`, `self_capture`),
  `api.py` (`entry_photo`), the custom_hr README, `tests/test_custom_hr.py`. Public PR #77, tested on the test site on
  25 November 2026 at `2a9f149` (12 of 12 live checks). Decision entry added by the owner's agent at merge.

### Design decisions about use are written into the SOPs in the same change (P96)

- **Decision:** a decision that says how people will use the system goes into the SOPs when it is taken, without
  being asked for: the picture by role in `docs/sop/how-we-use-the-system.md`, the steps in the procedure concerned.
- **Why:** owner, 26 November 2026: our decisions already contain how we plan to use the app; if that stays in the
  decision log and the work list, the people who use the system never read it.
- **Where:** `docs/sop/README.md` (rule), `docs/sop/how-we-use-the-system.md`.

### Face capture queue: recorded in the supervisor's name, decided by another approver (P95)

- **Decision:** a team photograph sent without choosing the worker is validated once on arrival (place, time,
  photograph) and kept privately in a queue. A confident face match is recorded and submitted at once in the
  capturing supervisor's name, through the same capture rules as before, and then needs the usual approval.
  Everything else waits for the site's approvers, who pick the worker or reject with a reason. An approver cannot
  decide their own capture or record themselves, and the chosen worker must be on the capturing supervisor's team.
  The queue's copy of the photograph is deleted when the capture is recorded; a rejected capture keeps it for 30
  days (confirmed by the owner the same day).
- **Why:** owner, 26 November 2026: the supervisor only takes photographs, also without connection; the project
  manager clears what the server cannot settle. Validating on arrival keeps the one-day limit for offline captures
  meaningful even when the project manager decides later. Recording through the existing capture and submit
  functions, with an explicit actor that no request can set, keeps one set of attendance rules.
- **Where:** `custom_hr/face_queue.py`, `face_queue_rules.py`, the Field Face Capture DocType, `service.capture`
  and `service.submit_entry` (`actor`, `evidence`), `api.py`, the field team page, `tests/test_custom_hr_face_queue.py`.

### Face engine: OpenCV Zoo's YuNet and SFace in the ERP image, pinned by commit and checksum (P95)

- **Decision:** the face engine uses YuNet (detection) and SFace fp32 (128 numbers per face) from OpenCV Zoo at
  commit `48b10fa`, fetched into the ERP add-on image with a SHA-256 check per file, and run by the OpenCV already
  in the image (5.0.0.93, pinned). It is switched on per site in site config. A photograph must hold exactly one
  clear face. The daily watch follows the model pin.
- **Why:** owner, 26 November 2026: build on SFace now (adoption check above: Apache-2.0 code and weights, MIT for
  YuNet, no open advisories for OpenCV 5.0.0.93 or numpy 2.5.4, OSV). The engine test on OpenCV's sample photos
  separated the same face (0.93 to 0.97 when mirrored, smaller or darker) from a different person (0.18) at the
  0.363 threshold. Detection confidence is 0.8, not the 0.9 of the samples, because 0.9 refused a smaller copy of a
  clear face; field photos will vary more.
- **Still before production:** the legal opinion and the SFace training-data question (P95); tuning on real
  photos in the trial.
- **Where:** `custom_hr/face_sface.py`, `deployment/face-models.json`, `tools/fetch_face_models.py`,
  `deployment/erp/Dockerfile.addon`, register BUILD-11, `tests/test_custom_hr_face_engine.py`.

### Recovery only after the project manager checks the phone in person; leavers' files stay; 30 days for rejected captures

- **Decision (owner, 26 November 2026):**
  - **Lost passkey or replacement phone:** the project manager verifies the person's phone in person and confirms
    the request in their own app (P82); until the app does this, they confirm it to the admin themselves. Nothing
    is re-issued on a message, mail or call.
  - **Leavers:** their personal business files stay in place and are not deleted. Mailboxes are shared in the
    present setup, so there is no personal mailbox to close or redirect; the person is removed from the shared ones.
  - **Rejected face captures** keep their photograph for 30 days, then only the record and the reason remain (P95).
- **Why:** recovery is the easiest way around a strong sign-in, so it gets the same in-person check as onboarding.
  Files a person made for the business belong to the business. Thirty days is long enough to answer a dispute
  about a rejected capture and short enough not to keep faces without a purpose.
- **Where:** `docs/sop/invite-a-user.md`, `onboarding-identity-and-biometrics.md`, `leaver-offboarding.md`,
  `attendance-approval.md`; P82, P86, P95 and P96 in the P list; `custom_hr/face_queue_rules.py` (30 days).

### Trial app for passkeys held by the mobile app (P82, first step)

- **Decision:** Before anything is built into the mobile app, a small throw-away Kotlin test app answers the
  open questions of P82 on real phones: whether a computer's QR sign-in accepts a third-party passkey service's
  keys, what works on Android 9 to 13, and whether the fingerprint lock (strong biometrics only, no PIN, key
  destroyed when a fingerprint or face is added) holds on the phone brands in use. The app reads back what the
  phone really did and refuses a key that is weaker than asked. It is never shipped.
- **Why:** The whole P82 design rests on these three points and none is documented by Google or the phone
  makers; a trial costs days, a wrong assumption costs the design.
- **Dependency review:** On 26 November 2026, `androidx.credentials` 1.6.0 and `androidx.biometric` 1.1.0
  (Apache-2.0, Google, both the latest stable releases) and JUnit 4.13.2 (EPL-1.0, tests only) were checked in
  OSV: none open for the two AndroidX libraries; JUnit's GHSA-269g-pwp5-87pp is fixed since 4.13.1. Built with
  the Android Gradle plugin 9.2.1 and its built-in Kotlin. Library checksums are not pinned in the trial.
  For the own QR route (owner's go, 26 November): OkHttp 4.12.0 (Apache-2.0, Square) and Google's
  `play-services-code-scanner` 16.1.0, both checked in OSV on 26 November 2026: none open. The route's reference
  is the hybrid authenticator in microG GmsCore (Apache-2.0, active); no file was copied.
- **Where:** `mobile/trials/passkey-android/` (its README lists the trial-only shortcuts). AI-assisted by Claude Code.

### Correction: removing a fingerprint does not destroy an ERP Mobile key (P82)

- **Correction:** P82 said that adding **or removing** a fingerprint or face destroys the key. The P82 trial (PR #98,
  two phones) found that Android destroys it only when one is **added**; removing one leaves the key working. The
  record now says so (owner's yes, 26 November 2026). This changes nothing in the design: the onboarding check
  that only the person's own fingerprints are enrolled (P96) still covers the fingerprints that were there before.

### Sign-ins from unusual places alert the admin (P82)

- **Decision:** the sign-in server learns each person's usual IP addresses, networks and approximate locations
  (city and country from the IP address, not GPS). A sign-in from somewhere unusual, or two sign-ins too far apart
  for the time between them, alerts the admin on the Desk widget and/or by mail. It alerts and does not block at
  first. The admin can mark office and site networks as usual for everyone.
- **Why:** owner, 26 November 2026: a stolen or shared sign-in usually shows up as a new place. authentik already
  records address and location with each sign-in event, and has a free GeoIP policy and notification rules, so no
  paid feature is needed (to verify on test). Sign-in locations of employees are personal data: they go in the
  staff notice, are kept for 90 days (then only the learned usual places remain; owner), and only the sign-in admin
  sees them.
- **Where:** P82 in the P list (also P53, P72); not built.

### Face attendance, first part: templates encrypted on the server, readable by no role, deleted for good (P95)

- **Decision:** a worker's face is kept only as encrypted templates (site encryption key) in **Field Face
  Enrolment**, one record per worker, in a field no role can read and with no version history; photographs taken
  for enrolment are not stored. Consent is a separate **Biometric Consent** record that stays as evidence.
  Identification compares one photograph only with the workers the requesting supervisor may record on that site
  and shift, and decides alone only above a threshold with a clear margin over the next worker. Templates are
  deleted permanently on withdrawal, when a worker leaves, or when the employee record is deleted. The face model
  is a separate slot that stays off until a model passes the adoption check.
- **Why:** owner, 26 November 2026: faces of field workers live on our server, not on supervisors' phones, and the
  owner asked to build now without waiting for the lawyer's opinion. Keeping templates out of every role's view,
  out of version history and out of Deleted Documents limits who and what can ever copy them; the margin rule
  keeps look-alikes for a person to decide.
- **Where:** `erpnext_drive_integrations/custom_hr/face.py`, `face_service.py`, `face_engine.py`, the two DocTypes,
  `api.py` (`face_enrol`, `face_identify`, `face_withdraw`), `tests/test_custom_hr_face.py`, the module README.

### One list of the open-source projects we use, credited and tracked in step (P35)

- **Decision:** every open-source project we use, borrow code from or evaluate is in `docs/open-source.json` with
  its repository, licence, where we use it and how we track it. The README acknowledgements and
  `docs/open-source.md` are generated from it, and a test fails when a component the upstream watch follows, or an
  upstream named in `modules.json`, is missing from the list (or the other way round). Projects under evaluation
  are listed but not credited as used; they are credited and tracked in the pull request that adopts them.
- **Why:** owner, 26 November 2026: we rely on many open-source projects (microG is being evaluated now) and must
  credit them and follow their repositories. The README thanks had fallen behind the daily watch (the monitoring
  stack, backup tools, CoreDNS, frappe_docker, the hosts' software), because the two lists were kept apart. The
  first list also found that ownCloud Web's repository was archived on 23 November 2026 and that ocis-konnectd has
  been archived since 2020.
- **Where:** `docs/open-source.json`, `tools/open_source.py`, `tests/test_open_source.py`, `README.md`, `AGENTS.md`.

### Every upstream post is listed and checked for replies until we stop using that project (P35)

- **Decision:** our bug reports, feature requests, comments and workarounds on other projects are listed in
  `docs/upstream-posts.json` with a log of every check and follow-up. `tools/upstream_posts.py check` (read-only)
  reports replies, state changes and threads the account posted on that the list lacks; it runs at every session
  start and inside the daily upstream watch. A post stops being watched only when we no longer use the project, with
  the reason. Private reports stay in the private companion.
- **Why:** owner, 26 November 2026: a post is only useful if someone reads the answer; a maintainer replied to our
  Collabora findings two days before anyone noticed, and a Coolify bug we reported was fixed the same day. The rule
  is in the working agreements for every project.
- **Where:** `tools/upstream_posts.py`, `docs/upstream-posts.json` and `.md`, `tools/upstream_watch.py`,
  `AGENTS.md`, `tests/test_upstream_posts.py`.

### Computer sign-in by QR runs through our own app on every phone, keeping the Bluetooth check (P82)

- **Decision:** ERP Mobile carries out the standard QR-and-Bluetooth computer sign-in (FIDO hybrid) itself, on
  every Android version, instead of relying on Android 14's passkey-provider service. The Bluetooth nearness check
  and the browser's origin check stay; an approval-only QR without them stays refused (25 November).
- **Why:** owner, 26 November 2026: staff with phones below Android 14 must be able to sign in on a computer too.
  The alternatives were app-only use on older phones, or counting the affected staff first. One route on every phone
  also means one way to test and support. Cost: about 4 to 6 weeks plus the review.
- **Where:** P82 in the P list; the Android trial verifies the tunnel service, Bluetooth on our phone brands and
  attestation through this route.
- **Temporary (owner, same day):** few phones below Android 14 remain, and in about a year there will probably be
  none. The app reports each phone's Android version, the admin sees how many active phones are below 14, and when
  none are left the route is retired, after which phones use Android's own provider route. The add-on is kept
  separate and removable so that retiring it is a switch.
- **Relay (owner, same day):** our route uses the public relay the standard names, run by Google, for the trial and
  for real sign-ins until the add-on is retired; no relay of our own is built. The relay sees only encrypted data.
  Accepted: no agreement with Google, which can change or stop the service (fallback: our own relay, or app-only use
  on older phones). Before any real sign-in, the route's encryption code is reviewed by an AI agent in the role of
  a senior security analyst, not by an outside expert (owner, same day): **Codex** (OpenAI), a different model from
  the Claude agent that wrote it. Accepted: no independent human review. The review is done in a separate session
  from the code and the standard, with the standard's test cases and live checks against Chrome, well-reviewed
  libraries for the encryption, and a written report with the owner's acceptance. Codex works under the working
  agreements, with no production keys or secrets. Planned for the week of 30 November 2026; P82 stays open for it.

### Office computers are bound by company certificates, not authentik's paid stage (P82)

- **Decision:** each office computer gets a certificate from our own certificate authority (smallstep step-ca); the
  proxy requires it on the host names computers use and passes it on; a free authentik expression policy checks it
  against an allow-list the admin manages (list and remove computers). The phone app's host names stay without it.
- **Why:** owner, 26 November 2026: only free tools. authentik's client-certificate stage is Enterprise and its
  Endpoint Devices is a preview; the alternatives checked either bind only the network path (Headscale, kept as a
  later complement), rely on self-reported passkey types (Windows Hello), or need paid editions (Pomerium device
  approval, Teleport, NetBird). Certificates bind every request to a key that cannot be copied off a Windows PC.
- **Where:** P82 in the P list; to build and verify on test first.

### Unused-key grace days are set per group by the admin; leavers are removed from the Frappe HR exit (P82, P95)

- **Decision:** the admin sets how many unused days each authentik group allows before the sign-in server removes a
  key (7 when not set), including the Apple exception group. The exit procedure in Frappe HR (separation, status
  Left) triggers removal of the person's keys, devices and sessions and purges their data in the app; face templates
  are deleted with it.
- **Why:** owner, 26 November 2026: one fixed period does not suit every group; leaving must close every way in
  without depending on someone remembering each app.
- **Where:** P82 and P95 in the P list; SOP A14 (`docs/sop/README.md`).

### Face model: build on SFace now; the legal opinion and the training-data question are settled before production (P95)

- **Decision:** the face engine uses OpenCV Zoo's SFace (fp32) with the YuNet detector, run by OpenCV on the server.
  The unanswered question of which dataset trained the published SFace weights was added to the existing upstream
  issue (opencv/opencv_zoo#313). The residual risk, and the lawyer's opinion, are settled before the app is
  connected to production; development and tests go ahead.
- **Why:** owner, 26 November 2026. SFace's code and weights are Apache-2.0 (rare among face models; InsightFace's
  free models are non-commercial only), but its training data is not documented.
- **Where:** P95 in the P list; `custom_hr/face_engine.py`.

### The admin receives the alerts, and sees alerts and exceptions in a Desk widget (P72, P53)

- **Decision:** monitoring, backup and sign-in exception alerts go to the admin. The person with authentik admin
  rights also gets a Desk widget listing them, each linked to where it is handled (scope added to the parked P53).
- **Why:** owner, 26 November 2026: alerts nobody watches are no alerts; the admin is the one who acts on them.
- **Where:** P72 and P53 in the P list; SOP F5.

### ERP Mobile keys not used for 7 days are removed by the sign-in server (P82)

- **Decision:** the sign-in server removes a person's ERP Mobile passkey when it has not been used for 7 days; the
  person onboards again (project manager, then admin). The app reports the removal and deletes its own copy.
- **Why:** owner, 26 November 2026: a safety net for phones that are lost, left in a drawer or passed on without
  anyone reporting it. It runs on the server because the server knows each key's last use and a switched-off phone
  cannot act. Accepted cost: anyone away for more than 7 days onboards again; the period can be lengthened (14 or 30
  days) if that is too frequent.
- **Where:** P82 in the P list (`docs/p-list/signin.md`); the onboarding SOP (`docs/sop/`); not built yet.

### Onboarding through the project manager and the admin; strong biometrics only; 5 misses erase the key (P82)

- **Decision:** a person requests access in ERP Mobile (mail address, mobile number, a face photo for the identity
  check only, not kept). The project manager approves their identity in person, then the admin approves in
  authentik; the app creates the key in the phone's secure hardware and authentik stores only its public half.
  The key unlocks only with Android's strong (Class 3) biometrics, so weak camera face unlock is never offered and
  a phone without a strong sensor is refused. The app counts misses in a row (reset after a successful sign-in,
  tries left shown, growing waits) and erases the key after 5; the person then onboards again through both
  approvals. The person confirms at onboarding that only their own fingerprints and face are enrolled. Phones on
  Android 9 to 13 stay supported: the trial tests whether the app can run the computer QR sign-in itself there.
- **Why:** owner, 26 November 2026: identity must be checked by someone who knows the person, and the key accepts
  every fingerprint on the phone, so that is a manual check. Counting only misses in a row avoids erasing keys for
  wet or dusty fingers on site. Forcing Face ID would not close the Apple exception's gap (synced passkeys unlock
  with the other person's own Face ID), so the fix there is the Apple version of the app.
- **Where:** P82 in the P list (`docs/p-list/signin.md`); app code to follow in `mobile/`.

### Self check-in uses the biometric and the location fence, no selfie (P82; amends the 22 November decision)

- **Decision:** employees with the app check in with the fingerprint (or strong face unlock) at each check-in plus
  the site's location fence and the server's time; the selfie is dropped. Approval by the site's approvers is
  unchanged.
- **Why:** owner, 26 November 2026: the biometric already proves who is holding the phone at that moment, so a
  selfie adds face data without adding proof. The location check is our own server code and costs nothing.
- **Where:** P82 in the P list; `custom_hr` and `mobile/` when built.

### Field team attendance by face: liveness on the phone, matching on the server (P95)

- **Decision:** HR enrols field workers with one good phone (several angles, checked against their ID); the server
  keeps encrypted face templates, never the supervisor's phone. The supervisor photographs each worker without
  selecting them first; the phone checks liveness offline (MediaPipe head turn and blink, a photo and screen
  check), the server matches against that site's roster (SFace). Uncertain matches are picked by the supervisor
  when online; offline captures are queued and the project manager clears what the server cannot match. Consent
  is a separate agreement at onboarding, with a path without a face for those who refuse. A lawyer's opinion
  under India's DPDP Act is obtained before launch; development goes ahead meanwhile with synthetic or consenting
  test data only.
- **Why:** owner, 26 November 2026: field workers often have no phone of their own, and the supervisor should only
  have to take photos. Keeping faces off the supervisor's phone limits what a lost phone exposes; matching against
  one site's roster is more accurate than against the whole company. InsightFace's free models are for
  non-commercial use only, so they are not used; the licences of the chosen tools are checked before adoption.
- **Where:** P95 in the P list (`docs/p-list/erp.md`).

### Standard operating procedures are written alongside the build (P96)

- **Decision:** every step that needs a person to act or check gets a written SOP in `docs/sop/` (by role, not by
  name; client specifics stay private), and every change that adds or alters a manual step updates its SOP in the
  same pull request. The first task is a study of the decisions, the P list and the runbooks for such steps.
- **Why:** owner, 26 November 2026: designs like P82 and P95 rely on people doing checks no code enforces (removing
  a family member's fingerprint, bulk onboarding a field team); without written procedures they are done
  differently by each person or forgotten. The rule also applies to all the owner's projects (working agreements).
- **Where:** P96 in the P list (`docs/p-list/general.md`); `docs/sop/` once the first SOP is written.

### Keep logs and images across releases: archive container logs, no forced image cleanup (P59)

- **Decision:** before any stack is recreated, `tools/archive_container_logs.py` saves every container's logs on the
  host (root-only, compressed, 30 days); the promotion plan lists it first. Coolify's forced nightly Docker cleanup
  is off on production (it was on; the test VM already had it off); Coolify still cleans above 80 percent disk use.
- **Why:** a recreate deletes container logs (the 20 November failed save could not be diagnosed), and the forced
  cleanup deleted the unused ERP core and prepared release images three times (each core rebuild about 20 minutes;
  a 25 November release start had to stop). Production disk use is 23 percent of 394 GB; disk space is monitored
  (P72). Switching Docker's log driver was not chosen: it restarts every container.
- **Where:** `tools/archive_container_logs.py`, `tools/promotion_plan.py`, `deployment/README.md`; Coolify server
  setting on production (live change, private record).

### Coolify's proxy runs a pinned Traefik image: 3.7.20 (P90)

- **Decision:** the proxy image is pinned by tag and digest in `deployment/coolify-proxy.json` and applied with
  `tools/coolify_proxy_image.py`, instead of Coolify's moving `traefik:v3.7` tag. First pin: 3.7.20.
- **Why:** the upstream watch (P62) found GHSA-3rh5-223h-cpwr (high: unauthenticated memory exhaustion in the
  Compress middleware's Brotli writer) and two medium advisories (GHSA-42x2-976f-ph52, GHSA-9657-c2gv-wjpj)
  affecting 3.7.19 on a public component; 3.7.20 fixes all three, is a patch release without breaking changes,
  and has no open advisory (GitHub advisories and OSV checked 26 November 2026). A moving tag made the running
  version depend on the last pull. The 3.7 line reached end of life on 23 November; moving to 3.8 (released the
  same day) is a separate step once it has a patch release.
- **Where:** `deployment/coolify-proxy.json`, `tools/coolify_proxy_image.py`, `tests/test_coolify_proxy_image.py`,
  `deployment/README.md`, `deployment/promotion-map.json`.

### Client identity stays out of the public repository, checked by fingerprints (P84)

- **Decision:** a client's name in every form, logo, domains, mail addresses and people never appear in this
  repository. `tools/check_client_identity.py` fails a push or pull request when one appears in a file, a file
  name, the pull request title or description, or a commit message. Only fingerprints (SHA-256 of each
  identifier with a fixed prefix) are stored here; the plain list stays in the private operations repository.
  Identifiers of 6 or more characters are found inside longer names too; shorter ones only as whole words, so
  hashes in lock files cannot match by chance. The two places that named the client (a front-page test and the
  test-data rehearsal's mail audit) now use the check or read the domains from the private worker profile
  (`audit_mail_domains`). Our own Unformat branding is public (P85). The history keeps the earlier lines; the
  owner chose to clean the current files only.
- **Why:** the owner's norm for all projects (26 November 2026): our brand is public, a client's identity is
  not. A plain list of client names in a public check would itself publish them, and a check that needs a
  secret would not run on pull requests from forks. Fingerprints of short names can be guessed by trying
  words; this is accepted, as the check is a guard against accidents, not a secret store.
- **Where:** `tools/check_client_identity.py`, `.client-identity-fingerprints`, `.github/workflows/check.yml`,
  `tests/test_client_identity.py`, `tools/rehearse_cripple.py`, `AGENTS.md`, `CONTRIBUTING.md`.

### No offline web app: offline work is built in the native mobile app (P23 closed, P50)

- **Decision:** the planned offline and poor-connection behaviour for the web portal (installable web app with
  caches and a send queue, P23) is not built. P23 is closed as superseded. Working without a signal is part of the
  native app ERP Mobile (P50): capture works offline and is sent later, with a visible "waiting to send" state.
- **Why:** the owner decided to develop the native mobile app, so the phone work happens there; a second offline
  layer in the browser would duplicate the queue, the cache isolation and the wipe-on-sign-out design for the same
  people. The related work stays with the app: push notifications (P14), native sign-in on production (P64), the
  photo and document store (P74) and passkeys in the app (P82).
- **Where:** `docs/p-list/mobile.md` (P50), `docs/p-closed.md` (P23).

### The mail archive reader signs in with a passkey, to mail only (P69)

- **Decision:** the archive is read through the dedicated `archive-reader` account in webmail, signing in with a
  passkey. A new group, Mail Archive Readers, passes the passkey sign-in gate and is admitted by the mail
  application only; the reader is in no staff or test group.
- **Why:** the sign-in gate admitted staff only, so the reader could not sign in at all. Adding it to the staff
  group would have given it every staff application; leaving it in the test group would have given it every test
  application. An app password in a desktop mail client would have skipped the passkey. The owner chose a
  passkey sign-in limited to mail.
- **Where:** `integrations/authentik/archive-reader/`, `configuration.json` (group, gate, mail binding),
  `configure_test_clients.py` (`also_groups`), README "Mail archive reader (P69)".

### Upgrade authentik to 2026.8.7 for its security fixes (P83)

Move the authentik pin (server and worker) from 2026.8.5 to 2026.8.7 by digest, with no configuration change.
2026.8.7 fixes three critical and seven high advisories that affect 2026.8.5. One of them: a stage whose display a
policy decides could be skipped when that policy failed, so anyone knowing a username could sign in without a
passkey while, for example, the database disk was full. The passkey sign-in gate is exactly such a stage. The
others cover the proxy-provider and forward-auth sign-in in front of the ERP and suite gateways, and request
smuggling. Both releases since 2026.8.5 are patch releases with no migration notes. After the upgrade a failing
policy is treated as its binding says (fail closed), not skipped. The image's build provenance was verified
against the upstream release tag. The security fix comes before the mail archive reader's sign-in change (P69).

Release notes: [authentik 2026.8.7](https://docs.goauthentik.io/releases/2026.8#fixed-in-202687);
[advisories](https://github.com/goauthentik/authentik/security/advisories).

## 2026-11-25

### The office editor stays registered with Drive after every Drive restart (P80)

- **Decision:** (1) every script that recreates, restarts or starts Drive (oCIS)
  runs one shared step afterwards, `host_check.py editor-restart`: wait until
  Drive is healthy, restart the editor bridge, confirm the editor is registered;
  (2) the nightly backup starts its stopped containers in order, each after the
  previous one is healthy (Drive before the bridge); (3) a signed-in check every
  five minutes reads Drive's app list with its own low-rights account, restarts
  the bridge once when the editor is missing while Drive is healthy (at most every
  30 minutes) and reports every such run as failed in the journal.
- **Why:** Drive learns which editors exist only when the bridge starts and
  registers; restarting Drive alone empties the list without any error, and
  office files then only download. On 25 November a release recreated Drive
  alone and editing was down for about 6.5 hours; the step was known but lived
  in prose, and no check could see it. The nightly backup's simultaneous start
  made the bridge's first registration fail on 24 and 25 November (only Docker's
  restart policy recovered it). The automatic repair turns a silent outage into
  at most about five minutes; the failed run keeps it visible.
- **Account:** a normal Drive user (no admin or space role), created with a
  10-minute admin app token from Drive's own CLI; its own app token is stored
  root-only and renewed by the check through the same CLI. No new software.
- **Where:** `tools/host_check.py`, `tools/render_host_checks.py`,
  `integrations/backup/backup.py`, `docs/production-moves.md`. Follow-ups:
  a Compose dependency safety net and the release rule (P81). AI-assisted by Claude.

### Invitation links allow 1 to 5 attempts (P78)

- **Decision:** the administrator chooses how many times an invitation link may
  be opened, 1 to 5, default 5, for first-time setup and for recovery. Each
  opening counts as one attempt. The link is removed after the last attempt and
  ends as soon as setup succeeds. One attempt stays a native single-use link.
- **Why:** Authentik consumes a single-use link as soon as it is opened, so one
  failed passkey prompt meant a new invitation.
- **How:** reusable invitations carry `fixed_data.attempts`. The invitation
  policies count openings in a server-side ledger (once per flow) and remove the
  invitation at the limit. A site offers the choice only when its
  `invite-mode.mjs` sets `attemptsAvailable`, after its policies are updated.
- **Where:** `integrations/authentik/invite-recovery/` (form and `native_recovery.py`).

### Approved passkey providers are one setting (P79)

- **Decision:** `integrations/authentik/passkey-providers.json` is the only list
  of approved providers: Apple Passwords, Bitwarden (also with Vaultwarden),
  Google Password Manager and Chrome on Mac. Everything else is refused,
  including providers that report no identity.
- **Why:** the list was copied in five places, and phones on Android 13 or
  older cannot use a third-party passkey app, so they need Google Password
  Manager. Chrome on Mac keeps a passkey on that Mac only, so a lost Mac needs a
  recovery invitation.
- **How:** `tools/sync_passkey_providers.py` rewrites the literal copies
  Authentik needs (policies, installer, blueprint), and
  `tests/test_passkey_providers.py` fails on any difference. Setup emails and
  the invitation form name the same providers.

### Choose the first administrator at setup; switch off `akadmin` (P77)

- **Decision:** a fresh authentik asks the person setting it up for the
  administrator's email and name. That administrator has no password and signs
  in with a passkey from an approved provider, registered through a one-time
  24-hour link; rerunning the command issues a new link. The built-in `akadmin`
  is switched off (inactive, unknown password, no groups, roles or tokens), not
  deleted.
- **Why:** nothing chose who administers a new instance, and `akadmin` kept an
  unused generated password. Deleting it would reopen upstream's first-time
  setup page, which opens whenever `akadmin` is missing or has no usable
  password; upstream's bootstrap blueprint only creates the account, so a
  switched-off `akadmin` stays off.
- **Approved passkey providers** are one list in
  `integrations/authentik/first-admin/passkey-providers.json`: Apple Passwords,
  Bitwarden (also with Vaultwarden), Google Password Manager and Chrome on Mac.
  Google Password Manager is included because phones on Android 13 or older
  cannot use a third-party passkey app. Moving every other check onto this list
  is P79.
- **Existing instances** whose administrator is managed elsewhere (for example a
  Google-linked account) use `first-admin.sh --akadmin-only`: `akadmin` is
  recreated switched off when it was deleted, so upstream's bootstrap blueprint
  cannot bring it back active. A lost administrator passkey is replaced through
  upstream's `ak create_recovery_key` from a root shell on the server, or by
  rerunning the setup for an administrator it created.
- **Where:** [`integrations/authentik/first-admin/`](../integrations/authentik/first-admin/README.md).

## 2026-11-24

### Upgrade the mail server to Stalwart 1.1.1 before mail retention (P75)

Move the Stalwart pin from 1.1.0 to 1.1.1 by digest, with no configuration
change. 1.1.1 fixes IMAP requests that could exhaust memory before login, file
downloads that could run an uploaded page's script on the mail server's origin,
and Sieve redirects that were dropped without a trace when they could not be
queued. The last one matters for the mail retention journal (P69), which is a
Sieve redirect. The image's build provenance was verified against the upstream
release tag. Version 1.2.0 is not adopted yet: it is a large feature release with
a manual role-permission step and new Exchange protocols that the retention
policy would also have to cover.

Release notes: [Stalwart 1.1.1](https://github.com/stalwartlabs/stalwart/releases/tag/v1.1.1).

### Work photos in each project's Drive space, reached only through ERPNext (P74)
- **Decision:** the mobile app's site photos (progress, hindrance, incident) go straight to the project's
  Drive (oCIS) space, one folder per site and date, tagged with project, site, type, time, GPS, who took
  them, "From gallery" and "Captured offline". The phone talks only to ERPNext: ERPNext checks the person's
  site membership (the attendance rule) and a dedicated Drive account writes and reads the space with an
  oCIS app token renewed every 30 days, the document worker's pattern. Nobody deletes a work photo: the
  records cannot be deleted and the store never deletes in Drive. Receipts, bills and scans keep going to the
  DMS first; project photo spaces stay outside the document worker. Immich and PhotoPrism were compared and
  not adopted for now (no user groups / single sign-on only in a paid edition).
  Drive's thumbnail sizes gain `256x256` (upstream defaults kept): oCIS serves only listed sizes and returned
  1080 px for the 256 px preview on test.
- **Why:** one sign-in for staff (no Drive key on the phone, no Drive account needed to see project photos),
  permissions from ERPNext only, no new service to run or back up, and photos next to the project's other
  files in Drive.
- **Where:** `erpnext_drive_integrations/drive_store/`, `tests/test_drive_store.py`, issue #53.

### Patch the production identity images before the P49 cutover

Keep PostgreSQL on major version 16 and move its identity pin to 16.16.
The November PostgreSQL release addresses high-severity advisories affecting
16.15. Use NGINX 1.30.8 for both identity support services so the gateway's
upstream DNS resolver also receives the November fixes. Retain the existing
Authentik version and test the database upgrade and gateway routes in isolation.
Render both identity proxy configurations from their repository templates.
TLS certificate material stays in its existing private mount.

Official notes are in the [PostgreSQL 16.16 release](https://www.postgresql.org/docs/release/16.16/)
and [NGINX advisories](https://nginx.org/en/security_advisories.html).

### Invitation controls are part of the Authentik build (P49)

Both **Invite users** and **Invitations** are required in the Authentik admin
console. The deployment stages the companion, CSS and native menu override
from this module at a recorded Git revision. Check both controls after a
rebuild or Authentik upgrade. Their roles are user selection and email
submission in the companion, and status and cancellation in the native console.

The isolated test issuer reuses the companion with its own enrollment flow.
Only active synthetic accounts waiting for their first passkey are listed.
Synthetic addresses do not receive mail, so the test form addresses the
administrator's mailbox. Production enrollment and recovery retain their
own policies, hosts and mail transport.

## 2026-11-20

### A reboot must bring everything back by itself (P57)
- **Decision:** the Drive editor bridge is placed on every network Drive's
  oCIS is on and starts after oCIS is healthy; databases get 60 s (Redis 30 s)
  to shut down; Docker starts after Tailscale and waits briefly for the tailnet
  address; a boot check verifies containers, hosts, tailnet ports and the
  editor bridge after every start and restarts the bridge once if it cannot
  register; a five-minute watch flags crash-looping containers; a checklist
  and a planned-reboot procedure are documented, and the test host is
  rebooted as a drill after changes.
- **Why:** an unplanned reboot (20 November 2026, kernel update after six days)
  left Drive offering downloads instead of the editor: oCIS had advertised its
  proxy-network address at random and the bridge was not on that network, so it
  crash-looped 181 times. A single manual network attach fixed it, which is
  exactly the repair a rule and a test should make unnecessary. Everything
  else came back by itself, which this keeps provable.
- **Where:** `tools/prepare_runtime.py` (`NETWORK_PEERS`), the stack files,
  `tools/host_check.py`, `tools/render_host_checks.py`,
  [procedures](production-moves.md), `tests/test_reboot_resilience.py`,
  `tests/test_host_checks.py`.

### Logout ends on the website; one passkey prompt per sign-in (P56)
- **Decision:** every logout (ERP, Drive, Mail, DMS, the portal, idle logout)
  ends on the company website. The address is named once, `sso.LANDING`,
  rendered from the private profile (`landing_url`, default
  `https://www.<domain>/`; the test site uses its own front page). Apps keep
  handing over to the ERP's `/login?logged_out=1` (or `/signed-out`, which
  first finishes a still-valid session); the ERP forwards to the landing
  address, and authentik's logout flow redirects there after it ends the
  gateway session. The ERP's sign-in no longer sends `prompt=login` with
  `max_age=0`: it sends `max_age=600` and the callback accepts an
  authentication from the last ten minutes.
- **Why:** with `max_age=0` a passkey login that took a second already counted
  as too old, so authentik asked twice; ten minutes keeps the intent (a recent
  passkey login) without the second prompt. One named landing address avoids
  five copies drifting apart, and changing only the ERP avoids rebuilding Mail
  or restarting Drive and DMS.
- **Where:** `erpnext_drive_integrations/portal/sso.py`, `tools/render_runtime.py`,
  `tests/test_logout_and_signin.py`.

### The portal page keeps its name; only the logo changed
- **Decision (owner):** the portal page stays exactly as before (title, and the
  company name beside the logo); only the logo is new, in the top-left brand
  and in the auto-hiding menu's home button. This reverts the "Desk" label of
  the previous release.
- **Where:** `erpnext_drive_integrations/www/place_holder.*`, `tests/test_brand_assets.py`.

### Company front page on www; the bare domain redirects to it
- **Decision:** the company address (`www`) serves a small static front page
  that is always reachable, signed in or not: an original pencil drawing of a
  tunnel construction site drawn stroke by stroke in four batches, the logo,
  "Launching soon..." typed letter by letter, and a plain "Employee Zone" link
  to the staff sign-in. The bare domain redirects permanently to `www`. The
  page is a module (`integrations/website`) with its own pinned, read-only
  nginx container; it is tenant-neutral and gets its names, logo, favicons and
  link from the private profile. On the test site the same page is served by the
  test host itself at the exact front path `/` (no extra test host name); every
  other path still reaches the portal. The portal shell moving onto `www` is a
  later step.
- **Why:** a public address that is always open while apps stay behind sign-in;
  one host name fewer on test; our own drawing instead of a photo avoids a
  licence and credit question and loads in a few kilobytes.
- **Where:** `integrations/website/`, `deployment/stacks/website.compose.json`,
  `deployment/production/website.traefik.yaml`, `tools/prepare_ingress.py`.
### No "All apps" item in the app sidebars
- **Decision:** the sidebar of ERPNext, HRMS, Onboarding, India Compliance and
  every other module-sidebar app has no "All apps" item. The app's logo at the
  top still leads back to the portal page (`/place_holder`, whole tab), and the
  Edit Sidebar and Help actions and the hidden native Home item stay.
- **Why:** the owner removed the item earlier by patching files on the server;
  the repository build replaced those files and brought it back. A removal that
  lives outside the repository is lost at the next build, so it is now in the
  source (`module-header-20261115.js`), a stale copy in an already open tab is
  removed by the script, the script version is bumped so browsers refresh, and
  `tests/test_app_menu_link.py` fails if the item returns.
- **Where:** `erpnext_drive_integrations/public/module-header-20261115.js`,
  `tests/test_app_menu_link.py`.

### Tenant branding is private
- **Decision:** the company logo and a favicon set (SVG plus PNG 16 to 512) are
  supplied through the private runtime profile (`company_logo`,
  `company_favicon_dir`), never stored in this repository, which ships only
  neutral placeholders. Rendered files keep their names and every reference
  carries `?v=<release commit>` so browsers refresh them. The portal page
  (route `place_holder`) is named **Desk** (browser title and the text beside
  the logo) because dashboards and widgets will live there; its menu's home
  button uses the compact favicon, the top-left brand the full logo. Frappe's
  own desk and website favicon and logo, authentik's branding, the webmail
  favicon and the push-notification icon use the same files.
- **Why:** one repository serves several tenants (the product is the
  repository, the company is the tenant); a 500 KB detailed logo is unreadable
  and wasteful as a 16 to 44 px icon; a fixed file name needs a version
  parameter or browsers keep the old picture.
- **Where:** `tools/render_runtime.py`, `tools/prepare_runtime.py`,
  `erpnext_drive_integrations/www/place_holder.*`, `tests/test_brand_assets.py`.

### The order of work: branch, test, merge, main, production
- **Decision:** every change follows branch → test → merge → `main` →
  production. The branch itself is deployed to the test site and validated
  before the owner merges it; production receives that same content from
  `main`. Unit tests are a gate before the test deployment, not a replacement.
  Production-only files (route files, port bindings) cannot be tried on test, so
  they get a recorded browser and protocol check right after promotion and are
  named in the release record as not covered by test. The pull request carries
  a required "tested commit and result" line.
- **Why:** merging first and testing afterwards puts untested code on the
  branch that production is built from; and a gap of exactly that kind
  (production-only settings that the tests could not see) broke Mail inside the
  portal once. GitHub cannot verify a test happened, so a written record is the
  control.
- **Where:** `AGENTS.md`, `CONTRIBUTING.md`, the pull request template.

## 2026-11-19

### Test refresh: separate code and data buttons; crippled 60-day data
- **Decision:** the test site gets two buttons. "Refresh code" resets test to
  the tested release (`main`); "Refresh data" brings a crippled production
  copy and is used rarely. Crippled means: strictly the last 60 days (ERP
  included; balances need not add up), every piece of personal information
  replaced with irreversible fakes, document contents replaced by placeholder
  files, mail not copied (test mailboxes start empty), and outbound e-mail,
  WhatsApp and payments off. Scrambling runs on production, on copies in
  throwaway database containers, before anything leaves the server. Members
  of the authentik group "Testers" keep their login identity (e-mail,
  username, name) and nothing else: their other profile data is scrambled too.
  Full names of accounts that are not kept are swept from free text as well.
- **Why:** a developer may now deploy to test freely, and code they deploy can
  read everything on test; the test copy must therefore hold no real personal
  data (minimisation, as India's DPDP Act also expects). Test data is for
  trying things, not for accuracy, and a smaller copy keeps refreshes
  manageable as production grows. Mail is left out because its store cannot be
  scrambled safely offline.
- **Where:** `tools/cripple_snapshot.py`, `tools/export_snapshot.py`,
  `tools/test_refresh_worker.py`, `tools/rehearse_cripple.py`,
  [test-refresh module](modules/test-refresh.md).

### Test access through one flat "Testers" group
- **Decision:** the test site's applications admit only members of one flat
  authentik group, "Testers", bound directly to each test application. No
  parent/child groups. The owner adds the people who help test new changes;
  production access (the staff group and each person's ERP rights) is
  separate and unaffected.
- **Why:** inherited groups made everyone a tester by default and were hard
  to read. A flat group makes "who can open test" a single visible list, and
  pairs with the scrambled test data (only testers keep real login accounts
  on test).
- **Where:** authentik application bindings (production sign-in serves both
  sites); operations record in the private repository.

### Public repository under AGPL-3.0, operations records private (P35)
- **Decision:** publish the code as a new public repository,
  `ERPNext_Owncloud_Stalwart_Integrations`, under AGPL-3.0-or-later, starting
  from a clean snapshot with fresh history. Dated operations records (release
  log, task list, migration runbooks with real addresses and service IDs) stay
  private: the earlier private repository, keeping its full history, becomes
  the internal operations repository and no longer holds code. The company is credited by name; the
  company logo is not published (a neutral placeholder ships, each deployment
  supplies its own). Test and production fetch the public repository.
- **Why:** sharing what we build (owner principle 3) and letting
  contributors work by fork and pull request with branch protection, which a
  free private repository lacks. AGPL keeps changes to network-served
  versions shared, matching the AGPL parts we modify (ONLYOFFICE, Bulwark,
  frappe/suite icons). Fresh history, because the old history contains
  personal e-mail addresses, host names and infrastructure details that a
  scrub of the current files would not remove.
- **Where:** `LICENSE`, `LICENSES.md`, `README.md`, `CONTRIBUTING.md`,
  [method for moving services](production-moves.md).

## 2026-11-18

### Office editor: ONLYOFFICE replaces Collabora (P42)
- **Decision:** replace Collabora Online with ONLYOFFICE Docs (Community
  Edition) as the Drive editor, completely. Order: switch the test site, back
  up, restore production data onto a stack built with ONLYOFFICE on a spare
  machine (P39), then switch production.
- **Why:** Collabora (LibreOffice) converts Excel workbooks to its own model
  and renders on the server: a real 1 MB register took 20 to 40 seconds to
  open, filled sheets slowly and misbehaved with rows; heavy files hit its
  100-second load limit. ONLYOFFICE edits OOXML natively and renders in the
  browser: the same original register opened in 3 to 5 seconds (Collabora 42).
  Its default saving behaviour (changes written to Drive only after everyone
  closes) is handled by its built-in auto-assembly (interval 2 minutes): on the
  test site Drive received an edit about 3 minutes later while the editor
  stayed open, and the final save 7 seconds after closing. No extra watcher is
  needed. ONLYOFFICE 10 calls only WOPI hosts named in its `ipfilter` rules,
  so Drive's WOPI bridge is named explicitly.
- **Layout (owner, final 18 November 2026, for working space):** one header
  row (logo, tabs, file name) with Drive's ⋮ and ✕ placed in it; avatar,
  header search, Share and open-location removed; one always-visible side
  strip on the right in header grey holding both former strips (the pivot
  field list and object settings exist only there; auto-hide was tried and
  rejected); darker row/column headers (#D9D9D9, selected #A6A6A6) because the
  row-number width cannot be changed; Drive's file menu styled like
  ONLYOFFICE's and closed by a click in the editor; square edges. After the
  phone check: ✕ and ⋮ moved to the top left (reachable with a thumb) and
  ONLYOFFICE's logo to the far right in exchange; always
  the light theme (dark mode hid the strip's icons and clashed with the grey
  headers). Final strip: a status-bar button (bottom right, like the sheet
  list) opens it over the sheet on desktop and phones, replacing the
  always-visible strip and a phone edge handle; phones use the desktop editor
  because the free edition's touch editor is view-only. Tabs take priority
  over file name and logo (both shrink); filtered row numbers blue. The strip
  button is a hamburger at the far right of the status bar; on phones sheet
  tabs and zoom are removed (sheets via ONLYOFFICE's sheet list); the editor
  frame fills the window edge to edge for a native-app look. The owner asked
  to remove About; it stays because it is the only place the licence notices
  appear (additional term 3), but it now always closes (✕, Esc, hamburger). Details and
  exact values: `integrations/onlyoffice/README.md`.
- **Private sheet views by default:** every person works in their own view
  per sheet ("Private - <name>", reused), shown without the green sheet-view
  headers, so filters and sorting do not change what others see.
- **How:** ONLYOFFICE Community ignores layout options, so a patched copy of
  its WOPI start page (Apache-2.0) applies the layout in the editor frame,
  using only official API calls and theme tokens, pinned to the image by
  fingerprint.
- **Licence:** the logo stays (not linked); About keeps ONLYOFFICE's notices
  and states that this is a modified version based on ONLYOFFICE by Ascensio
  System SIA (additional terms 1 to 3).
- **Reliability:** the container removes a stale supervisord PID file before
  starting; otherwise a restart could leave ONLYOFFICE down (502).
- **Trade-offs:** Collabora-specific additions (P27 filter search fix, P34
  private sheet views, header theming) are retired; ONLYOFFICE's native sheet
  views and filter search replace them. Community
  Edition is AGPL v3; connection and mobile-editing limits are verified
  against the pinned version.
- **Production:** switched 18 November 2026 after the owner set the tablet
  check (P43) aside; mapped onto production's pre-repository Drive stack
  ([method](production-moves.md)).
- **Collabora retired (19 November 2026):** removed from production through
  Coolify's own delete (configuration archived in the P42 rollback folder) and
  from the repository (module, stack, tests, build tool, renderer branches);
  ONLYOFFICE is the renderer's only editor and its default.
- **Where:** P42, `integrations/onlyoffice/`, `integrations/drive/workspace.js`.


### TEST SITE marker in every app
- **Decision:** every app on the test site shows the same marker (orange
  striped 3px top line with a small TEST SITE tab, overlaying, top window
  only). Apps decide by hostname; the renderer enforces that test hostnames
  start with `test.` or `test-` and production ones never do.
- **Why:** the owner entered real rows on the test site by mistake (19
  November 2026); test data is overwritten at every refresh and never flows
  back to production, so the two sites must be told apart at a glance.
- **Where:** `session.js`, `place_holder.html`, Drive `workspace.js`, the
  ONLYOFFICE start page, the DMS adapter, the Mail overlay; `prepare_runtime.py`.

### Sign-in rebuilt from the repository with production's secret key (P44)
- **Decision:** after a loss, rebuild authentik from the repository
  `identity` stack and reuse production's `AUTHENTIK_SECRET_KEY` and database
  password, read from the backed-up Coolify compose; back up authentik's media
  volume and invitation templates too.
- **Why:** authentik derives users' sign-in identifiers from the secret key;
  a new key would make every app treat each user as new. Proven on the old
  VPS: same users, applications, providers and identifiers as production.
- **Where:** `tools/restore_identity.py`, `deployment/stacks/identity.compose.json`,
  [disaster recovery](disaster-recovery.md), P44.

### Backups: Restic to S3 storage on a home NAS, protected by ZFS snapshots
- **Decision:** nightly Restic backups of production (databases dumped
  online; Drive and Mail stopped for seconds and copied) to RustFS (S3) on the
  owner's TrueNAS, RAID10 pool, over the tailnet. Retention 7 daily, 4 weekly,
  6 monthly. Weekly restore drill on the test VM with a read-only key. Daily
  ZFS snapshots of the backup storage, kept 60 days.
- **Why:** off-server, encrypted and deduplicated, no cloud storage cost;
  Restic runs from a digest-pinned container so nothing is installed on the
  host; a drill that imports every dump proves restorability. ZFS snapshots
  protect the backups from a compromised production server, which has no
  TrueNAS login. TrueNAS's snapshot tasks refuse its internal app storage, so
  a TrueNAS cron job running as root (`integrations/backup/zfs-snapshot-guard.sh`)
  snapshots the RustFS dataset in place daily and removes only its own
  snapshots beyond 60; no data move or RustFS downtime needed.
- **Where:** `integrations/backup/`, [disaster recovery](disaster-recovery.md), P02, P40.

### Recovery essentials kept by the owner
- **Decision:** encryption password, TrueNAS admin, SSH keys and the
  provider/registrar/GitHub/Tailscale/Meta/authentik logins with recovery
  codes are kept outside the servers and reviewed quarterly.
- **Why:** everything else is reproducible from Git and the backups; these
  are the only things that are not. **Where:** [disaster recovery](disaster-recovery.md), `AGENTS.md`, P41.

### Full restore rehearsal on a spare machine
- **Decision:** restore production from backup onto the idle old VPS on
  private names, quarantined, and time it.
- **Why:** a database drill proves dumps import; only a full restore proves
  the business can be recovered and how long it takes. **Where:** P39.

### Portal deep links: app pages always open inside the portal
- **Decision:** Desk, Raven and Insights pages opened on their own (new tab,
  pasted link) reopen inside the portal at the same page: a server redirect
  for whole-tab requests (`Sec-Fetch-Dest: document`) plus a client-side
  check in `session.js`.
- **Why:** the left-edge app menu belongs to the portal frame. Raven's service
  worker fetches navigations itself without that header, so the server alone
  cannot tell; the page checks `window.top` instead. Frames and installed app
  windows are never redirected. **Where:** `portal/sso.py`, `public/session.js`, `www/place_holder.html`.

### Test site on a home server behind the production proxy
- **Decision:** the permanent test site runs in a VM on the owner's TrueNAS.
  Public test hostnames resolve to production, whose proxy terminates TLS for
  them (its wildcard certificate covers them) and forwards each request over
  HTTPS to the test VM through the tailnet, verifying the VM's certificate per
  hostname; the VM trusts the relay's X-Forwarded-For. HTTP/3 is off on both
  proxies. SSO for test is reached over the tailnet through a private entry
  point.
- **Why:** no extra hosting cost and no fixed public address needed at home.
  A plain TCP pass-through by SNI was tried first and failed in browsers:
  with a wildcard certificate on production, browsers reuse ("coalesce") an
  open production connection for any covered hostname, so test requests
  arrived inside connections opened for other names and production answered
  them itself (503). HTTP/3 (UDP) likewise reached production's own 503 page.
- **Where:** `tools/prepare_test_relay.py`, `tools/coolify_proxy_hosts.py`,
  `tools/coolify_proxy_http3.py`, `tools/prepare_auth_bridge.py`.

### Production ERP built from the repository (P37)
- **Decision:** production ERP runs the image built from a tested release on
  production itself, reusing the existing data volumes and keeping legacy
  network names as aliases; later updates recreate only app containers.
- **Why:** reproducible from Git, same code as validated on test, about two
  minutes of downtime, data untouched. **Where:** [method](production-moves.md).

### Short production pause for test refreshes
- **Decision:** the export copies files while production runs, then only the
  changes during a bounded pause; dumps are compressed after resuming.
- **Why:** the store grew and the old exporter exceeded its 100-second
  consistency limit; the pause is now about 45 seconds. **Where:** `tools/export_snapshot.py`.

### Test-only app access and safe contributions (P38)
- **Decision:** an app under test is blocked on production (unusable OAuth
  redirect URIs) and re-enabled on test after every refresh; the developer
  contributes by fork and pull request, only the owner merges, production
  changes only after test validation and owner confirmation.
- **Why:** forks keep write access with the owner; since the public release
  (P35) the main branch is also protected on GitHub. **Where:** `CONTRIBUTING.md`, P38.

### WhatsApp through frappe_whatsapp with signature checks
- **Decision:** use frappe_whatsapp (MIT) with Meta's Cloud API, wrapped to
  verify Meta's webhook signature (fail closed), with test copies limited to
  allowed recipient numbers.
- **Why:** the upstream webhook accepts unsigned posts; refreshed test data
  holds real contacts. **Where:** `erpnext_drive_integrations/whatsapp/`, P04.
- **Correction (26 November 2026, P92):** this is a plan, not built yet. The
  folder does not exist and frappe_whatsapp is not installed; the wrapper will
  be built with P04, and the decision above still applies when it is.

### App menu in two columns above five apps
- **Decision:** the portal's auto-hiding app menu switches from one to two
  balanced vertical columns when it lists more than five apps; the home button is
  not counted so the layout does not change when it appears.
- **Why:** with seven or more apps a single column no longer fits short
  windows and needs scrolling. **Where:** `erpnext_drive_integrations/www/place_holder.html`,
  `tests/test_portal_menu_columns.py`, P58.

### Forwarded headers are trusted on the SSO host's private entry point from the test VM only
- **Decision:** the SSO host's proxy trusts forwarded headers (`X-Forwarded-Uri` and the others) on the private
  tailnet entry point used by the test sign-in bridge, and only from the test VM's exact address. The public entry
  points never trust them. The Docker gateway address that was also on the bridge allow list is not trusted (it carries
  other host and container traffic), and is to be dropped from the allow list.
- **Why:** without it the proxy dropped the requested page, so the first sign-in on the test site (and the mobile app's
  sign-in) landed on the landing page. Trusting only the bridge's real source keeps others from setting those headers.
  Production-only setting: it cannot be exercised on the test site; it is checked in a browser right after it is
  applied. **Where:** `tools/sso_proxy_trust.py`, `tools/prepare_auth_bridge.py`, the test rebuild runbook, P65.

### A standing session routine, written into CLAUDE.md
- **Decision:** `CLAUDE.md` tells every session (and every contributor's AI agent) to
  read the latest handover and the priority list in the private operations
  repository at the start, to update that repository after every production change,
  and to write a handover when the owner closes the session. The private repository
  holds records and private assets only, never secrets.
- **Why:** continuity between sessions, machines and contributors without the owner
  re-asking, and records that never lag behind production (a stack was missed in one
  promotion and an incident went unrecorded until asked on 21 November 2026).
  **Where:** `CLAUDE.md`, P59.

### Work is organised in numbered P items, related ones taken up together
- **Decision:** every piece of planned work is a **P item**: a numbered, self-contained
  unit with a scope, a status and its dependencies, kept in the operations repository's
  pending list. Numbers are never changed or reused, and commits, pull requests, release
  records and handovers refer to them (for example P58). Related items (same module,
  same stack, same decision, or one depends on the other) are built on one branch,
  tested together and merged as one release, while each keeps its own status. The owner
  decides what starts and when; every group still follows branch, test, merge, `main`,
  production.
- **Why:** development stays modular, with each module reusable on its own, and
  continuity between working sessions, contributors and AI agents is simple: reading
  the item and its status is enough, with no need to replay earlier conversations.
  Grouping related items means a stack is changed and promoted once instead of several
  times. **Where:** `docs/pending.md` in the operations repository (priority order and
  usage at its top), `AGENTS.md` for the release order.

### The P list is published in full, with identifiers replaced
- **Decision:** the work list is kept in two forms: the private `docs/pending.md` in the
  operations repository (source of truth) and the public `docs/p-list.md`, generated from
  it. The public copy keeps every line, every reason and every priority; only the categories
  that identify the deploying organisation or its servers are replaced by placeholders (organisation
  name, host names, IP addresses, server paths and rollback folders, mail addresses, names of
  people and of third parties' internal products, business file names, links to private
  records). The generator never deletes or summarises a line, lists every substitution in a report
  and refuses to publish while any sensitive token survives.
- **Why:** the team and outside contributors need the roadmap and the reasons behind it to
  work in modules and take up related items together; detail must not be lost in the
  translation, and nothing identifying may leave the private repository. **Where:**
  `docs/p-list.md`, `CLAUDE.md` (session routine, step 5), the private `tools/publish_p_list.py`.

### The P list is organised by app
- **Decision:** the work list is split into one list per app (ERP, portal, sign-in, Drive, editor, mail,
  DMS, Raven and Insights, mobile, test site) plus `general` for platform and security items that belong to
  no app; an index holds the usage rules, the priority order across all apps and by-app tables. An item has one
  home and names the other apps it touches, with a state (open, in progress, blocked, parked, recurring,
  done, closed). Numbers stay global. The split kept every line of every item.
- **Why:** changes now land in every app, and one long list made it hard to see what is open for the app
  being worked on; related items are taken up together per app, and the roadmap is easier to read for people
  who work on one app. **Where:** `docs/p-list.md` (index) and `docs/p-list/<app>.md`; the private source is
  `docs/pending.md` and `docs/pending/` in the operations repository.

### HR additions live in the one app as `custom_hr` (formerly the field-attendance part)
- **Decision:** our customisations stay in the single app `erpnext_drive_integrations`. Everything Frappe HR lacks
  for our HR work, and every HR function the mobile app needs, is built in its `custom_hr` part (the former `field`
  part, module "Cloud Field", renamed "Custom HR"). Frappe HR's own features are used as they are. The part adds no
  desk app icon (no `add_to_apps_screen`, no workspace; tested). DocType, role and page names stay unchanged; a
  migration patch renames the Module Def with Frappe's own rename before the DocTypes are synced, without touching
  records; the former `cloud_features` key `field` is still honoured.
- **Why:** owner, 22 November 2026: more HR functions will be built into this part than field attendance, and one
  app is easier to manage, review and upgrade than several. **Where:** `erpnext_drive_integrations/custom_hr/`,
  `erpnext_drive_integrations/patches.txt`, `tests/test_custom_hr.py`, `modules.json`.

### Self check-in with a selfie, approved by the project manager like team attendance; one attendance path

**Amended 26 November 2026:** the selfie is replaced by the biometric at each check-in (see "Self check-in uses
the biometric and the location fence, no selfie" above).

- **Decision:** employees with a login check in themselves through `custom_hr` (selfie, location inside the site's
  fence, the server's time), and every attendance, team or self, is approved by the site's approvers, singly or in
  bulk; HR attendance is created only on approval. Offline captures (self and team) carry the phone's clock and its
  measured difference to the server, are accepted for at most one day and are marked for the approver; an exact
  native clock follows with a development build. Sites can be set to need no approval (for example head office):
  there an online entry becomes HR attendance at once, while offline entries still go to the approvers. One
  attendance path, left to the administrator: a box in HR Settings (ticked on first install) blocks Frappe HR's own
  check-in on the server for everyone except the roles listed there, and keeps its button and automatic attendance
  on our sites' shifts off; unticked, our app leaves those settings alone.
- **Why:** owner, 22 November 2026: the project manager's approval is required for all attendance; Frappe HR has no
  selfie, no approval step for check-ins, takes the phone's clock and has no offline capture. Head-office staff
  need no approval, and the admin, not the code, decides who may still use Frappe HR's check-in (owner, same
  day). **Where:**
  `erpnext_drive_integrations/custom_hr/` (service, api, domain, setup, the Field Attendance Entry and Field Site
  Member DocTypes), `tests/test_custom_hr.py`, `custom_hr/integration_tests.py`.

### Contributor access to the test site: own key, deploy-only, never the owner's key
- **Decision:** a contributor who needs to install a branch on the test site gets their own SSH key (they send only
  the public half), bound to a dedicated account whose forced command can only deploy a branch of the public
  repository, with every deploy logged, plus access to the test host over the private network for that one port.
  The owner's personal keys are never shared. Until that exists, a maintainer reviews the branch and installs it.
- **Why:** a shared personal key cannot be revoked for one person, leaves no separate audit trail, and the test host
  holds test secrets and a restricted route to the production export. **Where:** P54, P67; asked for on
  21 November 2026 when the mobile app branch could not reach the test site.

### Tests import the real module under test
- **Decision:** unit tests may fake Frappe and external services, but not the project's own modules that the code
  under test imports; and the repository checks resolve imports of the project's own names.
- **Why:** a test that replaced `portal/combined.py` with a fake copy hid a leftover import of a function that does
  not exist, so every native app request failed with HTTP 500 on the test site (21 November 2026). **Where:**
  `tests/portal/test_mobile.py` (PR #15), P64, P68; the import check is `check_imports` in
  `tools/check_repository.py` (every import of the project's own modules, also inside functions, must name an
  existing module and name; it finds the P64 import when run on the code before its fix), rule in `AGENTS.md`.

### The native app: owner decisions, one build guide, and a review workflow for agents (P50)
- **Decision:** the app's tabs are Today, Inbox, My HR and Menu; Chat, Mail and Drive stay separate apps and are
  not linked; every person can do in the app what their roles allow on the web. Incidents go to Raven threads the
  person chooses; approvals and their limits come from ERPNext workflows; English only for now; self check-in
  outside a site fence is refused by the server; remote wipe and at most one day of offline data; TestFlight for
  iPhones. Agents build from `mobile/BUILD-GUIDE.md` with a fixed workflow: explore, design with the data path of
  every feature, owner go, build, review agents and security review, tests, pull request, test site. Only
  vetted official plugins and skills are used (Anthropic, Expo, Callstack), read before installing.
- **Why:** owner, 22 November 2026: the app must be built like a production app, not "vibe-coded", and an
  externally written build guide contradicted the working sign-in, the one-app rule and existing modules.
  **Where:** `mobile/BUILD-GUIDE.md`, `mobile/AGENTS.md`, `mobile/README.md`, `tests/test_mobile_app.py`.

### Only open work stays in the P list
- **Decision:** a P item is removed from its app list as soon as the task is completed, or becomes redundant or
  irrelevant. It leaves one line in the closed log (number, title, app, outcome, date, reason), so numbers are never
  reused; its full text stays in the git history and the work itself in the release log and this file.
- **Why:** the lists are what people work from; finished items made them long and hid what is still open. **Where:**
  `docs/p-closed.md`, `docs/p-list/`, `CLAUDE.md` (session routine, step 6); the private `tools/p_close.py`.

### Sign-in settings the ERP depends on are one setting each, and tested against authentik (P49)
- **Decision:** the approval claim's name is one setting (`APPROVED_CLAIM` in the ERP, overridable per site), and a
  test fails when the ERP provider's scope mapping, the example mappings or the test clients send another name;
  after every ERP or sign-in deployment someone signs in once in a browser with a passkey. The invitation pages' and
  e-mails' brand name and template file names are profile settings, so an installation keeps the names authentik's
  database refers to. The webmail product name comes from its existing setting. The identity stack carries
  production's tuning: PostgreSQL `jit = off`, 3 GB for the authentik server, an explicit web worker lifetime (the
  pinned default of 1000 requests), and policy caching kept off as production runs it (origin unknown; a change is a
  separate, measured decision).
- **Why:** on 20 November 2026 production's ERP provider sent a legacy claim name while the ERP required
  `cloud_approved`, and new ERP sign-ins failed for days; production's pages, templates and tuning had drifted from
  the repository. Importing production's newer pages and templates follows separately. **Where:**
  `erpnext_drive_integrations/portal/sso.py`, `integrations/authentik/`, `tools/prepare_runtime.py`,
  `deployment/stacks/identity.compose.json`, `deployment/stacks/inputs.json`, `tests/test_signin_settings.py`.

### Demo test site: the portal at `/` once signed in, and the landing page options (P63, P60 closed)
- **Decision:** on a host that is both landing page and portal (the test site), `/` shows the landing page only to
  visitors without an ERP session; signed-in people get the portal at `/`, so the address bar is as clean as on a
  production ERP host. The rename of `/place_holder` to `/ezone` (P60) is dropped as redundant. The landing page gets
  profile options for a demo (tagline, entry label, a corner badge and its colour, a flower-and-bee drawing). On the
  test site the portal shows the logo alone (larger, no company name) and the clean address `/`, through that site's
  own settings (see the next entry). The test refresh buttons sit in one row beside the logo with their dates under
  them.
- **Why:** owner, 21 November 2026: the demo site should look like a neutral product, the entry should take one
  click and read "Apps", and the address should not show an internal page name. The landing page options default to
  the production look. **Where:** `tools/prepare_ingress.py`, `tools/prepare_runtime.py`,
  `integrations/website/`, `erpnext_drive_integrations/www/place_holder.*`, `public/test-refresh.*`.

### A daily upstream watch reports releases and flaws; it never upgrades (P62)
- **Decision:** once a day a watch compares every pinned component (locks, image digests, host components from a
  private profile) with public sources only (GitHub releases and advisories, OSV.dev, NVD, endoflife.date, the CISA
  list of actively exploited flaws) and writes a digest into a folder on the server: a baseline, a daily digest only
  when something is new, a weekly roll-up. Each finding carries severity, whether our version is affected, exposure,
  the fixed version and a rule-based recommendation (upgrade now, schedule, ignore); the owner decides. It runs on a
  host without production credentials, as an unprivileged user, with an optional read-only GitHub token; it never
  upgrades, commits, pushes or sends messages (alerts come with P72). The version behind each pinned image digest is
  recorded in the repository, because the images carry no reliable version.
- **Why:** owner, 21 November 2026: new releases and advisories reached us only by chance (the ONLYOFFICE sheet-view
  crash of 20 to 21 November had an upstream side). An upgrade stays a normal branch, test, merge and production
  change. **Where:** `tools/upstream_watch.py`, `deployment/upstream-watch.json`, `deployment/upstream-watch.*.example`,
  `deployment/upstream-watch.example.json`, `tests/test_upstream_watch.py`, `deployment/README.md`.

### Production and test have separate asset sets
- **Decision:** each site's look (logo, favicons, names, landing page options and the portal page's look) comes from
  that site's own private settings and assets; shared code carries no site-specific look. The portal page reads its
  site-specific look from site settings (`cloud_portal_hide_entity_name`, `cloud_portal_logo_height`,
  `cloud_portal_logo_position`, `cloud_portal_clean_root_address`); with none set it is exactly production's page. The test site sets them through an
  allow list (`erp_site_settings` in its private profile); the test-only stylesheet styles only the test refresh row.
- **Why:** owner, 21 November 2026: a change to the test site's look must never change production. A guard test
  renders the page as production sees it and checks that every site-specific part sits inside its setting.
  **Where:** `erpnext_drive_integrations/www/place_holder.*`, `public/test-refresh.css`, `tools/prepare_test_profiles.py`,
  `tests/test_portal_site_look.py`.

### Every release lists the stacks it reaches and ends with a clean drift check (P59)
- **Decision:** a map in the repository says which stacks, setup steps, live settings and restarts each file
  reaches; every pull request carries the resulting promotion plan, and a promotion is finished only when the drift
  check on production reports every stack clean for the promoted commit (also run nightly). The drift check only
  reads: each stack's recorded commit against `main`, and served pages against local files. The ERP core image's loss
  to the nightly cleanup is documented; the fix comes with P71 (build once, registry).
- **Why:** owner, 21 November 2026: a production ERP release missed the website stack, and an earlier statement that
  one ERP swap carried the fix was wrong; production stacks are promoted one by one and nothing listed what a merge
  reached. **Where:** `deployment/promotion-map.json`, `tools/promotion_plan.py`, `tools/drift_check.py`,
  `deployment/drift-check.*`, `AGENTS.md`, `.github/pull_request_template.md`, `docs/production-moves.md`,
  `tests/test_promotion_plan.py`.

  **Follow-up:** read promotion rules from the target commit so a long-lived
  checker uses the current ownership map. Treat unmapped changed files as
  unknown. Compare public bytes against the live container asset where the
  deployed stack serves the file from its image.

### Private sheet views isolate filters; every person is kept in their own view (P61)
- **Decision:** a private sheet view exists only to keep each person's filters and sorting out of everyone
  else's work. Others may see the views, and other people's cursors stay visible (they only show where someone
  is working; data is shared, the last value entered in a cell wins). The editor keeps every person in their own
  view: a create or rename that ONLYOFFICE refuses (another person in View manager) is tried again, and a notice
  with "Back to my view" shows when someone stays in the Default view or another person's view.
- **Why:** owner, 23 November 2026, after filters reached other people. The first keeper (PR #12) tried once and
  gave up, so a refused attempt left the person in the shared Default view. The crash guard of PR #12 was checked
  against the pinned build (its method names are right) and now cleans the list in place. **Where:**
  `integrations/onlyoffice/editor-wopi.ejs`, `tests/test_onlyoffice_private_views.py`,
  `tests/test_onlyoffice_sheetview_filter.py`.

### Security before features and deployments
- **Decision:** every production promotion, upgrade or new dependency starts with a check of the official security
  advisories and release notes of what it ships, against the pinned versions; the result is recorded in the pull
  request and the release record, and a known high or critical flaw blocks the release unless the owner accepts it in
  writing. New software is adopted only after a licence, maintenance and security-history check recorded here.
- **Why:** on 21 November 2026 releases were promoted with Frappe v16.56.0 although a high-severity advisory
  (GHSA-vwqr-4mjv-ffrm, unauthorised sending of email, fixed in 16.60.1) had been published on 19 November; it was found
  only on 22 November by the first run of the upstream watch (P62). **Where:** `AGENTS.md`, the release log, P62.

### Editor file safety: see failed saves within minutes, never lose or delete edits (P61)
- **Decision:** a five-minute watch on the editor host raises an alarm on failed saves to Drive, edits the editor
  cannot apply and parked documents, copies every parked document to a root-only recovery folder, and checks disk and
  cache; a stuck document is closed for everyone only on request, after a forced save and a rescue. No tool deletes a
  parked document or a Drive file; people are told not to delete or re-upload a file that will not open. The editor gets
  five minutes to stop, so ONLYOFFICE's own shutdown routine saves every open document; before a host reboot the editor
  is stopped first. The cache is left to ONLYOFFICE's own hourly expiry.
- **Why:** owner, 21 November 2026, after a shared workbook became unusable and edits were parked unsaved on
  20 November: a file must never be left in that state. Nothing guarantees that a save never fails; the aim is that a
  failure is seen within minutes, no edit is lost and a stuck file is recoverable without deleting it. **Where:**
  `tools/editor_safety.py`, `integrations/onlyoffice/` (runbook, systemd and settings examples),
  `deployment/stacks/editor-onlyoffice.compose.json`, `docs/production-moves.md`, `tests/test_editor_safety.py`.



## Engineer verification for field attendance

Configure the reporting relationship on the Field Site. An assigned engineer verifies a supervisor’s submission.
The engineer can also capture for workers assigned to that supervisor for the shift. These submissions are verified
automatically and retain the engineer’s identity and the applicable supervisor. Both paths require final approval by
a separate project manager before creating official HR Attendance. Teams without an engineer and employees who
check themselves in keep their existing workflows.

### Forward the test reset from trusted pull-request closure events (P71)

- **Decision:** An unmerged PR targeting main from a branch in this repository
  can request a test reset. The default-branch workflow passes the PR number
  to the private test workflow with a short-lived, repository-scoped GitHub App
  token. The workflow never checks out a PR or accepts credentials from it.
- **Why:** Test deployment uses a private runner. The private workflow verifies
  the closed PR and the currently deployed revision before it can restore main.
- **Dependency review:** GitHub's official MIT-licensed
  `actions/create-github-app-token` v3.4.0 was checked on 24 November 2026.
  The version is pinned to its commit. The official repository was active and
  no advisory matched in GitHub Security Advisories or OSV.
- **Where:** `.github/workflows/test-pr-close.yml`. Development was assisted by Codex.

### Keep only data refresh on the test Desk (P71)

- **Decision:** GitHub Actions restores the test code baseline after an unmerged
  test PR closes. Retire the Desk's code refresh button and its worker command.
  The one-way data refresh and its last successful refresh timestamp stay in use.
- **Where:** the test Desk, the test refresh API, and the data refresh worker.

### Private metrics and monitoring logs (P72)

- **Decision:** Run the workspace dashboard and storage on a host with spare
  memory. Use Grafana and Loki (AGPL-3.0), Prometheus, node_exporter, cAdvisor
  and Alloy (Apache-2.0). Keep the dashboard behind private HTTPS and metric
  and log storage on the monitoring network. Keep phone delivery disabled.
- **Why:** Preserve probe logs through application redeployments and use the
  same dashboard for host and container measurements. Versioned storage
  limits keep this deployment bounded.
- **Dependency review:** On 24 November 2026, official maintainers' releases,
  GitHub advisories and OSV were reviewed for the six pinned images. Grafana
  13.3.1 includes the November security fixes and does not use Elasticsearch
  or the image renderer here. Prometheus 3.16.0 is newer than the listed
  fixes in 3.11.3. No OSV commit match was returned for the six pins.
- **Where:** `integrations/monitoring/observability/`. AI-assisted by Codex.

### One register of our changes to upstream apps, walked on every upgrade (P89)

- **Decision:** Keep every change we make to software we did not write in
  `docs/upstream-customizations.md`: build-time patches, overrides, overlays on
  their screens, proxy rules, objects and settings made in their admin screens,
  and workarounds for their bugs. Each entry names the upgrade action
  (re-apply, re-check or none), how to test it and the upstream issue. A pull
  request that changes or starts relying on upstream behaviour updates the
  register; an upgrade walks the entries for that app on the test site. What
  cannot be public stays in a private companion in the operations repository.
- **Why:** These changes were spread over this log, the retained record, the
  handovers and the code, so an upgrade could silently undo one, above all a
  setting made by hand that no code reproduces. A CI check that the register
  is updated is deferred until the register has settled.
- **Where:** `docs/upstream-customizations.md`, `AGENTS.md`. AI-assisted by Claude Code.

### Upgrade checks fail loudly on a changed upstream file, image or commit (P91)

- **Decision:** A patch on an upstream file must find every line it changes exactly
  once, or the build stops (frappe_docker's Containerfile, the Insights frontend
  patch). A file we replace whole is tied to the exact upstream version it was made
  from: `integrations/onlyoffice/upstream.json` records the image and the checksum of
  its own start page, and `overlay_base` in `integrations/mail/upstream.json` records
  the upstream checksum of every webmail file the overlay replaces. The tests fail
  when the image or commit changes without the record, and two tools refresh the
  record during an upgrade (`tools/refresh_editor_original.py`,
  `tools/refresh_webmail_overlay_base.py`). The upstream watch points every app
  with a workaround at its register entries and also reads the module compose
  files, so the monitoring images are watched.
- **Why:** Before, an upstream rewording silently dropped our pins, a changed import
  left the Insights sidebar broken at runtime, and an image or commit bump alone
  passed CI while mounting our old copy over the new upstream files (register
  entries BUILD-1, INSIGHTS-1, OFFICE-1, WEBMAIL-1). The generated build files are
  byte-identical before and after this change.
- **Where:** `tools/prepare_erp_image.py`, `integrations/insights/patch_session.py`,
  `tools/prepare_mail.py`, the two refresh tools, `tools/upstream_watch.py`,
  `deployment/upstream-watch.json`, their tests and module READMEs. AI-assisted by
  Claude Code.

### Retired Collabora material removed; private operational names checked like client identity (P92)

- **Decision:** The Drive and deployment READMEs describe deploying ONLYOFFICE, not
  Collabora. The test ingress rule that guarded Collabora's admin paths now guards
  ONLYOFFICE's own status page and internal interface (`/info`, `/internal`, also
  under a version prefix); ONLYOFFICE 10 has no admin panel. The automatic identity
  check (P84) also fingerprints private operational names such as the hosting
  provider's, which `docs/retained.md` no longer names; git history is left as it
  is (owner). A correction note marks the WhatsApp wrapper as planned, not built.
- **Why:** The old instructions described a retired editor, the old rule guarded
  paths that do not exist, and the public P list already replaces the provider's
  name while one public record still carried it.
- **Where:** `integrations/drive/README.md`, `deployment/README.md`,
  `tools/prepare_ingress.py`, `.client-identity-fingerprints`, `docs/retained.md`,
  register entry OFFICE-7. AI-assisted by Claude Code.

### Every public name has its own certificate; no copied wildcard (P11)

- **Decision:** The production proxy obtains a Let's Encrypt certificate for every
  public name itself. The production names use the HTTP challenge it already used
  for some of them: a port-80 challenge route with a priority above every other
  port-80 route sends each name's challenge to Traefik
  (`own-certificate-acme-validation`). The relayed test names use a second resolver,
  `letsencrypt-tls`, with the TLS-ALPN challenge on port 443
  (`tools/coolify_proxy_tls_resolver.py`), because their port-80 challenges belong
  to the test host, which renews its own certificates through the relay. The
  wildcard certificate copied onto the proxy at the November migration is removed
  once both are live. A test checks that every name using the HTTP resolver has a
  challenge route that outranks the rest, and that the relay leaves port 80,
  challenges included, to the test host.
- **Why:** The copied wildcard had no renewal: Traefik cannot issue a wildcard with
  the HTTP challenge, and the DNS host has no API it can use. While any loaded
  certificate covers a name, Traefik does not request its own, and it does not look
  at the expiry date (Traefik 3.7.20, `getUncheckedDomains`). So ERP, sign-in, Drive,
  Respond, the website and the test site would all have failed on the wildcard's
  expiry. The wildcard was once needed for the test relay. That reason is gone,
  because the relay ends TLS on production and has its own certificate per name.
  Respond's host-wide port-80 redirect also sent challenges to HTTPS, where they
  fail. Traefik's HTTP challenge handler answers only its own tokens (404
  otherwise), so two hosts cannot share port-80 challenges for one name.
- **Consequence:** Adding the resolver restarts the proxy once (about 16 seconds).
  Removing the wildcard leaves a short gap: Traefik requests the new certificates
  only once nothing covers the names.
- **Where:** `deployment/config/proxy/office-acme.yml`, `tools/prepare_test_relay.py`,
  `tools/coolify_proxy_hosts.py`, `tools/coolify_proxy_tls_resolver.py`,
  `tests/test_rebuild_templates.py`, register entry PROXY-6. AI-assisted by Claude Code.

### Alerts in the native app: Google's messaging library, and every word written by the app (P50, P108)

- **Decision:** The native Android app receives alerts through Firebase Cloud Messaging
  (`firebase-messaging` 26.0.2), the messaging part only: no analytics, no crash reports,
  no advertising ID. There is no settings file in the project and no build plug-in for it;
  the four values the library needs are private build properties, as the server address
  is. A signal carries a kind and short fields only. Every word an alert shows is a fixed
  sentence in the app (`core/Alerts.kt`); nothing the app shows is ever taken from a signal, and
  an unknown kind is dropped. The server must send data-only signals: one that carries a
  ready-made notification text is shown by Google's library itself while the app is in
  the background, without asking the app. The phone remembers a short fingerprint of each
  waiting reference (at most 500) so it can count and remove, never the reference. A
  phone without its key shows no alert. An alert decides nothing: a
  tap opens the app, which asks for the fingerprint first. A lost key removes every alert.
  The phone asks Google for a delivery address only when the app asks for one.
- **Why:** An Android app that is closed can only be reached through this service; the
  earlier app used the same service through a packaged library. Writing the words in the
  app means a wrong or forged signal cannot put a name or an amount on a locked phone.
  Leaving out the settings file keeps a deployment's identity out of this repository and
  removes one build tool.
- **Consequence:** The library makes its own connection to Google, the one exception to
  "the app talks to one server". Google learns that the app is installed on a phone,
  when a signal is delivered, and the signal's short fields: its kind and, for an
  approval, a rejection or a removal, the document type and name the server puts in so the phone can count and
  remove. Open with the owner: the server sends a keyed fingerprint instead of the name.
  A "decided elsewhere" signal that gets lost leaves a count too high until the real
  Inbox sets it right (not built yet). The fingerprint match is known to the phone only;
  the server gets no proof of it (open with the owner). Phones without Google services
  get no alerts this way. The merged app also
  carries the library's own permissions (network state, wake lock, receiving messages).
- **Checked:** version published 11 November 2026 (older than two weeks); all 63 resolved
  library versions asked in OSV on 28 November 2026, none used by the app has an open
  advisory; every one has its checksum in `gradle/verification-metadata.xml`, recorded by Gradle at
  the first download and not compared with a second source.
- **Where:** `mobile-native/core/.../Alerts.kt`, `mobile-native/app/.../AlertCenter.kt`,
  `AlertsScreen.kt`, `tests/test_mobile_native.py`. AI-assisted by Claude Code.

### Native app: the approval's full page also while the phone is in use, by the person's own switch (P50, P108)

- **Decision:** The native Android app asks for `SYSTEM_ALERT_WINDOW` ("display over other
  apps"). It is used for one thing: when an approval rings while the phone is unlocked and
  in use, the app opens its own full page (`RingActivity`), the same page a locked phone
  shows. Only where the person switched it on in the phone's settings; the Alerts screen
  says what happens without it and leads to the switch. The app draws no window over any
  other app. Decided by the developer on 28 November 2026: both, according to the phone.
- **Why:** Android shows an app's full page by itself only on a locked or dark phone; on a
  phone in use it shows a banner. People who decide approvals asked for the full page in
  both cases. On current Android an app may open a page from the background only in a few
  cases; this switch is the one a person can give an app.
- **Consequence:** Phones without the setting (phones with little memory) and people who
  leave it off get the banner, which rings and carries Approve, Reject and Remind. The
  page shows fixed words only and decides nothing. It opens only for an approval the phone
  did not know yet or a reminder the person asked for, never during a call, at most once
  a minute, and its buttons answer only after a moment. The store may ask for a reason
  for this permission at release. A repository test holds that nothing is drawn over other apps.
- **Where:** `mobile-native/app/.../AlertCenter.kt` (`onTop`, `inUse`, `show`),
  `AlertsScreen.kt`, `AndroidManifest.xml`, `tests/test_mobile_native.py`. AI-assisted by
  Claude Code.
