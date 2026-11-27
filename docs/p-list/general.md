# General: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 28 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# General: P items

Platform, infrastructure, release process, backups, network and security items that do not belong to a single app.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P11 — Certificate issuance and renewal acceptance

**App:** general · **Also touches:** none · **State:** in progress

**Status (27 November 2026):** **issuance done on production.** Every public name has its own Let's Encrypt certificate
from Traefik (to 25 February 2027). Production names use the HTTP challenge, with challenge routes above every port-80
route. The relayed test names use the `letsencrypt-tls` resolver (TLS-ALPN), so the test host keeps renewing its own
certificates through the port-80 relay. The copied wildcard is no longer loaded. Records: release log 27 November,
receipts `p11-production-challenge-routes-662aaf9` and `p11-production-own-certificates-662aaf9`; public #126 and #128.

- **Left to accept:**
  - the first automatic renewal, due about 26 January 2027 (check the dates in the HTTPS probe);
  - Stalwart's own `mx` certificate renewing before 11 February;
  - the test host's own certificates renewing (from 9 February).
- **Clean-up:** remove the copied certificate files from the proxy folder after a week (the rollback set keeps a copy);
  then delete register PROXY-P5.
- **Notes:** the HTTPS probe's failures still reach nobody (P72, separate decision). `docs` has no DNS record (its
  certificate will lapse; harmless if unused). mx on 443 serves Traefik's default certificate (no HTTPS route asks for
  it).

### P13 — Remaining users, app permissions and worker enrollment

**App:** general · **Also touches:** signin, mail, dms · **State:** in progress

**Status:** ten users are in the shared sign-in group; the intended twenty-user rollout is incomplete.

- Enroll the remaining intended users and verify ordinary-user access in each app.
- Complete first Drive/DMS sign-ins and per-owner document-worker enrollment; only the previously enrolled user/shared Space is verified.
- Assign mailbox membership/read/send access separately. The current personal/shared mailbox mapping is for the existing account, not every group member.
- Verify ordinary users can access shared business files while other users' personal files and private Paperless documents stay private.

### P29 — Self-hosted mesh VPN with Headscale and Headplane

**App:** general · **Also touches:** none · **State:** open

**Status:** planned; replace hosted Tailscale coordination for business scale.
Assume the requested UI is Headplane (confirm if a different project was meant).
Deploy pinned Headscale and compatible Headplane as versioned VPS/Coolify
services. Assess authentik OIDC, ordinary users, administrator isolation, ACLs,
server tags, branch/subnet routing, device approval/expiry/revocation, supported
Windows/iOS/router clients and DERP/STUN requirements. Headscale replaces the
coordination server; compatible Tailscale clients may still be used. Do not
assume hosted-service feature parity or subscription seat limits apply unchanged.

Design administrative recovery independent of the mesh being migrated. Test on
isolated clients first, preserve existing management connectivity during staged
migration, and explicitly verify both Coolify controllers, SSH, inter-server
refresh and application access before retiring the old control plane. Avoid
DNS/SSO bootstrap dependencies that require an already-working new mesh.
Choose VPS placement and recovery/backup arrangements before rollout; do not
expose the administration UI publicly by default. Repo → test → production applies.
References: https://github.com/juanfont/headscale and https://github.com/tale/headplane

### P30 — Technitium filtered DNS for mesh devices and branch routers

**App:** general · **Also touches:** none · **State:** open

**Status:** planned; depends on P29's tested connectivity and routing design.
Deploy a pinned Technitium DNS service on VPS as a versioned Coolify project.
Provide caching/recursive or forwarded DNS with agreed ad/tracker blocklists,
allowlisting and internal split DNS to approved mesh devices. Branch routers
will forward client DNS over the mesh to this resolver; assess native router
client support or a branch gateway where required. Agree whether branches use
router DNS proxying or routed client subnets, including IPv6 and source ACLs.

Keep DNS UDP/TCP 53 and administration restricted to approved mesh/branch
sources; no public recursive resolver. Preserve public authoritative DNS and
mail records at the existing DNS provider unless separately decided. Coordinate
Headscale/MagicDNS internal zones and conditional forwarding without loops.
DNS filtering cannot remove every advertisement, especially first-party content.

Decide upstream resolver/privacy policy, query-log retention/access, blocklist
updates, branch caches and resolver redundancy/failover. A public fallback may
bypass filtering; explicitly select behavior during VPS/mesh outages. Verify
branch latency, resolution after reboot, DNSSEC behavior, internal/public names,
allowlisting, outage recovery and bootstrap without a working mesh resolver.
Reference: https://technitium.com/dns/help.html

### P35 — Public release and upstream sharing

**App:** general · **Also touches:** none · **State:** in progress

**Status:** **published 19 November 2026.** Public repository
`rdavuluri44/ERPNext_Owncloud_Stalwart_Integrations` (AGPL-3.0-or-later,
copyright "Unformat and contributors", fresh history: one commit `eb887b7`,
authored with the owner's GitHub no-reply address; tree identical to the
tested private release `bd78277`). `main` protected (pull requests, no force
push or deletion). Operations records (this file, release log, runbooks)
kept in the private operations repository (full history kept; deploy keys
removed). Artwork audit: company logo not published (placeholder), app icons
from frappe/suite (AGPL-3.0) attributed. Test and production fetch the public
repository. Still open: (a)–(d) presentation polish per module, upstream
sharing (bug reports, forum posts). Owner, 19
November 2026: before publishing, the repository must present itself as
(a) modular, each module explaining what it set out to achieve, (b) the open
source tools that made it possible, (c) the decisions taken and the
integrations built, and (d) how it was done (process, tests, rehearsals).
Builds on P36 (`modules.json`, module READMEs) and `docs/decisions.md`.

