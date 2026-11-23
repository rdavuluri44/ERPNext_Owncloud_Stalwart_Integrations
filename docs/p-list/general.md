# General: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 22 November 2026
> with every line kept; only identifying names, addresses, paths and links to private records are
> replaced by placeholders (see the [P list index](../p-list.md) for the rules).

# General: P items

Platform, infrastructure, release process, backups, network and security items that do not belong to a single app.

Part of the P list: back to the [index and priority order](../p-list.md). Items are numbered across the whole project; a new item goes into the list of the app it belongs to (or `general`), and `python3 tools/p_index.py` refreshes the index.

### P11 — Certificate issuance and renewal acceptance

**App:** general · **Also touches:** none · **State:** open

**Status:** current HTTPS validation passes; ERP/SSO automation is configured, but renewal/individual issuance has not been accepted.

ERP, SSO, Drive and Respond currently present certificates expiring **30 January 2027**. Confirm the active renewal mechanism covers all four names, issue/renew through the intended configuration, and verify the served certificate afterwards. Office, Mail and DMS currently have February 2027 expiries. Do this before the January expiry; no reminder has been scheduled.

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
kept in the old private repository, renamed `the private operations repository` and
now the internal operations repository (full history kept; deploy keys
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

**App:** general · **Also touches:** none · **State:** open

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


### P59 — Promotion plan and drift check: no stack left behind

**App:** general · **Also touches:** none · **State:** open

**Status:** open, owner request 21 November 2026 ("add a P for this and we'll do it
again"); not started. **Why:** on 21 November the production ERP swap for `3a93de8`
missed the website stack (Employee Zone single-click fix): the test deploy script
re-renders every stack, but production stacks are promoted by hand from separate
profiles (ERP in `p37`, website, Drive, Mail, DMS and identity in `p45`), and nothing
says which stacks or live settings a merged change reaches. It was caught only because
the assistant checked afterwards, and an earlier statement that one ERP swap carried the
fix was wrong. The same release also had manual pieces outside the image (bootstrap
step, live authentik brand), and PR #12 adds an ONLYOFFICE restart.

**To build (branch, test, merge, production):**
1. `tools/promotion_plan.py <from> <to>`: from `modules.json` and the stack ownership,
   list every stack, bootstrap step, live setting (authentik brand, flows) and restart
   that the changed files reach, and what cannot be covered by test. The pull request
   must carry this list before merge.
2. Drift check on production (`tools/` plus a nightly timer, like the host checks in
   P57): compare the commit each stack runs (ERP image tag, website/Drive/Mail/DMS/
   identity profile commits and registered definitions) with `main` for the files it
   owns; report any stack that is behind, and fail loudly. Run it after every promotion
   and nightly. Include a check that served content matches (for example the landing
   page script and the ERP favicon hash).
3. `AGENTS.md`: a promotion is not finished until the drift check is clean, plus a
   `docs/decisions.md` entry (what and why).
4. Keep the nightly image cleanup from deleting `erp-core` (a rebuild costs about 20
   minutes at every ERP release): tag-protect it or build the add-on from a pinned
   copy.
Related: P57 (reboot and post-boot checks), the release checklist in
`docs/production-moves.md`.

### P62 — Daily upstream watch: new releases, security flaws, patches, upgrade decisions

**App:** general · **Also touches:** none · **State:** open

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

**Status:** owner decision 22 November 2026; not started; placed on the **TrueNAS home server after the test machine
moves to its VPS**. Links: P57 (boot check and restart watch feed alerts), P61 (logs must outlive container
recreation), P15 (mail health), P02/P40 (backup results), P11 (certificate expiry).

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

### P73 — Matrix as federated messaging between tenants

**App:** general · **Also touches:** none · **State:** open · **Category:** long-term plan

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

