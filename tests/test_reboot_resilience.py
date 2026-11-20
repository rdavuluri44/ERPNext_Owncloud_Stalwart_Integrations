"""P57: a reboot or restart must not leave a stack half-working.

The editor bridge must be on every network oCIS is on (oCIS advertises one of
its own addresses, chosen at random at each start), starts only after oCIS is
healthy, and databases get time to shut down cleanly.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_runtime import prepare, missing_peer_networks  # noqa: E402

STACKS = sorted((ROOT / 'deployment/stacks').glob('*.compose.json'))
DATABASE = re.compile(r'(mariadb|mysql|postgres)', re.I)
REDIS = re.compile(r'redis', re.I)


def seconds(value):
    match = re.fullmatch(r'(\d+)(s|m)', value or '')
    return int(match.group(1)) * (60 if match.group(2) == 'm' else 1) if match else 0


def profile(extra=None):
    value = {'instance': 'isolated-prod', 'tier': 'production', 'domain': 'example.com',
             'hosts': {k: k + '.example.com' for k in ['erp', 'sso', 'drive', 'office', 'mail', 'dms', 'respond']},
             'network': 'isolated-workspace', 'network_subnet': '10.45.0.0/24',
             'erp_image': 'example/erp:prod', 'mail_image': 'example/mail:prod', 'projects': ['drive'],
             'settings': {'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID': 'office-mail'}}
    if extra:
        value['extra_networks'] = extra
    return value


class EditorBridgeNetworkTests(unittest.TestCase):
    def render(self, extra=None):
        with tempfile.TemporaryDirectory() as temp:
            prepare(ROOT, Path(temp) / 'runtime', profile(extra))
            return json.loads((Path(temp) / 'runtime/compose/drive.json').read_text())

    def test_stack_definition_alone_already_satisfies_the_rule(self):
        compose = json.loads((ROOT / 'deployment/stacks/drive.compose.json').read_text())
        self.assertEqual(missing_peer_networks(compose, 'drive'), [])

    def test_bridge_joins_every_network_the_profile_adds_to_ocis(self):
        # What production did: ocis got the proxy network, the bridge did not.
        compose = self.render({'drive': {'ocis': {'coolify': ['drive-ocis-production'], 'erp-production': ['office-ocis'],
                                                  'office-backend': ['office-ocis']}}})
        ocis = set(compose['services']['ocis']['networks'])
        bridge = set(compose['services']['collaboration']['networks'])
        self.assertIn('coolify', ocis)
        self.assertTrue(ocis <= bridge, 'bridge must be on every network oCIS is on: ' + str(ocis - bridge))
        self.assertEqual(missing_peer_networks(compose, 'drive'), [])
        # The extra networks are declared as external networks of the stack.
        self.assertEqual(compose['networks']['coolify'], {'external': True, 'name': 'coolify'})

    def test_bridge_keeps_its_own_aliases_and_does_not_steal_oci_aliases(self):
        compose = self.render({'drive': {'ocis': {'coolify': ['drive-ocis-production']},
                                         'collaboration': {'erp-production': ['office-collaboration']}}})
        bridge = compose['services']['collaboration']['networks']
        self.assertEqual(bridge['erp-production']['aliases'], ['office-collaboration'])
        self.assertNotIn('drive-ocis-production', json.dumps(bridge))

    def test_a_violation_is_detected(self):
        compose = {'services': {'ocis': {'networks': {'default': {}, 'coolify': {}}},
                                'collaboration': {'networks': {'default': {}}}}}
        self.assertEqual(missing_peer_networks(compose, 'drive'), [('collaboration', 'ocis', 'coolify')])

    def test_bridge_starts_only_after_ocis_is_healthy_and_restarts_itself(self):
        compose = json.loads((ROOT / 'deployment/stacks/drive.compose.json').read_text())
        bridge, ocis = compose['services']['collaboration'], compose['services']['ocis']
        self.assertEqual(bridge['depends_on']['ocis']['condition'], 'service_healthy')
        self.assertTrue(ocis.get('healthcheck'))
        self.assertEqual(bridge['restart'], 'unless-stopped')
        self.assertEqual(ocis['restart'], 'unless-stopped')


class ShutdownTimeTests(unittest.TestCase):
    def test_databases_get_time_to_shut_down_cleanly(self):
        found = []
        for stack in STACKS:
            for name, service in json.loads(stack.read_text())['services'].items():
                image = service.get('image', '')
                if DATABASE.search(image):
                    found.append(stack.name + '/' + name)
                    self.assertGreaterEqual(seconds(service.get('stop_grace_period')), 60,
                                            stack.name + '/' + name + ' needs stop_grace_period >= 60s')
                elif REDIS.search(image):
                    self.assertGreaterEqual(seconds(service.get('stop_grace_period')), 30,
                                            stack.name + '/' + name + ' needs stop_grace_period >= 30s')
        self.assertGreaterEqual(len(found), 3, 'expected the ERP, DMS and sign-in databases: ' + str(found))

    def test_every_long_running_service_restarts_after_a_reboot(self):
        for stack in STACKS:
            for name, service in json.loads(stack.read_text())['services'].items():
                if service.get('restart') == 'no' or service.get('profiles'):
                    continue
                # One-off initialisation jobs may use "no" or on-failure; daemons must not.
                self.assertIn(service.get('restart'), ('unless-stopped', 'always', 'on-failure', 'no', None),
                              stack.name + '/' + name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
