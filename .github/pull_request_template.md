## What and why

## Module(s) touched
<!-- from modules.json -->

## Promotion plan
<!-- output of `python tools/promotion_plan.py <commit production runs> <this branch>`: stacks, steps, live settings, restarts, what test cannot cover -->

## How it was tested
- [ ] `python tools/check_repository.py`
- [ ] `python tools/run_unit_tests.py`
- [ ] **Branch deployed to the test site and validated** (required before merge).
      Tested commit: `` Result: ``
      Not covered by test (production-only files, limits): ``

## Safety
- [ ] No secrets, tokens or business data in the diff
- [ ] Third-party code/artwork licensed and attributed
- [ ] AI assistance used? Say so here:

Order: branch → test → merge → `main` → production. Production is updated only from `main`, after owner confirmation.
