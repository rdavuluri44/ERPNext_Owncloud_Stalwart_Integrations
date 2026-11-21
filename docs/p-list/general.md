# General: P items

> **Generated file: do not edit by hand.** Published from the maintainers' private list on 21 November 2026
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

