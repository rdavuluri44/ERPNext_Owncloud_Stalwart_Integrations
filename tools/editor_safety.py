#!/usr/bin/env python3
"""Editor file safety (P61): rescue parked edits, unstick a document, watch saves and disk.

Runs as root on the Docker host of ONLYOFFICE Docs. It reaches ONLYOFFICE only through
`docker exec` in the editor container: the command service on http://localhost/command, signed
with the container's own JWT secret (read from the container, kept in memory, never printed or
passed on a command line), and the editor's log files.

    editor_safety.py forgotten             list parked ("forgotten") documents
    editor_safety.py rescue                copy every parked document into the recovery folder
    editor_safety.py unstick KEY [--yes]   force save and rescue; with --yes also close the
                                           document for everyone so it reopens from Drive
    editor_safety.py watch                 save-failure alarms, rescue, disk and cache checks (timer)

It never deletes a parked document or a Drive file. Signals only (alerts are P72): the exit code
(0 fine, 1 the tool failed, 2 an alarm), status.json in the state folder, one journal line per run.
"""
import argparse
import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

COMMAND_URL = 'http://localhost/command'
LOGS = ['/var/log/onlyoffice/documentserver/docservice/out.log',
        '/var/log/onlyoffice/documentserver/docservice/err.log']
CACHE = '/var/lib/onlyoffice/documentserver/App_Data/cache/files'
EDITOR_PATHS = ['/var/lib/onlyoffice', '/var/www/onlyoffice/Data']
MAX_READ = 5 * 1024 * 1024  # ponytail: per log and run; a busier editor needs a streaming reader
WAIT = 15  # seconds for a forced save or a close to reach Drive
DEFAULTS = {'editor_container': 'onlyoffice-', 'bridge_container': 'collaboration-', 'drive_container': 'ocis-',
            'drive_paths': ['/var/lib/ocis'], 'state_dir': '/var/lib/cloud-editor-safety',
            'recovery_dir': '/var/lib/cloud-editor-safety/recovery', 'disk_alert_percent': 80, 'cache_alert_mb': 2048}
# Kinds of log line that mean a save or an edit is in danger (incident of 20 November 2026).
KINDS = {
    'save_failed': re.compile(r'(?i)put_?file[^\n]*(error|fail|\b5\d\d\b)|(error|fail)[^\n]*put_?file'),
    'parked': re.compile(r'(?i)storeforgotten|in forgotten'),
    'apply_failed': re.compile(r'changesError'),
}
PREFIX = re.compile(r'^\[[^\]]*\] \[[A-Z]+\] \[[^\]]*\] \[([^\]]*)\]')  # [time] [LEVEL] [tenant] [docId]


def run(args, data=None):
    """Run a host command. Tests replace this function."""
    result = subprocess.run(args, input=data, capture_output=True, timeout=300)
    if result.returncode:
        raise RuntimeError(' '.join(args[:3]) + ' failed: ' + result.stderr.decode(errors='replace').strip()[-300:])
    return result.stdout


def container(prefix):
    names = [n for n in run(['docker', 'ps', '--format', '{{.Names}}']).decode().split() if n.startswith(prefix)]
    if len(names) != 1:
        raise RuntimeError('expected one running container starting with ' + prefix + ', found ' + str(len(names)))
    return names[0]


def jwt(payload, secret, lifetime=300):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(',', ':')).encode()).rstrip(b'=').decode()
    now = int(time.time())
    body = part({'alg': 'HS256', 'typ': 'JWT'}) + '.' + part({**payload, 'iat': now, 'exp': now + lifetime})
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    return body + '.' + base64.urlsafe_b64encode(signature).rstrip(b'=').decode()


