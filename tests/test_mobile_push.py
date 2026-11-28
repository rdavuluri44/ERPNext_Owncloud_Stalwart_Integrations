"""mobile-push: alerts to closed phones through Google FCM (owner, 26 November 2026).

The rules are tested on the real module. These checks fail if a name or amount could reach Google, if a 400
could switch phones off, or if someone could register a phone for another person. Who is alerted, and when, is
the notification service's (`tests/test_notifications.py`).
"""
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUSH = ROOT / 'erpnext_drive_integrations/mobile_push'

fake = types.ModuleType('frappe')
fake.conf = {}
fake.session = types.SimpleNamespace(user='actor@example.com')
fake.whitelist = lambda **_: (lambda f: f)
fake._ = lambda s: s
sys.modules['frappe'] = fake
from erpnext_drive_integrations import hooks  # noqa: E402
from erpnext_drive_integrations.mobile_push import rules  # noqa: E402

TOKEN = 'f' * 30 + ':APA91b' + 'x' * 120


class Rules(unittest.TestCase):
    def test_only_long_url_safe_tokens(self):
        self.assertTrue(rules.valid_token(TOKEN))
        for bad in ('', 'short', TOKEN + ' ', TOKEN + '<', None, 12345, 'a' * 5000):
            self.assertFalse(rules.valid_token(bad), repr(bad)[:20])

    def test_message_is_data_only_high_priority_and_carries_no_text(self):
        m = rules.message(TOKEN, 'approval', 'Payment Entry', 'ACC-PAY-0001')['message']
        self.assertEqual(set(m), {'token', 'data', 'android'})
        self.assertNotIn('notification', m, 'the phone writes the text; Google never sees one')
        self.assertEqual(m['android']['priority'], 'HIGH')
        self.assertEqual(m['data'], {'v': '1', 'kind': 'approval', 'doctype': 'Payment Entry', 'docname': 'ACC-PAY-0001'})
        site = rules.message(TOKEN, 'verify', 'Field Attendance Entry', 'FAE-1', 'S1', 'Site A')['message']['data']
        self.assertEqual(set(site), {'v', 'kind', 'doctype', 'docname', 'site', 'site_label'})
        self.assertTrue(all(isinstance(v, str) for v in site.values()), 'FCM data values must be strings')

    def test_the_service_s_own_fields_never_replace_the_message_s(self):
        data = rules.message(TOKEN, 'approval', 'Payment Entry', 'ACC-PAY-0001',
                             extra={'needs': 'decide', 'kind': 'other', 'docname': 'X', 'count': 3})['message']['data']
        self.assertEqual(data, {'v': '1', 'kind': 'approval', 'doctype': 'Payment Entry', 'docname': 'ACC-PAY-0001',
                                'needs': 'decide', 'count': '3'})
        bare = rules.message(TOKEN, 'reminder', extra={'count': 2, 'oldest_hours': 5})['message']
        self.assertEqual(bare['data'], {'v': '1', 'kind': 'reminder', 'count': '2', 'oldest_hours': '5'})
        self.assertEqual(bare['android']['collapse_key'], 'reminder:')

    def test_dead_address_only_on_404_or_unregistered(self):
        self.assertTrue(rules.dead_token(404, None))
        self.assertTrue(rules.dead_token(400, {'error': {'details': [{'errorCode': 'UNREGISTERED'}]}}))
        self.assertFalse(rules.dead_token(400, {'error': {'status': 'INVALID_ARGUMENT'}}), 'a bad message switches nothing off')
        for status in (401, 403, 429, 500, 503):
            self.assertFalse(rules.dead_token(status, None))

    def test_recipients_skip_the_actor_and_system_users(self):
        self.assertEqual(rules.recipients(['b', 'a', 'a', None, 'Guest', 'Administrator', 'me'], 'me'), ['a', 'b'])
        self.assertEqual(rules.recipients(['b', 'me', 'Guest'], None), ['b', 'me'], 'an alert to remove is for the actor too')


class Surface(unittest.TestCase):
    API = (PUSH / 'api.py').read_text(encoding='utf-8')
    SENDER = (PUSH / 'sender.py').read_text(encoding='utf-8')

    def test_calls_are_post_only_and_for_the_signed_in_person(self):
        for name in ('register_device', 'unregister_device'):
            self.assertRegex(self.API, r"@frappe\.whitelist\(methods=\['POST'\]\)\s*def " + name + r'\(', name)
        self.assertNotIn('user=None', self.API, 'nobody registers a phone for someone else')
        self.assertIn("filters={'user': user, 'token_hash'", self.API, 'sign-out removes only the own record')
        self.assertIn("platform != 'android' or not rules.valid_token(token)", self.API)

    def test_sending_waits_for_the_commit_and_logs_no_address(self):
        self.assertIn("enqueue_after_commit=True", self.SENDER)
        log = self.SENDER.split('frappe.log_error(')[1].split('\n')[0]
        self.assertNotIn('token', log)
        self.assertNotIn('json=', log)
        self.assertIn("frappe.conf.get('mobile_push_fcm_key_file')", self.SENDER)

    def test_device_list_is_for_system_managers_and_hides_the_address(self):
        doc = json.loads((PUSH / 'doctype/mobile_device/mobile_device.json').read_text(encoding='utf-8'))
        self.assertEqual([p['role'] for p in doc['permissions']], ['System Manager'])
        fields = {f['fieldname']: f for f in doc['fields']}
        self.assertTrue(fields['token']['hidden'] and fields['token']['read_only'])
        self.assertTrue(fields['token_hash']['unique'])
        self.assertEqual(doc['module'], 'Mobile Push')
        self.assertIn('Mobile Push', (ROOT / 'erpnext_drive_integrations/modules.txt').read_text(encoding='utf-8').splitlines())

    def test_hooks_are_composed(self):
        self.assertIn('erpnext_drive_integrations.mobile_push.events.on_user_update', hooks.doc_events['User']['on_update'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
