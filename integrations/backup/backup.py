#!/usr/bin/env python3
"""Encrypted off-server backups with Restic to S3-compatible storage (P02).

Runs as root on the backed-up host from a private JSON profile kept outside
Git. Restic runs from a digest-pinned image; nothing is installed on the host.
The encryption password and S3 keys are read from root-only files and passed
to Restic as mounted files / an env file, never on the command line.

  backup.py --profile P init     create the repository (once)
  backup.py --profile P run      dump, copy, back up, apply retention
  backup.py --profile P check    verify repository integrity (sample of data)

Databases are dumped online with consistent snapshots (no downtime). Stores
that are unsafe to copy while running (e.g. Drive, Mail) are stopped briefly,
copied to local staging and restarted before the upload; the stop is bounded
and the containers are restarted even on failure. They are started in the
listed order, each after the previous one is healthy (list Drive before its
editor bridge).
"""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')
DIGEST = re.compile(r'[a-z0-9./-]+@sha256:[0-9a-f]{64}')


def validate(profile):
    if profile.get('tier') not in {'production', 'test'}: raise ValueError('Unknown tier')
    if not DIGEST.fullmatch(profile.get('restic_image', '')): raise ValueError('Restic image must be pinned by digest')
    repo = profile.get('repository', '')
    local_test = profile.get('tier') == 'test' and repo.startswith('/') and repo != '/' and '..' not in repo
    if not (re.fullmatch(r's3:https?://[^\s]+', repo) or local_test):
        raise ValueError('Repository must be an s3: URL (a local path only on a test host)')
    for key in ['password_file', 'staging', 'state'] + (['s3_credentials_file'] if repo.startswith('s3:') else []):
        if not Path(profile[key]).is_absolute(): raise ValueError(key + ' must be absolute')
    for path in profile.get('paths', []) + [p for c in profile.get('stop_and_copy', []) for p in c['paths']]:
        if not Path(path).is_absolute() or path == '/': raise ValueError('Backup paths must be absolute, not /')
    for item in profile.get('databases', []) + profile.get('stop_and_copy', []):
        if not NAME.fullmatch(item['name']): raise ValueError('Invalid name')
    for db in profile.get('databases', []):
        if db['kind'] not in {'mariadb', 'postgres'} or not NAME.fullmatch(db['container']):
            raise ValueError('Invalid database entry')
    for group in profile.get('stop_and_copy', []):
        if not group['containers'] or any(not NAME.fullmatch(c) for c in group['containers']):
            raise ValueError('Invalid stop_and_copy containers')
        wait = group.get('start_wait_seconds', 120)
        if not isinstance(wait, int) or isinstance(wait, bool) or not 0 <= wait <= 600:
            raise ValueError('start_wait_seconds must be 0 to 600')
    retention = profile.get('retention', {'daily': 7, 'weekly': 4, 'monthly': 6})
    if not all(isinstance(v, int) and v > 0 for v in retention.values()): raise ValueError('Retention counts must be positive')
    return profile


def restic(profile, args, mounts=(), network='host'):
    """docker run argv for Restic; secrets only as read-only mounted files."""
    cache = Path(profile['state']) / 'cache'
    argv = ['docker', 'run', '--rm', '--network', network, '--hostname', profile.get('hostname', 'backup-source'),
            *(['--env-file', profile['s3_credentials_file']] if profile.get('s3_credentials_file') else []),
            '-e', 'RESTIC_REPOSITORY=' + profile['repository'],
            '-e', 'RESTIC_PASSWORD_FILE=/run/secrets/restic-password',
            '-v', profile['password_file'] + ':/run/secrets/restic-password:ro',
            '-v', str(cache) + ':/root/.cache/restic']
    if profile['repository'].startswith('/'):
        # Local repository (test hosts only): mounted read-write at its own path.
        argv += ['-v', profile['repository'] + ':' + profile['repository']]
    for source, target in mounts:
        argv += ['-v', source + ':' + target + ':ro']
    return argv + [profile['restic_image']] + list(args)


def dump_command(db):
    if db['kind'] == 'mariadb':
        inner = ('export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot --all-databases '
                 '--single-transaction --routines --triggers --events --hex-blob')
    else:
        inner = 'exec pg_dumpall -U "$POSTGRES_USER"'
    return ['docker', 'exec', db['container'], 'sh', '-c', inner]


def dump(db, output, run=subprocess.run):
    with open(output, 'wb') as file:
        result = run(dump_command(db), stdout=file, stderr=subprocess.PIPE)
    if result.returncode: raise RuntimeError('Database dump failed: ' + db['name'])


