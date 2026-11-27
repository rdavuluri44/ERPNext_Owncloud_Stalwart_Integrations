#!/usr/bin/env python3
"""Send an alert to the ERP alert inbox (P72, P53). Every check on every server reports through this one tool.

  send --key K --severity S --title T [--detail D] [--link L] [--resolved]
        one alert (or its resolve) to the inbox; exit 0 when delivered or, for a critical alert the inbox
        could not take, mailed directly instead (fallback_mail); 1 otherwise.
  run --key K --title T [--severity critical] [--warn-exit N ...] [--link L] -- COMMAND...
        run a check, pass its output through unchanged (the journal keeps it), then report: exit 0 resolves K,
        a failure opens it (warning for the exit codes in --warn-exit) with the check's DOWN / ALERT / FAIL /
        ERROR / DRIFT / "Upgrade now" lines, or its last 10 lines. Exits with the check's own exit code.

Config (JSON, default /etc/cloud-alerts/config.json, root-only): `url` (the report method on ERP), `source`
(this server's source name in the ERP site config), `token_file` (root-only file with the token; ERP stores only
its SHA-256), optional `host` (label shown with the alert), `address` (connect to this address but verify the
certificate for the URL's host name), `timeout` (seconds, default 10) and `fallback_mail` (path to the host-check
config whose `alert` section host_check.py mails with). The token is never printed.

Standard library only, Python 3.9 or newer.
"""
import argparse
import http.client
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import threading
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import host_check  # noqa: E402  (its mail sender is the fallback when ERP is unreachable)

DEFAULT_CONFIG = '/etc/cloud-alerts/config.json'
HEADER = 'X-Alert-Token'  # not Authorization: Frappe refuses an unknown two-part Authorization header itself
MARKED = re.compile(r'^\s*(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d\S*\s+)?(DOWN|ALERT|FAIL|ERROR|DRIFT|Upgrade now)')
LIMITS = {'title': 140, 'detail': 2000, 'link': 300, 'host': 64}


class AddressHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS to `address` (for example a tailnet address) with the certificate verified for `host`."""

    def __init__(self, host, address, port=443, timeout=10, context=None):
        super().__init__(host, port, timeout=timeout, context=context or ssl.create_default_context())
        self.address = address
        self.context = context or self._context

    def connect(self):
        raw = socket.create_connection((self.address, self.port), self.timeout, self.source_address)
        self.sock = self.context.wrap_socket(raw, server_hostname=self.host)


def load_config(path):
    with open(path, encoding='utf-8') as handle:
        config = json.load(handle)
    for key in ('url', 'source', 'token_file'):
        if not config.get(key):
            raise ValueError(f'{path}: {key} is missing')
    if urllib.parse.urlsplit(config['url']).scheme != 'https':
        raise ValueError(f'{path}: url must be https')
    return config


def read_token(config):
    with open(config['token_file'], encoding='utf-8') as handle:
        return handle.read().strip()


def payload(config, key, severity, title, detail='', link='', resolved=False):
    host = config.get('host') or socket.gethostname().split('.')[0]
    body = {'source': config['source'], 'key': key, 'severity': severity, 'state': 'resolved' if resolved else 'open',
            'title': title, 'detail': detail, 'host': host, 'link': link}
    return {k: (v[:LIMITS[k]] if k in LIMITS else v) for k, v in body.items() if v not in ('', None)}


def post(config, body, token, connection=AddressHTTPSConnection):
    """POST the alert; returns the HTTP status (raises OSError and http.client errors on network failures)."""
    url = urllib.parse.urlsplit(config['url'])
    conn = connection(url.hostname, config.get('address') or url.hostname, url.port or 443,
                      timeout=float(config.get('timeout', 10)))
    try:
        conn.request('POST', (url.path or '/') + ('?' + url.query if url.query else ''), json.dumps(body).encode(),
                     {'Content-Type': 'application/json', 'Accept': 'application/json', HEADER: token,
                      'User-Agent': 'cloud-send-alert'})
        response = conn.getresponse()
        response.read()
        return response.status
    finally:
        conn.close()


def fallback_mail(config, body):
    """Mail a critical alert directly through the host-check sender; True when sent."""
    path = config.get('fallback_mail')
    alert = host_check.load_config(path).get('alert') if path else None
    if not alert:
        return False
    text = '\n'.join([f"Source: {body['source']}", f"Host: {body.get('host', '-')}", f"Severity: {body['severity']}",
                      f"Key: {body['key']}", '', body.get('detail', ''), '', body.get('link', ''),
                      'The ERP alert inbox could not be reached, so this was mailed directly.'])
    host_check.Environment().send_mail(alert, '[Alert, ERP unreachable] ' + body['title'], text.strip() + '\n')
    return True


def attempt(config, body, connection):
    """None when the inbox took the alert, else why not: ('refused', reason) or ('unreachable', reason)."""
    try:
        token = read_token(config)
    except OSError as error:
        return 'unreachable', f'cannot read the token file, {type(error).__name__}'
    try:
        status = post(config, body, token, connection)
    except (OSError, http.client.HTTPException, ValueError) as error:
        return 'unreachable', type(error).__name__
    if 200 <= status < 300:
        return None
    return ('refused' if 400 <= status < 500 else 'unreachable'), f'HTTP {status}'


def deliver(config, body, connection=AddressHTTPSConnection):
    """Send to the inbox; when it is unreachable, mail a critical open alert directly. True when it got through."""
    failure = attempt(config, body, connection)
    if failure is None:
        return True
    kind, reason = failure
    print(f'send_alert: the alert inbox {"refused" if kind == "refused" else "is unreachable for"} '
          f'{body["key"]} ({reason})', file=sys.stderr)
    if kind == 'refused' or body['severity'] != 'critical' or body['state'] == 'resolved':
        return False
    try:
        if fallback_mail(config, body):
            print('send_alert: mailed the alert directly instead', file=sys.stderr)
            return True
    except Exception as error:  # the fallback must never hide the original failure
        print(f'send_alert: the fallback mail failed too ({type(error).__name__})', file=sys.stderr)
    return False


def run_command(command, out=None, err=None):
    """Run the check, copying its stdout and stderr through unchanged; returns (exit code, output lines)."""
    out = out or sys.stdout.buffer
    err = err or sys.stderr.buffer
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as error:
        line = f'ERROR cannot run {command[0]}: {error.strerror or type(error).__name__}'
        err.write((line + '\n').encode())
        return 127, [line]
    lines, lock = [], threading.Lock()

    def pump(stream, target):
        for raw in iter(stream.readline, b''):
            target.write(raw)
            target.flush()
            with lock:
                lines.append(raw.decode('utf-8', 'replace').rstrip('\r\n'))
        stream.close()

    threads = [threading.Thread(target=pump, args=(process.stdout, out)),
               threading.Thread(target=pump, args=(process.stderr, err))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    code = process.wait()
    return (128 - code if code < 0 else code), lines


def summary(lines):
    """The check's marked lines (max 20 of 200 characters), else its last 10 lines."""
    marked = [line.strip()[:200] for line in lines if MARKED.match(line)][:20]
    return '\n'.join(marked or [line[:200] for line in lines[-10:]])


