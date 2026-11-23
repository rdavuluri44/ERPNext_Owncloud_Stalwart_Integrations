"""P49: sign-in settings that must agree between the ERP and authentik, and the identity stack's tuning.

On 20 November 2026 production's ERP provider sent a legacy approval claim while the ERP required
`cloud_approved`; new ERP sign-ins failed for days. These tests fail when the claim the ERP requires is not
the one the provider's scope mapping sends. No live authentik or ERP: the real modules with a small fake frappe.
"""
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

frappe = types.ModuleType('frappe')
frappe.conf = {}
frappe.AuthenticationError = type('AuthenticationError', (Exception,), {})
frappe.whitelist = lambda **kwargs: (lambda f: f)
oauth = types.ModuleType('frappe.utils.oauth')
for name in ['get_oauth2_authorize_url', 'get_oauth2_flow', 'get_oauth_keys', 'get_oauth2_providers',
             'get_redirect_uri', 'login_oauth_user', 'consume_oauth_state', 'create_oauth_state']:
    setattr(oauth, name, lambda *a, **k: None)
sys.modules.update({'frappe': frappe, 'frappe.utils': types.ModuleType('frappe.utils'), 'frappe.utils.oauth': oauth})
sys.modules.setdefault('jwt', types.ModuleType('jwt'))
spec = importlib.util.spec_from_file_location('sso_under_test', ROOT / 'erpnext_drive_integrations/portal/sso.py')
sso = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sso)
sys.path.insert(0, str(ROOT / 'tools'))
import prepare_runtime  # noqa: E402

GRAPH = json.loads((ROOT / 'integrations/authentik/configuration.json').read_text())['entries']


def claims_sent(expression):
    """The claim names a scope mapping's `return {...}` sends."""
    body = re.search(r'return\s*\{(.*)\}', expression, re.S)
    return set(re.findall(r'[\'"]([a-z_]+)[\'"]\s*:', body.group(1))) if body else set()


class ApprovalClaim(unittest.TestCase):
    def tearDown(self):
        frappe.conf = {}

    def test_the_erp_provider_sends_the_claim_the_erp_requires(self):
        by_id = {e.get('id'): e for e in GRAPH}
        provider = next(e for e in GRAPH if e.get('model', '').endswith('oauth2provider')
                        and e.get('identifiers', {}).get('name') == 'Workspace ERPNext')
        sent = set()
        for ref in provider['attrs']['property_mappings']:
            sent |= claims_sent(by_id[ref['$ref']]['attrs'].get('expression', ''))
        self.assertIn(sso.APPROVED_CLAIM, sent, 'the ERP provider must send the approval claim the ERP checks')

    def test_examples_and_test_clients_send_the_same_claim(self):
        examples = json.loads((ROOT / 'deployment/scope-mappings.example.json').read_text())
        approved = next(m for m in examples if m['name'] == 'Workspace approved identity')
        self.assertIn(sso.APPROVED_CLAIM, claims_sent(approved['expression']))
        script = (ROOT / 'integrations/authentik/configure_test_clients.py').read_text()
        self.assertIn("claim=profile.get('approved_claim','" + sso.APPROVED_CLAIM + "')", script)

    def test_the_erp_names_the_claim_in_one_place(self):
        named = []
        for path in (ROOT / 'erpnext_drive_integrations').rglob('*.py'):
            for line in path.read_text(encoding='utf-8').splitlines():
                if re.search(r'["\']' + sso.APPROVED_CLAIM + r'["\']', line):
                    named.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(named, ['erpnext_drive_integrations/portal/sso.py'])

    def test_only_a_literal_true_approves(self):
        self.assertTrue(sso.is_approved({'cloud_approved': True}))
        for claims in ({}, {'cloud_approved': 'true'}, {'cloud_approved': 1}, {'legacy_approved': True}):
            self.assertFalse(sso.is_approved(claims), claims)

    def test_a_deployment_can_name_its_claim_and_bad_names_are_refused(self):
        frappe.conf = {'cloud_approved_claim': 'legacy_approved'}
        self.assertTrue(sso.is_approved({'legacy_approved': True}))
        self.assertFalse(sso.is_approved({'cloud_approved': True}))
        for bad in ('', 'x-y', '1abc', 'a b', ['cloud_approved']):
            frappe.conf = {'cloud_approved_claim': bad}
            if bad == '':
                self.assertTrue(sso.is_approved({'cloud_approved': True}), 'empty means the default')
                continue
            with self.assertRaises(frappe.AuthenticationError):
                sso.is_approved({'cloud_approved': True})