class Editor:
    def __init__(self, name):
        self.name = name
        env = json.loads(run(['docker', 'inspect', '--format', '{{json .Config.Env}}', name]))
        self.secret = next((e.split('=', 1)[1] for e in env if e.startswith('JWT_SECRET=')), None)
        if not self.secret:
            raise RuntimeError('the editor container has no JWT_SECRET')

    def command(self, body):
        """The stack sends tokens in the Authorization header: payload wrapped as {"payload": body}.
        The header goes on stdin (curl -H @-), so the token never appears in a process list."""
        header = 'Authorization: Bearer ' + jwt({'payload': body}, self.secret) + '\n'
        out = run(['docker', 'exec', '-i', self.name, 'curl', '-sS', '-m', '60', '-X', 'POST', COMMAND_URL,
                   '-H', 'Content-Type: application/json', '-H', '@-', '--data-binary', json.dumps(body)],
                  header.encode())
        answer = json.loads(out)
        if answer.get('error') == 6:
            raise RuntimeError('the editor refused the signature (error 6)')
        return answer

    def fetch(self, url):
        """Forgotten-file URLs name the editor's public host; ask the editor itself on localhost."""
        parts = urlsplit(url)
        return run(['docker', 'exec', self.name, 'curl', '-sS', '-f', '-m', '300',
                    'http://localhost' + parts.path + ('?' + parts.query if parts.query else '')])

    def text(self, *args):
        return run(['docker', 'exec', self.name, *args]).decode(errors='replace')


def forgotten(editor):
    answer = editor.command({'c': 'getForgottenList'})
    return list(answer.get('keys') or []) if answer.get('error') in (0, None) else []


def rescue(editor, recovery):
    """Copy every parked document into recovery/<key>/; already copied content is skipped."""
    recovery = Path(recovery)
    recovery.mkdir(parents=True, exist_ok=True, mode=0o700)
    copied = []
    for key in forgotten(editor):
        answer = editor.command({'c': 'getForgotten', 'key': key})
        if answer.get('error') != 0 or not answer.get('url'):
            continue
        data = editor.fetch(answer['url'])
        digest = hashlib.sha256(data).hexdigest()
        folder = recovery / re.sub(r'[^A-Za-z0-9._-]', '_', key)[:120]
        target = folder / (digest[:16] + (Path(urlsplit(answer['url']).path).suffix or '.bin'))
        if target.exists():
            continue
        folder.mkdir(exist_ok=True, mode=0o700)
        target.write_bytes(data)
        os.chmod(target, 0o600)
        record = {'time': now(), 'key': key, 'file': str(target), 'bytes': len(data), 'sha256': digest}
        with open(recovery / 'manifest.jsonl', 'a') as manifest:
            manifest.write(json.dumps(record) + '\n')
        copied.append(record)
    return copied


def unstick(editor, key, recovery, close=False, say=print):
    users = editor.command({'c': 'info', 'key': key})
    say('document ' + key + ': ' + ('open for ' + str(len(users.get('users') or [])) + ' user(s)'
                                    if users.get('error') == 0 else 'not open in the editor (error ' + str(users.get('error')) + ')'))
    saved = editor.command({'c': 'forcesave', 'key': key})
    say({0: 'forced save sent to Drive', 4: 'no unsaved changes'}.get(saved.get('error'),
        'forced save not possible (error ' + str(saved.get('error')) + ')'))
    time.sleep(WAIT)
    copied = rescue(editor, recovery)
    if close:
        dropped = editor.command({'c': 'drop', 'key': key})
        say('closed for everyone' if dropped.get('error') == 0 else 'close not possible (error ' + str(dropped.get('error')) + ')')
        time.sleep(WAIT)
        copied += rescue(editor, recovery)
    else:
        say('not closed: run again with --yes to close it for everyone (people must reopen it from Drive)')
    for c in copied:
        say('rescued parked edits: ' + c['file'])
    say('next: open the file from Drive. If it still fails, see "A file will not open" in integrations/onlyoffice/README.md')
    return copied


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def read_new(editor, path, offsets):
    size = int(editor.text('sh', '-c', 'wc -c < "$1" 2>/dev/null || echo 0', 'sh', path).strip() or 0)
    start = offsets.get(path, 0)
    if size < start:
        start = 0  # rotated or the container was recreated
    start = max(start, size - MAX_READ)
    offsets[path] = size
    return editor.text('tail', '-c', '+' + str(start + 1), path) if size > start else ''


def classify(lines, counts, documents):
    for line in lines:
        for kind, pattern in KINDS.items():
            if pattern.search(line):
                counts[kind] += 1
                found = PREFIX.match(line)
                if found and found.group(1) and len(documents) < 20:
                    documents.add(found.group(1))


def percent_used(editor, paths):
    out = editor.text('df', '-P', *paths).splitlines()[1:]
    return {row.split()[-1]: int(row.split()[-2].rstrip('%')) for row in out if row.split()}


