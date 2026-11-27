#!/usr/bin/env python3
"""Add a TLS-ALPN Let's Encrypt resolver to a Coolify proxy (P11).

The relay host terminates TLS for the relayed test names, so it needs its own
certificate for each of them. Their port-80 certificate challenges must keep
reaching the test host, which renews its own certificates through the port-80
relay, and Traefik's HTTP challenge handler answers only its own tokens. The
relay host therefore proves these names on port 443 (TLS-ALPN challenge), with
a second resolver (`letsencrypt-tls`) that shares the existing ACME storage.

Writes Coolify's saved proxy configuration and the compose file; `--restart`
recreates the proxy and reattaches its networks; `--check` reports whether the
running proxy has the resolver. Only the resolver's flags change.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coolify_proxy_hosts import COMPOSE, TLS_RESOLVER, apply, psql, tls_resolver_flags  # noqa: E402


def enable(server_id=0, name=TLS_RESOLVER):
    text = apply(COMPOSE.read_text(), {}, tls_resolver=name)
    proxy = json.loads(psql(f'select proxy from servers where id={server_id};'))
    if proxy.get('last_saved_proxy_configuration'):
        proxy['last_saved_proxy_configuration'] = apply(proxy['last_saved_proxy_configuration'], {}, tls_resolver=name)
        proxy['last_saved_settings'] = hashlib.md5(proxy['last_saved_proxy_configuration'].encode()).hexdigest()
        tag = 'p' + hashlib.sha256(json.dumps(proxy).encode()).hexdigest()[:16]
        psql(f"update servers set proxy=${tag}${json.dumps(proxy)}${tag}$::json where id={server_id};")
    COMPOSE.write_text(text)
    return f'resolver {name} in the saved proxy configuration and compose file; restart the proxy to apply'


def running_has(name=TLS_RESOLVER, run=subprocess.run):
    args = json.loads(run(['docker', 'inspect', 'coolify-proxy', '--format', '{{json .Args}}'],
                          capture_output=True, text=True, check=True).stdout)
    return all(flag in args for flag in tls_resolver_flags(name))


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--server-id', type=int, default=0)
    p.add_argument('--restart', action='store_true', help='recreate the proxy, keeping its networks')
    p.add_argument('--check', action='store_true', help='only report whether the running proxy has the resolver')
    a = p.parse_args()
    if a.check:
        ok = running_has()
        print('running proxy has', TLS_RESOLVER, 'resolver:', 'yes' if ok else 'no')
        raise SystemExit(0 if ok else 1)
    print(enable(a.server_id))
    if a.restart:
        from coolify_proxy_http3 import restart_keeping_networks
        print('Proxy recreated; reattached networks:', restart_keeping_networks() or 'none needed')
