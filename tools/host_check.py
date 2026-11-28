#!/usr/bin/env python3
"""Host checks for a Docker/Coolify server (P57): after a reboot or restart.

Subcommands (all read a private JSON config, see tools/render_host_checks.py):
  boot            wait until the stacks are up and healthy, repair the one known
                  weak spot (the editor bridge not registered), compare with the
                  containers that ran before the reboot and start each missing one
                  once, report and exit non-zero with a clear message if something
                  stays wrong; mail the admin when it repaired or failed something;
  watch           flag containers whose restart count keeps rising (crash loops),
                  and save the list of running containers for the next boot;
  wait-tailnet    wait (best effort) until the tailnet address exists, so Docker
                  can bind ports to it;
  editor          (P80) signed-in check that the office editor is in Drive's app
                  list; when it is missing while Drive is healthy, restart the
                  editor bridge once (at most every repair_interval_seconds),
                  report, and exit non-zero for every run that found it missing;
  editor-restart  (P80) the step every release or rollback runs right after it
                  recreated, restarted or started Drive (ocis): wait until Drive
                  is healthy, restart the editor bridge, wait until the editor is
                  registered again; non-zero when it does not come back;
  editor-setup    (P80) once per host: create the low-rights Drive account the
                  editor check signs in with and its app token (root-only file).

Why the editor needs this: Drive learns which editors exist only when the bridge
(`collaboration`) starts and registers. Recreating or restarting ocis alone
empties that list until the bridge is restarted, and office files then offer
only a download (production, 25 November 2026).

Standard library only. Every outside effect goes through Environment so the
logic is tested without Docker, a network or a clock.
"""
import argparse
import base64
import datetime
import email.message
import json
import os
import re
import secrets
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
    # P80: only active when the config has an "editor" section with a Drive URL.
    'editor': {'account': 'editor-check', 'token_file': '/etc/cloud-host-check/drive-editor.json',
               'provider': 'OnlyOffice', 'extensions': ['docx', 'xlsx', 'pptx'], 'ocis_prefix': 'ocis-',
               'repair': True, 'repair_interval_seconds': 1800, 'registration_wait_seconds': 180,
               'drive_wait_seconds': 300, 'min_drive_uptime_seconds': 60, 'token_expiry': '720h',
               'admin_user': 'admin', 'poll_seconds': 10},
}

TOKEN_IN_TEXT = re.compile(r'[A-Za-z0-9_\-+/=]{16,}')
TOKEN_FROM_CLI = re.compile(r'[Tt]oken[:\s]+([A-Za-z0-9_\-+/=]{16,})')


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

    def request_json(self, method, url, headers=None, body=None, timeout=15):
        """(status, parsed JSON or None). Never raises for HTTP or network errors."""
        data = json.dumps(body).encode() if body is not None else None
        merged = {'User-Agent': 'cloud-host-check', 'Content-Type': 'application/json'}
        merged.update(headers or {})
        request = urllib.request.Request(url, data=data, method=method, headers=merged)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw, status = response.read(), response.status
        except urllib.error.HTTPError as error:
            raw, status = error.read(), error.code
        except (urllib.error.URLError, OSError, ValueError):
            return None, None
        try:
            return status, (json.loads(raw) if raw else None)
        except ValueError:
            return status, None

    def read_secret(self, path):
        try:
            with open(path, encoding='utf-8') as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return None

    def write_secret(self, path, value):
        """Root-only file, written atomically."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        descriptor = os.open(path + '.tmp', os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            json.dump(value, handle)
        os.chmod(path + '.tmp', 0o600)
        os.replace(path + '.tmp', path)

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
        elif editor_enabled(config):
            editor = editor_registered(config, env, names)
            if not editor['ok']:
                problems.append(editor['why'])
                if not editor.get('token_problem'):
                    # Lets boot repair a bridge that logs no error but never registered.
                    bridge.update(errors=1, why=editor['why'])
    return problems, bridge


# ---- P80: the office editor's registration with Drive ----

def editor_enabled(config):
    return bool((config.get('editor') or {}).get('url'))


def redact(text):
    return TOKEN_IN_TEXT.sub('<redacted>', text or '')[:300]


def basic(login, token):
    return {'Authorization': 'Basic ' + base64.b64encode((login + ':' + token).encode()).decode()}


def container_state(env, name):
    """(status, health, uptime seconds) of a container, or None when it cannot be read."""
    code, out = env.run(['docker', 'inspect', '-f',
                         '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} '
                         '{{.State.StartedAt}}', name])
    parts = out.split() if code == 0 else []
    if len(parts) < 3:
        return None
    return parts[0], parts[1], env.now() - parse_started(parts[2])


def drive_ready(config, env, names):
    """Drive (ocis) running, healthy (or without a health check) and up long enough to accept registrations."""
    editor = config['editor']
    name = find_container(names, editor['ocis_prefix'])
    if not name:
        return False, 'Drive (ocis) is not running'
    state = container_state(env, name)
    if not state:
        return False, 'cannot inspect Drive (ocis)'
    status, health, uptime = state
    if status != 'running' or health not in ('healthy', 'none'):
        return False, 'Drive (ocis) is %s/%s' % (status, health)
    if uptime < editor['min_drive_uptime_seconds']:
        return False, 'Drive (ocis) only just started'
    return True, name


def cli_token(env, ocis, user, expiry):
    """An app token made by Drive's own CLI. (token or None, redacted output for messages)."""
    code, out = env.run(['docker', 'exec', ocis, 'ocis', 'auth-app', 'create',
                         '--user-name=' + user, '--expiration=' + expiry], timeout=60)
    found = TOKEN_FROM_CLI.findall(out or '')
    return (found[-1] if code == 0 and found else None), redact(out)