def watch(config, say=print):
    state_dir = Path(config['state_dir'])
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_file = state_dir / 'state.json'
    state = json.loads(state_file.read_text()) if state_file.exists() else {'offsets': {}}
    since = state.get('since') or (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)
                                   ).strftime('%Y-%m-%dT%H:%M:%SZ')
    started = now()
    editor = Editor(container(config['editor_container']))
    counts, documents, alarms, problems = dict.fromkeys(KINDS, 0), set(), [], []
    for path in LOGS:
        classify(read_new(editor, path, state['offsets']).splitlines(), counts, documents)
    try:
        bridge = container(config['bridge_container'])
        logs = subprocess_logs(bridge, since)
        counts['save_failed'] += sum(1 for line in logs if KINDS['save_failed'].search(line))
    except RuntimeError as exc:
        problems.append('Drive editor bridge log: ' + str(exc))
    if counts['save_failed']:
        alarms.append(str(counts['save_failed']) + ' failed save(s) to Drive')
    if counts['apply_failed']:
        alarms.append(str(counts['apply_failed']) + ' edit(s) the editor could not apply')
    if counts['parked']:
        alarms.append(str(counts['parked']) + ' document(s) parked with unsaved edits')
    copied = rescue(editor, config['recovery_dir'])
    if copied:
        alarms.append(str(len(copied)) + ' parked document(s) copied to ' + config['recovery_dir'])
    parked_now = len(forgotten(editor))
    disk = percent_used(editor, EDITOR_PATHS)
    try:
        drive = container(config['drive_container'])
        out = run(['docker', 'exec', drive, 'df', '-P', *config['drive_paths']]).decode().splitlines()[1:]
        disk.update({row.split()[-1]: int(row.split()[-2].rstrip('%')) for row in out if row.split()})
    except RuntimeError as exc:
        problems.append('Drive disk: ' + str(exc))
    for mount, used in sorted(disk.items()):
        if used >= config['disk_alert_percent']:
            alarms.append('disk ' + mount + ' ' + str(used) + '% full')
    cache_mb = int(editor.text('du', '-sk', CACHE).split()[0]) // 1024
    if cache_mb >= config['cache_alert_mb']:
        alarms.append('editor cache ' + str(cache_mb) + ' MB')
    state['since'] = started
    state_file.write_text(json.dumps(state, indent=1) + '\n')
    status = {'time': started, 'alarms': alarms, 'problems': problems, **counts, 'documents': sorted(documents),
              'rescued': [c['file'] for c in copied], 'parked_now': parked_now, 'disk_percent': disk, 'cache_mb': cache_mb}
    (state_dir / 'status.json').write_text(json.dumps(status, indent=1) + '\n')
    say('editor-safety ' + ('ALERT: ' + '; '.join(alarms) if alarms else 'ok') +
        (' | documents: ' + ', '.join(sorted(documents)) if documents else '') +
        (' | not checked: ' + '; '.join(problems) if problems else '') +
        ' | parked now: ' + str(parked_now) + ', cache ' + str(cache_mb) + ' MB')
    return 2 if alarms else 1 if problems else 0


def subprocess_logs(name, since):
    """The bridge logs to stdout and stderr; both are read."""
    out = run(['sh', '-c', 'exec docker logs --since "$1" "$2" 2>&1', 'sh', since, name])
    return out.decode(errors='replace').splitlines()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Editor file safety (P61); never deletes a document.')
    parser.add_argument('--config', help='private JSON settings (container prefixes, folders, thresholds)')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('forgotten')
    sub.add_parser('rescue')
    one = sub.add_parser('unstick')
    one.add_argument('key', help="the document key (from status.json 'documents' or the editor log)")
    one.add_argument('--yes', action='store_true', help='also close the document for everyone')
    sub.add_parser('watch')
    args = parser.parse_args(argv)
    config = {**DEFAULTS, **(json.loads(Path(args.config).read_text()) if args.config else {})}
    try:
        if args.action == 'watch':
            return watch(config)
        editor = Editor(container(config['editor_container']))
        if args.action == 'forgotten':
            keys = forgotten(editor)
            print('\n'.join(keys) if keys else 'no parked documents')
        elif args.action == 'rescue':
            copied = rescue(editor, config['recovery_dir'])
            print('\n'.join(c['file'] for c in copied) if copied else 'nothing new to rescue')
        else:
            unstick(editor, args.key, config['recovery_dir'], close=args.yes)
        return 0
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('editor-safety failed: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
