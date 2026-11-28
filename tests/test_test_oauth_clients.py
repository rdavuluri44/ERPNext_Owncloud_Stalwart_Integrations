"""P38: an app blocked on production gets its OAuth redirect URIs back on test."""
import os
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
STORE = {}
frappe = types.ModuleType('frappe')
frappe.conf = {}
frappe.get_all = lambda doctype, filters=None, pluck=None: [n for n, v in STORE.items() if v['app_name'] == filters['app_name']]
frappe.db = types.SimpleNamespace(set_value=lambda doctype, name, values: STORE[name].update(values))


class Doc(dict):
    def insert(self, ignore_permissions=False, set_name=None):
        STORE[set_name] = dict(self)


frappe.get_doc = lambda values: Doc(values)
sys.modules['frappe'] = frappe
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from erpnext_drive_integrations.operations import bootstrap  # noqa: E402
from prepare_test_profiles import native_site_settings  # noqa: E402

BLOCKED = 'urn:blocked:production-test-only-app'


class TestOAuthClients(unittest.TestCase):
    def setUp(self):
        STORE.clear()
        STORE['c1'] = {'app_name': 'Mobile', 'redirect_uris': BLOCKED, 'default_redirect_uri': BLOCKED}
        STORE['c2'] = {'app_name': 'Other', 'redirect_uris': BLOCKED, 'default_redirect_uri': BLOCKED}
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'test'
        frappe.conf = {'cloud_test_copy': True}

    def test_restores_only_the_named_app(self):
        out = bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb exp://x/cb',
                                                     'default_redirect_uri': 'app://cb'}])
        self.assertEqual(out, ['Mobile'])
        self.assertEqual(STORE['c1']['redirect_uris'], 'app://cb exp://x/cb')
        self.assertEqual(STORE['c1']['default_redirect_uri'], 'app://cb')
        self.assertEqual(STORE['c2']['redirect_uris'], BLOCKED)

    def test_refuses_outside_a_marked_test_copy(self):
        frappe.conf = {}
        with self.assertRaises(RuntimeError):
            bootstrap.restore_test_oauth_clients([])
        frappe.conf = {'cloud_test_copy': True}
        os.environ['CLOUD_DEPLOYMENT_TIER'] = 'production'
        with self.assertRaises(RuntimeError):
            bootstrap.restore_test_oauth_clients([])

    def test_default_must_be_one_of_the_uris(self):
        with self.assertRaises(ValueError):
            bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb',
                                                   'default_redirect_uri': 'evil://x'}])

    def test_creates_a_missing_native_client_with_its_fixed_id(self):
        out = bootstrap.restore_test_oauth_clients([{'app_name': 'UNformat ERP', 'client_id': 'mobile0test1',
                                                     'redirect_uris': 'exp://10.0.0.5:8081/--/oauth/callback'}])
        self.assertEqual(out, ['UNformat ERP'])
        made = STORE['mobile0test1']
        self.assertEqual((made['app_name'], made['grant_type'], made['response_type']), ('UNformat ERP', 'Authorization Code', 'Code'))
        self.assertEqual(made['token_endpoint_auth_method'], 'None')
        self.assertEqual(made['skip_authorization'], 0)
        self.assertEqual(made['default_redirect_uri'], 'exp://10.0.0.5:8081/--/oauth/callback')
        self.assertEqual(STORE['c1']['redirect_uris'], BLOCKED)

    def test_an_existing_client_keeps_its_id(self):
        bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'client_id': 'other0id1', 'redirect_uris': 'app://cb'}])
        self.assertNotIn('other0id1', STORE)
        self.assertEqual(STORE['c1']['redirect_uris'], 'app://cb')

    def test_consent_screen_only_skipped_when_profile_says_true(self):
        bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb'}])
        self.assertNotIn('skip_authorization', STORE['c1'])  # untouched unless named
        bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb', 'skip_authorization': True}])
        self.assertEqual(STORE['c1']['skip_authorization'], 1)
        bootstrap.restore_test_oauth_clients([{'app_name': 'Mobile', 'redirect_uris': 'app://cb', 'skip_authorization': 'yes'}])
        self.assertEqual(STORE['c1']['skip_authorization'], 0)  # only a real true skips it
        bootstrap.restore_test_oauth_clients([{'app_name': 'New App', 'client_id': 'newapp0001', 'redirect_uris': 'app://cb',
                                               'skip_authorization': True}])
        self.assertEqual(STORE['newapp0001']['skip_authorization'], 1)

    def test_client_id_is_validated(self):
        with self.assertRaises(ValueError):
            bootstrap.restore_test_oauth_clients([{'app_name': 'New', 'client_id': '../x', 'redirect_uris': 'app://cb'}])

    def test_only_native_clients_with_fixed_ids_enable_native_sign_in(self):
        self.assertEqual(native_site_settings([{'app_name': 'Web', 'redirect_uris': 'https://x/cb'}]), {})
        self.assertEqual(native_site_settings([{'app_name': 'UNformat ERP', 'client_id': 'mobile0test1', 'native': True}]),
                         {'cloud_native_mobile_enabled': True, 'cloud_native_mobile_clients': ['mobile0test1']})
        with self.assertRaises(ValueError):
            native_site_settings([{'app_name': 'UNformat ERP', 'native': True}])

    def tearDown(self):
        os.environ.pop('CLOUD_DEPLOYMENT_TIER', None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
