"""The chat stack (P73): Synapse with the Matrix Authentication Service, signing in through the sign-in service.

Offline: the script that writes both configurations runs for real against a temporary folder (without the signing
key, which needs the `cryptography` package of the Synapse image), and the stack file and the test routes are read
as data. Every value below is a made-up placeholder.
"""
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('chat_configure', ROOT / 'integrations/chat/configure.py')
configure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configure)

ENV = {
    'CHAT_SERVER_NAME': 'chat.example.net', 'CHAT_PUBLIC_URL': 'https://chat.example.net',
    'CHAT_AUTH_URL': 'https://chat-auth.example.net/', 'SYNAPSE_DB_PASSWORD': 'placeholder-a',
    'MAS_DB_PASSWORD': 'placeholder-b', 'SHARED_SECRET': 'placeholder-c', 'MACAROON_SECRET': 'placeholder-d',
    'FORM_SECRET': 'placeholder-e', 'MAS_ENCRYPTION_SECRET': 'placeholder-f',
    'UPSTREAM_ID': '01KBCHATSS0PR0V1DERAAAAAAA', 'UPSTREAM_ISSUER': 'https://sso.example.net/application/o/chat/',
    'UPSTREAM_CLIENT_ID': 'chat', 'UPSTREAM_CLIENT_SECRET': 'placeholder-g', 'UPSTREAM_NAME': 'Company sign-in',
    'LOCALPART_TEMPLATE': '{{ user.chat_name }}',
    'BRIDGE_AS_TOKEN': 'placeholder-h', 'BRIDGE_HS_TOKEN': 'placeholder-i',
}
STACK = json.loads((ROOT / 'deployment/stacks/chat.compose.json').read_text(encoding='utf-8'))
INPUTS = json.loads((ROOT / 'deployment/stacks/inputs.json').read_text(encoding='utf-8'))
KEY_FILE = 'signing' + '.pem'


