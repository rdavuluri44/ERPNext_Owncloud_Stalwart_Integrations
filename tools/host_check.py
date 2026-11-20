#!/usr/bin/env python3
"""Host checks for a Docker/Coolify server (P57): after a reboot or restart.

Subcommands (all read a private JSON config, see tools/render_host_checks.py):
  boot          wait until the stacks are up and healthy, repair the one known
                weak spot (the editor bridge not registered), report and exit
                non-zero with a clear message if something stays wrong;
  watch         flag containers whose restart count keeps rising (crash loops);
  wait-tailnet  wait (best effort) until the tailnet address exists, so Docker
                can bind ports to it.

Standard library only. Every outside effect goes through Environment so the
logic is tested without Docker, a network or a clock.
"""
import argparse
import datetime
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULTS = {
    'timeout_seconds': 600,
    'interval_seconds': 15,
    'http_ok': [200, 204, 301, 302, 303, 307, 308, 401, 403],
    'bridge': {'container_prefix': 'collaboration-', 'error_patterns': ['AddAppProvider failed', 'i/o timeout'],
               'quiet_seconds': 120, 'min_uptime_seconds': 45, 'restart_once': True},
    'watch': {'restart_increase': 3},
    'state_dir': '/var/lib/cloud-host-check',
}


class Environment:
    """Real effects; tests pass a fake with the same methods."""

    def run(self, command, timeout=60):
        try:
            done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
            return done.returncode, (done.stdout or '') + (done.stderr or '')
        except (OSError, subprocess.TimeoutExpired) as error:
            return 255, str(error)

    def http(self, url, timeout=10):
        request = urllib.request.Request(url, headers={'User-Agent': 'cloud-host-check'})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def tcp(self, host, port, timeout=5):
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except OSError:
            return False

    def now(self):
        return time.time()

    def sleep(self, seconds):
        time.sleep(seconds)


def load_config(path):
    with open(path, encoding='utf-8') as handle:
        loaded = json.load(handle)
    config = json.loads(json.dumps(DEFAULTS))
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key].update(value)
        else:
            config[key] = value
    for check in config.get('http', []):
        if not str(check.get('url', '')).startswith(('http://', 'https://')):
            raise ValueError('Invalid http check URL for ' + str(check.get('name')))
    return config


def log(message):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ') + message, flush=True)


def parse_started(value):
    """Docker's StartedAt ('2026-11-20T06:07:15.96680943Z') to epoch seconds."""
    text = value.strip()[:19]
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp()


def running_names(env):
    code, out = env.run(['docker', 'ps', '--format', '{{.Names}}'])
    return [line.strip() for line in out.splitlines() if line.strip()] if code == 0 else None


def find_container(names, prefix):
    for name in names or []:
        if name.startswith(prefix):
            return name
    return None


def bridge_state(config, env, names):
    """One reading of the editor bridge: running, uptime and recent error count."""
    bridge = config['bridge']
    name = find_container(names, bridge['container_prefix'])
    if not name:
        return {'name': None, 'ok': False, 'why': 'editor bridge container is not running'}
    code, out = env.run(['docker', 'inspect', '-f', '{{.State.Status}} {{.State.StartedAt}}', name])
    if code != 0:
        return {'name': name, 'ok': False, 'why': 'cannot inspect the editor bridge'}
    status, started = out.split()[:2]
    uptime = env.now() - parse_started(started)
    window = int(min(bridge['quiet_seconds'], max(uptime, 1)))
    code, logs = env.run(['docker', 'logs', '--since', str(window) + 's', name])
    errors = sum(logs.count(pattern) for pattern in bridge['error_patterns'])
    if status != 'running':
        return {'name': name, 'ok': False, 'why': 'editor bridge is ' + status, 'errors': errors}
    if uptime < bridge['min_uptime_seconds']:
        return {'name': name, 'ok': False, 'why': 'editor bridge only just started', 'errors': errors, 'wait': True}
    if errors:
        return {'name': name, 'ok': False, 'why': 'editor bridge logs %d registration errors in the last %ds' % (errors, window),
                'errors': errors}
    return {'name': name, 'ok': True, 'errors': 0}


def evaluate(config, env, names):
    problems = []
    if names is None:
        return ['docker is not answering'], None
    for prefix in config.get('containers', []):
        if not find_container(names, prefix):
            problems.append('container ' + prefix + '* is not running')
    for check in config.get('http', []):
        accepted = check.get('ok', config['http_ok'])
        status = env.http(check['url'])
        if status not in accepted:
            problems.append('%s answers %s (%s)' % (check.get('name', check['url']), status, check['url']))
    for check in config.get('tcp', []):
        if not env.tcp(check['host'], check['port']):
            problems.append('%s is not listening on %s:%s' % (check.get('name', 'port'), check['host'], check['port']))
    bridge = None
    if config.get('bridge', {}).get('container_prefix') and config.get('check_bridge', True):
        bridge = bridge_state(config, env, names)
        if not bridge['ok']:
            problems.append(bridge['why'])
    return problems, bridge


