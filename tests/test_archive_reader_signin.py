"""P69: the mail archive reader may pass the passkey sign-in gate, and reaches only the mail application.

Offline checks of the retained authentik graph against the live-change script. The behaviour itself
(who passes the gate, which applications admit whom, rollback) is tested on a throwaway authentik by
integrations/authentik/archive-reader/test_native.py.
"""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRAPH = json.loads((ROOT / 'integrations/authentik/configuration.json').read_text())['entries']
SCRIPT = ROOT / 'integrations/authentik/archive-reader/archive_reader_access.py'
READERS = 'Mail Archive Readers'
STAFF = 'Workspace Users'


def gate_template():
    for node in ast.parse(SCRIPT.read_text()).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', None) == 'GATE':
            return ast.literal_eval(node.value)
    raise AssertionError('GATE not found')


def entry(entry_id):
    return next(e for e in GRAPH if e['id'] == entry_id)


class ArchiveReaderSignin(unittest.TestCase):
    def test_gate_in_graph_matches_the_live_change(self):
        policy = next(e for e in GRAPH if e['identifiers'].get('name') == 'cloud-passkey-approved-account')
        self.assertEqual(policy['attrs']['expression'], gate_template().format(groups=json.dumps([STAFF, READERS])))

    def test_reader_group_is_plain(self):
        group = next(e for e in GRAPH if e['model'] == 'authentik_core.group' and e['identifiers']['name'] == READERS)
        self.assertEqual(group['attrs'], {'is_superuser': False, 'parents': [], 'attributes': {}})

    def test_only_mail_admits_the_reader_group(self):
        group_id = next(e['id'] for e in GRAPH if e['model'] == 'authentik_core.group' and e['identifiers']['name'] == READERS)
        targets = [e['identifiers']['target']['$ref'] for e in GRAPH
                   if e['model'] == 'authentik_policies.policybinding' and (e['identifiers'].get('group') or {}).get('$ref') == group_id]
        self.assertEqual([entry(t)['identifiers']['slug'] for t in targets], ['office-mail'])
        mail = entry(targets[0])
        self.assertEqual(mail['attrs']['policy_engine_mode'], 'any')
        bindings = [e for e in GRAPH if e['model'] == 'authentik_policies.policybinding'
                    and e['identifiers']['target']['$ref'] == mail['id']]
        # Mode "any" is only safe when every binding on the application is a plain group binding.
        for b in bindings:
            self.assertIsNone(b['identifiers']['policy'])
            self.assertIsNotNone(b['identifiers']['group'])
            self.assertFalse(b['attrs']['negate'])
        self.assertEqual(len(bindings), 2)

    def test_test_client_setup_keeps_extra_groups(self):
        source = (ROOT / 'integrations/authentik/configure_test_clients.py').read_text()
        self.assertIn("settings.get('also_groups',[])", source)
        self.assertIn("app.policy_engine_mode='any' if several else 'all'", source)


if __name__ == '__main__':
    unittest.main()
