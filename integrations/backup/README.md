# Off-server backups with Restic (`backup`)

Encrypted, deduplicated nightly backups of a Docker/Coolify host to
S3-compatible storage, plus a restore drill that proves the backups restore.

## Purpose

P02: protect production (ERP, sign-in, Drive, DMS, Mail and their
configuration) against loss of the server. Backups go to an S3 bucket on the
owner's TrueNAS (RustFS, on the RAID10 `tank` pool) over the tailnet. The
restore drill runs on the test host and imports every database dump into a
throwaway container, so "backup succeeded" is checked by an actual restore.

## Contents

- `integrations/backup/backup.py`: `init`, `run`, `check` from a private profile
- `integrations/backup/restore_drill.py`: restore latest snapshot and verify
- `integrations/backup/*.example.json`: profile templates (no secrets)
- `integrations/backup/*.service.example`, `*.timer.example`: systemd units
- `tests/backup/test_backup.py`

## Requirements

Root on the host, Docker, network access to the S3 endpoint. Restic runs from
a digest-pinned image (`restic/restic` 0.18.0); nothing is installed on the
host. An S3 bucket with a **read-write key for the source host** and a
separate **read-only key for the drill host**.

## Reuse

Copy `integrations/backup/`. Write a root-only profile from the example
(databases with their container and kind, `stop_and_copy` groups for stores
that are unsafe to copy live, `paths` copied live, `exclude`, `retention`),
a root-only password file and an S3 env file (`AWS_ACCESS_KEY_ID=`,
`AWS_SECRET_ACCESS_KEY=`). Run `backup.py --profile P init` once, then install
the timer.

## Configuration

- Databases are dumped online: MariaDB `--single-transaction --all-databases`,
  PostgreSQL `pg_dumpall`. No downtime.
- `stop_and_copy` containers are stopped (30 s grace), copied to staging with
  `cp -a` and restarted in a `finally` block, before the upload; the stop
  time is recorded per group in `last-run.json`. They are started **in the
  listed order**, each only after the previous one reports healthy (bounded by
  `start_wait_seconds`, default 120, 0 to 600). List a service before anything
  that registers with it: Drive's `ocis` before its editor bridge
  (`collaboration`), which otherwise races Drive's start and can fail to
  register (P80). Every container is started even if a wait times out.
- Include the sign-in service's media volume (authentik `/data`: branding,
  invitation pages) and invitation templates in `paths`; its database is in
  `databases` and its secret key lives in the Coolify compose under
  `/data/coolify` (P44: a rebuilt sign-in service must reuse that key).
- Tamper resistance (P40): `harden_storage.py apply` (admin key, run once)
  turns on bucket versioning and a lifecycle rule keeping non-current versions
  30 days; `harden_storage.py policy` prints the policy for the source host's
  key (no version deletes, no versioning/lifecycle/policy changes);
  `harden_storage.py verify` proves it from the source host with a canary.
- Retention defaults: 7 daily, 4 weekly, 6 monthly (`forget --prune`).
- The encryption password lives in a root-only file **and in the owner's
  password manager**: without it the backups cannot be read by anyone,
  including the owner. Never store it in Git, chat or the bucket.
- The drill uses `--no-lock` with the read-only key and network-less
  throwaway databases from pinned images; it deletes its scratch data.

## Tests

- `tests/backup/test_backup.py`: validation, secrets only as files, read-only
  source mounts, ordering (dumps → brief stop → upload → retention),
  restart after a failed copy, drill restore arguments.

## Licenses

- Restic: BSD-2-Clause, https://github.com/restic/restic (used as a pinned
  container image, not vendored)
- RustFS: Apache-2.0, https://github.com/rustfs/rustfs (storage service, not
  vendored)

Developed with AI assistance (Claude); the owner reviews and is responsible.