class InvitationBranding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = ROOT / 'integrations/authentik/invite-recovery'
        self.templates = Path(self.tmp.name) / 'templates'
        self.public = Path(self.tmp.name) / 'public'
        shutil.copytree(base / 'templates', self.templates)
        shutil.copytree(base / 'public', self.public)

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_leave_every_file_unchanged(self):
        before = {p: p.read_bytes() for p in Path(self.tmp.name).rglob('*') if p.is_file()}
        prepare_runtime.brand_invitations(self.templates)
        prepare_runtime.brand_invitations(self.public)
        self.assertEqual({p: p.read_bytes() for p in Path(self.tmp.name).rglob('*') if p.is_file()}, before)

    def test_brand_and_template_names_come_from_the_profile(self):
        prepare_runtime.brand_invitations(self.templates, 'Acme Works', 'acme-')
        prepare_runtime.brand_invitations(self.public, 'Acme Works', 'acme-')
        names = sorted(p.name for p in (self.templates / 'email').iterdir())
        self.assertEqual(names, ['acme-enrollment-invitation.html', 'acme-enrollment-invitation.txt',
                                 'acme-passkey-steps.html', 'acme-passkey-steps.txt',
                                 'acme-recovery-invitation.html', 'acme-recovery-invitation.txt'])
        html = (self.templates / 'email/acme-enrollment-invitation.html').read_text()
        self.assertIn('Set up your Acme Works passkey', html)
        self.assertIn('iCloud Keychain', html, 'iCloud is not the brand')
        self.assertIn('SET UP YOUR ACME WORKS PASSKEY', (self.templates / 'email/acme-enrollment-invitation.txt').read_text())
        page = (self.public / 'invitations.mjs').read_text()
        self.assertIn('email/acme-recovery-invitation.html', page)
        self.assertIn('email/acme-enrollment-invitation.html', page)
        self.assertNotIn('email/cloud-', page)
        self.assertIn('Invite user · Acme Works', (self.public / 'index.html').read_text())
        for path in Path(self.tmp.name).rglob('*'):
            if path.is_file():
                self.assertNotIn('Cloud passkey', path.read_text(errors='replace'), path)

    def test_unsafe_settings_are_refused(self):
        for brand, prefix in (('<b>x</b>', 'acme-'), ('Acme', 'Acme-'), ('Acme', 'acme'), ('Acme', '../x-')):
            with self.assertRaises(ValueError):
                prepare_runtime.brand_invitations(self.templates, brand, prefix)


class IdentityStack(unittest.TestCase):
    STACK = json.loads((ROOT / 'deployment/stacks/identity.compose.json').read_text())['services']
    INPUTS = json.loads((ROOT / 'deployment/stacks/inputs.json').read_text())

    def test_database_runs_without_jit(self):
        self.assertEqual(self.STACK['postgresql']['command'], ['postgres', '-c', 'jit=off'])

    def test_server_has_three_gigabytes_and_a_worker_lifetime(self):
        self.assertEqual(self.STACK['server']['mem_limit'], '3g')
        self.assertIn('AUTHENTIK_WEB__MAX_REQUESTS', self.STACK['server']['environment'])
        self.assertEqual(self.INPUTS['CI_IDENTITY_SERVER_AUTHENTIK_WEB__MAX_REQUESTS']['default'], '1000')

    def test_policy_cache_stays_off_as_production_runs_it(self):
        for role in ('SERVER', 'WORKER'):
            self.assertEqual(self.INPUTS['CI_IDENTITY_' + role + '_AUTHENTIK_CACHE__TIMEOUT_POLICIES']['default'], '0')


class WebmailName(unittest.TestCase):
    def test_an_explicit_product_name_reaches_webmail(self):
        source = (ROOT / 'tools/prepare_runtime.py').read_text()
        self.assertIn("'APP_NAME':profile.get('settings',{}).get('CI_MAIL_WEBMAIL_APP_NAME') or 'Mail'", source)
        self.assertNotIn("'APP_NAME':'Mail'", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
