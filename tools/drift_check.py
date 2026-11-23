#!/usr/bin/env python3
"""Drift check (P59): is every stack running what main says it should?

For each stack named in the private settings, finds the commit it runs and compares it with main:
the stack is behind when a file it owns (deployment/promotion-map.json) changed since that commit.
Also compares served content with a local file (for example the landing page script). Read-only:
it reads git, the commit records and public pages, and changes nothing.

Where a stack's commit comes from ("commit_from" per stack):
  {"coolify_service": NAME}    the "Source commit <sha>" description written by tools/coolify_native.py
  {"profile": PATH, "key": K}  a JSON file (a deployment profile or receipt) holding the commit (key "commit")
  {"container": PREFIX}        the running container's image tag or its org.opencontainers.image.revision label

    drift_check.py --config /etc/cloud-drift-check/config.json

Signals: exit code 0 clean, 1 a check could not run, 2 drift; status.json in the state folder; one line.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from promotion_plan import load, rules_for  # noqa: E402

SHA = re.compile(r'[0-9a-f]{7,40}')
IMAGE_TAG = re.compile(r'([0-9a-f]{7,40})(?:-runtime)?')


def run(args):
    """Run a host command. Tests replace this function."""
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError(' '.join(args[:3]) + ' failed: ' + result.stderr.strip()[-300:])
    return result.stdout


def fetch(url):
    """Public page bytes. Tests replace this function."""
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'drift-check'}), timeout=30) as r:
        return r.read()


def deployed_commit(spec, config):
    if 'coolify_service' in spec:
        name = spec['coolify_service']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise ValueError('invalid Coolify service name')
        out = run(['docker', 'exec', config.get('coolify_db_container', 'coolify-db'), 'psql', '-U', 'coolify', '-d',
                   'coolify', '-At', '-c', "select description from services where name = '" + name + "'"])
        found = re.findall(r'Source commit (' + SHA.pattern + ')', out)
        if len(set(found)) != 1:
            raise RuntimeError('Coolify service ' + name + ': ' + ('no' if not found else 'more than one') + ' source commit')
        return found[0]
    if 'profile' in spec:
        value = json.loads(Path(spec['profile']).read_text()).get(spec.get('key', 'commit'))
        if not value or not SHA.fullmatch(str(value)):
            raise RuntimeError(spec['profile'] + ': no commit under "' + spec.get('key', 'commit') + '"')
        return str(value)
    if 'container' in spec:
        names = [n for n in run(['docker', 'ps', '--format', '{{.Names}}']).split() if n.startswith(spec['container'])]
        if not names:
            raise RuntimeError('no running container starting with ' + spec['container'])
        commits = set()
        for name in names:
            image = run(['docker', 'inspect', '--format',
                         '{{.Config.Image}} {{index .Config.Labels "org.opencontainers.image.revision"}}', name]).split()
            tag = image[0].rsplit(':', 1)[-1] if ':' in image[0].split('/')[-1] else ''
            tagged = IMAGE_TAG.fullmatch(tag)
            revision = image[1] if len(image) > 1 else ''
            commit = revision if SHA.fullmatch(revision) else tagged.group(1) if tagged else None
            if not commit:
                raise RuntimeError(name + ': the image names no commit (tag or revision label)')
            commits.add(commit)
        if len(commits) != 1:
            raise RuntimeError(spec['container'] + '*: containers run different commits ' + ', '.join(sorted(commits)))
        return commits.pop()
    raise ValueError('commit_from needs coolify_service, profile or container')


def git(source, *args):
    return run(['git', '-C', str(source), *args]).strip()


def check(config, today=None):
    source = Path(config['source'])
    if config.get('fetch', True):
        git(source, 'fetch', '--quiet', 'origin')
    main = git(source, 'rev-parse', config.get('branch', 'origin/main') + '^{commit}')
    rules = load(source)
    results, problems, drift = {}, [], []
    for stack, spec in sorted(config['stacks'].items()):
        try:
            short = deployed_commit(spec['commit_from'], config)
            try:
                commit = git(source, 'rev-parse', '--verify', '--quiet', short + '^{commit}')
            except RuntimeError:
                raise RuntimeError('runs commit ' + short + ', which this checkout does not know') from None
            entry = {'commit': commit, 'main': main}
            if commit != main:
                try:
                    git(source, 'merge-base', '--is-ancestor', commit, main)
                except RuntimeError:
                    entry['state'] = 'not on main'
                    drift.append(stack + ' runs ' + commit[:12] + ', which is not on main')
                    results[stack] = entry
                    continue
                changed = [f for f in git(source, 'diff', '--name-only', '--no-renames', commit, main).splitlines()
                           if any(stack in r['stacks'] for r in rules_for(f, rules))]
                if changed:
                    entry.update(state='behind', files=changed)
                    drift.append(stack + ' is behind main (' + str(len(changed)) + ' file(s), e.g. ' + changed[0] + ')')
                    results[stack] = entry
                    continue
            entry['state'] = 'clean'
            results[stack] = entry
        except (RuntimeError, ValueError, OSError) as exc:
            results[stack] = {'state': 'unknown', 'error': str(exc)}
            problems.append(stack + ': ' + str(exc))
    served = []
    for item in config.get('served', []):
        try:
            remote = hashlib.sha256(fetch(item['url'])).hexdigest()
            local = hashlib.sha256(Path(item['file']).read_bytes()).hexdigest()
            served.append({'url': item['url'], 'same': remote == local})
            if remote != local:
                drift.append(item['url'] + ' serves different content than ' + item['file'])
        except (OSError, ValueError) as exc:
            served.append({'url': item['url'], 'error': str(exc)})
            problems.append(item['url'] + ': ' + str(exc))
    return {'time': (today or datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'main': main, 'stacks': results, 'served': served, 'drift': drift, 'problems': problems}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Drift check (P59): every stack against main; read-only.')
    parser.add_argument('--config', required=True)
    args = parser.parse_args(argv)
    config = json.loads(Path(args.config).read_text())
    try:
        status = check(config)
    except (RuntimeError, ValueError, OSError) as exc:
        print('drift-check failed: ' + str(exc), file=sys.stderr)
        return 1
    state = Path(config.get('state_dir', '/var/lib/cloud-drift-check'))
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    (state / 'status.json').write_text(json.dumps(status, indent=1) + '\n')
    clean = [s for s, r in status['stacks'].items() if r['state'] == 'clean']
    print('drift-check main ' + status['main'][:12] + ': ' +
          ('DRIFT: ' + '; '.join(status['drift']) if status['drift'] else 'clean') +
          (' | could not check: ' + '; '.join(status['problems']) if status['problems'] else '') +
          ' | clean: ' + (', '.join(clean) or 'none'))
    return 2 if status['drift'] else 1 if status['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
