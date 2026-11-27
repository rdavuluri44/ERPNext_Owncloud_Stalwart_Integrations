# Contributing

Thank you for helping. This repository runs a live business system, so every
change follows one path (see `AGENTS.md`, which is mandatory):

**your branch (in your fork) → test site → owner merges → `main` →
production.**

The code is public under AGPL-3.0-or-later (see `LICENSE`); by contributing
you agree that your contribution is licensed the same way.

## How to contribute

1. **Fork** this repository on GitHub (only the maintainers push here).
2. Create a branch in your fork from `main`.
3. Make the change. Keep it inside the module it belongs to (`modules.json`
   lists every module and its files; each module has a README).
4. Run the checks locally:
   ```
   python tools/check_repository.py
   python tools/check_client_identity.py
   python tools/run_unit_tests.py
   ```
   Never put a client's name (in any form), logo, domains, mail addresses or people in this
   repository: not in code, tests, comments, file names, commit messages or the pull request text.
   They come from the private deployment profile. The client identity check fails if one appears.
   GitHub runs the same "Offline checks" on your pull request.
5. Open a **pull request** to `main`. Describe what changed, why,
   and how you tested it. Use the template.

Only the owner merges, and only **after your branch has been deployed to the
test site and validated there** (the maintainers' permanent test site). Members
of the maintainers' "developer" group deploy branches themselves; for everyone
else the maintainers deploy the branch after reviewing the diff, because
deploying runs the branch's code on the test host. Write the tested commit and
the result in the pull request. Production is updated from `main` only after
the owner confirms; production reads this repository with a read-only key and
is never updated by a merge alone.

## Rules

- **No secrets or business data in Git**: no passwords, tokens, API keys,
  customer/employee data or production URLs with credentials. The checks
  reject common secret patterns, but you are responsible.
- **Test site only for app development**: point apps at the maintainers'
  test site, never at production. Test data is replaced from production at every
  refresh: work entered there is temporary and never reaches production.
- **Respect licenses**: check upstream licenses before copying code or
  artwork; keep notices and attributions (`LICENSES.md`).
- **AI assistance** is welcome and must be disclosed in the pull request;
  you remain responsible for understanding and testing your change.
