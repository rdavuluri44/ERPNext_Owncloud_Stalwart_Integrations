#!/usr/bin/env python3
"""Which runtime mounts are made from which repository files, and the record of what was mounted (P99).

`tools/prepare_runtime.py` fills each mount listed in `deployment/stacks/mounts.json`; the tables below say
which repository file or folder it is made from. Both the deployment (which writes the record) and
`tools/drift_check.py` (which reads it) use them, so the two cannot disagree.

The record (`mount-record.json` in the runtime folder, next to `mounts/`) holds, per mount: the repository
source, the commit it was made from, and the checksum of what was written. The drift check compares the file
on disk with the record (a difference means it was changed by hand) and the source at that commit with
`main` (a difference means it is behind). Secrets and data folders are never recorded.

After a promotion that replaces one mounted file by hand (for example P97), record it:

    python3 tools/runtime_mounts.py record --runtime RUNTIME --mount erp_frontend_2 --commit SHA

RUNTIME is the folder that holds `mounts/`; SHA is the main commit the file was taken from.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

# Mount target -> repository file, copied with the deployment's public names filled in.
copy_files = {
    '/opt/cloud/backend_start.py': 'deployment/erp/backend_start.py',
    '/opt/cloud/netbird_realtime.cjs': 'deployment/erp/netbird_realtime.cjs',
    '/templates/nginx/frappe.conf.template': 'deployment/erp/frappe.conf.template',
    '/app/document-worker.py': 'integrations/document-worker/document-worker.py',
    '/etc/nginx/conf.d/default.conf': 'integrations/website/nginx-default.conf',
    '/configure.py': 'integrations/chat/configure.py',
}
# Mount name -> repository file (the two identity proxies share the target /etc/nginx/nginx.conf).
identity_proxy_files = {
    'identity_support_gateway_0': 'integrations/authentik/identity-support/nginx.conf',
    'identity_support_invitations_1': 'integrations/authentik/invite-recovery/nginx.conf',
}
# Mount target -> repository folder, copied (and branded) as a whole.
copy_dirs = {'/opt/cloud-extension': 'integrations/dms',
             '/templates': 'integrations/authentik/invite-recovery/templates',
             '/srv/public': 'integrations/authentik/invite-recovery/public',
             '/srv/site': 'integrations/website/site'}
# Mount target -> repository file, copied unchanged (office editor).
editor_files = {
    '/etc/onlyoffice/documentserver/local-production-linux.json': 'deployment/config/onlyoffice-local-production-linux.json',
    '/var/www/onlyoffice/documentserver/web-apps/apps/api/wopi/editor-wopi.ejs': 'integrations/onlyoffice/editor-wopi.ejs',
}

RECORD = 'mount-record.json'


def source_of(item):
    """The repository file or folder a mount (an entry of mounts.json) is made from, or None (data,
    secrets, operator-owned files)."""
    if item['path'] in identity_proxy_files:
        return identity_proxy_files[item['path']]
    target = item['target']
    if item['stack'] == 'editor':
        return editor_files.get(target)
    return copy_files.get(target) or copy_dirs.get(target)


def digest(path):
    """sha256 of a file, or of a folder's files (sorted relative paths and their checksums)."""
    path = Path(path)
    if path.is_file() and not path.is_symlink():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if not path.is_dir() or path.is_symlink():
        raise ValueError('not a regular file or folder: ' + str(path))
    total = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            item = Path(root) / name
            relative = item.relative_to(path).as_posix()
            value = ('link:' + os.readlink(item)) if item.is_symlink() else hashlib.sha256(item.read_bytes()).hexdigest()
            total.update((relative + '\0' + value + '\n').encode())
    return total.hexdigest()


def read_record(runtime):
    path = Path(runtime) / RECORD
    if not path.is_file():
        return {}
    data = json.loads(path.read_text())
    return data.get('mounts', {}) if isinstance(data, dict) else {}


def record_entries(runtime, entries, write):
    """Merge {mount name: {source, commit, sha256}} into the runtime's record; `write(path, text)` writes it
    (owner-only)."""
    mounts = read_record(runtime)
    mounts.update(entries)
    write(Path(runtime) / RECORD, json.dumps({'version': 1, 'mounts': dict(sorted(mounts.items()))}, indent=1) + '\n')


def write_owner_only(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Record a runtime mount after a promotion (P99).')
    commands = parser.add_subparsers(dest='command', required=True)
    record = commands.add_parser('record', help='record one mount as deployed from a commit')
    record.add_argument('--runtime', required=True, help='the folder that holds mounts/')
    record.add_argument('--mount', required=True, help='the mount name, for example erp_frontend_2')
    record.add_argument('--commit', required=True, help='the main commit the mount was made from')
    record.add_argument('--repository', default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)

    def git(*items, text=True):
        return subprocess.run(['git', '-C', args.repository, *items], check=True, capture_output=True, text=text).stdout
    try:
        commit = git('rev-parse', '--verify', '--quiet', args.commit + '^{commit}').strip()
        catalogue = json.loads(git('show', commit + ':deployment/stacks/mounts.json'))
    except subprocess.CalledProcessError:
        print('record: unknown commit ' + args.commit, file=sys.stderr)
        return 1
    item = next((m for m in catalogue if m['path'] == args.mount), None)
    relative = source_of(item) if item else None
    if not relative:
        print('record: ' + args.mount + ' is not a mount made from a repository file', file=sys.stderr)
        return 1
    path = Path(args.runtime) / 'mounts' / args.mount
    if not path.exists():
        print('record: missing ' + str(path), file=sys.stderr)
        return 1
    value = digest(path)
    note = ''
    if path.is_file():
        try:
            same = hashlib.sha256(git('show', commit + ':' + relative, text=False)).hexdigest() == value
        except subprocess.CalledProcessError:
            same = False
        note = ' (same bytes as the file at that commit)' if same else ' (differs from the file at that commit: rendered)'
    record_entries(args.runtime, {args.mount: {'source': relative, 'commit': commit, 'sha256': value}}, write_owner_only)
    print('recorded ' + args.mount + ' from ' + relative + ' at ' + commit[:12] + note)
    return 0


if __name__ == '__main__':
    sys.exit(main())
