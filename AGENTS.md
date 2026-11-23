# Mandatory development and release policy

This policy is nonnegotiable and applies to every contributor and automation
working on this deployment.

The isolated test site is a permanent part of the system. Every development
change must follow this order:

1. Implement and commit the change in this repository, then push it to GitHub.
2. Deploy the pushed revision to the permanent isolated test environment.
3. Validate the change there, including affected integrations and regression
   checks. Record the tested commit, results and any remaining limitations.
4. Only after successful test validation, promote that same tested revision
   and its versioned deployment definitions to production.

In branch terms the rule is: **branch → test → merge → `main` → production**.
Work happens on a branch (a fork for outside contributors). That branch itself
is deployed to the test site and validated there, and the tested commit is
recorded. Only then does the owner merge it to `main`, and production receives
that same tested content from `main`, never from a branch. The unit tests and
repository checks are a gate before the test deployment, not a substitute for
it. Unit tests may fake Frappe and outside services, but import the project's
own modules for real (never a fake copy of them); the repository check refuses
an import of a module or name that does not exist (P68). Files that exist only in production (route files, port bindings, host
entries) cannot be exercised on the test site: for them, record a browser and
protocol check of the affected apps immediately after promotion, and say in the
release record that test could not cover them. GitHub cannot verify that a
branch was tested, so the written record in the pull request is the control:
the owner merges only when it is there.

Do not develop directly in production, deploy uncommitted changes, bypass the
test environment, or copy undocumented runtime patches into production. If a
test exposes a defect, fix it in the repository and repeat the sequence. This
also applies to urgent fixes, menu/CSS changes, configuration templates,
integration adapters and database migration code.

Keep environment-specific secrets and business data outside Git. Use separate
test credentials and the documented outbound-integration safeguards. Data
refresh is strictly one-way from production to test; never restore test data
into production. Retain the refresh completion timestamp on the test portal.

Before production promotion, retain a rollback point and document the exact
revision being promoted. Update the repository documentation whenever retained
behavior or deployment procedures change. An unavailable or failing test
environment blocks production promotion until it is restored and validation
passes.

Every pull request carries its promotion plan (`tools/promotion_plan.py`: the
stacks, steps, live settings and restarts the change reaches, and what the test
site cannot cover). A promotion is not finished until `tools/drift_check.py` on
production reports every stack clean for the promoted commit.

# Working agreements for every agent (owner, 22 November 2026)

The owner keeps general rules for all AI-assisted work (any project, any agent or model) in a
private repository; agents working here follow them. The essentials, binding in this repository:

1. **No change of any kind until the owner says "go"**: no edits, commits, pull requests, merges,
   deploys, server or configuration changes, or record edits. Discuss first (what you understood,
   what you would change, options and trade-offs), then wait; a "go" covers only what was asked.
2. **Never print secret values** (profiles, env files, secret JSON, container environments): show
   key names or "same / different" only, redact nested values too, and report any exposure at once.
3. **Report honestly**: what was done, what was tested, what was not; correct earlier wrong statements.
4. **Security before features and deployments**: before any production promotion, upgrade or new
   dependency, check the official security advisories (GitHub Security Advisories, OSV) and release
   notes of every component the change ships or touches against the pinned versions, and record
   "advisories checked: none open / list" in the pull request and the release record. A known high
   or critical flaw in what we ship blocks the release unless the owner accepts it in writing. Before
   adopting new software, check licence, maintenance, security history and how fixes are published,
   and record it in `docs/decisions.md`. Read the latest upstream-watch digest (P62) when it exists;
   security fixes for what we run come before new features unless the owner decides otherwise.

# Project principles (owner, 17 November 2026)

These are nonnegotiable and apply to this and all future projects:

1. **Code → repository → test → production**, always, so every deployment is
   reproducible from this repository (see the policy above).
2. **Respect rights.** Check upstream licenses before copying, vendoring or
   modifying code or artwork; keep notices and attributions; act ethically.
3. **Share what we build or fix** wherever possible: upstream bug reports and
   patches, official forum or tracker posts, and this repository (public
   since 19 November 2026 under AGPL-3.0-or-later; operations records stay in
   a private repository).
4. **Acknowledge the open-source stack** we use, integrate or configure (see
   the README acknowledgements).
5. **Disclose AI assistance.** Development is assisted by AI agents; say so in
   the README, user-facing notes and public posts. Contributors remain
   responsible for understanding, testing and standing behind every change.
6. **One repository, built modularly.** Integrations live in this repository as
   self-contained modules so others can reuse a single module, rather than as
   separate exclusive repositories.
7. **Modularity review at the TrueNAS rebuild.** Where the repository is not yet
   modular enough, restructure it when the permanent test site is rebuilt on
   the TrueNAS home server (P33).

# Recovery essentials (owner, 18 November 2026)

Keep the recovery items listed in `docs/disaster-recovery.md` outside the
servers (password manager plus an offline copy): the backup encryption
password, TrueNAS admin access, the SSH keys, and the provider, registrar,
GitHub, Tailscale, Meta and authentik logins with recovery codes. Review the
list every three months. Backups follow the ransomware protections in the same
document; never give production the ability to delete protected backups.

# Decision log (owner, 18 November 2026)

Record every adopted plan change in `docs/decisions.md` in the same change
that implements it: what was decided and why (not the discussion), so others
can build a similar setup from scratch.