def health(name, run=subprocess.run):
    """'healthy', 'starting', 'unhealthy', or 'none' for a container without a health check."""
    result = run(['docker', 'inspect', '-f', '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}', name],
                 capture_output=True, text=True)
    return (getattr(result, 'stdout', '') or '').strip() or 'none'


def start_in_order(containers, run=subprocess.run, clock=time.monotonic, sleep=time.sleep, wait=120):
    """Start the containers in the listed order. Before starting the next one, wait (bounded) until the previous
    one is healthy, so a dependent never races the service it registers with: Drive's editor bridge failed its
    first registration on 24 and 25 November 2026 when both started at once (P80). Every container is started
    even when a wait times out or a start fails; the first failure is raised afterwards."""
    failure = None
    for index, name in enumerate(containers):
        try:
            run(['docker', 'start', name], check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as error:
            failure = failure or error
            continue
        if index == len(containers) - 1:
            break
        deadline = clock() + wait
        while health(name, run) not in ('healthy', 'none') and clock() < deadline:
            sleep(2)
    if failure:
        raise failure


def stop_and_copy(group, staging, run=subprocess.run, clock=time.monotonic, sleep=time.sleep):
    """Stop the group's containers, copy their paths, always restart them (in the listed order)."""
    started = clock()
    run(['docker', 'stop', '--time', '30', *group['containers']], check=True, stdout=subprocess.DEVNULL)
    try:
        for path in group['paths']:
            target = Path(staging) / 'stopped' / group['name'] / path.lstrip('/')
            if target.exists(): shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            run(['cp', '-a', '--reflink=auto', path, str(target)], check=True)
    finally:
        start_in_order(group['containers'], run=run, clock=clock, sleep=sleep, wait=group.get('start_wait_seconds', 120))
    return round(clock() - started, 1)


def mounts_for(profile):
    staging = profile['staging']
    rows = [(staging, '/backup/staging')]
    rows += [(path, '/backup' + path) for path in profile.get('paths', [])]
    return rows


def run_backup(profile, run=subprocess.run):
    state = Path(profile['state']); state.mkdir(parents=True, exist_ok=True, mode=0o700)
    (state / 'cache').mkdir(exist_ok=True, mode=0o700)
    staging = Path(profile['staging'])
    with open(state / 'backup.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if staging.exists(): shutil.rmtree(staging)
        (staging / 'databases').mkdir(parents=True, mode=0o700)
        report = {'started_at': datetime.now(timezone.utc).isoformat(), 'stopped_seconds': {}}
        try:
            for db in profile.get('databases', []):
                dump(db, staging / 'databases' / (db['name'] + '.sql'), run=run)
            for group in profile.get('stop_and_copy', []):
                report['stopped_seconds'][group['name']] = stop_and_copy(group, staging, run=run)
            excludes = [arg for pattern in profile.get('exclude', []) for arg in ('--exclude', '/backup' + pattern)]
            run(restic(profile, ['backup', '/backup', '--tag', profile.get('tag', 'nightly'), *excludes],
                       mounts_for(profile)), check=True)
            keep = profile.get('retention', {'daily': 7, 'weekly': 4, 'monthly': 6})
            run(restic(profile, ['forget', '--prune', '--tag', profile.get('tag', 'nightly'),
                                 '--keep-daily', str(keep['daily']), '--keep-weekly', str(keep['weekly']),
                                 '--keep-monthly', str(keep['monthly'])]), check=True)
            report.update(result='succeeded')
        except Exception as error:
            report.update(result='failed', error=type(error).__name__)
            raise
        finally:
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            shutil.rmtree(staging, ignore_errors=True)
            (state / 'last-run.json').write_text(json.dumps(report, indent=2) + '\n')
            if report.get('result') == 'succeeded':
                (state / 'last-success.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--profile', required=True)
    parser.add_argument('action', choices=['init', 'run', 'check'])
    args = parser.parse_args(); os.umask(0o077)
    path = Path(args.profile)
    if path.stat().st_uid != 0 or path.stat().st_mode & 0o077: raise SystemExit('Profile must be root-owned and private')
    profile = validate(json.loads(path.read_text()))
    Path(profile['state'], 'cache').mkdir(parents=True, exist_ok=True, mode=0o700)
    if args.action == 'init': subprocess.run(restic(profile, ['init']), check=True)
    elif args.action == 'check': subprocess.run(restic(profile, ['check', '--read-data-subset=5%']), check=True)
    else: print(json.dumps(run_backup(profile)))