def mint_token(config, env, names):
    """A fresh app token for the check account; stored root-only, never printed. Old tokens expire by themselves."""
    editor = config['editor']
    ocis = find_container(names, editor['ocis_prefix'])
    if not ocis:
        return False, 'Drive (ocis) is not running'
    token, output = cli_token(env, ocis, editor['account'], editor['token_expiry'])
    if not token:
        return False, 'cannot create an app token for %s: %s' % (editor['account'], output)
    stored = env.read_secret(editor['token_file']) or {}
    env.write_secret(editor['token_file'], {'login': stored.get('login') or editor['account'], 'token': token})
    return True, ''


def app_list(config, env, secret):
    url = config['editor']['url'].rstrip('/') + '/app/list'
    return env.request_json('GET', url, basic(secret['login'], secret['token']))


def editor_registered(config, env, names=None):
    """One signed-in reading of Drive's app list: ok, why, token_problem (the check itself could not sign in)."""
    editor = config['editor']
    names = names if names is not None else running_names(env)
    secret = env.read_secret(editor['token_file'])
    if not secret or not secret.get('token'):
        made, why = mint_token(config, env, names)
        if not made:
            return {'ok': False, 'why': 'editor check cannot sign in: ' + why, 'token_problem': True}
        secret = env.read_secret(editor['token_file'])
    status, body = app_list(config, env, secret)
    if status == 401:
        # Expired or revoked token: make a new one once.
        made, why = mint_token(config, env, names)
        if not made:
            return {'ok': False, 'why': 'editor check cannot sign in: ' + why, 'token_problem': True}
        status, body = app_list(config, env, env.read_secret(editor['token_file']))
    if status != 200 or not isinstance(body, dict):
        return {'ok': False, 'why': 'Drive app list answers %s' % status, 'token_problem': True}
    rows = body.get('mime-types') or []
    have = {row.get('ext') for row in rows
            if any(p.get('name') == editor['provider'] for p in row.get('app_providers') or [])}
    missing = [ext for ext in editor['extensions'] if ext not in have]
    if missing:
        return {'ok': False, 'why': '%s is not registered with Drive (no editor for %s): office files only download'
                                    % (editor['provider'], ', '.join(missing))}
    return {'ok': True, 'why': ''}


def wait_registered(config, env, seconds):
    deadline = env.now() + seconds
    while True:
        state = editor_registered(config, env)
        if state['ok'] or env.now() >= deadline:
            return state
        env.sleep(config['editor']['poll_seconds'])


def wait_drive(config, env, seconds):
    deadline = env.now() + seconds
    while True:
        ready, why = drive_ready(config, env, running_names(env))
        if ready or env.now() >= deadline:
            return ready, why
        env.sleep(config['editor']['poll_seconds'])


def write_json(config, name, payload):
    try:
        os.makedirs(config['state_dir'], exist_ok=True)
        path = os.path.join(config['state_dir'], name)
        with open(path + '.tmp', 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2)
        os.replace(path + '.tmp', path)
    except OSError as error:
        log('cannot write ' + name + ': ' + str(error))


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



def read_json(config, name):
    try:
        with open(os.path.join(config['state_dir'], name), encoding='utf-8') as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def restart_bridge(config, env, names):
    name = find_container(names, config['bridge']['container_prefix'])
    if not name:
        return False, 'editor bridge container is not running'
    code, out = env.run(['docker', 'restart', name], timeout=120)
    return code == 0, ('' if code == 0 else 'docker restart failed: ' + redact(out))


