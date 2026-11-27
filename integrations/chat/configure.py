#!/usr/bin/env python3
"""Write the Synapse and Matrix Authentication Service (MAS) configuration from the stack's environment (P73).

Runs once before the two services start, as the `configure` service of `deployment/stacks/chat.compose.json`, in
the Synapse image (Python with `cryptography`). Neither service reads secrets from environment variables, and the
MAS image has no shell, so the settings the renderer puts in this service's environment become two files:

* `/synapse-config/homeserver.yaml` for Synapse (uid 991);
* `/mas-config/config.yaml` and `/mas-config/signing.pem` for MAS (uid 65532).

Both files are written as JSON, which is valid YAML, so no YAML library is needed. The MAS signing key is made
once and kept: replacing it would sign every session out. Choices fixed here (owner, 27 November 2026): sign-in
only through the upstream sign-in service (no passwords, no registration), no federation at first, rooms not
encrypted by default so the company can keep and search them, and people cannot change the name or mail address
that comes from the sign-in service.
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

SYNAPSE_UID, MAS_UID = 991, 65532
REQUIRED = ('CHAT_SERVER_NAME', 'CHAT_PUBLIC_URL', 'CHAT_AUTH_URL', 'SYNAPSE_DB_PASSWORD', 'MAS_DB_PASSWORD',
            'SHARED_SECRET', 'MACAROON_SECRET', 'FORM_SECRET', 'MAS_ENCRYPTION_SECRET', 'UPSTREAM_ID',
            'UPSTREAM_ISSUER', 'UPSTREAM_CLIENT_ID', 'UPSTREAM_CLIENT_SECRET', 'UPSTREAM_NAME', 'LOCALPART_TEMPLATE',
            'BRIDGE_AS_TOKEN', 'BRIDGE_HS_TOKEN')
# The business system's bot (P73): it creates the rooms, invites people into them and posts; people cannot use
# its name. It needs no admin right: Synapse accepts its invitations for people (auto_accept_invites, below).
BRIDGE_USER = 'erp'
ULID = re.compile(r'[0-7][0-9A-HJKMNP-TV-Z]{25}')
HOST = re.compile(r'[a-z0-9]([a-z0-9.-]*[a-z0-9])?')


def settings(env):
    """The checked settings; every problem is named without printing a value."""
    missing = [name for name in REQUIRED if not str(env.get(name) or '').strip()]
    if missing:
        raise ValueError('Missing chat settings: ' + ', '.join(missing))
    values = {name: str(env[name]).strip() for name in REQUIRED}
    if not HOST.fullmatch(values['CHAT_SERVER_NAME']):
        raise ValueError('CHAT_SERVER_NAME must be a host name')
    for name in ('CHAT_PUBLIC_URL', 'CHAT_AUTH_URL', 'UPSTREAM_ISSUER'):
        if not values[name].startswith('https://'):
            raise ValueError(name + ' must be an https address')
        if not values[name].endswith('/'):
            values[name] += '/'
    if not ULID.fullmatch(values['UPSTREAM_ID']):
        raise ValueError('UPSTREAM_ID must be a ULID (26 characters)')
    if values['BRIDGE_AS_TOKEN'] == values['BRIDGE_HS_TOKEN']:
        raise ValueError('BRIDGE_AS_TOKEN and BRIDGE_HS_TOKEN must differ')
    return values


def homeserver(values):
    return {
        'server_name': values['CHAT_SERVER_NAME'],
        'public_baseurl': values['CHAT_PUBLIC_URL'],
        'pid_file': '/data/homeserver.pid',
        'listeners': [{'port': 8008, 'type': 'http', 'tls': False, 'x_forwarded': True, 'bind_addresses': ['0.0.0.0'],
                       'resources': [{'names': ['client'], 'compress': False}]}],
        'database': {'name': 'psycopg2', 'args': {
            'user': 'synapse', 'password': values['SYNAPSE_DB_PASSWORD'], 'dbname': 'synapse',
            'host': 'database-synapse', 'port': 5432, 'cp_min': 2, 'cp_max': 10}},
        'media_store_path': '/data/media_store',
        'signing_key_path': '/data/signing.key',
        'max_upload_size': '50M',
        'report_stats': False,
        'macaroon_secret_key': values['MACAROON_SECRET'],
        'form_secret': values['FORM_SECRET'],
        # Sign-in only through MAS, which sends people to the upstream sign-in service.
        'enable_registration': False,
        'password_config': {'enabled': False},
        'matrix_authentication_service': {'enabled': True, 'endpoint': 'http://mas:8080/',
                                          'secret': values['SHARED_SECRET']},
        # No federation at first: no other server is contacted or answered.
        'federation_domain_whitelist': [],
        'trusted_key_servers': [],
        'allow_public_rooms_over_federation': False,
        # Company rooms are not encrypted, so the company can keep, search and export them.
        'encryption_enabled_by_default_for_room_type': 'off',
        'url_preview_enabled': False,
        'enable_room_list_search': True,
        # The business system's bot signs in with its own token (bridge(), below).
        'app_service_config_files': ['/config/bridge.yaml'],
        # An invitation from someone on this server is accepted at once, so the bot can put a person into their
        # site room (and a colleague's one-to-one chat opens) without a tap. Nobody outside can invite: no federation.
        'auto_accept_invites': {'enabled': True, 'only_for_direct_messages': False, 'only_from_local_users': True},
    }


def bridge(values):
    """The bot's registration with Synapse: its two tokens, its one user and the room addresses it owns. No
    address to call back: the business system only calls Synapse, never the other way round."""
    server = re.escape(values['CHAT_SERVER_NAME'])
    return {
        'id': 'business-system', 'url': None, 'sender_localpart': BRIDGE_USER, 'rate_limited': False,
        'as_token': values['BRIDGE_AS_TOKEN'], 'hs_token': values['BRIDGE_HS_TOKEN'],
        'namespaces': {'users': [{'exclusive': True, 'regex': '@' + BRIDGE_USER + ':' + server}],
                       'aliases': [{'exclusive': True, 'regex': '#(site|team|notices)-.*:' + server}], 'rooms': []},
    }


def encryption_key(secret):
    """MAS wants 32 bytes in hex; the renderer makes URL-safe text. The same secret always gives the same key."""
    return hashlib.sha256(('mas-encryption:' + secret).encode()).hexdigest()


def mas(values):
    return {
        'http': {
            'public_base': values['CHAT_AUTH_URL'],
            'listeners': [{'name': 'web', 'binds': [{'address': '[::]:8080'}],
                           'resources': [{'name': name} for name in
                                         ('discovery', 'human', 'oauth', 'compat', 'graphql', 'assets')]},
                          {'name': 'internal', 'binds': [{'address': '[::]:8081'}], 'resources': [{'name': 'health'}]}],
        },
        'database': {'uri': 'postgresql://mas:%s@database-mas:5432/mas?sslmode=disable' % values['MAS_DB_PASSWORD']},
        'matrix': {'kind': 'synapse', 'homeserver': values['CHAT_SERVER_NAME'], 'endpoint': 'http://synapse:8008',
                   'secret': values['SHARED_SECRET']},
        'secrets': {'encryption': encryption_key(values['MAS_ENCRYPTION_SECRET']),
                    'keys': [{'kid': 'chat-1', 'key_file': '/config/signing.pem'}]},
        'passwords': {'enabled': False},
        'account': {'email_change_allowed': False, 'displayname_change_allowed': False,
                    'password_registration_enabled': False, 'password_change_allowed': False,
                    'password_recovery_enabled': False, 'account_deactivation_allowed': False},
        'upstream_oauth2': {'providers': [{
            'id': values['UPSTREAM_ID'], 'human_name': values['UPSTREAM_NAME'], 'issuer': values['UPSTREAM_ISSUER'],
            'client_id': values['UPSTREAM_CLIENT_ID'], 'client_secret': values['UPSTREAM_CLIENT_SECRET'],
            'token_endpoint_auth_method': 'client_secret_basic', 'scope': 'openid profile email chat',
            'claims_imports': {
                'localpart': {'action': 'require', 'template': values['LOCALPART_TEMPLATE']},
                'displayname': {'action': 'force', 'template': '{{ user.name }}'},
                'email': {'action': 'force', 'template': '{{ user.email }}'}},
        }]},
    }


def signing_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def is_root():
    return hasattr(os, 'geteuid') and os.geteuid() == 0


def write(path, data, uid):
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(path.name + '.new')
    staged.write_bytes(data)
    staged.chmod(0o600)
    if is_root():
        os.chown(staged, uid, uid)
    staged.replace(path)


def main(env=os.environ, synapse_dir=Path('/synapse-config'), mas_dir=Path('/mas-config'), data_dir=Path('/data')):
    try:
        values = settings(env)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    write(synapse_dir / 'homeserver.yaml', (json.dumps(homeserver(values), indent=1) + '\n').encode(), SYNAPSE_UID)
    write(synapse_dir / 'bridge.yaml', (json.dumps(bridge(values), indent=1) + '\n').encode(), SYNAPSE_UID)
    write(mas_dir / 'config.yaml', (json.dumps(mas(values), indent=1) + '\n').encode(), MAS_UID)
    key = mas_dir / 'signing.pem'
    if not key.exists():
        write(key, signing_key(), MAS_UID)
    if is_root():
        for folder, uid in ((synapse_dir, SYNAPSE_UID), (mas_dir, MAS_UID), (data_dir, SYNAPSE_UID)):
            if folder.is_dir():
                os.chown(folder, uid, uid)
    print('chat configuration written; signing key kept' if key.exists() else 'chat configuration written')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
