#!/usr/bin/env python3
"""Drift check (P59): is every stack running what main says it should?

For each stack named in the private settings, finds the commit it runs and compares it with main:
the stack is behind when a file it owns (deployment/promotion-map.json) changed since that commit.
Also compares served content with a local file (for example the landing page script), and (P99) every
read-only runtime file the running containers mount from this repository: a mounted file that equals main
does not count as behind even when the stack's commit is older; one that differs from what was deployed
("changed by hand") or is older than main counts as drift; one with no record and no exact match is listed as
not compared. Read-only: it reads git, the commit records, the mounted files and public pages, and changes
nothing.

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
from promotion_plan import parse_rules, rules_for  # noqa: E402
import runtime_mounts  # noqa: E402

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


def expected_hash(item):
    if "container" not in item:
        return hashlib.sha256(Path(item["file"]).read_bytes()).hexdigest()
    container = item["container"]
    path = item["file"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", container) or not Path(path).is_absolute():
        raise ValueError("expected a container name and absolute file path")
    output = run(["docker", "exec", container, "sha256sum", "--", path])
    digest, _, _ = output.partition(" ")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("could not read the file checksum")
    return digest


def mounted_files(source, main):
    """Read-only bind mounts of the running containers that are made from repository files (P99)."""
    try:
        listed = git(source, 'ls-tree', '--name-only', main, 'deployment/stacks/mounts.json')
    except RuntimeError:
        listed = ''
    if not listed:
        return []  # a checkout without the stack mounts list (sample repositories in tests)
    catalogue = {m['path']: m for m in json.loads(git(source, 'show', main + ':deployment/stacks/mounts.json'))}
    found = {}
    for name in run(['docker', 'ps', '--format', '{{.Names}}']).split():
        for mount in json.loads(run(['docker', 'inspect', '--format', '{{json .Mounts}}', name]) or '[]') or []:
            if mount.get('Type') != 'bind' or mount.get('RW', True):
                continue
            path = Path(mount.get('Source', ''))
            item = catalogue.get(path.name)
            if path.parent.name != 'mounts' or item is None:
                continue
            relative = runtime_mounts.source_of(item)
            if not relative:
                continue  # data, secrets and operator-owned files are not compared
            entry = found.setdefault(str(path), {'mount': path.name, 'stack': item['stack'], 'source': relative,
                                                 'path': path, 'runtime': path.parent.parent, 'containers': []})
            entry['containers'].append(name)
    return [found[key] for key in sorted(found)]


def mount_state(source, main, entry):
    """'equal to main', 'behind', 'changed by hand' or 'not compared', with a reason."""
    path, relative = entry['path'], entry['source']
    if path.is_file() and not path.is_symlink():
        try:
            same = git(source, 'hash-object', '--no-filters', '--', str(path)) == git(source, 'rev-parse', main + ':' + relative)
        except RuntimeError:
            same = False
        if same:
            return 'equal to main', 'same bytes as the file on main'
    record = runtime_mounts.read_record(entry['runtime']).get(entry['mount'])
    if not record:
        return 'not compared', 'no record of what was deployed, and not byte-equal to main'
    if record.get('sha256') != runtime_mounts.digest(path):
        return 'changed by hand', 'differs from what was deployed from ' + str(record.get('commit') or 'an unknown commit')[:12]
    commit = record.get('commit')
    if not commit:
        return 'not compared', 'the record names no commit'
    try:
        commit = git(source, 'rev-parse', '--verify', '--quiet', commit + '^{commit}')
    except RuntimeError:
        return 'not compared', 'deployed from ' + commit[:12] + ', which this checkout does not know'
    if git(source, 'diff', '--name-only', commit, main, '--', relative):
        return 'behind', 'deployed from ' + commit[:12] + '; the source changed on main since'
    return 'equal to main', 'deployed from ' + commit[:12] + '; the source is unchanged on main'


def compare_mounts(source, main, results, problems):
    rows = []
    try:
        entries = mounted_files(source, main)
    except (RuntimeError, ValueError, OSError) as exc:
        problems.append('mounted files: ' + str(exc))
        return rows
    for entry in entries:
        try:
            state, reason = mount_state(source, main, entry)
        except (RuntimeError, ValueError, OSError) as exc:
            state, reason = 'not compared', str(exc)
        rows.append({'mount': entry['mount'], 'stack': entry['stack'], 'source': entry['source'],
                     'runtime': str(entry['runtime']), 'state': state, 'reason': reason})
        stack = results.get(entry['stack'])
        if not stack or stack.get('state') not in ('clean', 'behind'):
            continue
        relative = entry['source']
        inside = (lambda f: f == relative or f.startswith(relative + '/'))
        if state == 'equal to main' and stack.get('files'):
            stack['files'] = [f for f in stack['files'] if not inside(f)]
            stack.setdefault('equal_mounts', []).append(entry['mount'])
        elif state == 'behind' and not any(inside(f) for f in stack.get('files', [])):
            stack.setdefault('files', []).append(relative)
    for stack in results.values():
        if stack.get('state') in ('clean', 'behind'):
            stack['state'] = 'behind' if stack.get('files') else 'clean'
            if not stack.get('files'):
                stack.pop('files', None)
    return rows


def check(config, today=None):
    source = Path(config['source'])
    if config.get('fetch', True):
        git(source, 'fetch', '--quiet', 'origin')
    main = git(source, 'rev-parse', config.get('branch', 'origin/main') + '^{commit}')
    rules = parse_rules(git(source, "show", main + ":deployment/promotion-map.json"))
    results, problems, drift = {}, [], []
    if not config["stacks"]:
        raise ValueError("configure at least one stack")
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
                files = git(source, "diff", "--name-only", "--no-renames", "-z", commit, main).split("\0")
                changed = []
                for path in filter(None, files):
                    matching = rules_for(path, rules)
                    if not matching:
                        raise ValueError("no promotion rule for " + path)
                    if any(stack in rule["stacks"] for rule in matching):
                        changed.append(path)
                if changed:
                    entry.update(state='behind', files=changed)
                    results[stack] = entry
                    continue
            entry['state'] = 'clean'
            results[stack] = entry
        except (RuntimeError, ValueError, OSError) as exc:
            results[stack] = {'state': 'unknown', 'error': str(exc)}
            problems.append(stack + ': ' + str(exc))
    mounts = compare_mounts(source, main, results, problems) if config.get('mounts', True) else []
    for stack, entry in sorted(results.items()):
        if entry.get('state') == 'behind':
            drift.append(stack + ' is behind main (' + str(len(entry['files'])) + ' file(s), e.g. ' + entry['files'][0] + ')')
    for row in mounts:
        if row['state'] == 'changed by hand':
            drift.append(row['stack'] + ': mounted ' + row['mount'] + ' (' + row['source'] + ') ' + row['reason'])
        elif row['state'] == 'behind' and row['stack'] not in results:
            drift.append(row['stack'] + ': mounted ' + row['mount'] + ' (' + row['source'] + ') is behind main')
    served = []
    for item in config.get('served', []):
        try:
            remote = hashlib.sha256(fetch(item['url'])).hexdigest()
            local = expected_hash(item)
            served.append({'url': item['url'], 'same': remote == local})
            if remote != local:
                drift.append(item['url'] + ' serves different content than ' + item['file'])
        except (OSError, RuntimeError, ValueError) as exc:
            served.append({'url': item['url'], 'error': str(exc)})
            problems.append(item['url'] + ': ' + str(exc))
    return {'time': (today or datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'main': main, 'stacks': results, 'mounts': mounts, 'served': served, 'drift': drift, 'problems': problems}


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
          (' | mounted files not compared: ' + str(sum(r['state'] == 'not compared' for r in status['mounts']))
           if any(r['state'] == 'not compared' for r in status['mounts']) else '') +
          ' | clean: ' + (', '.join(clean) or 'none'))
    return 2 if status['drift'] else 1 if status['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
