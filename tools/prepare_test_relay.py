#!/usr/bin/env python3
"""Render a pass-through relay for the test hostnames on another Traefik host.

Used when the test host has no public address (e.g. a home server reached over
a tailnet): public DNS for the test hostnames points to the relay host, whose
proxy terminates TLS and forwards each request over HTTPS to the test host
(verifying its certificate per hostname); the test host trusts the relay's
X-Forwarded-For. Port 80 is forwarded so the test host's HTTP certificate
challenges and redirects work; the relay host proves the same names on port
443 instead (TLS-ALPN resolver, P11), so both hosts renew their own
certificates.

Only the six test hostnames from a test profile are relayed, plus the chat stack's two when the profile names
them; nothing else.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import yaml

NAMES = ['erp', 'drive', 'office', 'mail', 'dms', 'respond']
# Relayed only when the test profile names them (the chat stack, P73).
OPTIONAL = ['chat', 'chat-auth', 'chat-web']


def prepare(profile):
    if profile.get('tier') != 'test':
        raise ValueError('Only a test workspace may be relayed')
    prefix = profile.get('ingress_prefix', 'cloud-test')
    if not re.fullmatch('[a-z0-9-]+', prefix): raise ValueError('Invalid route prefix')
    hosts = [profile['hosts'][name] for name in NAMES] + [profile['hosts'][name] for name in OPTIONAL if name in profile['hosts']]
    for host in hosts:
        if not re.fullmatch(r'test[a-z0-9-]*\.[a-z0-9.-]+', host):
            raise ValueError('Only test hostnames may be relayed: ' + host)
    target = str(ipaddress.ip_address(profile['relay_target']))
    resolver = profile.get('relay_cert_resolver', 'letsencrypt-tls')
    # The relay host terminates TLS for the test hostnames with its own
    # certificate per name (P11: no copied wildcard). It must not use the
    # port-80 challenge for them, which belongs to the test host (Traefik's
    # challenge handler answers only its own tokens), so its resolver uses the
    # TLS-ALPN challenge (tools/coolify_proxy_tls_resolver.py). It forwards
    # HTTP over HTTPS to the test host, verifying the test host's certificate
    # for each hostname.
    # TCP pass-through by SNI is not used: browsers reuse ("coalesce") an
    # existing connection to the relay host for any hostname its certificate
    # covers, so requests for test hostnames arrive inside connections opened
    # for other names and would be answered by the relay host itself.
    routers, services, transports = {}, {}, {}
    for host in hosts:
        key = prefix + '-relay-' + host.split('.')[0]
        routers[key] = {'rule': 'Host(`' + host + '`)', 'entryPoints': ['https'], 'priority': 100000,
                        'service': key, 'tls': {'certResolver': resolver}}
        transports[key] = {'serverName': host}
        services[key] = {'loadBalancer': {'servers': [{'url': 'https://' + target}], 'passHostHeader': True,
                                          'serversTransport': key}}
    routers[prefix + '-relay-http'] = {'rule': ' || '.join('Host(`' + h + '`)' for h in hosts), 'entryPoints': ['http'],
                                       'priority': 52000, 'service': prefix + '-relay-http'}
    services[prefix + '-relay-http'] = {'loadBalancer': {'servers': [{'url': 'http://' + target}], 'passHostHeader': True}}
    return {'http': {'routers': routers, 'services': services, 'serversTransports': transports}}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--profile', required=True); p.add_argument('--output', required=True)
    a = p.parse_args()
    Path(a.output).write_text(yaml.safe_dump(prepare(json.loads(Path(a.profile).read_text())), sort_keys=False))
