#!/usr/bin/env python3
"""Move the webmail overlay to a new upstream commit (P91, register WEBMAIL-1).

    git clone https://github.com/bulwarkmail/webmail /tmp/bulwark && git -C /tmp/bulwark checkout <new commit>
    tools/refresh_webmail_overlay_base.py --checkout /tmp/bulwark --version 1.22.0

It lists every file we replace whose upstream content changed since the recorded base:
merge our changes into each of those (three-way: old upstream, new upstream, ours),
then run it again with --write to record the new commit, version and checksums in
integrations/mail/upstream.json. Without --write it changes nothing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / 'integrations/mail/upstream.json'
OVERLAY = ROOT / 'integrations/mail/overlay'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compare(lock, overlay, checkout):
    """(changed upstream files we replace, overlay files that are new upstream, new checksums)."""
    files = sorted(p.relative_to(overlay).as_posix() for p in Path(overlay).rglob('*') if p.is_file())
    base = lock['overlay_base']
    replaced, added, changed, clashes = {}, [], [], []
    for name in files:
        upstream = Path(checkout) / name
        if upstream.is_file():
            replaced[name] = sha(upstream)
            if base['replaced'].get(name) != replaced[name]:
                changed.append(name)
            if name in base['added']:
                clashes.append(name)
        else:
            added.append(name)
    return changed, clashes, {'replaced': replaced, 'added': added}


def main(argv=None, lock_path=LOCK, overlay=OVERLAY):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--checkout', required=True, help='clone of the upstream repository at the new commit')
    parser.add_argument('--version', help='upstream version of that commit, for example 1.22.0')
    parser.add_argument('--write', action='store_true', help='record the new base (after merging)')
    args = parser.parse_args(argv)
    lock = json.loads(Path(lock_path).read_text())
    commit = subprocess.check_output(['git', '-C', args.checkout, 'rev-parse', 'HEAD'], text=True).strip()
    changed, clashes, base = compare(lock, overlay, args.checkout)
    print(f'upstream {lock["overlay_base"]["commit"][:12]} -> {commit[:12]}')
    for name in changed:
        print(f'  merge needed: {name}')
    for name in clashes:
        print(f'  upstream now has a file we add: {name}')
    if not args.write:
        print('Nothing written. Merge the files above, then run again with --write.')
        return 1 if changed or clashes else 0
    lock['commit'] = commit
    if args.version:
        lock['version'] = args.version
    lock['overlay_base'] = {'commit': commit, **base}
    Path(lock_path).write_text(json.dumps(lock, indent=2) + '\n')
    print(f'recorded {len(base["replaced"])} replaced and {len(base["added"])} added files at {commit[:12]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