def parser():
    top = argparse.ArgumentParser(description='Send an alert to the ERP alert inbox.')
    top.add_argument('--config', default=DEFAULT_CONFIG)
    commands = top.add_subparsers(dest='command', required=True)
    send = commands.add_parser('send')
    send.add_argument('--key', required=True)
    send.add_argument('--severity', required=True, choices=['critical', 'warning', 'info'])
    send.add_argument('--title', required=True)
    send.add_argument('--detail', default='')
    send.add_argument('--link', default='')
    send.add_argument('--resolved', action='store_true')
    run = commands.add_parser('run')
    run.add_argument('--key', required=True)
    run.add_argument('--title', required=True)
    run.add_argument('--severity', default='critical', choices=['critical', 'warning', 'info'])
    run.add_argument('--warn-exit', type=int, nargs='+', action='extend', default=[])
    run.add_argument('--link', default='')
    run.add_argument('check', nargs=argparse.REMAINDER)
    return top


def main(argv=None, connection=AddressHTTPSConnection, out=None, err=None):
    """`out` and `err` receive the check's own output (binary streams; default the real ones)."""
    args = parser().parse_args(argv)
    if args.command == 'run':
        check = args.check[1:] if args.check[:1] == ['--'] else args.check
        if not check:
            print('send_alert: run needs a command after --', file=sys.stderr)
            return 2
        code, lines = run_command(check, out, err)
    try:
        config = load_config(args.config)
    except (OSError, ValueError) as error:
        print(f'send_alert: cannot read the config ({type(error).__name__}: {error})', file=sys.stderr)
        return code if args.command == 'run' else 1
    if args.command == 'send':
        body = payload(config, args.key, args.severity, args.title, args.detail, args.link, args.resolved)
        return 0 if deliver(config, body, connection) else 1
    if code == 0:
        body = payload(config, args.key, args.severity, args.title, link=args.link, resolved=True)
    else:
        severity = 'warning' if code in args.warn_exit else args.severity
        body = payload(config, args.key, severity, args.title, summary(lines), args.link)
    deliver(config, body, connection)  # a failure is one line on stderr; the check's exit code stands
    return code


if __name__ == '__main__':
    sys.exit(main())