def editor_check(config, env):
    """P80 (D), every five minutes: 0 registered; 1 when it was missing (repaired or not) or the check cannot sign in."""
    if not editor_enabled(config):
        log('editor check is not configured (no editor.url)')
        return 0
    names = running_names(env)
    if names is None:
        log('ALERT: docker is not answering')
        return 1
    state = editor_registered(config, env, names)
    status = {'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'registered': state['ok'],
              'problem': state['why'], 'repaired': False}
    if state['ok']:
        write_json(config, 'editor-status.json', status)
        return 0
    editor = config['editor']
    if state.get('token_problem'):
        log('ALERT: ' + state['why'])
    elif not editor['repair']:
        log('ALERT: ' + state['why'] + ' (automatic repair is off)')
    else:
        ready, why = drive_ready(config, env, names)
        since = env.now() - read_json(config, 'editor-repair.json').get('at', 0)
        if not ready:
            log('ALERT: ' + state['why'] + '; not repairing: ' + why)
        elif since < editor['repair_interval_seconds']:
            log('ALERT: ' + state['why'] + '; the bridge was restarted %ds ago, not again yet' % int(since))
        else:
            log('ALERT: ' + state['why'] + '; restarting the editor bridge')
            write_json(config, 'editor-repair.json', {'at': env.now(), 'reason': state['why']})
            restarted, why = restart_bridge(config, env, names)
            after = (wait_registered(config, env, editor['registration_wait_seconds']) if restarted
                     else {'ok': False, 'why': why})
            status.update(repaired=after['ok'], registered=after['ok'])
            if after['ok']:
                log('ALERT: the editor was not registered; repaired by restarting the editor bridge')
            else:
                status['problem'] = after['why']
                log('ALERT: the editor is still not registered after restarting the bridge: ' + after['why'])
    write_json(config, 'editor-status.json', status)
    return 1


def editor_restart(config, env):
    """P80 (A): the one step after any ocis recreate, restart or start. 0 when the editor is registered again."""
    editor = config['editor']
    ready, why = wait_drive(config, env, editor['drive_wait_seconds'])
    if not ready:
        log('EDITOR RESTART FAILED: Drive is not ready after %ds: %s' % (editor['drive_wait_seconds'], why))
        return 1
    restarted, why = restart_bridge(config, env, running_names(env))
    if not restarted:
        log('EDITOR RESTART FAILED: ' + why)
        return 1
    if editor_enabled(config):
        state = wait_registered(config, env, editor['registration_wait_seconds'])
        if not state['ok']:
            log('EDITOR RESTART FAILED: ' + state['why'])
            return 1
        log('editor bridge restarted; %s is registered with Drive' % editor['provider'])
        return 0
    # Without the signed-in check: the bridge must stay up and log no registration error.
    deadline = env.now() + editor['registration_wait_seconds']
    while True:
        env.sleep(config['bridge']['min_uptime_seconds'])
        bridge = bridge_state(config, env, running_names(env))
        if bridge['ok']:
            log('editor bridge restarted; no registration errors (no signed-in check configured)')
            return 0
        if env.now() >= deadline:
            log('EDITOR RESTART FAILED: ' + bridge['why'])
            return 1


def editor_setup(config, env):
    """P80, once per host as root: the check account (a normal user with a random password nobody keeps) and its
    app token. A temporary admin app token (10 minutes) is used only to look up and create the account."""
    if not editor_enabled(config):
        log('editor-setup: no editor.url in the config')
        return 1
    editor = config['editor']
    names = running_names(env)
    ocis = find_container(names, editor['ocis_prefix'])
    if not ocis:
        log('editor-setup: Drive (ocis) is not running')
        return 1
    token, output = cli_token(env, ocis, editor['admin_user'], '10m')
    if not token:
        log('editor-setup: cannot create a temporary admin token: ' + output)
        return 1
    admin = basic(editor['admin_user'], token)
    users = editor['url'].rstrip('/') + '/graph/v1.0/users'
    # Lookup by name: oCIS 8.2 answers 501 to a $filter on onPremisesSamAccountName.
    status, body = env.request_json('GET', users + '/' + editor['account'], admin)
    if status not in (200, 404):
        log('editor-setup: user lookup answers %s' % status)
        return 1
    if status == 200:
        log('editor-setup: account %s already exists' % editor['account'])
    else:
        status, body = env.request_json('POST', users, admin, {
            'displayName': 'Editor registration check', 'onPremisesSamAccountName': editor['account'],
            'mail': editor['account'] + '@example.invalid',
            'passwordProfile': {'password': secrets.token_urlsafe(32)}})
        if status not in (200, 201):
            log('editor-setup: creating %s answers %s' % (editor['account'], status))
            return 1
        log('editor-setup: account %s created' % editor['account'])
    env.write_secret(editor['token_file'], {'login': editor['account'], 'token': ''})
    made, why = mint_token(config, env, names)
    if not made:
        log('editor-setup: ' + why)
        return 1
    state = editor_registered(config, env, names)
    log('editor-setup: token stored in %s (root only); check: %s'
        % (editor['token_file'], 'registered' if state['ok'] else state['why']))
    return 1 if state.get('token_problem') else 0


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
    parser.add_argument('command', choices=['boot', 'watch', 'wait-tailnet', 'editor', 'editor-restart',
                                            'editor-setup'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--timeout', type=int, default=60, help='wait-tailnet only')
    args = parser.parse_args(argv)
    config = load_config(args.config)
    env = env or Environment()
    if args.command == 'boot':
        return boot(config, env)
    if args.command == 'watch':
        return watch(config, env)
    if args.command == 'editor':
        return editor_check(config, env)
    if args.command == 'editor-restart':
        return editor_restart(config, env)
    if args.command == 'editor-setup':
        return editor_setup(config, env)
    return wait_tailnet(config, env, args.timeout)


if __name__ == '__main__':
    sys.exit(main())
