#!/usr/bin/env python3
"""Render the host check config and systemd files for one server (P57).

Reads the deployment's private profile (the same JSON the other renderers use,
with an optional "host_checks" section) and writes into an output directory:
  config.json                      the check configuration (hosts from the profile)
  cloud-boot-check.service         runs the boot check after Docker and Tailscale
  cloud-restart-watch.service/.timer   crash-loop watch every five minutes
  docker.service.d/10-after-tailscale.conf   Docker starts after Tailscale
Nothing is installed; docs/production-moves.md lists the copy commands.
No host name, address or tenant detail lives in Git: they come from the profile.
"""
import argparse
import ipaddress
import json
import re
from pathlib import Path

INSTALL_DIR = '/opt/cloud-host-check'
CONFIG_PATH = '/etc/cloud-host-check/config.json'

# Public host key -> path to request and statuses that count as up.
HOST_PATHS = {'erp': ('/', None), 'sso': ('/', None), 'drive': ('/', None), 'mail': ('/', None),
              'dms': ('/', None), 'office': ('/healthcheck', [200])}


def bridge_wanted(profile, options):
    """Check the editor bridge when the host runs Drive. A host whose checks are rendered from a profile
    without Drive (for example the ERP profile on a server that also runs Drive) says so explicitly
    with host_checks.check_bridge."""
    if 'check_bridge' in options:
        if not isinstance(options['check_bridge'], bool):
            raise ValueError('host_checks.check_bridge must be true or false')
        return options['check_bridge']
    return 'drive' in (profile.get('projects') or ['drive'])


def build_config(profile):
    hosts = profile.get('hosts') or {}
    options = profile.get('host_checks') or {}
    checks = []
    for key, (path, ok) in HOST_PATHS.items():
        host = hosts.get(key)
        if not host:
            continue
        if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
            raise ValueError('Invalid host name for ' + key)
        item = {'name': key, 'url': 'https://' + host + path}
        if ok:
            item['ok'] = ok
        checks.append(item)
    config = {'http': checks, 'containers': list(options.get('containers', [])),
              'tcp': list(options.get('tcp', [])), 'check_bridge': bridge_wanted(profile, options),
              'bridge': {'container_prefix': options.get('bridge_prefix', 'collaboration-')}}
    if options.get('tailnet_ip'):
        if not re.fullmatch(r'[0-9.]+', options['tailnet_ip']):
            raise ValueError('Invalid tailnet address')
        config['tailnet_ip'] = options['tailnet_ip']
    if options.get('ignore_prefixes'):
        config['watch'] = {'ignore_prefixes': list(options['ignore_prefixes'])}
    if options.get('alert'):
        config['alert'] = alert_config(options['alert'])
    for check in config['tcp']:
        if not re.fullmatch(r'[0-9.]+', str(check.get('host', ''))) or not str(check.get('port', '')).isdigit():
            raise ValueError('Invalid tcp check')
    return config


def alert_config(alert):
    """The dedicated alert sender (P57 follow-up 7, owner 26 November 2026): SMTP host, port, account, password file,
    sender and the admin's address. The password itself stays in its root-only file on the server."""
    if not isinstance(alert, dict):
        raise ValueError('host_checks.alert must be an object')
    host, port = str(alert.get('smtp_host', '')), alert.get('smtp_port')
    if not re.fullmatch(r'[A-Za-z0-9.-]+', host) or not isinstance(port, int) or not 0 < port < 65536:
        raise ValueError('Invalid alert SMTP host or port')
    if alert.get('security', 'ssl') not in ('ssl', 'starttls'):
        raise ValueError('host_checks.alert.security must be ssl or starttls')
    if not str(alert.get('password_file', '')).startswith('/'):
        raise ValueError('host_checks.alert.password_file must be an absolute path')
    to = alert.get('to')
    addresses = [alert.get('username'), alert.get('sender')] + (to if isinstance(to, list) else [None])
    if not to or not all(isinstance(a, str) and re.fullmatch(r'[^@\s]+@[A-Za-z0-9.-]+', a) for a in addresses):
        raise ValueError('host_checks.alert needs username, sender and a list of recipient addresses')
    rendered = {'smtp_host': host, 'smtp_port': port, 'security': alert.get('security', 'ssl'),
                'username': alert['username'], 'password_file': alert['password_file'], 'sender': alert['sender'],
                'to': list(to)}
    if alert.get('address') is not None:
        # Connect here (e.g. the mail server's tailnet address); the certificate is still checked for smtp_host.
        try:
            rendered['address'] = str(ipaddress.ip_address(str(alert['address'])))
        except ValueError:
            raise ValueError('host_checks.alert.address must be an IP address') from None
    return rendered


BOOT_SERVICE = """[Unit]
Description=Check that every stack came up after boot (P57)
After=docker.service tailscaled.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {install}/host_check.py boot --config {config}
TimeoutStartSec=900
SuccessExitStatus=0

[Install]
WantedBy=multi-user.target
"""

WATCH_SERVICE = """[Unit]
Description=Flag containers that keep restarting (P57)
After=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {install}/host_check.py watch --config {config}
"""

WATCH_TIMER = """[Unit]
Description=Crash-loop watch every five minutes (P57)

[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
"""

DOCKER_DROPIN = """[Unit]
Wants=tailscaled.service
After=tailscaled.service network-online.target

[Service]
# Best effort (the leading minus ignores failure): wait up to a minute for the
# tailnet address so containers bound to it can start at once.
ExecStartPre=-/usr/bin/python3 {install}/host_check.py wait-tailnet --config {config} --timeout 60
"""


def render(profile, output):
    output = Path(output)
    (output / 'docker.service.d').mkdir(parents=True, exist_ok=True)
    fill = {'install': INSTALL_DIR, 'config': CONFIG_PATH}
    files = {'config.json': json.dumps(build_config(profile), indent=2) + '\n',
             'cloud-boot-check.service': BOOT_SERVICE.format(**fill),
             'cloud-restart-watch.service': WATCH_SERVICE.format(**fill),
             'cloud-restart-watch.timer': WATCH_TIMER,
             'docker.service.d/10-after-tailscale.conf': DOCKER_DROPIN.format(**fill)}
    for name, text in files.items():
        (output / name).write_text(text)
    return sorted(files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    for written in render(json.loads(Path(args.profile).read_text()), args.output):
        print(written)
