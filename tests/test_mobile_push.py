"""mobile-push: alerts to closed phones through Google FCM (owner, 26 November 2026).

The rules are tested on the real module; the triggers run on the real `events` module against a small fake frappe.
These checks fail if a name or amount could reach Google, if a 400 could switch phones off, if someone could
register a phone for another person, or if an approval reached a person who may not read the document.
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
from erpnext_drive_integrations.mobile_push import events, rules  # noqa: E402

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
        site = rules.message(TOKEN, 'verify', rules.ATTENDANCE, 'FAE-1', 'S1', 'Site A')['message']['data']
        self.assertEqual(set(site), {'v', 'kind', 'doctype', 'docname', 'site', 'site_label'})
        self.assertTrue(all(isinstance(v, str) for v in site.values()), 'FCM data values must be strings')

    def test_only_waiting_and_returned_attendance_alerts(self):
        self.assertEqual(rules.attendance_kind('Submitted'), 'approval')
        self.assertEqual(rules.attendance_kind('Verified'), 'approval')
        self.assertEqual(rules.attendance_kind('Pending Verification'), 'verify')
        self.assertEqual(rules.attendance_kind('Returned'), 'returned')
        for quiet in ('Approved', 'Draft', None):
            self.assertIsNone(rules.attendance_kind(quiet))

    def test_dead_address_only_on_404_or_unregistered(self):
        self.assertTrue(rules.dead_token(404, None))
        self.assertTrue(rules.dead_token(400, {'error': {'details': [{'errorCode': 'UNREGISTERED'}]}}))
        self.assertFalse(rules.dead_token(400, {'error': {'status': 'INVALID_ARGUMENT'}}), 'a bad message switches nothing off')
        for status in (401, 403, 429, 500, 503):
            self.assertFalse(rules.dead_token(status, None))

    def test_recipients_skip_the_actor_and_system_users(self):
        self.assertEqual(rules.recipients(['b', 'a', 'a', None, 'Guest', 'Administrator', 'me'], 'me'), ['a', 'b'])


class FakeSite:
    """Just enough frappe for the triggers: rows by doctype, roles, permissions; records what would be sent."""

    def __init__(self, devices, roles=None, readable=(), entry=None):
        self.devices, self.roles, self.readable, self.entry, self.sent = devices, roles or {}, set(readable), entry, []
        fake.db = types.SimpleNamespace(get_value=self.get_value)
        fake.get_all = self.get_all
        fake.has_permission = lambda doctype, ptype, name, user: (user, name) in self.readable
        events.sender.send = lambda users, kind, doctype, docname=None, site=None, site_label=None: self.sent.append(
            (sorted(users), kind, doctype, docname, site, site_label))

    def get_value(self, doctype, name, fields, as_dict=False):
        if doctype == 'User':
            return 1
        if doctype == 'Field Site':
            return 'Site A'
        return types.SimpleNamespace(**self.entry) if self.entry else None

    def get_all(self, doctype, filters=None, pluck=None, distinct=False, fields=None):
        if doctype == 'Has Role':
            return sorted({u for u, rs in self.roles.items() if set(rs) & set(filters['role'][1])})
        if doctype == 'Mobile Device':
            return sorted({u for u in filters['user'][1] if u in self.devices})
        raise AssertionError(doctype)


def action(**values):
    row = {'status': 'Open', 'reference_doctype': 'Purchase Order', 'reference_name': 'PO-1', 'user': None,
           'permitted_roles': [types.SimpleNamespace(role='Purchase Manager')]}
    row.update(values)
    return types.SimpleNamespace(get=row.get, **row)


class WorkflowApprovals(unittest.TestCase):
    def test_role_holders_with_a_phone_who_may_read_it(self):
        site = FakeSite(devices={'pm@x', 'other@x', 'actor@example.com'},
                        roles={'pm@x': ['Purchase Manager'], 'other@x': ['Purchase Manager'], 'clerk@x': ['Purchase Manager'],
                               'actor@example.com': ['Purchase Manager'], 'hr@x': ['HR Manager']},
                        readable={('pm@x', 'PO-1'), ('actor@example.com', 'PO-1')})
        events.on_workflow_action(action())
        # other@x cannot read it (user permissions), clerk@x has no phone, hr@x lacks the role. The actor is still
        # listed here; sender.send drops them (rules.recipients, tested above).
        self.assertEqual(site.sent, [(['actor@example.com', 'pm@x'], 'approval', 'Purchase Order', 'PO-1', None, None)])

    def test_closed_or_incomplete_actions_send_nothing(self):
        site = FakeSite(devices={'pm@x'}, roles={'pm@x': ['Purchase Manager']}, readable={('pm@x', 'PO-1')})
        events.on_workflow_action(action(status='Completed'))
        events.on_workflow_action(action(reference_name=None))
        self.assertEqual(site.sent, [])


class AttendanceNotices(unittest.TestCase):
    def notice(self, state):
        site = FakeSite(devices={'pm@x'}, entry={'state': state, 'site': 'S1'})
        events.on_notification(types.SimpleNamespace(document_type=rules.ATTENDANCE, document_name='FAE-1', for_user='pm@x'))
        return site.sent

    def test_waiting_and_returned_alert_with_the_site(self):
        self.assertEqual(self.notice('Submitted'), [(['pm@x'], 'approval', rules.ATTENDANCE, 'FAE-1', 'S1', 'Site A')])
        self.assertEqual(self.notice('Returned')[0][1], 'returned')

    def test_approved_and_other_notices_send_nothing(self):
        self.assertEqual(self.notice('Approved'), [])
        site = FakeSite(devices={'pm@x'})
        events.on_notification(types.SimpleNamespace(document_type='ToDo', document_name='T1', for_user='pm@x'))
        self.assertEqual(site.sent, [])


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
        self.assertIn('erpnext_drive_integrations.mobile_push.events.on_workflow_action', hooks.doc_events['Workflow Action']['after_insert'])
        self.assertIn('erpnext_drive_integrations.mobile_push.events.on_notification', hooks.doc_events['Notification Log']['after_insert'])
        self.assertIn('erpnext_drive_integrations.mobile_push.events.on_user_update', hooks.doc_events['User']['on_update'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
