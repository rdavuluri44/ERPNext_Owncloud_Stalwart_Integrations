#!/usr/bin/env python3
"""Save every container's logs before a stack is recreated (P59, P61 scenario 4).

Docker keeps a container's logs only as long as the container exists: recreating a stack for a release deletes them.
On 20 November that erased the only evidence of a failed save in the editor. Run this on the host, as root, before
any stack is recreated; the promotion plan lists it as the first step.

    python3 tools/archive_container_logs.py                    # all containers
    python3 tools/archive_container_logs.py --name ocis --name collaboration

Writes one compressed file per container, `<dest>/<YYYY-MM-DD>/<HHMMSS>-<container>.log.gz` (folders 0700, files
0600), with Docker's timestamps, and removes dated folders older than `--keep-days`. Prints counts and sizes only,
never log contents: logs can hold personal data, so the folder stays root-only on the host.
"""
import argparse
import datetime
import gzip
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEST = Path("/var/log/cloud-integrations/container-logs")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def containers(run=subprocess.run):
    out = run(["docker", "ps", "-a", "--format", "{{.ID}} {{.Names}}"], capture_output=True, text=True, check=True).stdout
    return [tuple(line.split(" ", 1)) for line in out.splitlines() if " " in line]


def archive(dest=DEST, names=(), keep_days=30, now=None, run=subprocess.run):
    """Archive the selected containers' logs; returns (files written, bytes written, folders removed)."""
    now = now or datetime.datetime.now()
    folder = Path(dest) / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    os.chmod(dest, 0o700)
    os.chmod(folder, 0o700)
    written, size = 0, 0
    for cid, name in containers(run):
        if names and not any(n in name for n in names):
            continue
        target = folder / f"{now.strftime('%H%M%S')}-{SAFE.sub('_', name)}.log.gz"
        logs = run(["docker", "logs", "--timestamps", cid], capture_output=True, check=False)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb") as out:
            out.write(logs.stdout or b"")
            out.write(logs.stderr or b"")
        written += 1
        size += target.stat().st_size
    removed = 0
    cutoff = (now - datetime.timedelta(days=keep_days)).date()
    for old in Path(dest).iterdir():
        if old.is_dir() and DAY.match(old.name) and datetime.date.fromisoformat(old.name) < cutoff:
            shutil.rmtree(old)
            removed += 1
    return written, size, removed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--dest", default=str(DEST))
    parser.add_argument("--name", action="append", default=[], help="only containers whose name contains this")
    parser.add_argument("--keep-days", type=int, default=30)
    args = parser.parse_args(argv)
    written, size, removed = archive(Path(args.dest), args.name, args.keep_days)
    print(f"archived logs of {written} containers ({size // 1024} KiB compressed) to {args.dest}; "
          f"removed {removed} folders older than {args.keep_days} days")
    return 0 if written else 1


if __name__ == "__main__":
    sys.exit(main())
