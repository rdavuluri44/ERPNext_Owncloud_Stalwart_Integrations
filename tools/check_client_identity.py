#!/usr/bin/env python3
"""Fail when a client's identity appears in this public repository (P84).

A client's name in any form, its domains and its abbreviations never belong in this repository (owner,
26 November 2026). The list of those identifiers is private, so this repository only holds their
fingerprints in `.client-identity-fingerprints`: one line per identifier, `<length>:<sha256>` of the
lower-cased identifier with the prefix below. The check never prints a matched word, only where it is.

    python3 tools/check_client_identity.py                  # every tracked file, its name and its text
    python3 tools/check_client_identity.py --text "$TITLE"  # also check text such as a pull request title
    python3 tools/check_client_identity.py --commits origin/main..HEAD   # also check commit messages
    python3 tools/check_client_identity.py --make < terms   # fingerprints for a private list (one per line)

How words are matched: text is split into runs of letters and digits and lower-cased. An identifier of
6 or more characters is also found inside a longer run (for example in `clientname_logo` or
`clientnameApp`); a shorter one (an abbreviation) only as a whole run, so random strings such as hashes
in lock files do not match by chance. Runs longer than 40 characters are only compared whole.
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINGERPRINTS = ROOT / ".client-identity-fingerprints"
PREFIX = "client-identity-v1:"
SUBSTRING_MIN = 6
LONG_RUN = 40
WORD = re.compile(r"[a-z0-9]+")


def fingerprint(term):
    return hashlib.sha256((PREFIX + term.strip().lower()).encode()).hexdigest()


def load(path=FINGERPRINTS):
    """{length: {sha256, ...}} from the fingerprint file (comments and blank lines ignored)."""
    table = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        length, digest = line.split(":", 1)
        table.setdefault(int(length), set()).add(digest.strip())
    return table


def hits(text, table):
    """Positions (line numbers, 1-based) of runs that match a fingerprint; the words are never returned."""
    found = []
    lengths = sorted(table)
    for number, line in enumerate(text.lower().splitlines() or [""], 1):
        for run in WORD.findall(line):
            if len(run) in table and fingerprint(run) in table[len(run)]:
                found.append(number)
                continue
            if len(run) > LONG_RUN:
                continue
            if any(fingerprint(run[i:i + n]) in table[n]
                   for n in lengths if SUBSTRING_MIN <= n < len(run)
                   for i in range(len(run) - n + 1)):
                found.append(number)
    return found


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout
    return [name for name in out.decode().split("\0") if name]


def scan(table, files=None):
    problems = []
    for name in files if files is not None else tracked_files():
        if name == FINGERPRINTS.name:
            continue
        if hits(name, table):
            problems.append(f"{name}: file name")
        path = ROOT / name
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data[:8192]:
            continue                      # binary: not scanned (images are checked by review)
        for number in hits(data.decode("utf-8", "replace"), table):
            problems.append(f"{name}:{number}")
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--make", action="store_true", help="read terms on stdin, print fingerprint lines")
    parser.add_argument("--text", action="append", default=[], help="extra text to check (repeatable)")
    parser.add_argument("--commits", help="also check the messages of the commits in this git range")
    args = parser.parse_args(argv)
    if args.make:
        for term in sorted({t.strip().lower() for t in sys.stdin if t.strip()}):
            print(f"{len(term)}:{fingerprint(term)}")
        return 0
    table = load()
    problems = scan(table)
    for index, text in enumerate(args.text, 1):
        problems += [f"--text {index}:{n}" for n in hits(text, table)]
    if args.commits:
        log = subprocess.run(["git", "log", "--format=%H%x00%B%x00", args.commits], cwd=ROOT, check=True,
                             capture_output=True).stdout.decode("utf-8", "replace").split(chr(0))
        for commit, message in zip(log[0::2], log[1::2]):
            if hits(message, table):
                problems.append(f"commit {commit.strip()[:12]}: message")
    if problems:
        print("Client identity found (P84: client names, domains and abbreviations stay private):")
        for problem in problems:
            print("  " + problem)
        return 1
    print(f"client identity check: clean ({sum(len(v) for v in table.values())} fingerprints)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
