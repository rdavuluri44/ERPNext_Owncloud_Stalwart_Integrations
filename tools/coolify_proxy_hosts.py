#!/usr/bin/env python3
"""Persist the test workspace's settings in Coolify's proxy configuration.

1. The proxy joins the workspace network with the test hostnames as aliases,
   so containers reach the test sites through trusted local HTTPS. Without
   this in the saved configuration, a proxy restart from the dashboard
   silently drops the network (found on the TrueNAS VM, 18 November 2026).
2. Optional `proxy_hosts` pin hostnames to private addresses (e.g. a tailnet).
3. Optional `proxy_protocol_trusted_ips`: sources allowed to send the PROXY
   protocol on HTTPS (a relay host, see prepare_test_relay.py). On a tailnet
   host this is the proxy network's Docker gateway, as Tailscale masquerades
   forwarded traffic; connections without the header still work.
4. With `relay_target` set, HTTP/3 is switched off (no UDP 443, no Alt-Svc
   advertisement), because the relay passes TCP only.

A test host on a connection without a fixed public address reaches the remote
SSO host's private entry point instead. Docker containers do not read the
host's /etc/hosts, so the mapping is added as `extra_hosts` on the proxy. It
is written both to Coolify's saved proxy configuration (so a proxy restart
from the dashboard keeps it) and to the proxy compose file. Only a block of
entries marked by this tool is changed; other entries are kept.

Usage: coolify_proxy_hosts.py --profile PROFILE, then restart the proxy.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import yaml

COMPOSE = Path('/data/coolify/proxy/docker-compose.yml')


def validate(mapping):
    out = []
    for host, address in sorted(mapping.items()):
        if not re.fullmatch(r'[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+', host):
            raise ValueError('Invalid hostname ' + host)
        out.append(host + ':' + str(ipaddress.ip_address(address)))
    return out


PROXY_FLAG = '--entrypoints.https.proxyprotocol.trustedips='
FORWARDED_FLAG = '--entrypoints.https.forwardedheaders.trustedips='


TLS_RESOLVER = 'letsencrypt-tls'


def tls_resolver_flags(name=TLS_RESOLVER):
    # P11: a second Let's Encrypt resolver using the TLS-ALPN challenge (port
    # 443), for names whose port-80 challenges belong to another host (the
    # relayed test names: the test host renews through the port-80 relay).
    if not re.fullmatch(r'[a-z0-9-]+', name): raise ValueError('Invalid resolver name')
    return [f'--certificatesresolvers.{name}.acme.tlschallenge=true',
            f'--certificatesresolvers.{name}.acme.storage=/traefik/acme.json']


def apply(text, mapping, network=None, aliases=(), proxy_trusted=None, http3=None, tls_resolver=None):
    """Return compose text with these pinned hosts, workspace network and the
    HTTPS entry point's PROXY-protocol trusted sources (a relay host)."""
    data = yaml.safe_load(text)
    service = data['services']['traefik']
    if tls_resolver:
        prefix = f'--certificatesresolvers.{tls_resolver}.'
        command = [c for c in service.get('command', []) if not str(c).startswith(prefix)]
        service['command'] = command + tls_resolver_flags(tls_resolver)
    if http3 is False:
        # A relayed host is reached by TCP pass-through only; advertising
        # HTTP/3 (UDP) sends browsers to the relay host, which cannot pass it.
        service['command'] = [x for x in service.get('command', []) if not str(x).startswith('--entrypoints.https.http3')]
        service['ports'] = [x for x in service.get('ports', []) if not str(x).endswith('/udp')]
    if proxy_trusted is not None:
        ranges = [str(ipaddress.ip_network(r if '/' in r else r + ('/128' if ':' in r else '/32')))
                  for r in proxy_trusted]
        # The relay now forwards HTTP (X-Forwarded-For) instead of TCP with the
        # PROXY protocol; drop any earlier PROXY-protocol trust.
        command = [c for c in service.get('command', []) if not str(c).startswith((PROXY_FLAG, FORWARDED_FLAG))]
        if ranges: command.append(FORWARDED_FLAG + ','.join(ranges))
        service['command'] = command
    if mapping:
        wanted = validate(mapping)
        names = {entry.split(':', 1)[0] for entry in wanted}
        kept = [e for e in service.get('extra_hosts', []) if e.split(':', 1)[0] not in names]
        service['extra_hosts'] = kept + wanted
    if network:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', network): raise ValueError('Invalid network')
        validate({alias: '127.0.0.1' for alias in aliases})
        data.setdefault('networks', {})[network] = {'external': True}
        nets = service.get('networks') or []
        if isinstance(nets, list): nets = {name: None for name in nets}
        nets[network] = {'aliases': list(aliases)}
        service['networks'] = nets
    return yaml.safe_dump(data, sort_keys=False)


def psql(sql):
    return subprocess.run(['docker', 'exec', '-i', 'coolify-db', 'psql', '-U', 'coolify', '-d', 'coolify', '-At', '-v', 'ON_ERROR_STOP=1'],
                          input=sql, capture_output=True, text=True, check=True).stdout


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--profile', required=True); parser.add_argument('--server-id', type=int, default=0)
    args = parser.parse_args()
    profile = json.loads(Path(args.profile).read_text())
    if profile.get('tier') != 'test': raise ValueError('Only test hosts pin proxy hostnames')
    mapping = profile.get('proxy_hosts') or {}
    aliases = [profile['hosts'][k] for k in ['erp', 'drive', 'office', 'mail', 'dms', 'respond']]
    aliases += [profile['hosts'][k] for k in ['chat', 'chat-auth'] if k in profile['hosts']]
    args_apply = (mapping, profile['network'], aliases, profile.get('proxy_protocol_trusted_ips'),
                  False if profile.get('relay_target') else None)
    text = apply(COMPOSE.read_text(), *args_apply)
    proxy = json.loads(psql(f'select proxy from servers where id={args.server_id};'))
    if proxy.get('last_saved_proxy_configuration'):
        proxy['last_saved_proxy_configuration'] = apply(proxy['last_saved_proxy_configuration'], *args_apply)
        proxy['last_saved_settings'] = hashlib.md5(proxy['last_saved_proxy_configuration'].encode()).hexdigest()
        tag = 'p' + hashlib.sha256(json.dumps(proxy).encode()).hexdigest()[:16]
        psql(f"update servers set proxy=${tag}${json.dumps(proxy)}${tag}$::json where id={args.server_id};")
    COMPOSE.write_text(text)
    print('Proxy configuration written (network ' + profile['network'] + (', pins ' + ', '.join(validate(mapping)) if mapping else '') + '); restart the proxy to apply')