def write_status(config, payload):
    try:
        os.makedirs(config['state_dir'], exist_ok=True)
        path = os.path.join(config['state_dir'], 'status.json')
        with open(path + '.tmp', 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
        os.replace(path + '.tmp', path)
    except OSError as error:
        log('cannot write the status file: ' + str(error))


def boot(config, env):
    """Wait up to timeout_seconds for everything to be up; 0 when it is, 1 when not."""
    started = env.now()
    deadline = started + config['timeout_seconds']
    restarted = False
    attempts = 0
    problems = []
    while True:
        attempts += 1
        names = running_names(env)
        problems, bridge = evaluate(config, env, names)
        if not problems:
            break
        # The one known weak spot: restart the editor bridge once when it cannot register.
        if (bridge and bridge.get('errors') and not bridge.get('wait') and not restarted
                and config['bridge'].get('restart_once')):
            log('restarting the editor bridge once: ' + bridge['why'])
            env.run(['docker', 'restart', bridge['name']], timeout=120)
            restarted = True
        if env.now() >= deadline:
            break
        env.sleep(config['interval_seconds'])
    ok = not problems
    write_status(config, {'ok': ok, 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          'attempts': attempts, 'bridge_restarted': restarted,
                          'waited_seconds': int(env.now() - started), 'problems': problems})
    if ok:
        log('boot check passed after %d attempt(s)%s' % (attempts, ', editor bridge restarted once' if restarted else ''))
        return 0
    log('BOOT CHECK FAILED: ' + '; '.join(problems))
    return 1


def watch(config, env):
    """Compare restart counts with the last run; 1 when a container keeps restarting."""
    names = running_names(env)
    if names is None:
        log('ALERT: docker is not answering')
        return 1
    code, out = env.run(['docker', 'ps', '-a', '--format', '{{.Names}}'])
    everything = [line.strip() for line in out.splitlines() if line.strip()]
    state_path = os.path.join(config['state_dir'], 'restart-counts.json')
    try:
        with open(state_path, encoding='utf-8') as handle:
            before = json.load(handle)
    except (OSError, ValueError):
        before = {}
    now_counts, alerts = {}, []
    ignore = tuple(config.get('watch', {}).get('ignore_prefixes', []))
    threshold = int(config['watch']['restart_increase'])
    for name in everything:
        if ignore and name.startswith(ignore):
            continue
        code, info = env.run(['docker', 'inspect', '-f', '{{.RestartCount}} {{.State.Status}}', name])
        if code != 0 or not info.split():
            continue
        count, status = int(info.split()[0]), info.split()[1]
        now_counts[name] = count
        if status == 'restarting':
            alerts.append(name + ' is restarting right now')
        elif name in before and count - before[name] >= threshold:
            alerts.append('%s restarted %d times since the last check' % (name, count - before[name]))
    try:
        os.makedirs(config['state_dir'], exist_ok=True)
        with open(state_path, 'w', encoding='utf-8') as handle:
            json.dump(now_counts, handle)
        with open(os.path.join(config['state_dir'], 'restart-alerts.json'), 'w', encoding='utf-8') as handle:
            json.dump({'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'alerts': alerts}, handle)
    except OSError as error:
        log('cannot write the watch state: ' + str(error))
    for alert in alerts:
        log('ALERT: ' + alert)
    return 1 if alerts else 0


def wait_tailnet(config, env, timeout):
    """Best effort: wait for the tailnet address; never block boot for long or fail it."""
    address = config.get('tailnet_ip')
    if not address:
        return 0
    deadline = env.now() + timeout
    while True:
        code, out = env.run(['ip', '-4', '-o', 'addr', 'show'])
        if code == 0 and (' ' + address + '/') in (' ' + out.replace('\t', ' ')):
            log('tailnet address ' + address + ' is present')
            return 0
        if env.now() >= deadline:
            log('tailnet address ' + address + ' still missing after ' + str(timeout) + 's; continuing')
            return 0
        env.sleep(2)


def main(argv=None, env=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('command', choices=['boot', 'watch', 'wait-tailnet'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--timeout', type=int, default=60, help='wait-tailnet only')
    args = parser.parse_args(argv)
    config = load_config(args.config)
    env = env or Environment()
    if args.command == 'boot':
        return boot(config, env)
    if args.command == 'watch':
        return watch(config, env)
    return wait_tailnet(config, env, args.timeout)


if __name__ == '__main__':
    sys.exit(main())
