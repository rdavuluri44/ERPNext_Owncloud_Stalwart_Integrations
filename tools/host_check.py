#!/usr/bin/env python3
"""Host checks for a Docker/Coolify server (P57): after a reboot or restart.

Subcommands (all read a private JSON config, see tools/render_host_checks.py):
  boot          wait until the stacks are up and healthy, repair the one known
                weak spot (the editor bridge not registered), compare with the
                containers that ran before the reboot and start each missing one
                once, report and exit non-zero with a clear message if something
                stays wrong; mail the admin when it repaired or failed something;
  watch         flag containers whose restart count keeps rising (crash loops),
                and save the list of running containers for the next boot;
  wait-tailnet  wait (best effort) until the tailnet address exists, so Docker
                can bind ports to it.

Standard library only. Every outside effect goes through Environment so the
logic is tested without Docker, a network or a clock.
"""
import argparse
import datetime
import email.message
import json
import os
import smtplib
import socket
import ssl
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
    # P57 follow-up 7: containers that ran before the reboot must run again; each missing one is started once.
    'after_reboot': {'start_missing': True, 'start_after_seconds': 60, 'policies': ['always', 'unless-stopped']},
    'alert': None,
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

    def boot_id(self):
        try:
            with open('/proc/sys/kernel/random/boot_id', encoding='ascii') as handle:
                return handle.read().strip()
        except OSError:
            return None

    def send_mail(self, alert, subject, body):
        """One plain-text mail through the dedicated sender; the password is read from its root-only file."""
        with open(alert['password_file'], encoding='utf-8') as handle:
            password = handle.read().strip()
        message = email.message.EmailMessage()
        message['From'], message['To'], message['Subject'] = alert['sender'], ', '.join(alert['to']), subject
        message.set_content(body)
        server = verified_smtp(alert, ssl.create_default_context())
        with server:
            server.login(alert['username'], password)
            server.send_message(message)


def verified_smtp(alert, context, timeout=30):
    """Open the SMTP connection for the alert sender. With `address` set (for example the mail server's tailnet
    address, when the server cannot reach its own public name), connect there but still verify the certificate for
    `smtp_host`; certificate checks are never switched off (P57 follow-up 10)."""
    hostname, port = alert['smtp_host'], int(alert['smtp_port'])
    address = alert.get('address') or hostname
    implicit = alert.get('security', 'ssl') == 'ssl'
    base = smtplib.SMTP_SSL if implicit else smtplib.SMTP

    class Verified(base):
        def _get_socket(self, host, port, timeout):
            raw = socket.create_connection((address, port), timeout, self.source_address)
            return context.wrap_socket(raw, server_hostname=hostname) if implicit else raw

    if implicit:
        return Verified(hostname, port, timeout=timeout, context=context)
    server = Verified(hostname, port, timeout=timeout)
    server.starttls(context=context)  # verifies the certificate for smtp_host as well
    return server


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


def ignored(config, name):
    prefixes = tuple(config.get('watch', {}).get('ignore_prefixes', []))
    return bool(prefixes) and name.startswith(prefixes)


def restart_policies(env, names):
    """{name: restart policy} for the given containers, in one docker call."""
    if not names:
        return {}
    code, out = env.run(['docker', 'inspect', '-f', '{{.Name}} {{.HostConfig.RestartPolicy.Name}}', *names])
    if code != 0:
        return {}
    found = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            found[parts[0].lstrip('/')] = parts[1]
    return found


def snapshot_path(config):
    return os.path.join(config['state_dir'], 'running-containers.json')