Share what we build and fix (AGENTS.md principles 3-5): choose an open-source
license for this repository (owner decision), complete the artwork/branding
and third-party license audit noted in LICENSES.md, remove private
deployment-specific values, then publish. Keep upstream bug reports and fixes
flowing (for example the Collabora AutoFilter search findings, issue
CollaboraOnline/online#16276) with an AI-assistance disclosure.

Shared 17 November 2026: findings and the workaround posted upstream
(https://github.com/CollaboraOnline/online/issues/16276#issuecomment-6947112394),
including that the search field only appears for lists longer than 25
entries, with an AI-assistance credit.

**Upstream posts list and reply check (owner, 26 November 2026, go):** every post we make upstream is listed with
why, the P item, the register entry and a log of every check and follow-up, and checked for replies until we stop
using that project (also a working-agreements rule for all projects). Built on public branch `p35/upstream-posts`:
`docs/upstream-posts.json` and `.md` (11 public posts), `tools/upstream_posts.py` (read-only check; finds replies,
state changes and posts the list lacks; `check --gh --record` at every session start), the daily upstream watch
reports new replies once (`YYYY-MM-DD-posts.md`), tests, `AGENTS.md` rule. The private report (frappe_docker
advisory) is in `docs/upstream-posts-private.md` here. First check, 26 November: Collabora's maintainer had replied on
24 November (confirmed our analysis, passed to the Calc developers); Coolify fixed our bug the same day (commit
`8dbaecc`; remove the COOLIFY-1 workaround once a release we run carries it, then say so on the issue); the rest
waiting. **Open (owner):** Collabora, which we no longer use (P42): a one-line thank-you and stop watching, or stop
watching without a post.

**Open-source list (owner, 26 November 2026, go):** every open-source project we use, borrow from or evaluate is in
public `docs/open-source.json` (62: 47 in use, 14 being evaluated, 1 retired; licences read from GitHub the same day).
The README acknowledgements are generated from it, and a test keeps it in step with the upstream watch and
`modules.json` (public PR #97, branch `p35/open-source-list`; working-agreements rule on PR #3). Found: the README
thanks had fallen behind (the monitoring stack, backup tools, CoreDNS, frappe_docker, the hosts' software were
missing); `owncloud/web` was archived upstream on 23 November 2026 (ocis carries the web client; where development
continues: to verify); `ocis-konnectd` archived since 2020. Gap kept visible: the mobile app's dependencies are
credited but not in the daily watch.

### P40 — Backup hardening against ransomware

**App:** general · **Also touches:** none · **State:** in progress

**Status:** owner approved ZFS snapshots on 18 November 2026. See
[disaster recovery](../disaster-recovery.md).

- Daily ZFS snapshots of the backup storage on TrueNAS, kept 60 days, by a
  root cron job (`integrations/backup/zfs-snapshot-guard.sh`), because
  TrueNAS snapshot tasks refuse internal app storage. TrueNAS time zone set
  to India. Done 18 November 2026; first production backup and restore drill
  passed the same day (ERP 1,055, DMS 75, identity 230 tables; 54,025 files).
- Tamper resistance for production's key: versioned bucket (hidden versions
  kept 30 days) and a key policy without version deletes or versioning,
  lifecycle and policy changes. Tool `integrations/backup/harden_storage.py`
  added 19 November 2026. **Done 19 November:** owner applied versioning
  with the admin key and attached the policy to `backup-production`;
  `harden_storage.py verify` from production: writes versioned, a delete only
  hides, old versions survive and cannot be deleted, versioning cannot be
  switched off; restic check with the restricted key clean. Lifecycle rule
  set (hidden versions expire after 30 days, so pruning still frees space).
- Periodic offline copy to a USB disk kept away from the servers.
- Back up the test VM's own settings (`<test host secrets folder>`, profiles).
- Tailnet access rule: production may reach only the backup storage port on
  TrueNAS.

### P41 — Owner recovery essentials (recurring)

**App:** general · **Also touches:** none · **State:** recurring

**Status:** guideline added 18 November 2026 (`AGENTS.md`,
[disaster recovery](../disaster-recovery.md)). Every three months the owner
checks that the encryption password, TrueNAS admin access, SSH keys and the
provider, registrar, GitHub, Tailscale, Meta and authentik logins with
recovery codes are in the password manager, with an offline copy of the
first three.

### P43 — Tablet layout and touch check (all apps)

**App:** general · **Also touches:** portal, drive, editor, mail, dms · **State:** open

**Status:** open, added by the owner on 18 November 2026. The apps will be used
on tablets, so every app must work well there, in portrait and landscape.
Check the ONLYOFFICE part on the test site **before** the P42 production
switch; the rest can follow.

Scope (test site, owner's tablets plus browser emulation of common sizes,
e.g. iPad 768 to 1024 px and 10 to 11 inch Android, both orientations):
- **Portal:** login, home, left-edge app menu (it opens by hover on desktop;
  on touch it must open by swipe or tap), deep links, opening apps in tabs.
- **ERP desk, Raven, Insights:** layout, menus, tables and forms usable by
  touch, on-screen keyboard not covering inputs.
- **Drive and ONLYOFFICE:** the P42 layout at tablet widths. Our phone rules
  start at 768 px and below, so an iPad in portrait sits on the edge: decide
  per width whether tablets get the desktop or phone status bar (sheet tabs,
  zoom). Also check: the ✕ ⋮ buttons, the side-menu hamburger, the About
  card, the private sheet views, the filter drop-downs and the pivot field
  list by touch, and the on-screen keyboard while editing cells. Tablets use
  the desktop editor (ONLYOFFICE's touch editor is view-only in the free
  edition).
- **Mail and DMS:** reading, composing, attachments, document viewing.

Done when each app passes on at least one iPad-size and one Android tablet in
both orientations, defects are fixed in the repository through the normal
test-first flow, and the tablet rules are recorded in the module READMEs.

### P45 — Production Drive, DMS, Mail and sign-in on the repository build

**App:** general · **Also touches:** drive, dms, mail, signin · **State:** in progress

**Status:** started 19 November 2026 (owner). Plan, order and the Drive
comparison: P45 runbook (private record). Renderer gained
`existing_mounts` to reuse production data folders; Drive route file added.
Each app switches in a short planned pause with a rollback point.
**Drive done 19 November 2026** (13 s pause; release `0cfa9c1`; owner
confirmed opening and editing a spreadsheet on production). **DMS and
document processing done 19 November 2026** (2 min 17 s pause; release
`24eb5dd`). **Private DNS and Mail done 19 November 2026** (seconds and 10 s;
release `593d8c8`). Remaining: sign-in and its support service, after P49. Next: DMS, then Mail, then
sign-in.

### P46 — TrueNAS as network video recorder (NVR)

**App:** general · **Also touches:** none · **State:** in progress

**Status:** planned, owner request 19 November 2026. Besides the test VM and
the backup storage, the TrueNAS server records IP cameras that stream over
the internet. Scope: choose the recorder (Frigate is the first candidate:
open source under the MIT licence, so commercial use is allowed; its paid
Frigate+ model service is optional; to be re-verified at selection), object
detection on a Coral TPU, secure ingest of remote camera streams (no camera
exposed publicly; over the tailnet or an authenticated relay), retention and
storage sizing, and the hardware: larger disks, more RAM, Coral. Keep it
isolated from the backup storage and the test VM (separate dataset, quotas,
no access from production), and include the recorder configuration in this
repository as its own module.

**Trial (owner, 26 November 2026):** a proof of concept with one camera on the
local network; capacity and remote sites are not in scope yet. Frigate 0.18.3
(MIT, re-verified) from the TrueNAS catalogue, detection with OpenVINO on the
processor (the host has no graphics chip), recordings in their own dataset with a
100 GiB quota, the web page with its login on the local and private networks only.
Coral is dropped: Frigate no longer recommends it for new installations. Settings
in the `integrations/frigate/` module; Frigate is in the daily upstream watch. The
owner installs the camera (an Annke I51DS) later.

**Long-term placement and hardware (owner, 26 November 2026):** backups and the Frigate NVR stay on a local server
(the TrueNAS host), because video processing (detection on an accelerator) cannot run on the VPS; the test VM may
move to the VPS if required. Long-term TrueNAS upgrade: (i) more RAM; (ii) four 8 TB hard disks; (iii) a detection
accelerator, which the owner named as Coral. Note for the hardware choice: the trial above dropped Coral because
Frigate no longer recommends it for new installations; choose the accelerator Frigate recommends at purchase time
(for example an Intel graphics chip with OpenVINO, or a Hailo card) and record the choice. Disk layout, redundancy
and the split between backup and recordings are decided with the purchase.

**Advisories rechecked and accepted for the trial (27 November 2026).** Of the five Frigate advisories without a
listed fix, the two high ones (GHSA-c4qf-xxq4-vf55, GHSA-mgh5-cr9h-g6hr) are closed in 0.18.3 in the code; three
medium ones remain (GHSA-74x4-gw64-2mq5, GHSA-w3c4-957q-2jw4, GHSA-4xp7-86rr-9758). The code was read; no attack was
tried. **Owner: the trial runs with these open**, on the private network, with administrator accounts only and our
own camera; no camera-limited or view-only accounts until GHSA-74x4-gw64-2mq5 is fixed. Production is decided after
the trial, including whether detection is needed at all (a recording-only tool has far less exposed code). Public
draft #81 was brought up to date with main (`aac5887`, CI passed); Frigate and its bundled detection model are in the
open-source list. Still open: a detection check and the first admin password change.

### P48 — Remote branch router and gateway firewall

**App:** general · **Also touches:** none · **State:** blocked

**Status:** planned, owner request 19 November 2026; depends on P29
(Headscale) and P30 (Technitium DNS). Find or build a branch router that joins
the mesh, sends local DNS to the Technitium server over Headscale, and acts
as the branch gateway firewall: user-activity logging (kept for legal
reasons) and restriction of streaming to save bandwidth. Compare hardware and
operating systems (for example OpenWrt, OPNsense, pfSense) on mesh support,
logging, filtering, licence and cost. Activity logging must follow the
applicable law (for example India's IT Act and the Digital Personal Data
Protection Act: notice to users, purpose, retention, access control); define
that policy with the owner before enabling it.

**Hardware choice (owner discussion, 26 November 2026; prices from Indian listings that day, agent estimates):**
- **Box:** a fanless mini PC with an Intel N150 (or N100) processor, 4 Intel i226-V network ports (not Realtek:
  FreeBSD's drivers are less reliable), 8 GB RAM and a 256 GB NVMe SSD; about ₹18,000–22,000 per site; a seller
  with an Indian warranty. Many units are sold without RAM and SSD.
- **System:** OPNsense (needs an x86 processor) for DHCP, DNS, firewall and the mesh gateway; spare ports for a
  separate camera network or a second internet line.
- **Wipe on arrival:** install OPNsense fresh; never use a preinstalled system.
- **Addresses:** every branch and the NVR site get their own LAN range; the mesh cannot route between sites that use
  the same range.
- **To check before buying:** the OPNsense Tailscale plugin (`os-tailscale`, community-supported) must sign in to our
  own Headscale (P29), not only hosted Tailscale; it creates no firewall rules (interface and rules added by hand);
  licence, maintenance and security review per the adoption rule.
- **Owner decision:** trial the box on hosted Tailscale now and move it to Headscale later, or wait for P29.
- The box also carries the project's cameras that can be wired back to it (P88).

### P57 — The platform survives restarts and reboots without an outage

**App:** general · **Also touches:** drive, mail, editor · **State:** in progress

**Status:** approved by the owner 20 November 2026 ("take precautions that all
systems come up without the outage we faced today"); in progress. Background:
production rebooted unexpectedly at 10:34 IST (provider question open); 33
containers returned by themselves, tailnet ports came back, but the Drive
editor bridge (collaboration) crash-looped because Drive's oCIS advertises one
of its five internal addresses at random after each start (emergency fix: the
bridge was attached to the `coolify` network, a runtime patch).
**Precautions to build (all in the repository, test first):**
1. **Bridge on every oCIS network** in the Drive stack and production profile
   (`extra_networks`), so any advertised address is reachable; start it after
   oCIS is healthy (depends_on healthy, retry on failure).
2. **Docker after Tailscale** on the hosts (systemd drop-in for docker.service:
   After/Wants tailscaled), so containers bound to tailnet addresses (private
   DNS, Mail 465/587/993/8020/8030) never start before the address exists.
3. **Post-boot check with self-repair** (a systemd unit after docker): waits for
   the containers, checks the editor bridge is stable and registered (restarts
   it once if not), checks ERP, sign-in, Drive, Mail, DMS and the editor host,
   checks the tailnet ports, writes a status file/log and fails loudly if
   anything stays wrong; alert for "container restarting".
4. **Longer shutdown time for databases** (stop grace period) so a reboot never
   cuts a database off mid-write.
5. **Reboot drill on the test VM** (planned, night or when the VM is free):
   reboot it and prove that every test host comes back, the Drive editor opens
   an .xlsx, sign-in and Mail work, and the backup timer is intact; repeat after
   restarting oCIS several times.
6. **Checklist and planned reboots:** a post-reboot checklist in
   `docs/production-moves.md`; kernel-update reboots planned for the night
   window, announced, followed by the check; ask the provider (owner raised the
   10:34 IST reboot with them, answer awaited) to give notice of maintenance.
7. **Stalwart after a reboot (found 21 November 2026):** after the 20 November
   reboot production Mail sign-in returned a Stalwart 500 until its settings were
   reloaded (see the 21 November release entry). The post-boot check must run
   `ReloadSettings` through the admin API and then a real sign-in check; Stalwart's
   tracer must also write somewhere that exists (stdout or a mounted folder).
8. Do NOT reboot production as a test; after the drill on test passes and the
   provider answers, the owner decides whether to schedule a planned production
   reboot.
Order (owner's rule): branch, test (drill), merge, production with a rollback
point (the production changes are small: recreate the editor bridge with the
extra network, install the drop-in and the check unit; none restarts Docker).
Coordination: the test VM must be free of the first crippled refresh before the
drill.

**Tested on test (21 November 2026, owner go "2": drill today on the current test host):** PR #7 brought up to date with
`main` (`58585ab`), deployed to test, host checks installed. Editor bridge on all of oCIS's networks; five oCIS restarts
in a row: bridge never restarted, boot check passed each time. **Reboot drill 16:53:50 UTC:** back in about half a minute;
boot check "passed after 4 attempt(s)" 54 s after Docker started, no repair needed; Docker started after Tailscale; same 26
containers and images; the bridge retried 6 times in the first 20 s (oCIS NATS and the editor address not yet up), then
stable with no errors. **Learned for the production promotion:** the new shutdown grace reaches database and Redis
containers only when they are recreated (test: ERP `db`, `redis-cache`, `redis-queue`, 11 s), so the release must recreate
them at a quiet moment. Test record on PR #7. **Remaining:** owner opens a document in Drive on test after the reboot;
then merge and production promotion on the owner's go; repeat the drill on the VPS after the move (P33 successor).

**Released (21 November 2026, PR #7, `d2acab5`):** shutdown grace live on ERP and DMS databases and Redis; host checks
installed on production and passing; Drive's bridge already on all oCIS networks. **Open follow-ups:** (1) ~~enable the
editor-bridge check on production~~ done 22 Nov (PR #23, `85c3f01`);
(2) ~~port 587~~ removed 22 Nov; (3) ~~worker settings drift~~ not drift (the file is written once and kept by design;
release log 22 Nov); (4) repeat the reboot drill on the VPS after the test move; (5) ~~a planned production reboot~~ done 22 Nov 00:55 UTC: everything came back by itself (release log).

**Reboot of 26 November 2026, 15:30 UTC: one container did not come back (owner: record it here).** After an
operator's reboot of production (new kernel), `p72-observability-prometheus-1` stayed down: clean exit 0 at
15:30:05 UTC, not out of memory, restart policy `unless-stopped`. Its five siblings in the monitoring stack (same
policy) and the other 33 containers came back. Found 16 minutes later by chance (P97 session); started by hand at
15:56:02 UTC on the owner's yes (receipt `production-prometheus-started-after-reboot-20261126`); metrics from 15:30
to 15:56 UTC are missing and no metric alert could fire in that time. The monitoring stack (P72) was added on
24 November, after the reboot drills, so it has never been through one.
**Likely cause, not proven:** Prometheus stops within half a second of the stop signal, so Docker recorded it as
exited before the Docker service itself stopped, and `unless-stopped` does not start a container recorded as
stopped when Docker starts again.
**Open follow-ups (nothing started; owner's go needed):**
(6) lasting fix through the repository and the test site: restart policy `always` for the monitoring stack (or
another start-at-boot guarantee), then reproduce with a reboot of the test VM to prove the cause and the fix;
(7) the boot check counts the containers that were running before the reboot and reports any that did not come
back, on test and production, with an alert that does not depend on Prometheus;
(8) check the other stacks for services that stop as fast (same risk); (9) the reboot drill list names the
monitoring stack.

**Follow-ups 6 to 9 built and tested on the test VM (owner's go, 26 November 2026, night; public PR #112, receipt
`p57-test-boot-counts-containers-f971f54`):**
- **Cause:** not reproduced. A reboot of the test VM brought back throwaway copies of Prometheus with
  `unless-stopped`, `always`, and `unless-stopped` with a slow stop. Production could not be read from this session.
  So the fix does not depend on the cause.
- **Fix:**
  - The watch saves the running containers. After a reboot the boot check starts each one that ran before
    (`always` or `unless-stopped`) and is still down after a minute, once, and fails on anything still down.
  - It mails the admin through a dedicated sender when it repaired or failed something.
  - The monitoring stack uses `restart: always`.
  - Exporter-only hosts remove the central containers instead of keeping them stopped. On the test VM the four
    pilot leftovers were removed; their volumes are kept.
- **Second reboot with the fix:** the boot check started a deliberately lost container once (76 s after boot) and
  passed.
- **Follow-up 8 (other stacks):** on test every container with a restart policy came back. The boot check's start
  now covers any stack that does not.
- **Follow-up 9:** the reboot checklist names the monitoring stack.
- **Open:**
  - Production promotion (host check, monitoring policy) and the dedicated SMTP-only alert sender on production
    mail with the admin as recipient. Both need production access and the owner's go.
  - The restart watch reports the editor bridge's normal start-up retries after every boot (small follow-up).
- **Merged** as `f5ac9ec` (PR #112, 26 November 2026, 18:30 UTC). **On production** since 26 November 19:07 UTC (owner's go, 27 November IST).

**Production (owner's go, 27 November 2026, IST; release log of that night):**
- Boot check from `f5ac9ec` installed; monitoring stack on `restart: always` without a restart; boot check by hand passed.
- Dedicated SMTP-only alert sender `smtp-host-alerts` created on production mail (send-as `noreply`, allowed only from
  the VPS's tailnet address); recipient: the owner's mailbox (owner's choice). No mail sent yet.
- **Follow-up 10 (found during the promotion; owner chose the repository fix):** the VPS cannot reach its own mail
  server under the certificate's name. Public PR **#117** adds `host_checks.alert.address` (connect to the tailnet
  address, certificate still verified for the name); on the test VM at `84c578e`, CI passed. **Done:** merged as
  `e82f0f2`; on production from main `b4fdae5` (26 November 19:19 UTC): alert section and Prometheus (owner: yes) in
  the boot check, one test alert mailed to the owner; **the owner confirmed it arrived** (27 November).
- Not covered: a production reboot with the new check (proven on the test VM).

### P62 — Daily upstream watch: new releases, security flaws, patches, upgrade decisions

**App:** general · **Also touches:** none · **State:** in progress

**Installed on the test VM (26 November 2026, owner go):** read-only clone of public `main` in
`<server path>` (`47da25e`), profile `<server path>` (coolify 4.7.5 and rustfs 1.0.4
as recorded for production; docker 29.10.0, tailscale 1.104.7, ubuntu 24.04, linux 6.8.0 and traefik 3.7.19 read on the
test VM; **truenas, restic and production's own traefik version not yet entered**: this PC has no production key and
the TrueNAS host key did not match, so the connection was refused and not overridden), service and timer from the
examples without the GitHub token lines, timer daily 06:30 IST. First run with a guessed traefik 3.7.0 reported 4
urgent Traefik advisories; the test VM actually runs 3.7.19, which fixes them, so the profile was corrected and the
output reset. The second run had no urgent finding but 53 source errors: GitHub's limit for requests without a token
(60 an hour). **Remaining:** a read-only GitHub token on the test VM (owner creates it; the service lines are then
restored); production's traefik, TrueNAS and restic versions in the profile; confirm production traefik is at or above
3.7.15; digests into this repository (`docs/upstream-watch/`); one week of digests reviewed and the false-positive list;
then close.
**Token in place (26 November 2026):** the owner installed a fine-grained read-only token (root-only file on the test
VM); the service uses it. Full run: 0 source errors, 56 open findings, none urgent; baseline saved as
`docs/upstream-watch/2026-11-26-baseline.md`. **One "upgrade now":** Traefik 3.7.19 (Coolify proxy, public),
GHSA-3rh5-223h-cpwr (unauthenticated memory exhaustion in the Brotli compression), fixed in 3.7.20; the 3.7 line reached
end of life on 23 November. Raised to the owner; production's Traefik version still to be read. **Exposure:** part of
the token's text appeared in a screenshot in the agent conversation; rotation recommended to the owner. **Closed (owner,
26 November 2026):** the owner had already replaced the key; the exposure is closed. Check without reading the key:
the last run (26 November, 14:04 IST) had 0 source errors; whether it already used the new key is not recorded. The
next scheduled run (27 November, 06:40 IST) is the first known to use it.

**Status:** open, owner request 21 November 2026; not started. **Why:** the whole stack is
open source and pinned (ERP core and apps, authentik, Drive, ONLYOFFICE, Stalwart, Bulwark
webmail, Paperless, Coolify, Traefik, databases, backup tools, the host operating systems).
New releases, security advisories and upstream fixes reach us only by chance; the ONLYOFFICE
sheet-view crash of 20 to 21 November is an example of a defect that a watch would have
connected to a fix or a workaround.

**Build:** a daily job that (1) reads the inventory of pinned versions and image digests from
the repository (`deployment/` locks, stack definitions and `inputs.json`, each module's
`upstream.json`) plus the components that are not in it (Coolify, Docker, Tailscale,
TrueNAS, the Ubuntu hosts and kernels, restic, RustFS); (2) asks the public sources for
what is new: releases and changelogs, security advisories (GitHub advisories, OSV.dev,
NVD, vendor notices) and open upstream issues that match our versions; (3) writes a short
**daily digest** to the private repository (`docs/upstream-watch/YYYY-MM-DD.md`, only when
something changed, plus a weekly roll-up) and sends the owner a message; a critical,
actively exploited flaw on an internet-facing component is flagged the same day.

**For each finding:** component and our pinned version; what changed; severity and whether
our version is affected; exposure here (public, tailnet only, test only); whether a fixed
version or a workaround exists; compatibility and breaking-change notes; licence changes
(P35 principle 2); and a recommendation: ignore, schedule, or upgrade now, with the reason.
Findings that retire one of our own workarounds are linked (for example the ONLYOFFICE sheet-view
guard, to be removed once the pinned build no longer needs it).

**Rules:** the watch never upgrades anything. Every upgrade is a normal branch, test,
merge, production change with a rollback point, taken up by the owner, ideally together
with related P items. The recommendations are written by an AI agent and are advice: the owner
decides. Run it where it holds no production credentials (for example the test VM or a
scheduled agent), reading only public sources and this repository's pins. First run is
a baseline report of everything that is behind its latest stable release; dry-run for a
week before any message is sent; keep a short false-positive list. Related: P59 (drift
check), P57, P61, P42.

**First run and finding (22 November 2026):** the colleague's tool (PR #30, branch `p62-upstream-watch`, `a33dd47`, checks
green; review and test-site run pending) found, and our session confirmed at the source, that production's **Frappe
v16.56.0 is affected by GHSA-vwqr-4mjv-ffrm** (high, "Unauthorised sending of email in email communication due to
missing validation", published 19 November, affects >= 16.0.0 < 16.60.1, fix 16.60.1). All other recent Frappe
advisories were fixed before 16.56.0. **How it slipped through:** releases on 21 November were promoted without an
advisory check (the watch was still a plan); the owner's rule "security before features and deployments" now requires
that check for every promotion (working agreements, `AGENTS.md`, decision log). **Upgrade:** the colleague's agent was
asked to prepare the Frappe upgrade on a branch (release notes and advisories reviewed, compatible app versions,
tests); building the ERP image, the test site and production stay with the maintainers, each on the owner's go.

### P67 — Test deployments: one complete step, no hand-run pieces or drifting profiles

**App:** general · **Also touches:** test-site · **State:** open

**Status:** open (found 21 November 2026 installing PR #15). The test deploy script (also behind "Refresh code")
renders the stacks and rebuilds images, but not the test gateway file (`prepare_ingress.py`), the test profiles
(`prepare_test_profiles.py`) or the ERP setup (bootstrap); those were run by hand. The regenerated refresh profile
also differs from the installed one (code-refresh settings), so the installed profile has drifted from what the
repository produces. **Fix:** the deploy step renders and installs the gateway file and profiles and applies the ERP
setup when their inputs changed, shows a diff, keeps a rollback copy; reconcile the refresh profile. Belongs with P54
(branch deploy button) and P59 (drift check). Note: a "Refresh code" to `main` before PR #15 is merged would leave the
test gateway with PR #15's routes but `main`'s code.

### P68 — A repository check for imports of names that do not exist

**App:** general · **Also touches:** none · **State:** open

**Status:** open (lesson of P64, 21 November 2026). A lazy import inside a function (`from .combined import
before_request`) of a name that does not exist passes every unit test that fakes the module, and fails only at run
time. Add a static check to `tools/check_repository.py` (or CI) that resolves imports of the project's own modules
(for example pylint's `no-name-in-module` / `import-error` for `erpnext_drive_integrations`), and the rule that tests
import the real module under test rather than a fake copy of it.

### P70 — Mail and WhatsApp domain split: `tenant.example` for production, `example.com` for the demo

**App:** general · **Also touches:** mail, test-site, erp, signin · **State:** open

**Status:** owner decision 21 November 2026 ("tomorrow we'll have separate email domain for prod and separate email
for unformat; separate WhatsApp also"); not started, waits for the owner to take it up. Shared foundation of **P19**
and **P63**: the three are planned, tested and released together, each keeping its own status.

**Decided:** production mail uses the company domain `tenant.example`; `example.com` becomes the demo's own mail
identity; a second WhatsApp number is the demo's channel. Demo users send evaluation mail and messages from
`example.com` and the Unformat WhatsApp number (with the P63 allow list and test/demo marker).

**Scope**
1. **Production on `tenant.example`:** add the domain to the production mail server (DKIM, SPF, DMARC, MX, autoconfig),
   create or move the production mailboxes to it; the three Google mailboxes move under P19 (blocked by P12, PTR).
   Today `tenant.example` MX points at Google and `example.com` at our server; in the production ERP 9 of 10 active users
   sign in with personal addresses of a public mail provider and 1 with `example.com`, so few accounts change. List every place the old address is
   used (authentik, ERP users and Email Accounts, Drive, DMS mail import, sender addresses, invitations) and move each.
2. **`example.com` for the demo:** where its mail runs (recommended: production mail server as a separate domain,
   because the test site sits on a home connection with poor outgoing delivery; alternative: the test site's own mail
   server), the demo sending accounts, DNS records; production keeps nothing on it afterwards.
3. **Second WhatsApp number** for the demo (Meta business number), linked to P04; production WhatsApp stays separate.
4. **Web addresses:** production websites stay on `example.com` host names unless the owner decides otherwise; only
   the mail and messaging identities split.
5. **Order and rollback:** DNS changes, mailbox moves and client reconfiguration in an agreed order with a rollback
   point; nothing changes until the owner says so.

### P71 — GitHub CI/CD and central secrets management: Actions deploy test and production; "Refresh code" button removed

**App:** general · **Also touches:** test-site, erp, mail, drive, dms, signin · **State:** open

**Status:** owner decision 21 November 2026 ("lets go with this github ci/cd"); plan **settled** the same day;
**scheduled for later, nothing built**. Starts only when the owner says go (standing rule). Priority: rank 6 (tier 1). Replaces the hand-run deploy steps; takes over
the deploy parts of **P67** (one complete test deploy), **P54** (branch deploy button) and much of **P59** (promotion
plan and drift check); those items are reviewed and closed or narrowed when P71 is planned.

**Target flow (GitHub's standard practice):**
1. **Pull request opened or updated** (branches of this repository only): a GitHub Actions job deploys the branch to
   the test site and records a deployment (commit, time, result) on the pull request; merging can require it to have
   passed, so "tested on test" is enforced by GitHub instead of a written note.
2. **Pull request closed without merging:** a job deploys production's revision (`main`) to test, so test never keeps
   rejected code. **Merged:** nothing to reset.
3. **Merge to `main`:** a job promotes the **same tested build** (build once, promote that image) to production; it
   waits in a protected GitHub "production" environment for the **owner's approval**. Rollback = approve the previous
   version again.
4. **Runners:** GitHub's standard self-hosted runner on the test host and on production; they connect out to GitHub, so
   the design does not depend on where test runs (home host today, a VPS from 22 November 2026).

**"Refresh code" button removal (plan):** the button's job (put test back on production's code) is taken over by
step 2. Remove it only after the pipeline has run that reset successfully on test: (a) the pipeline's reset works and
is visible on the pull request; (b) remove the button, its endpoint and its worker path from the portal and the test
refresh module (keep "Refresh data", which is separate); (c) update the test-refresh module README, the runbook and
`docs/decisions.md`; (d) tests prove the button and its endpoint are gone and "Refresh data" still works.

**Design points to agree:**
- **Public logs:** job logs of a public repository are visible to anyone, while today's deploy scripts print host
  names, addresses, server paths and names; jobs print neutral output only, with a leak check that fails the job.
- **Secrets stay on the servers** (AGENTS.md): runners read the servers' own secret files; nothing in GitHub secrets
  beyond what GitHub itself needs.
- **The GitHub account becomes a key to production:** two-factor login and recovery codes (P41), `main` protected
  (no direct pushes), production approval by the owner (alone or with a second person: to decide), the production
  runner limited to deploying.
- **Fork pull requests** (outside contributors, for example the mobile app) never run on our runners automatically
  and never see secrets; their code is deployed to test only after a maintainer brings it into a branch here or
  approves the run.
- **Break-glass:** a written manual deploy and rollback for when GitHub is unavailable.
- **Production-only parts** (route files, DNS, proxy settings) keep the post-release browser and protocol check
  unless the pipeline is taught to check them.
- **Runner upkeep:** runners are updated like any other component (P62 watch).

**Discussion record (owner, 21 November 2026):**
- *Why "Refresh code" at all if releases go main, test, production?* In the normal flow it adds little: after a merge,
  test already runs what `main` has. It matters only when a branch is not merged (rejected, abandoned, or replaced by
  another branch), when test would keep code production will never get. Decision: replace the manual button by the
  pipeline's automatic reset on "pull request closed without merging", then remove the button.
- *Design must not rest on assumptions about where test runs* (owner): test moves to a VPS on 22 November 2026. The
  standard GitHub runner connects out to GitHub, so the design works on any host; a direct GitHub call (webhook) may be
  added on a public host as an extra trigger, never the only one.
- *Owner found the first sketch (polling and scripts of our own) a workaround with too many failure points* and asked
  for standard practice: GitHub Actions with self-hosted runners, deployments recorded on pull requests, a protected
  "production" environment with owner approval, build once and promote that build.
- *What we lose:* nothing functional; trade-offs accepted with mitigations: dependence on GitHub (break-glass manual
  procedure), the GitHub account as a key to production (two-factor, protected `main`, owner approval, limited
  runner), **public job logs** (neutral output plus a leak check), secrets stay on the servers, slower hands-on fixes
  in incidents (break-glass covers emergencies), production-only parts still checked after release, runner upkeep.
- *No reason to wait for the VPS move* to start: only the test runner is host-specific (minutes to reinstall).

**Agreed order of work (when the owner says go):**
1. Pipeline for test: pull request opened or updated deploys the branch to test, deployment recorded on the PR.
2. Reset on close: pull request closed without merging puts test back on `main`.
3. Remove the "Refresh code" button (after step 2 has worked on test), with docs and tests.
4. Central secrets management (scope added 22 November 2026, below): choose the tool, move the secrets, deploys
   read them from it.
5. Production: merge to `main`, same tested build promoted after the owner's approval; rollback by approving the
   previous version; break-glass procedure written.
6. Then review P67, P54 and P59: close or narrow what P71 has taken over.

**Still to confirm at the start:** who approves production (owner alone, or owner plus a second person).

**Scope added (owner, 22 November 2026): central secrets management.** Reason: secrets live as plain JSON in several
places on the servers (private profiles, rendered inputs files, Coolify definitions), the same value in several copies
(the ERP root password was in three inputs files plus the profile, and the profile silently overrides the inputs file),
and four credentials had to be rotated on 21 and 22 November after the agent printed them in a session terminal.
Note: a secrets manager does not stop someone with root on a server from reading secrets; the printing itself is
fixed by a working rule (never print values; recursive redaction; key names or same/different only).
- **Goal:** one place per secret; deploys (and the GitHub pipeline) read secrets from it at deploy time; no secret in
  GitHub, in job logs or in rendered files that are kept; rotation is one documented step per secret; an access log.
- **Options to compare:** (a) **Infisical** (self-hosted: a service with its own database and master key to run, back
  up and secure; access log, rotation, machine identities); (b) **sops with age** (secrets encrypted in the private
  repository, decrypted only on the server at deploy time; no new service; keys on the servers and in the password
  manager); (c) **Bitwarden Secrets Manager** (fits the owner's password manager; hosted). Criteria: what must run
  and be backed up, recovery if the key is lost (P41 recovery essentials), how the pipeline and the existing renderer
  read secrets, cost, audit.
- **Inventory first:** list every secret (ERP database, authentik, Stalwart, Drive, DMS, editor JWT, worker tokens,
  backup password, Coolify, mail relay, test copies) and where each copy lives today; remove duplicate copies.
- **Owner decides** the tool after the comparison; nothing is installed before that.

### P72 — Monitoring and alerting: know when something breaks (on the TrueNAS, watched from outside)

**App:** general · **Also touches:** erp, drive, mail, dms, signin, editor, test-site · **State:** open

**Status as of 24 November 2026:** production and the TrueNAS test VM check each other every minute.
The test VM checks the production Grafana HTTPS endpoint independently, and the VPS checks the
TrueNAS management port. The HTTPS probes report certificates with fewer than 14 days remaining.
Backup and restore-drill monitors check reports immediately after service failure and check freshness
every five minutes (26 hours and eight days). Phone delivery remains deferred by the owner.

Grafana, Prometheus, Loki and Alloy run on the VPS. The TrueNAS VM runs only the two exporters to
leave RAM available on the appliance. Prometheus collects host and container data from both Linux
hosts. Grafana uses tailnet-only HTTPS and a local administrator. Loki retains the VPS probe
journals for seven days. Test restore probe logs remain on the test VM. The production audit runs
weekly and checks Restic metadata, snapshot age and count, configured snapshot paths, processed-byte
changes and app downtime. First run passed with 16 of 16 parts, eight snapshots, and 23.9 seconds
maximum application stop time. Thresholds are 20% for a processed-byte drop and 120 seconds for
app downtime. TrueNAS direct ZFS inspection found seven recent backup-guard snapshots and enabled
cron, two healthy pools and two existing alert destinations.

**Still open:** a separate TrueNAS replication destination and scheduled ZFS freshness checks,
the bucket policy canary and retention/cost trend validation, offline-copy reminders and a combined
weekly report, and centralized test and application logs. P41 already records the quarterly recovery
check due 18 February 2027. Phone delivery stays pending. See the dated handoff and the private
deployment receipts before changing the service. Links: P57, P61, P15, P02/P40, P11.

**Why:** today every check (boot check, restart watch, backup result, hourly mail health, ERP error logs) writes only to
the server's own logs; nobody is told when something breaks at night. Container logs vanish when a container is
recreated (this slowed the 20 November workbook diagnosis).

**Phases (owner agreed the approach):**
1. **Alerts first:** an uptime monitor checking every public site every minute, and the existing boot-check,
   restart-watch, backup and mail-health failures sent to the owner's phone (mail, Telegram or a push app such as ntfy;
   to choose).
2. **Metrics:** Prometheus (node exporter, cAdvisor) and Grafana for disk, memory, CPU and per-container health on
   production, the test VPS and the TrueNAS; alerts for a filling disk, memory pressure, crash loops, certificate
   expiry.
3. **Logs:** Loki with Alloy, so logs outlive container recreation, with a set retention and access limited like the
   servers.
4. **Not Tempo:** the apps produce no traces; it would add load for no gain.

**Backup alerting in detail (owner, 22 November 2026: "do I get alerts if backups are not running as planned?").**
Today: no. The nightly backup (`cloud-backup`, Restic to off-server storage) and the weekly restore drill on the test
host (`restore-drill`, Sunday 05:00) write their results only to their server's log; nothing is sent. Alert on all of:
1. **Missed run, not only a failed run:** each successful backup sends a heartbeat; no success within 26 hours raises an
   alert (catches a timer that did not fire, a server that was down, a job that hung).
2. **Failed run:** an immediate alert with the reason (systemd `OnFailure`), separate from the heartbeat.
3. **Partial backup:** every expected part present in the snapshot (ERP database, Drive data, Mail, DMS database and
   media, sign-in database and media, configuration); a missing part or a size change beyond a set limit (for example
   a sudden drop of more than 20 %) is an alert, even if the job "succeeded".
4. **Downtime during backup:** the time each app was stopped (`stopped_seconds`) above a set limit is a warning.
5. **Restore drill:** a failed drill, or no drill for more than 8 days, is an alert (the drill moves with the test host
   to its VPS); the drill's own checks (every database imports, table counts) stay the proof that backups restore.
6. **Off-server storage health:** a weekly repository check (`restic check`); the bucket's versioning and the rule that
   production cannot delete protected versions verified on a schedule (`harden_storage.py verify` canary, P40); storage
   reachable; space and cost growth tracked.
7. **Retention:** the number and age of snapshots as planned (newest under 26 hours, oldest about 30 days per the
   lifecycle rule); anything outside is an alert.
8. **TrueNAS copies:** ZFS snapshots and replication on the TrueNAS (`zfs-snapshot-guard.sh`) and pool health, through
   TrueNAS's own alerts (see below).
9. **Human reminders:** the offline USB copy (P40) and the quarterly recovery check of the encryption password and logins
   (P41, next due 18 February 2027) as dated reminders.
10. **A weekly summary** ("all backups and the drill passed this week", or what did not), so silence is never mistaken
   for success.

**Watching the watcher (owner question: how can it monitor the TrueNAS it runs on?):** it cannot alone, so
(a) **TrueNAS's own alerts** (SMART, pool health, scrub failures, capacity) are configured to reach the owner
directly, independent of the monitoring stack; (b) a **heartbeat** ("dead man's switch"): the stack checks in with an
outside service or a small check on the production VPS every few minutes, and missing check-ins raise an alert;
(c) **mutual checks over the tailnet:** the TrueNAS watches both VPSs, and the production VPS runs a tiny check that the
TrueNAS answers.

**Constraints:** monitoring never runs only on the machine it watches; Prometheus, Loki and Grafana need roughly
1 to 2 GB of memory plus storage on the TrueNAS; dashboards and alert channels are reachable only over the tailnet;
no secrets in dashboards or alert texts; licences of Grafana, Loki (AGPL) and Prometheus (Apache) recorded; set up from
this repository as a module (stack files, config, README), branch, test, owner go, like every other stack.

**Alert delivery (owner, 26 November 2026, late evening):** the **admin** receives the alerts (no longer only the
owner; phone delivery as decided above), and the person with authentik admin rights also sees alerts and exceptions
in a widget on their Desk (scope added to P53). Who watches daily: the admin (P96, SOP F5). Sign-ins from unusual
places or networks (P82) reach the admin the same way: on the widget, by mail, or both.

**Taken up (owner's go, 27 November 2026), with the admin part of P53: one alert inbox for the admin.**
- **Inbox:** one alert inbox in ERP. Each alert records its source, server, severity, title and detail (no secrets),
  first and last seen, and a repeat count. A repeat updates the same alert. When the problem clears, the alert
  resolves itself.
- **Sources:** every check sends to it through one shared sender, with a separate key per server that can only
  create alerts:
  - boot check and restart watch;
  - HTTPS and certificate probes;
  - backup monitor and audit, and the restore drill;
  - drift check;
  - editor file safety;
  - the upstream watch's "upgrade now";
  - later, P82's unusual sign-ins.
- **Who:** people with the admin role (from the sign-in admin group). Set in the deployment profile, not in code.
- **Desk:** the alerts widget and the monitoring links panel are in P53.
- **Mail (owner: "yes, mail as well as desk"):** at once for serious alerts (a site down, a failed backup, a
  certificate under 14 days), and one daily summary for the rest. It uses P57's alert sender.
- **Fallback:** when ERP is down, the servers mail the admin directly. Production and the test VM keep watching each
  other.
- **Order:** test site first, then production. Follows the working-agreements rule "What every project's system
  has" (4).

**Public draft #134 brought up to date with main (27 November 2026): `ffd4d96`, CI passed, no conflicts.** Its
first test-site run shares one build with #142 (P53), because both change the Desk; it waits for the test host.

### P73 — Federated chat (Matrix or XMPP) in the mobile app, replacing Raven

**App:** general · **Also touches:** mobile, raven, erp, signin · **State:** open · **Category:** long-term plan

**Owner, 27 November 2026, evening: all at once and now.** Production is not in real use yet, so there are no live
chats to move. Raven's removal with the notification service (P108), Matrix chat (P73) and the light mail client
(P109) start now, in parallel. The agent had recommended deciding all together but building the app parts after
attendance and approvals, because the same app developer builds Phase 1 to 3; the owner chose parallel work and
accepts that risk.

**Matrix now (owner, 27 November 2026, evening):**
- **Server: Synapse** with the **Matrix Authentication Service** (MAS) signing in through authentik: the proven
  route for an outside sign-in service (MAS works only with Synapse today). Lighter servers (Tuwunel, continuwuity)
  stay on record as alternatives. Synapse needs about 1 to 2 GB of memory at minimum: check room on the test VM and
  the production server first.
- **App library:** Matrix's Rust SDK through its Kotlin bindings (Apache-2.0). Element X Android's screens may be
  reused (AGPL-3.0-only, compatible with this repository's AGPL; reused files keep their notices).
- **Company rooms unencrypted** so the company can keep, search and export them (record keeping); direct messages
  the same unless the owner decides otherwise.
- **ERPNext bot:** posts document events and approvals into the right rooms, rooms per project or site, people and
  groups from ERPNext and authentik.
- **Server name (owner, 27 November 2026, evening): `chat.<company domain>`**, so addresses are
  `@name:chat.<company domain>`. Chosen over the bare domain (which would tie chat to the website serving two
  well-known files for ever): the chat server stands on its own address, separate and replaceable. The name can
  never be changed afterwards, so production starts on the company domain people keep (P70's split), not the demo
  domain. The test server has its own throwaway name.
- **Chat name (owner, 27 November 2026, night): `firstname.initial`**, with a number on a clash (`asha.d`, then
  `asha.d2`); made once at onboarding, never changed and never reused; addresses are `@asha.d:chat.<domain>`.
  The sign-in user name stays the full mail address (which Matrix does not accept as a name). The sign-in service
  holds the chat name as a user attribute `chat_name` and gives it to the chat sign-in as a claim; without it a
  person cannot sign in to chat. The sign-up service (P82) generates it; until P82 is built it is set by hand.
- **Every new server part gets** monitoring, backups and a test copy from the first deployment (working agreements).
- **Progress (27 November 2026, night):** the stack is public PR #139 (`p73/matrix-stack`, `9890da2`) and runs on the
  test VM since 14:41 UTC (receipt `p73-test-chat-stack-9890da2`), with sign-in set up in the test sign-in service.
  #139 merged at `5f3a897` (14:45 UTC); the production relay carries the two test names since 14:46 UTC (receipt
  `p73-production-test-relay-chat-names-735b117`), so the test chat answers from outside with valid certificates.
  13 test people have a chat name. **Merged, on test only:** production gets a chat stack only on the company domain
  people keep (P70). The owner signed in on test (`@asha.d`). **The business system's bot** (`@erp`, no admin
  token; people join by automatic acceptance of its invitations) is public PR #143, on test since 17:57 UTC
  (receipt `p73-test-chat-bot-92b77c4`), merged as #143 (`2f296e2`). **The room module** (site, team and Notices
  rooms from Field Sites, nothing stored in ERPNext; a team is the supervisor's team at a site) is public draft PR
  #144, merged at `f30c4e2` (18:23 UTC, 27 November; tested commit `3c8aff5`): tried live against the test chat
  server and for four minutes on the test ERP (receipt `p73-test-erp-chat-rooms-3c8aff5`). **Merged, not deployed:**
  the test ERP is back on another session's build (#142) and gets the module with its next build from main;
  production has no chat stack yet (P70). Waiting: the Firebase key for the alert gateway. Not built:
  the push gateway, the ERPNext bot and rooms, monitoring, backups and the drift check for the stack, the production
  route file.
- **First step:** the adoption check (licence, maintenance, security history, how fixes are published) for Synapse,
  MAS, the Rust SDK and the push gateway, recorded in the decision log; then Synapse and MAS on the test site.

**Owner, 27 November 2026 (amends the plan below):** **Matrix**, not XMPP, as the internal chat, built into the
native app (P50) later. Raven is removed from ERPNext **before** this chat exists (P108), so step 4 below becomes "use
the Raven export from P108", and "run both for a period" no longer applies. The app is now native Kotlin, so the
client library to check is Matrix's Rust SDK through its Kotlin bindings (as Element X Android uses it; licence and
maturity to verify), not the React Native packages in the first findings.

**Plan (owner, 26 November 2026; replaces the "idea" below as the goal):** replace Raven with a federated chat
(Matrix or XMPP), built into ERP Mobile as its Chat tab (P50), and retire Raven once the new chat carries the work.
It must keep what Raven gives today inside ERPNext: the same users and roles (authentik sign-in), sharing ERP
documents, document-change and approval messages, and company record keeping.

**What:**
1. **Choose the protocol and server** on the test site: Matrix (servers Synapse, continuwuity or Tuwunel; sign-in with
   authentik through the Matrix Authentication Service) or XMPP (servers Prosody or ejabberd; lighter to run). Compare:
   a usable client library for the app (React Native) under a licence that allows commercial use, sign-in with
   authentik, push to phones (P14), federation, encryption against company record keeping (encrypted rooms cannot be
   archived or searched by the company), retention and export, running cost, security history.
2. **ERPNext integration:** messages for document changes and approvals, sharing a document into a chat, the people
   and groups from ERPNext.
3. **Chat in the app:** the Chat tab, chats per project or site, files through Drive (not stored twice; see P16),
   push.
4. **Move from Raven:** decide whether old Raven messages are moved, archived or kept read-only; run both for a
   period; then retire Raven and close the Raven items it makes redundant (owner decides each).

**First findings (26 November 2026, public sources, not verified):** the community package `react-native-matrix-sdk`
is unfinished and limited to non-commercial use, so it is not usable; the app would use Matrix's official libraries
(JavaScript, or the Rust SDK through native bindings: maturity to check). For XMPP, React Native libraries exist but
are small; check maintenance. **Agent recommendation:** compare both on the test site with the checks in step 1, with
Matrix as the first candidate for its apps, bridges and federation, and XMPP if running cost and simplicity weigh more.

**Owner decisions needed:** federation from the start or later; encryption policy for company rooms; what happens to the
Raven history; priority (the item stays a long-term plan until the owner ranks it).

**Earlier idea (22 November 2026):**

**Status:** owner idea, 22 November 2026; recorded as a long-term plan, not scheduled. Nothing starts until the owner
decides.

**Idea:** Matrix is a federated, open messaging standard: users on different organisations' servers can share rooms.
One day, separate tenants of this platform could talk to each other directly, which the current chat (Raven, inside
one ERP site) cannot do.

**Comparison made on 22 November 2026 (summary):**
- **Raven:** AGPL-3.0, now maintained by Frappe; deep ERPNext integration (same users and roles, share any ERP document,
  document-change messages, AI agents on ERP data); no federation; no end-to-end encryption (company can keep and
  search messages); mobile app younger (iPhone app, Android via app or the v3 PWA); almost no running cost here.
- **Matrix:** open standard (Matrix Foundation) with several servers (Synapse; lighter continuwuity and Tuwunel) and
  very polished apps (Element X, FluffyChat); federation built in; end-to-end encryption by default (privacy, but
  company records cannot be kept or searched in encrypted rooms unless configured); single sign-on with authentik
  needs the Matrix Authentication Service for Element X; group calls need a call server (LiveKit); bridges to other
  networks exist (WhatsApp bridging uses personal accounts: terms-of-service risk); no ready-made ERPNext integration
  (one-way notifications through a webhook bot or n8n); a full new stack to run, secure and back up; federation is an
  internet-facing service; the server software cannot be switched after installation.
- **Recommendation at the time:** keep Raven as the office chat; when federation between tenants becomes a real goal,
  pilot Matrix on the test site (light server, Element X, authentik sign-in) and decide its role (between companies
  only, or replacing Raven); a Raven-Matrix bridge would be custom work.

**To decide when taken up:** the goal (between tenants only, or the default chat), the server software, encryption
policy for company rooms, calls, bridges, where it runs, and the effect on mobile plans.

### P85 — Unformat brand public as the default; client brands supplied privately

**App:** general · **Also touches:** portal, mobile, erp, signin · **State:** in progress

**Progress (26 November 2026):** trademark owner: example.com (owner). Public PR #87 (`p85/unformat-brand`, head
`afd74c4`): `branding/unformat/` (logo, favicons with metadata stripped, `brand.json`), guide and trademark note, the
build's default logo and favicons and the front page's default title and name are Unformat, copyright "Copyright ©
2026 example.com". CI passed (55 suites, client identity clean). Not deployed to test: both sites supply their own
branding (no visible change) and the test ERP runs #77 for the colleague's phone test. **Remaining:** owner merges
#87; then the mobile step (app name, app ID `in.unformat.erp`, icons from `brand.json`), agreed with the colleague
because it touches the mobile module and the test sign-in link scheme.

**Why (owner, 26 November 2026):** about 95% of the work is public and only what licences, copyrights and clients
require stays private. Our own brand, Unformat (name, "UN" logo, favicons, app icon, colours), is published as the
default look; users can always replace it. Clients' brands stay private and are supplied when deploying or building.

**What (owner go 26 November 2026):**
- A `branding/unformat/` folder in the public repository with the logo, favicons, app icon and a brand file (name,
  colours, app ID such as `in.unformat.erp`); builds use it unless a deployment supplies its own (deployment
  profile for the portal logo and favicons, build settings for the app's name and ID, as `mobile/app.config.ts`
  already allows).
- A "Replace the branding" guide in the README.
- A trademark note: the code is AGPL-3.0; anyone shipping it as their own product replaces the name and logo.
- Copyright notice in `README.md` and `LICENSES.md`: "Copyright © 2026 example.com", nothing else (owner,
  26 November 2026), instead of "Unformat and contributors". The public P list rules replace this domain with a
  placeholder, so the public copy of this line shows the placeholder until the rules separate the brand domain from
  host names. Note: outside contributors keep the copyright in their
  own contributions unless they assign it; a contributor agreement would settle that (owner decision).
- Production details that are not branding (host names, addresses, the live sign-in policy and group names) stay
  replaced by placeholders in the public P list.

**Owner input needed:** who owns the name "Unformat" (the owner personally or a company) for the trademark note.

**Acceptance:** a build without private brand settings shows the Unformat brand; a build with a client's profile shows
only the client's brand; the guide's steps work on the test site; the copyright and trademark notes are in place.

**Related:** P84 (client identity), P50 (per-brand app builds), P63 (demo brand), P55 (tenant logo through the
private profile).

**Merged (27 November 2026): public #87 as `f02bf30`** (branch head `486c6d3`, brought up to date with main the
same evening; CI passed). **Merged, not deployed.** It reaches the ERP image (the default logo and favicons in the
build) and the renderer, so the promotion plan asks for a render check of every stack. Both sites supply their own
branding, so no visible change is expected. It goes out with the next ERP release; the mobile app's name and icons
are still a later step.

### P88 — Project camera sites connected to the NVR over the mesh

**App:** general · **Also touches:** mobile · **State:** open

**Why (owner, 26 November 2026):** every project has cameras (outdoor PTZ, at security and elsewhere) that must reach
the remote NVR (P46) over the mesh, so they can be recorded and watched in the app (P87). The test starts with the
Annke camera of the P46 trial.

**Design:**
- **Default:** cameras are wired back to the project's indoor switch; the P48 gateway box carries them to the NVR.
- **Only where a camera cannot be wired back:** an outdoor kit at the camera, powered from the camera's own PoE line:
  Raspberry Pi Zero 2 W with the Waveshare PoE Ethernet / USB HUB BOX (with case; 802.3af, 100 Mbit/s, enough for
  camera streams), a high-endurance microSD card, an outdoor 1-in-2-out PoE extender (IP66, 802.3at on both outputs)
  and an IP65/66 junction box in the shade (heat is the main risk). About ₹5,000–6,500 per camera (Indian listings,
  26 November 2026: Robocraze, Rees52, ThinkRobotics, IndiaMART; agent estimate).
- **PoE power budget:** PTZ cameras usually need 802.3at (about 25 W) or more with heaters or IR; the switch port must
  supply the camera, about 2–3 W for the Pi and the extender's loss; otherwise an 802.3bt port or a separate feed.
- The NVR site is on the mesh itself (P46).

**Not known yet (owner, 26 November 2026):** the number of cameras per project and how many can be wired back; counted
per project at each site survey, which then gives that project's parts list.

**Order:** the Annke test with P46; then one outdoor kit with one camera and the NVR; then per-project rollout.

**Acceptance:** a camera behind the gateway box and one behind an outdoor kit record on the NVR and play in the app;
the kit survives a hot day in its box (temperature logged).

**Related:** P46 (NVR), P48 (gateway box), P29 (Headscale), P87 (videos in the app), P72 (monitoring).

### P90 — Traefik security upgrade: pin Coolify's proxy to 3.7.20

**App:** general · **Also touches:** none · **State:** in progress

**Why (upstream watch, P62; owner "sort out traefik", 26 November 2026):** GHSA-3rh5-223h-cpwr (high, unauthenticated
memory exhaustion in the Compress middleware) plus two medium advisories affect Traefik 3.7.19, the public proxy in
front of every site; 3.7.20 fixes them. Coolify's moving `traefik:v3.7` tag made the running version depend on the last
pull.

**Done:** public PR #91 (`p90/traefik-3.7.20`, head `6ee9201`): pin file, `tools/coolify_proxy_image.py`, tests; CI
passed. Test VM pinned and restarted 26 November 14:09 IST: 3.7.20 running, networks kept, 7 hosts unchanged
(receipt `p90-test-traefik-3-7-20-6ee9201`); upstream watch profile set to 3.7.20.

**Production (26 November 14:22 IST, from the owner's Mac):** #91 merged (`45c2ec0`); production was on 3.7.19 (moving
tag); `--restart` from main `45c2ec0`: 3.7.20 running, network kept, 18 hosts unchanged on the server and from outside,
compose differs only in the image line (receipt `p90-production-traefik-3-7-20-45c2ec0`; rollback
`<rollback folder>`; production releases, 26 November).

**Remaining:** owner's browser check of the main sites; then move to the 3.8 line once it has a patch release (3.7
reached end of life 23 November).

### P89 — Register of our changes to upstream apps, and an upgrade checklist

**App:** general · **Also touches:** erp, portal, signin, drive, editor, mail, dms, raven, mobile · **State:** in progress

**Why (owner, 26 November 2026):** we customise many upstream apps (build-time patches, hook overrides, menu and
style overlays on their screens, proxy rules, objects created in admin screens, workarounds for their bugs). The
records are spread over the decision log, the retained record, handovers and the code, so nobody can see in one place
what must be re-applied or re-checked when an app is upgraded. Changes easily get lost, especially settings made by
hand that no code reproduces.

**What (owner go 26 November 2026):**
- Public `docs/upstream-customizations.md`: an upgrade checklist, then one entry per change grouped by upstream app:
  what and why, how it is applied, files, the version it was made against, the upgrade action (**re-apply**,
  **re-check** or **none**), how to test it, the upstream issue link and whether it is a workaround to retire.
- Private companion `docs/upstream-customizations-private.md` here: the parts that need host names, server paths,
  client identity or live object names (manual live settings, the client brand). It links to the public entries and
  does not repeat them.
- Rule in the public `AGENTS.md`: a pull request that changes or starts depending on upstream behaviour updates the
  register in the same pull request; an upgrade (a version change in `deployment/upstream-lock.json` or an image pin
  in `deployment/upstream-watch.json`) walks that app's entries and records the result in the pull request.
- Same rule for every project in the working agreements.
- First version built from the code, the decision log, the retained record and the private records; anything not
  confirmed from them is marked "to verify", not guessed.
- Not now (owner agreed with the recommendation): a CI check that warns when a pull request touches the patch or
  override files without the register; take it up once the register has settled.

**Acceptance:** every build-time patch, hook override, screen overlay and known manual live setting has an entry with
an upgrade action; the next upgrade pull request uses the checklist; the rule is in both instruction files.

**Related:** P62 (upstream watch: its `workaround` fields point to register entries), P59 (promotion plan and drift
check), P84 (no client identity in the public register).

**Upstream posts (26 November 2026, owner go; account rdavuluri44; now tracked in the public list, P35):**
- owncloud/ocis#3832 comment: https://github.com/owncloud/ocis/issues/3832#issuecomment-7186892628
- ONLYOFFICE/DocumentServer#3954: https://github.com/ONLYOFFICE/DocumentServer/issues/3954
- coollabsio/coolify#12667: https://github.com/coollabsio/coolify/issues/12667
- frappe/frappe#48437 comment (`?cmd=` on any path; not a Frappe vulnerability, hardening): https://github.com/frappe/frappe/pull/48437#issuecomment-7186893154
- shridarpatil/frappe_whatsapp#257 comment (already public with an open fix): https://github.com/shridarpatil/frappe_whatsapp/pull/257#issuecomment-7186893657
- goauthentik/authentik#16049 comment: https://github.com/goauthentik/authentik/issues/16049#issuecomment-7186894135
- goauthentik/authentik#14304 comment: https://github.com/goauthentik/authentik/issues/14304#issuecomment-7186894885
- goauthentik/authentik#28187 (authenticatorAttachment to policies): https://github.com/goauthentik/authentik/issues/28187
- goauthentik/authentik#28188 (per-user session limit): https://github.com/goauthentik/authentik/issues/28188
- **Private** frappe_docker advisory report GHSA-2qf7-29hw-ch4q (Origin overwrite disables Frappe's realtime Origin
  check; severity low; state triage): https://github.com/frappe/frappe_docker/security/advisories/GHSA-2qf7-29hw-ch4q
  (do not link from public files).

**Progress (26 November 2026):** first version written, 102 public entries and the private companion; rule added to
both instruction files. Public PR #86 (branch `p89/upstream-customizations`), private PR on the branch of the same name,
working-agreements PR on `upstream-customization-register`. Open questions found are listed at the end of the public
register and in the handover; none of them is changed by P89.

### P91 — Upgrade checks that cannot miss a changed upstream file; upstream watch gaps

**App:** general · **Also touches:** erp, editor, mail, signin, drive, dms · **State:** in progress

**Why (found 26 November 2026, P89):** some of our patches are applied in a way that an upgrade can silently
undo: six of the seven text replacements on frappe_docker's Containerfile and two replacements in the Insights
patch do nothing when the upstream text changes; the ONLYOFFICE patched start page is checked only against our stored
copy of the original, not against the file in a newly pinned image, so an image bump alone passes CI; the webmail
overlay is not tied to its base commit. The upstream watch has `workaround` notes only for Insights, Bulwark and
ONLYOFFICE, and does not watch the six monitoring images.

**What (owner go 26 November 2026):**
- Every Containerfile replacement and every Insights replacement must find its target or stop the build.
- ONLYOFFICE: a record ties the stored original start page to the image digest; CI fails when the digest changes
  without the record; a tool extracts the original from a new image during an upgrade.
- Webmail: the upstream checksum of every file we replace is recorded against the pinned commit; CI fails when the
  commit changes without the record; a tool refreshes it from a clone.
- Upstream watch: `workaround` notes for authentik, oCIS, Stalwart, Paperless, Coolify, Traefik and Tailscale
  pointing at register IDs; the monitoring images added.
- Register entries updated in the same pull request.

**Release (owner, 26 November 2026):** the generated build files are shown byte-identical before and after, instead
of a test-site rebuild; nothing that runs changes.

**Acceptance:** each check fails on a deliberately changed upstream text, digest or commit and passes on the pinned
one; build output byte-identical; watch tests pass.

**Related:** P89 (register: BUILD-1, INSIGHTS-1, OFFICE-1, WEBMAIL-1), P62 (upstream watch).

**Progress (26 November 2026):** built in public PR #88 (`p91/upgrade-checks`, `78e0142`), CI passed. Byte-identical
proof: generated Containerfile sha256 `8c97d70cdb34` before and after; patched Insights 3.50.3 sources identical; the
ONLYOFFICE original equals the start page extracted from the pinned image on the test VM (stopped container, removed);
the webmail base check passes on a clone of the pinned commit. The ONLYOFFICE version (P92's item) was corrected here.
Waiting for the owner's merge (after #86).

### P92 — Out-of-date Collabora material, ONLYOFFICE version, WhatsApp entry, hosting provider's name

**App:** general · **Also touches:** editor, drive · **State:** in progress

**Why (found 26 November 2026, P89):** Collabora was retired with P42, but the Drive and deployment READMEs still
tell readers to deploy it and the office ingress still guards Collabora admin paths; the ONLYOFFICE version is
written three ways; the decision log describes a WhatsApp wrapper that was never built; public `docs/retained.md`
names the hosting provider, which the P list rules treat as private.

**What (owner go 26 November 2026):** remove the Collabora instructions; guard ONLYOFFICE's own admin paths if
version 10 has any, otherwise remove the old rule (ingress change: through the test site); one verified ONLYOFFICE
version everywhere; a correction note in the decision log (the wrapper is planned under P04, not built); replace the
provider's name in `docs/retained.md` and add it to the automatic identity check. Git history left as it is (owner).

**Acceptance:** no Collabora deployment instructions remain; office admin paths refused on test; one version string;
the identity check fails on the provider's name.

**Related:** P89, P84 (identity check), P42 (editor change), P04 (WhatsApp).

**Progress (26 November 2026):** public PR #90 (`p92/stale-material`), CI passed. On the test VM (read-only): ONLYOFFICE 10
has no admin panel; `/info` and `/internal` return 403 through the test proxy (ONLYOFFICE's own localhost rule; no
real-IP trust), `/welcome/` returns 200. The provider's name is in `tools/client-identity-terms.private.txt` and its
fingerprint in the public `.client-identity-fingerprints`. Still to do: deploy the test ingress from the branch and run
the checks in the PR (needs a test-site slot, owner).

### P94 — Bring production stacks back in line with main

**App:** general · **Also touches:** editor, signin, portal, test-site · **State:** open

**Why (owner, 26 November 2026, splitting the stack releases off P59):** after today's drift check, four stacks are
behind main: merged changes were never released for them. The same check found dms, processing and private-dns on
revisions from the pre-publication repository; a read-only comparison showed them identical to main in substance, and
their recorded revision was re-linked to `33499fd` (receipt `p94-production-relink-dms-processing-dns-33499fd`; the
unrecorded dms render is incident `incident-dms-unrecorded-render-fdf4a43`).

**Per stack (each a normal release: promotion plan, test, rollback point, quiet moment, drift check clean after):**
- **editor:** behind main (5 files, e.g. `deployment/stacks/editor-onlyoffice.compose.json`); release together with
  P61's editor fixes (PR #34, #42) and safety tool.
- **identity:** behind main (8 files, e.g. `deployment/stacks/identity.compose.json`).
- **identity-support:** behind main (18 files, e.g. `deployment/stacks/inputs.json`).
- **website:** behind main (3 files); with the P85 brand defaults once #87 is merged (production supplies its own
  branding, so no visible change).

- **mail (found 26 November 2026, night):** behind main by 2 files plus the three rendering tools: P91's build-time
  webmail check (`tools/prepare_mail.py`, `integrations/mail/upstream.json`). It changes no running file: same
  webmail commit and customisations, and the check passes against the pinned commit. Main's
  `deployment/stacks/mail.compose.json` equals the released `bb546d7` (Stalwart 1.1.1). A render from `bb546d7`
  and from main with neutral sample values gave the same mail definition (only the per-render generated values and
  the output path differ) and the same mail policy file. **Owner's go for a re-link:** script
  `deployment/promotion/p94/relink-mail.sh <main sha>`. It reads the recorded commit, stops unless only those six
  files changed, saves the note, updates it guarded by the old value and reruns the drift check. **Done** (27 November
  2026, 01:07 IST, from the Mac session with production access, owner's go): note set from `bb546d7` to main `9f1116a`
  (main had moved on from `915228c` by P57 merges that touch no mail file); exactly the six expected files; nothing
  restarted. Drift check: **mail clean**. Receipt `p94-production-relink-mail-9f1116a`.

**First step for each:** run the promotion plan from the stack's recorded revision to main and list what users would
notice. **Order:** owner decides. **Acceptance:** the nightly drift check is clean for every stack.

**Rule (working agreements, 26 November 2026):** a merge is not a release; merged changes stay listed as "merged, not
deployed" until released.

**Progress (26 November 2026, afternoon):** website re-linked after a render comparison showed it identical (receipt
`p94-production-relink-website-33499fd`). Evaluation of the rest (file checksums against the running containers):
**identity** already runs main's authentik 2026.8.7 pin (the P83 image change left the Coolify note at `288993c`);
still pending from PR #72 are the email wording and the first-administrator tool. **identity-support:** the invitation
page differs from main (PR #72). **editor:** the editor page differs from main (P61, PR #33, #34, #42). The identity
stacks have no copy on the test site (it signs in through production's authentik), so their release is tested on a
throwaway authentik first, then applied to production at a quiet moment (authentik restart, install scripts).
Follow-up: release steps must update the Coolify "Source commit" note automatically (the P83 slip).
**Related:** P59 (tools, closed), P61, P85, P90.

### P96 — SOPs for every manual procedure, written alongside the build

**App:** general · **Also touches:** signin, mobile, erp, portal, drive, editor, mail, dms, raven, test-site · **State:** in progress

**Why (owner, 26 November 2026):** the systems we are designing rely on people doing checks that no code enforces
(for example removing a family member's fingerprint from a phone, or bulk onboarding a field team with one good
phone). These need written standard operating procedures, kept up to date as the design changes. The SOP work runs
in parallel with the build, not after it. The rule is also in the working agreements (all projects).

**What:**
- **Study first:** go through the decision log, the P list, the handovers and the runbooks, and list every step
  that needs a person to act or check.
- **One SOP per procedure:** purpose, who does it (by role: project manager, admin, HR, supervisor, owner), when,
  what they check, what they record and where, and what to do when it goes wrong.
- **Where:** the public repository holds the SOPs in `docs/sop/`, written for roles, not named people; the private
  repository holds the client-specific parts (names, contacts, sites).
- **Kept current:** every change that adds or alters a manual step updates its SOP in the same pull request.

**First SOPs already known:** project manager's identity check at onboarding; confirming the phone holds only the
person's own fingerprints and face, and removing family members'; re-onboarding after a lockout or erase; new, lost
or replacement phone; bulk onboarding of a field team with one good phone (P95); the consent agreement and its
withdrawal; leavers (remove the key, delete face data); exception group membership (Apple); the project manager
clearing offline queues and uncertain matches; attendance approval; the owner's emergency sign-in link; admin
approvals in authentik.

**Acceptance:** every manual step found in the study has an SOP or is listed as deliberately left out with a reason;
the owner reviews the first set.

**Related:** P82, P95, P24, P50.

**Progress (26 November 2026):** study done (decision log, P list, READMEs, runbooks, private records): 69
procedures in ten areas and 18 gaps, published as the inventory in public `docs/sop/README.md` (PR on branch
`p96/sop-first-set`), with the template and the first two SOPs (ERP Mobile onboarding; face enrolment and consent),
both drafts that apply when built. Next: the gaps that need owner decisions, then the in-use procedures.

**Second set (26 November 2026, night; public PR on `p96/sop-second-set`):** three SOPs for procedures in use
today (invite a user; approve field attendance; release a change to production) and two for the settled gaps (when
someone leaves, as a draft manual checklist until the automatic part of P82 is built; alerts and daily checks for
the admin). Seven inventory rows now link to an SOP. Open points for the owner are listed in the leaver SOP (personal
files, the leaver's mailbox, where the checklist lives) and in the invitation SOP (the identity check before a
recovery invitation). Still to write: the remaining in-use procedures (inventory rows without a link).

**Owner decisions of 26 November 2026, night (in the SOPs and the decision log):** recovery of a lost passkey only
after the project manager checked the phone in person and confirmed in their app (until built: confirmed to the
admin); leavers' personal files stay, and mailboxes are shared so nothing is redirected; rejected face captures
keep their photograph for 30 days. Still open: who may open a leaver's files and for how long; where the leaver
checklist and the admin's daily line are recorded.

**Owner decisions on the gaps (26 November 2026, late evening):**
- **Leavers:** the exit procedure in Frappe HR triggers removal of keys and purges all the person's data in the app
  (P82, P95); SOP A14 to write.
- **Where the biometric confirmation is kept, and the consent text and languages:** the agent prepares a proposal.
  Prepared 26 November: the confirmation is given in the app with the employee's fingerprint and the project
  manager's tick, stored by the sign-up service with the access request, kept while employed plus 3 years
  (onboarding SOP); the face attendance agreement draft 1 is in public `docs/sop/face-attendance-agreement.md`,
  for the lawyer. **Languages:** a proposal is in the private handover of 26 November (it names the region);
  translations by a qualified translator, each checked by translating back. Owner to confirm.
- **Monitoring:** the admin receives the alerts; the person with authentik admin rights also sees alerts and
  exceptions in a Desk widget (scope added to P53).

**Status:** in progress.

### P102 — Admin tools: single sign-on by default, the tailnet as the backup door

**App:** general · **Also touches:** signin, test-site · **State:** open

**Why (owner, 27 November 2026):** easy everyday access to the admin tools, and a way in when the sign-in service
(authentik) is down. This follows the working-agreements rule "What every project's system has" (3).

- **Two doors per tool:**
  - single sign-on for the admin group;
  - one local administrator account, reachable only over the tailnet, with its password in the owner's password
    manager.
- **Tools:**
  - Grafana (built-in SSO);
  - Coolify on production and on the test VM (its own sign-in options; otherwise an SSO gate in front);
  - TrueNAS (if it has no SSO for its screens: an SSO gate on one address, the direct tailnet address with its local
    admin as the backup);
  - Frigate (an SSO gate in front; the direct tailnet address as the backup).
  - The test VM's SSH keys stay as they are.
  - Check each tool's current SSO support before building.
- **Rules:**
  - admin tools are never published on the internet, even with SSO;
  - the tailnet's own login never depends on authentik (also when Headscale replaces hosted Tailscale, P29);
  - the backup door is tried at every quarterly recovery check (P41), with an SOP.
- **Order:** after the admin alerts (P72 with P53); one tool at a time, test first.


### P107 — User support: "Report a problem" in the apps, and an admin support desk

**App:** general · **Also touches:** erp, mobile, portal, signin · **State:** parked

**Status:** parked by the owner, 27 November 2026 ("we'll take this up later"). Nothing is built or decided beyond the
owner's decisions below. Do not start until the owner says.

**Why (owner, 27 November 2026):** support users without a remote-control tool. The owner first asked whether
RustDesk (a free server with single sign-on) would help, then chose help built into the apps. Admin work has grown
beyond a few Desk widgets: the admin needs one place to receive user problems, organise and track cases, keep a
record of finished ones, and reach server alerts and logs.

**Owner decisions (27 November 2026):**
- **No RustDesk.** No paid tool ("paying is not an option").
- **Not every user can be on the tailnet.** Field phones and some users stay off it.
- **Help built into the apps is the way forward**, on the phone app and on the web app (desktops).
- **An admin app is needed** for user complaints as well as server logs and alerts, "instead of just a few widgets
  over the Desk".

**What was found (research of 27 November 2026; re-check before taking this up):**
- **RustDesk** (rejected by the owner):
  - the free server (`hbbs`/`hbbr`, AGPL-3.0, version 1.1.16) only connects and relays devices: no user accounts, no
    web console, no single sign-on, no audit log, and no documented browser client;
  - single sign-on (OIDC) needs Server Pro "Basic", USD 23.88 a month billed yearly (10 staff, 100 devices);
  - the browser client needs a plan with (staff × 10) + devices of 400 or more ("Customized", about USD 48 a month,
    our own sum);
  - commercial use is allowed (AGPL-3.0; Pro is licensed for internal business use);
  - Android can be controlled (screen-capture and input permissions, granted again at every start); iPhones can only
    control;
  - 2026 security record: a batch of client CVEs in March (CVE-2026-30797 rated 9.3, some later lowered or
    withdrawn), CVE-2026-57850 (fixed in 1.4.9), CVE-2026-58056 (fix not confirmed), CVE-2026-131827 (Windows local
    privilege escalation, November, fixed);
  - its server ports (21115 to 21119) would have to be public for users off the tailnet.
- **Alternatives looked at** (not chosen):
  - MeshCentral: Apache-2.0, free, OIDC with authentik, browser-based for the helper. 1.3.1 (October 2026) was an
    urgent security update, released while servers were being actively attacked. Its server would have to be public
    for users off the tailnet. Android agent abilities not confirmed.
  - Apache Guacamole: Apache-2.0, browser-based RDP, VNC and SSH, OIDC (implicit flow). Suited to reaching servers,
    not to helping users; no phones; last release 1.6.0 on 22 June 2025.
- **Phones:** no remote-control app on workers' phones. Remote input on a phone that holds the ERP Mobile passkeys
  (P82) could approve things in the app, and the phones may be personal.

**What (proposal, to settle when taken up):**
1. **"Report a problem" in the native Android app (P50):**
   - a screenshot of the app's own screen (no special permission; other apps are never captured); the user sees it
     and can blur parts before sending;
   - diagnostics, shown to the user before sending:
     - app version, Android version, phone model, network type, offline or not;
     - the current screen;
     - the last request IDs and their results (P103);
     - the data-flow tracker state (P50 Phase 0);
     - saves waiting to upload;
     - a short app log with personal values removed;
   - never sent: passkeys, sign-in tokens, passwords, face images or location history;
   - sent with the user's own sign-in; queued when offline; a crash report offered at the next start.
2. **"Report a problem" in the ERP web app (desktops):**
   - in the Desk help menu: page, record, browser, user, recent browser errors, request IDs;
   - the server adds its own error log entries for that user and time;
   - screenshot: the browser's own "share this tab" prompt (recommended; accurate, no new library), with paste or
     attach as a fallback; a page-redrawing library is not recommended (inaccurate, a new dependency);
   - apps we did not write (Drive, the editor, webmail, DMS): no button inside them; the same form in ERP with a
     choice of app, and a support mail address that opens a case; their server logs come from Loki.
3. **The admin support desk: Frappe Helpdesk** (recommended over building our own):
   - free and open source (AGPL-3.0 on the repository page; licence file not yet read), no paid self-hosted edition,
     same framework as the ERP; a version-16 branch, v16.2.2 released 25 November 2026;
   - an agent screen, a portal where users follow and reply to their case, statuses, assignment rules, response and
     resolution targets, saved replies, a knowledge base, analytics;
   - advisories: GHSA-xf93-jjcj-44vm (moderate, fixed in 1.26.0, September 2026); a breaking change in 1.31.1 fixed
     agent-only fields set through the REST API; the install page still names the old `main` branch, so install the
     version-16 branch;
   - alternative on record: ERPNext's built-in Issue (statuses and response targets, a weaker agent screen, no user
     portal).
4. **Case flow:**
   - a report becomes a ticket, with the screenshot as a private attachment and the diagnostics stored with it;
   - the server adds its error log entries for the request IDs and a Grafana or Loki link filtered to that user,
     time and request;
   - assignment by app or type, with repeats grouped;
   - the admin replies inside the ticket, and the user is told in the app and by mail;
   - a bug is linked to a P item or a public issue with personal details removed;
   - resolved, then closed, and kept as the record; analytics show what keeps going wrong.
5. **One admin home: an "Operations" workspace in the ERP Desk for the admin role:**
   - user cases (Helpdesk);
   - system alerts (P72, public #134); critical alerts can also open a case;
   - links to Grafana, Loki, TrueNAS, Coolify and Frigate;
   - logs and metrics stay in Grafana and Loki, tailnet-only (P102), and are not copied into the public ERP;
   - later, an admin section in the native app for alerts and cases.

**Decisions for the owner when taken up:**
1. Case system: Frappe Helpdesk (recommended), ERPNext Issue, or our own.
2. Whether critical system alerts also open a case (recommended: yes).
3. The web screenshot method (recommended: "share this tab", with attach as a fallback).
4. How long screenshots and diagnostics are kept after a case closes (suggested: 90 days for attachments, case text
   kept).
5. Who handles cases: admin only, or also first-line helpers (HR for HR questions, supervisors for field problems).

**How it is tested (when built):**
- on the test site, report from a phone and from a desktop browser;
- check that the ticket holds the screenshot and diagnostics and that nothing listed as "never sent" appears;
- check that the server's evidence and the filtered log link are added;
- reply, resolve and close, and check what the user sees;
- check that a non-admin cannot see other people's cases.

**Depends on / with:**
- P103 (request IDs) first; P50 (native app);
- P72 and public #134 (alert inbox); P53's admin part (becomes the Operations workspace); P102 (admin tools
  tailnet-only).

**When taken up:**
- the adoption check for Frappe Helpdesk (licence file, maintenance, security history) in the decision log and the
  open-source list;
- a row in the working-agreements stack table (support desk);
- SOPs for handling a support case and for screenshot privacy (`docs/sop/`).

### P108 — Remove Raven from ERPNext; all messages through our own channels

**App:** erp · **Also touches:** raven, mail, mobile, portal, signin, general · **State:** open

**Owner, 27 November 2026, evening: all at once and now.** Production is not in real use yet, so there are no live
chats to move. Raven's removal with the notification service (P108), Matrix chat (P73) and the light mail client
(P109) start now, in parallel. The agent had recommended deciding all together but building the app parts after
attendance and approvals, because the same app developer builds Phase 1 to 3; the owner chose parallel work and
accepts that risk.

**Why (owner, 27 November 2026):** the phone app holds the person's key, and sharing it with Raven's and a mail app's
own phone apps is not possible. The owner's plan: (1) no Raven and no mail in the phone app for now; (2) remove Raven
from ERPNext and send every message through our own channels: mail, WhatsApp (P04) and an SMS gateway; (3) later,
Matrix chat (P73) and a light mail client (P109) inside the app.

**What:**
1. **One notification service in our ERP add-on:** every message the system sends to a person (approvals, document
   changes, attendance, incidents, alerts) goes through one function that picks the channel by the person's
   preference and the message's urgency (in the app and phone alert, mail, WhatsApp, SMS), sends each event once,
   records what was sent and delivered, and follows the test-site safeguards (allow list, test marker). P72's alert
   inbox and P22's notifications use it rather than their own senders.
2. **Replace what Raven does today:** Raven document notifications (P22 step 1) become ERPNext notifications through
   the service; incident reports that were to go to Raven threads (decision of 22 November) go to Matrix rooms
   (owner, 27 November; see below).
3. **Remove Raven:** from the ERP image and app list, the portal's app frames, onboarding's app rules, the phone menu,
   the Raven proxy route, tests and documents. **Keep the phone sign-in check** (`portal/mobile.py`): it was written for
   Raven but now signs in every phone app, ours included; rename its settings (`cloud_raven_mobile_enabled`,
   `cloud_raven_mobile_client`) on test and production in the same release.
4. **Raven's data:** uninstalling Raven deletes every message, channel and attachment record for good. Count them on
   production first (read-only, with the owner's OK), then export to Drive as a read-only archive or let them go
   (owner decides). Keep the export until P73's retention rule is set.
5. **Test site first** (uninstall, all checks, the phone app still signs in), then production at a quiet moment with a
   backup.
6. **SMS gateway:** sending SMS to Indian numbers needs DLT registration (the company, a sender name and every message
   template) with a telecom operator, and costs per message. Choose a provider after the licence and adoption checks;
   use SMS only where WhatsApp and mail do not reach.
7. **For the phone app (owner, 27 November 2026, night; public #114):** every message carries its kind ("needs a
   decision" or "informs"); a "what waits for me" call (per kind: count, longest wait, nearest deadline); a
   content-free "remove this alert" signal when something is decided anywhere; a reminder for a waiting decision
   every 4 hours between 07:00 and 21:00 only, counted by the server; approvals themselves alert round the clock; a
   per-site summary.

**Settled (owner, 27 November 2026, evening):** no gap to manage and no history to export, because production is not
in real use (count Raven's messages on production before uninstalling all the same, read-only). **External messages:**
mail, forms (the Respond app and ERPNext web forms) and WhatsApp (P04); SMS only where those do not reach.

**Progress (27 November 2026):** part 1, the removal, is public PR #138, merged at `86d5cd9` (13:59 UTC; tested commit
`5cc6d1a`, later commits documents only). On the test ERP since 13:52 UTC on a new core image without Raven (receipt
`p108-test-erp-remove-raven-5cc6d1a`). **Merged, not deployed** to production: it needs a new core image there, the
uninstall with the old image first, the config keys and the proxy files, at a quiet moment (decision log, 27 November).
Not yet built: the notification service (part 2); the SMS gateway choice.

**Incident reports go to Matrix (owner, 27 November 2026, evening):** the person picks one or more rooms, as the
22 November design did with Raven threads; the photos (and later clips, P106) still go to the project's Drive
through ERPNext (P74) and the room message links to them. Reason: the long-term plan is not to use ERPNext for
everything; modules stay separate and replaceable. The agent had proposed ERPNext records; it noted that chat
does not track whether an incident is open or closed, so a small separate incident tracker can be added later
if that is needed.

**Closes when done (owner decides each):** P16 (Raven attachments); the Raven parts of P14; the "Raven Mobile" client
question in P64; P22's "Raven inside the company" channel.

**Related:** P73 (Matrix), P04 (WhatsApp), P109 (mail in the app), P22, P72, P107, P50.