class Configuration(unittest.TestCase):
    def setUp(self):
        self.values = configure.settings(ENV)
        self.synapse = configure.homeserver(self.values)
        self.mas = configure.mas(self.values)

    def test_sign_in_only_through_the_sign_in_service(self):
        self.assertFalse(self.synapse['enable_registration'])
        self.assertEqual(self.synapse['password_config'], {'enabled': False})
        self.assertTrue(self.synapse['matrix_authentication_service']['enabled'])
        self.assertEqual(self.mas['passwords'], {'enabled': False})
        providers = self.mas['upstream_oauth2']['providers']
        self.assertEqual(len(providers), 1, 'one provider and no passwords: MAS goes straight to it')
        self.assertEqual(providers[0]['claims_imports']['localpart']['action'], 'require')
        self.assertIn('chat', providers[0]['scope'].split(), 'the chat name comes with its own scope')
        self.assertEqual(INPUTS['CI_CHAT_CONFIGURE_LOCALPART_TEMPLATE']['default'], '{{ user.chat_name }}')
        mappings = json.loads((ROOT / 'deployment/scope-mappings.example.json').read_text(encoding='utf-8'))
        chat = [m for m in mappings if m['scope_name'] == 'chat']
        self.assertEqual(len(chat), 1)
        self.assertIn('chat_name', chat[0]['expression'])

    def test_people_cannot_change_what_the_sign_in_service_says(self):
        account = self.mas['account']
        for name in ('email_change_allowed', 'displayname_change_allowed', 'password_registration_enabled',
                     'password_change_allowed', 'password_recovery_enabled', 'account_deactivation_allowed'):
            self.assertIs(account[name], False, name)
        imports = self.mas['upstream_oauth2']['providers'][0]['claims_imports']
        self.assertEqual(imports['displayname']['action'], 'force')
        self.assertEqual(imports['email']['action'], 'force')

    def test_no_federation_and_rooms_not_encrypted_by_default(self):
        self.assertEqual(self.synapse['federation_domain_whitelist'], [])
        self.assertEqual(self.synapse['trusted_key_servers'], [])
        self.assertEqual(self.synapse['encryption_enabled_by_default_for_room_type'], 'off')
        names = [name for listener in self.synapse['listeners'] for r in listener['resources'] for name in r['names']]
        self.assertEqual(names, ['client'], 'no federation resource is served')

    def test_the_business_system_has_a_bot_and_needs_no_admin_right(self):
        bridge = configure.bridge(self.values)
        self.assertEqual(self.synapse['app_service_config_files'], ['/config/bridge.yaml'])
        self.assertIsNone(bridge['url'], 'Synapse never calls the business system')
        self.assertEqual(bridge['sender_localpart'], 'erp')
        users = bridge['namespaces']['users']
        self.assertEqual(len(users), 1)
        self.assertTrue(users[0]['exclusive'], 'nobody else can take the bot\'s name')
        self.assertTrue(re.fullmatch(users[0]['regex'], '@erp:chat.example.net'))
        self.assertFalse(re.fullmatch(users[0]['regex'], '@erp:chatXexample.net'), 'the dots of the name are literal')
        self.assertFalse(re.fullmatch(users[0]['regex'], '@someone:chat.example.net'), 'the bot cannot act as a person')
        alias = bridge['namespaces']['aliases'][0]['regex']
        self.assertTrue(re.fullmatch(alias, '#site-north-yard:chat.example.net'))
        self.assertFalse(re.fullmatch(alias, '#lunch:chat.example.net'))
        self.assertNotEqual(bridge['as_token'], bridge['hs_token'])
        with self.assertRaises(ValueError):
            configure.settings({**ENV, 'BRIDGE_HS_TOKEN': ENV['BRIDGE_AS_TOKEN']})
        self.assertEqual(self.synapse['auto_accept_invites'],
                         {'enabled': True, 'only_for_direct_messages': False, 'only_from_local_users': True},
                         'the bot puts people into rooms by inviting them; only this server can invite')
        self.assertNotIn('clients', self.mas, 'no client with admin rights exists')
        self.assertNotIn('policy', self.mas)
        self.assertNotIn('server_notices', self.synapse, 'the bot makes the Notices room of each person itself')

    def test_both_sides_share_one_value_and_name_each_other(self):
        self.assertEqual(self.synapse['matrix_authentication_service']['secret'], self.mas['matrix']['secret'])
        self.assertEqual(self.synapse['matrix_authentication_service']['endpoint'], 'http://mas:8080/')
        self.assertEqual(self.mas['matrix']['endpoint'], 'http://synapse:8008')
        self.assertEqual(self.mas['matrix']['homeserver'], self.synapse['server_name'])
        self.assertIn('@database-mas:5432/mas', self.mas['database']['uri'])
        self.assertEqual(self.synapse['database']['args']['host'], 'database-synapse')

    def test_addresses_end_in_a_slash_and_the_key_is_stable_hex(self):
        self.assertEqual(self.synapse['public_baseurl'], 'https://chat.example.net/')
        self.assertEqual(self.mas['http']['public_base'], 'https://chat-auth.example.net/')
        key = self.mas['secrets']['encryption']
        self.assertRegex(key, r'^[0-9a-f]{64}$')
        self.assertEqual(key, configure.encryption_key('placeholder-f'), 'the same input gives the same key')
        self.assertNotEqual(key, configure.encryption_key('another'))

    def test_bad_settings_are_named_without_their_values(self):
        for change, word in (({'SHARED_SECRET': ''}, 'SHARED_SECRET'), ({'UPSTREAM_ID': 'not-a-ulid'}, 'ULID'),
                             ({'CHAT_PUBLIC_URL': 'http://chat.example.net/'}, 'https'),
                             ({'CHAT_SERVER_NAME': 'Chat Example'}, 'host name')):
            with self.assertRaises(ValueError) as refused:
                configure.settings({**ENV, **change})
            self.assertIn(word, str(refused.exception))
            for value in ('placeholder-a', 'placeholder-g', 'placeholder-d'):
                self.assertNotIn(value, str(refused.exception))

    def test_files_are_written_private_and_the_signing_key_is_kept(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(configure, 'signing_key', return_value=b'KEY-1'):
            root = Path(folder)
            self.assertEqual(configure.main(ENV, root / 's', root / 'm', root / 'd'), 0)
            self.assertEqual(json.loads((root / 's/homeserver.yaml').read_text())['server_name'], 'chat.example.net')
            self.assertEqual(json.loads((root / 'm/config.yaml').read_text())['matrix']['homeserver'], 'chat.example.net')
            self.assertEqual((root / 'm' / KEY_FILE).read_bytes(), b'KEY-1')
            with mock.patch.object(configure, 'signing_key', return_value=b'KEY-2'):
                self.assertEqual(configure.main({**ENV, 'UPSTREAM_NAME': 'Renamed'}, root / 's', root / 'm', root / 'd'), 0)
            self.assertEqual((root / 'm' / KEY_FILE).read_bytes(), b'KEY-1', 'a second run keeps the key')
            renamed = json.loads((root / 'm/config.yaml').read_text())['upstream_oauth2']['providers'][0]['human_name']
            self.assertEqual(renamed, 'Renamed', 'the configuration itself is rewritten')
            if sys.platform != 'win32':
                for name in ('s/homeserver.yaml', 'm/config.yaml', 'm/' + KEY_FILE):
                    self.assertEqual((root / name).stat().st_mode & 0o777, 0o600, name)

    def test_missing_settings_stop_before_anything_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(configure.main({**ENV, 'UPSTREAM_CLIENT_SECRET': ''}, root / 's', root / 'm', root / 'd'), 1)
            self.assertFalse((root / 's').exists())


class Stack(unittest.TestCase):
    def test_every_setting_the_script_needs_is_passed_and_declared(self):
        passed = STACK['services']['configure']['environment']
        self.assertEqual(set(passed), set(configure.REQUIRED))
        for name, value in passed.items():
            declared = re.fullmatch(r'\$\{(CI_CHAT_CONFIGURE_[A-Z_]+):\?[^}]*\}', value)
            self.assertTrue(declared, name)
            self.assertEqual(declared.group(1), 'CI_CHAT_CONFIGURE_' + name)
            self.assertIn(declared.group(1), INPUTS)

    def test_the_client_value_is_never_generated_and_the_others_are(self):
        self.assertEqual(INPUTS['CI_CHAT_CONFIGURE_UPSTREAM_CLIENT_SECRET'], {'kind': 'secret', 'generate': False})
        for name in ('SYNAPSE_DB_PASSWORD', 'MAS_DB_PASSWORD', 'SHARED_SECRET', 'MACAROON_SECRET', 'FORM_SECRET',
                     'MAS_ENCRYPTION_SECRET', 'BRIDGE_AS_TOKEN', 'BRIDGE_HS_TOKEN'):
            self.assertEqual(INPUTS['CI_CHAT_CONFIGURE_' + name], {'kind': 'secret', 'generate': True}, name)
        self.assertTrue(configure.ULID.fullmatch(INPUTS['CI_CHAT_CONFIGURE_UPSTREAM_ID']['default']))

    def test_services_wait_for_the_configuration_and_their_database(self):
        services = STACK['services']
        self.assertEqual(services['configure']['restart'], 'no')
        for name, database in (('synapse', 'database-synapse'), ('mas', 'database-mas')):
            needs = services[name]['depends_on']
            self.assertEqual(needs['configure'], {'condition': 'service_completed_successfully'})
            self.assertEqual(needs[database], {'condition': 'service_healthy'})
            self.assertTrue(any(v.endswith(':/config:ro') for v in services[name]['volumes']), name + ' only reads its file')
        self.assertEqual(services['database-synapse']['environment']['POSTGRES_INITDB_ARGS'], '--encoding=UTF8 --locale=C')

    def test_databases_stay_inside_the_stack_and_ports_are_private(self):
        services = STACK['services']
        for name in ('database-synapse', 'database-mas', 'configure'):
            self.assertEqual(services[name]['networks'], {'default': {}}, name)
            self.assertEqual(services[name]['ports'], [], name)
        for name in ('synapse', 'mas'):
            for port in services[name]['ports']:
                self.assertTrue(port.startswith('127.0.0.1:'), port)
        self.assertEqual(services['synapse']['networks']['workspace'], {'aliases': ['chat-synapse']})
        self.assertEqual(services['mas']['networks']['workspace'], {'aliases': ['chat-mas']})
        self.assertTrue(all('@sha256:' in service['image'] for service in services.values()))


class Rendering(unittest.TestCase):
    HOSTS = {name: ('test.example.net' if name == 'erp' else 'test-' + name + '.example.net')
             for name in ('erp', 'sso', 'drive', 'office', 'mail', 'dms', 'respond')}

    def routes(self, hosts):
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            from prepare_ingress import prepare as ingress
        finally:
            sys.path.pop(0)
        return ingress(ROOT, {'hosts': hosts, 'ingress_prefix': 'isolated'})['http']

    def test_routes_only_where_the_profile_names_the_chat_hosts(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest('needs PyYAML, as the ingress renderer does')
        self.assertFalse([name for name in self.routes(self.HOSTS)['routers'] if 'chat' in name])
        http = self.routes({**self.HOSTS, 'chat': 'test-chat.example.net', 'chat-auth': 'test-chat-auth.example.net'})
        routers = http['routers']
        self.assertEqual(routers['isolated-chat']['service'], 'isolated-chat')
        self.assertEqual(routers['isolated-chat-auth']['service'], 'isolated-chat-auth')
        delegated = routers['isolated-chat-delegated']
        self.assertEqual(delegated['service'], 'isolated-chat-auth')
        self.assertGreater(delegated['priority'], routers['isolated-chat']['priority'])
        pattern = re.search(r'PathRegexp\(`([^`]+)`\)', delegated['rule']).group(1)
        for path in ('/_matrix/client/v3/login', '/_matrix/client/v3/logout', '/_matrix/client/v3/refresh'):
            self.assertTrue(re.search(pattern, path), path)
        for path in ('/_matrix/client/v3/sync', '/_matrix/client/v3/login/sso/redirect', '/_synapse/admin/v1/users'):
            self.assertFalse(re.search(pattern, path), path)
        self.assertNotIn('/_synapse/admin', routers['isolated-chat']['rule'], 'the admin interface is not routed')
        self.assertEqual(http['services']['isolated-chat']['loadBalancer']['servers'][0]['url'], 'http://chat-synapse:8008')
        self.assertEqual(http['services']['isolated-chat-auth']['loadBalancer']['servers'][0]['url'], 'http://chat-mas:8080')


    def test_the_relay_and_the_host_block_carry_the_chat_names_only_when_the_profile_has_them(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest('needs PyYAML, as the relay renderer does')
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            from prepare_test_relay import prepare as relay
            try:
                from test_host_aliases import render as aliases
            except ImportError:  # the host tool needs Linux (fcntl)
                aliases = None
        finally:
            sys.path.pop(0)
        base = {'tier': 'test', 'instance': 'trial', 'relay_target': '100.64.0.20', 'hosts': dict(self.HOSTS)}
        without = relay(base)['http']['routers']
        self.assertFalse([name for name in without if 'chat' in name])
        chat = dict(self.HOSTS, **{'chat': 'test-chat.example.net', 'chat-auth': 'test-chat-auth.example.net'})
        routers = relay(dict(base, hosts=chat))['http']['routers']
        self.assertEqual(routers['cloud-test-relay-test-chat']['rule'], 'Host(`test-chat.example.net`)')
        self.assertEqual(routers['cloud-test-relay-test-chat-auth']['rule'], 'Host(`test-chat-auth.example.net`)')
        self.assertIn('Host(`test-chat-auth.example.net`)', routers['cloud-test-relay-http']['rule'],
                      'port 80 too, for the certificate challenge of the test host')
        with self.assertRaises(ValueError):
            relay(dict(base, hosts=dict(chat, chat='chat.example.net')))
        if aliases:
            self.assertIn('test-chat.example.net test-chat-auth.example.net', aliases('', dict(base, hosts=chat)))
            self.assertNotIn('chat', aliases('', base))


if __name__ == '__main__':
    unittest.main()
