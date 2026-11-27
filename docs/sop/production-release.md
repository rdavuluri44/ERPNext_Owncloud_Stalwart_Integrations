# Release a change to production

**Status:** in use · **Owner of this SOP:** operator (a person or an agent working for the owner) · **Last
reviewed:** 26 November 2026

The rule behind every step: **branch → test → merge → main → production**, and production always runs content
that is on `main` (`AGENTS.md`). A merge is not a release: merged changes stay "merged, not deployed" until this
procedure is finished.

## Purpose

The tools list what a release reaches and check afterwards that nothing was left behind, but people decide when
to release, make the rollback point, do the checks the test site cannot cover and write the record. Each of these
has been missed at least once (a stack left behind, a note not updated, logs lost on a recreate), which is why they
are written down.

## Who

- **Owner:** gives the go for each production change and picks the moment.
- **Operator:** carries it out and records it.

## When

After a pull request was tested on the test site, its tested commit recorded in the pull request, and the owner
merged it. Security fixes come before features.

## Steps

1. **Advisories.** Check the security advisories and release notes of every component the release ships or
   touches, against the versions we pin. Write "advisories checked: none open" or the list in the pull request and
   the release record. A known high or critical flaw blocks the release unless the owner accepts it in writing.
2. **Plan.** Run `python3 tools/promotion_plan.py <commit production runs> origin/main`. It lists every stack,
   setup step, live setting and restart the release reaches, and what the test site could not cover. Read it to
   the end; tell the owner what users will notice.
3. **Upgrades only:** walk the register of our changes to that app (`docs/upstream-customizations.md`, checklist
   at the top), on test first.
4. **Go and moment.** Get the owner's go for this release and agree a quiet moment.
5. **Rollback point** for every stack in the plan: image tags, copies of the compose and profile files. Write
   where they are.
6. **Logs.** On the host, before any stack is recreated: `tools/archive_container_logs.py` (a recreate deletes
   container logs).
7. **Promote every stack in the plan**, not only the ERP: build where the plan says, render and redeploy, run the
   setup steps, apply the live settings, restart what it names. For the ERP, plan about 20 minutes extra when the
   core image has to be rebuilt. A full render (`tools/prepare_runtime.py`) records every mount it writes
   (`mount-record.json` in the runtime folder). **When you replace one mounted file by hand** (a one-file
   promotion, as P97 did), record it right after: `python3 tools/runtime_mounts.py record --runtime RUNTIME
   --mount NAME --commit SHA` (SHA: the main commit the file came from).
8. **Check what test could not cover**, right after promotion: a browser and protocol check of the affected apps
   (production-only route files, sign-in).
9. **Drift check.** Run `tools/drift_check.py` on production with its config. Every stack must be clean (exit 0).
   The release is not finished while it reports drift. It also compares the mounted runtime files (P99): a file
   "changed by hand" or "behind" is drift; "not compared" means no record yet (listed, not a failure).
10. **Record**, in the same session: the release entry (tested commit, rollback point, what test could not
    cover, checks run, failed or skipped checks), the event receipt, the work item's status, and the handover.
11. **Owner's browser check** of the main sites, when the release changes what users see.

## Checks

- The commit promoted is the tested commit, from `main`.
- Rollback point exists and its location is written down before the first change.
- Drift check clean after the last change.
- Release record and receipt pushed.

## Record

The release log, the event receipt and the handover in the private operations repository; the pull request keeps
the promotion plan and the test record.

## When it goes wrong

- **A step fails:** stop. Do not improvise on production. Roll back the stacks already changed to the rollback
  point, say so in the record, and fix the cause in the repository (branch, test, merge), then release again.
- **The test site is down or failing:** that blocks the release until it is restored and the test passes.
- **Drift check reports a stack behind:** the release missed it; promote that stack and run the check again.
- **A hand change was needed on production:** record it at once as a manual live change (what, why, how verified),
  and bring it into the repository so the next release reproduces it.
- **Urgent fix:** the same order applies, faster; never a direct edit in production.

## Private companion

Host names, access, where each stack's profile and rollback copies live, the drift-check config and the release
log are in the private operations repository (promotion notes there).