def save_snapshot(config, env, names):
    """The containers running now, so the next boot can tell which did not come back (P57 follow-up 7)."""
    if names is None:
        return
    keep = [name for name in names if not ignored(config, name)]
    payload = {'boot_id': env.boot_id(), 'taken_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'containers': restart_policies(env, keep)}
    try:
        os.makedirs(config['state_dir'], exist_ok=True)
        path = snapshot_path(config)
        with open(path + '.tmp', 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
        os.replace(path + '.tmp', path)
    except OSError as error:
        log('cannot save the container list: ' + str(error))


def expected_after_reboot(config, env):
    """Containers that ran in an earlier boot and should restart by themselves; empty in the same boot."""
    try:
        with open(snapshot_path(config), encoding='utf-8') as handle:
            saved = json.load(handle)
    except (OSError, ValueError):
        return [], None
    if not saved.get('boot_id') or saved.get('boot_id') == env.boot_id():
        return [], saved.get('taken_at')
    policies = set(config['after_reboot']['policies'])
    names = [name for name, policy in sorted((saved.get('containers') or {}).items())
             if policy in policies and not ignored(config, name)]
    return names, saved.get('taken_at')


def notify(config, env, subject, body):
    """Mail the admin through the dedicated sender; a failure to send is logged, never fatal."""
    alert = config.get('alert')
    if not alert:
        log('no alert sender configured; result is in the status file and the journal only')
        return False
    try:
        env.send_mail(alert, subject, body)
        log('alert mailed to ' + ', '.join(alert['to']))
        return True
    except Exception as error:  # the boot check must finish even when mail is down
        log('ALERT NOT SENT (' + type(error).__name__ + '): ' + subject)
        return False


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
    expected, snapshot_taken = expected_after_reboot(config, env)
    after = config['after_reboot']
    started_once, start_failed = [], []
    while True:
        attempts += 1
        names = running_names(env)
        problems, bridge = evaluate(config, env, names)
        missing = [name for name in expected if names is not None and name not in names]
        # P57 follow-up 7: a container that ran before the reboot and did not come back by itself is started once,
        # after Docker had time to start everything it starts on its own.
        if missing and after.get('start_missing') and env.now() - started >= after['start_after_seconds']:
            for name in missing:
                if name in started_once or name in start_failed:
                    continue
                code, out = env.run(['docker', 'start', name], timeout=120)
                if code == 0:
                    log('started ' + name + ' once: it ran before the reboot and did not come back by itself')
                    started_once.append(name)
                else:
                    log('could not start ' + name + ': ' + out.strip()[:200])
                    start_failed.append(name)
            names = running_names(env)
            missing = [name for name in expected if names is not None and name not in names]
        problems += ['%s ran before the reboot and is not running' % name for name in missing]
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
                          'waited_seconds': int(env.now() - started), 'problems': problems,
                          'compared_with_containers_from': snapshot_taken, 'expected_after_reboot': len(expected),
                          'started_after_reboot': started_once, 'could_not_start': start_failed})
    save_snapshot(config, env, running_names(env))
    host = socket.gethostname()
    if ok:
        log('boot check passed after %d attempt(s)%s%s' % (
            attempts, ', editor bridge restarted once' if restarted else '',
            (', started once: ' + ', '.join(started_once)) if started_once else ''))
        if started_once or restarted:
            notify(config, env, '[%s] boot check repaired something' % host, boot_report(
                host, True, started_once, start_failed, restarted, problems, expected, snapshot_taken))
        return 0
    log('BOOT CHECK FAILED: ' + '; '.join(problems))
    notify(config, env, '[%s] BOOT CHECK FAILED' % host, boot_report(
        host, False, started_once, start_failed, restarted, problems, expected, snapshot_taken))
    return 1


def boot_report(host, ok, started_once, start_failed, restarted, problems, expected, snapshot_taken):
    lines = ['Boot check on %s: %s.' % (host, 'passed after a repair' if ok else 'FAILED'), '']
    if started_once:
        lines += ['Started once because they ran before the reboot and did not come back by themselves:']
        lines += ['  - ' + name for name in started_once] + ['']
    if start_failed:
        lines += ['Could not be started:'] + ['  - ' + name for name in start_failed] + ['']
    if restarted:
        lines += ['The editor bridge was restarted once (it could not register).', '']
    if problems:
        lines += ['Still wrong:'] + ['  - ' + problem for problem in problems] + ['']
    lines += ['Compared with %d containers that ran before the reboot (list from %s).' % (len(expected), snapshot_taken),
              'Status file: /var/lib/cloud-host-check/status.json; journal: journalctl -u cloud-boot-check.',
              'Procedure: docs/production-moves.md, "After a reboot or restart"; SOP: admin alerts and daily checks.']
    return '\n'.join(lines) + '\n'



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
    save_snapshot(config, env, names)
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
