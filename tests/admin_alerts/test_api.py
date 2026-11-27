"""P72, P53: the admin alert inbox's report endpoint, mail, digest and seen-tracking (tiny fake Frappe, no site)."""
import datetime
import hashlib
import html
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
TOKEN = 'token-for-tests-only'
STATE = {}


class Dict(dict):
    __getattr__ = dict.get

    def __setattr__(self, key, value):
        self[key] = value


def reset(conf=None, body=None, token=TOKEN):
    STATE.update(rows={}, mails=[], count=0, now=datetime.datetime(2026, 11, 27, 9, 0),
                 headers={'X-Alert-Token': token} if token is not None else {},
                 body=json.dumps(body or {}),
                 roles={'admin@example.com': ['System Manager'], 'off@example.com': ['System Manager'],
                        'Administrator': ['System Manager'], 'staff@example.com': ['Employee'],
                        'ops@example.com': ['Ops Admin']},
                 users={'admin@example.com': 1, 'off@example.com': 0, 'staff@example.com': 1, 'ops@example.com': 1})
    frappe.conf = {'cloud_alerts': {'sources': {'web': hashlib.sha256(TOKEN.encode()).hexdigest()}}, **(conf or {})}


class ValidationError(Exception):
    pass


class PermissionError_(Exception):
    pass


def throw(message, exc=ValidationError):
    raise exc(message)


class Doc(Dict):
    def insert(self, ignore_permissions=False):
        STATE['count'] += 1
        self['name'] = f'a{STATE["count"]}'
        STATE['rows'][self['name']] = dict(self)
        return self

    def save(self, ignore_permissions=False):
        STATE['rows'][self['name']].update(self)
        return self


def get_doc(arg, name=None):
    return Doc(arg) if isinstance(arg, dict) else Doc(STATE['rows'][name])


def matches(row, filters):
    for field, want in (filters or {}).items():
        have = row.get(field)
        if isinstance(want, list):
            op, value = want
            if op == 'in' and have not in value or op == '>' and not (have and have > value):
                return False
        elif have != want:
            return False
    return True


def get_all(doctype, filters=None, fields=None, pluck=None, distinct=False, order_by=None):
    if doctype == 'Has Role':
        return [u for u, roles in STATE['roles'].items() if filters['role'] in roles]
    if doctype == 'User':
        rows = [{'name': u, 'email': u, 'enabled': on} for u, on in STATE['users'].items()]
        return [Dict(name=r['name'], email=r['email']) for r in rows if matches(r, filters)]
    rows = [r for r in STATE['rows'].values() if matches(r, filters)]
    if order_by:
        field = order_by.split()[0]
        rows.sort(key=lambda r: r.get(field) or datetime.datetime.min, reverse=order_by.endswith('desc'))
    return [Dict({f: r.get(f) for f in fields}) for r in rows]


def get_value(doctype, filters, fields=None, as_dict=False, for_update=False):
    if isinstance(filters, str):
        return STATE['rows'].get(filters, {}).get(fields)
    row = next((r for r in STATE['rows'].values() if matches(r, filters)), None)
    return Dict({f: row[f] for f in fields}) if row else None


def set_value(doctype, name, field, value, update_modified=True):
    STATE['rows'][name][field] = value
    STATE['rows'][name]['modified_touched'] = update_modified


frappe = types.ModuleType('frappe')
frappe.conf = {}
frappe.ValidationError, frappe.PermissionError, frappe.throw = ValidationError, PermissionError_, throw
frappe.whitelist = lambda **kw: (lambda f: f)
frappe.get_doc, frappe.get_all = get_doc, get_all
frappe.db = types.SimpleNamespace(get_value=get_value, set_value=set_value)
frappe.request = types.SimpleNamespace(get_data=lambda as_text=False: STATE['body'])
frappe.get_request_header = lambda name: STATE['headers'].get(name)
frappe.session = types.SimpleNamespace(user='admin@example.com')
frappe.get_roles = lambda user: STATE['roles'].get(user, [])
frappe.sendmail = lambda recipients, subject, message: STATE['mails'].append(
    {'to': recipients, 'subject': subject, 'message': message})
limiter = types.ModuleType('frappe.rate_limiter')
limiter.rate_limit = lambda **kw: (lambda f: f)
utils = types.ModuleType('frappe.utils')
utils.add_days = lambda d, n: d + datetime.timedelta(days=n)
utils.escape_html = html.escape
utils.get_url = lambda path='': 'https://erp.example.com' + path
utils.now_datetime = lambda: STATE['now']
frappe.utils = utils
sys.modules.update({'frappe': frappe, 'frappe.rate_limiter': limiter, 'frappe.utils': utils})

from erpnext_drive_integrations.admin_alerts import api  # noqa: E402


def send(**fields):
    body = {'source': 'web', 'key': 'disk', 'severity': 'critical', 'title': 'Disk full', **fields}
    STATE['body'] = json.dumps(body)
    return api.report()


def later(minutes=5):
    STATE['now'] += datetime.timedelta(minutes=minutes)


class TokenTests(unittest.TestCase):
    def test_configured_source_with_its_token_is_accepted(self):
        reset()
        result = send()
        self.assertEqual(result['status'], 'Open')
        self.assertEqual(STATE['rows'][result['name']]['alert_key'], 'web:disk')

    def test_wrong_missing_or_unknown_source_tokens_are_refused(self):
        for token, source in (('wrong', 'web'), (None, 'web'), ('', 'web'), (TOKEN, 'other'), (TOKEN, None)):
            reset(token=token)
            with self.assertRaises(PermissionError_):
                send(source=source)
            self.assertEqual(STATE['rows'], {})

    def test_switched_off_feature_refuses(self):
        reset(conf={'cloud_features': {'admin_alerts': False}})
        with self.assertRaises(PermissionError_):
            send()


class ValidationTests(unittest.TestCase):
    def test_bad_fields_are_rejected(self):
        bad = [{'key': 'Disk Full'}, {'key': ''}, {'key': 'x' * 81}, {'key': 'a/b'}, {'severity': 'fatal'},
               {'state': 'gone'}, {'title': ''}, {'title': 'x' * 141}, {'detail': 'x' * 2001}, {'host': 'h' * 65},
               {'link': 'javascript:alert(1)'}, {'link': '//evil.example/x'}, {'link': '/\\evil.example'},
               {'link': 'https://x.example/' + 'a' * 300}, {'title': 5}]
        for fields in bad:
            reset()
            with self.assertRaises(ValidationError, msg=str(fields)):
                send(**fields)
            self.assertEqual(STATE['rows'], {}, fields)

    def test_control_characters_are_removed_and_good_links_kept(self):
        reset()
        name = send(title='Disk\x1b[31m full\x00', detail='line 1\nline\x07 2', host='web-1\r',
                    link='/desk/system-alert')['name']
        row = STATE['rows'][name]
        self.assertEqual((row['title'], row['detail'], row['host']), ('Disk[31m full', 'line 1\nline 2', 'web-1'))
        self.assertEqual(row['link'], '/desk/system-alert')
        reset()
        self.assertEqual(STATE['rows'][send(link='https://grafana.example.com/d/x')['name']]['link'],
                         'https://grafana.example.com/d/x')


class UpsertAndMailTests(unittest.TestCase):
    def test_new_critical_alert_opens_and_mails_enabled_admins_once(self):
        reset()
        name = send(detail='<b>sda1</b> 99%', link='/desk')['name']
        row = STATE['rows'][name]
        self.assertEqual((row['status'], row['repeat_count'], row['first_seen'], row['last_seen']),
                         ('Open', 1, STATE['now'], STATE['now']))
        self.assertEqual(len(STATE['mails']), 1)
        mail = STATE['mails'][0]
        self.assertEqual(mail['to'], ['admin@example.com'])  # disabled user and Administrator skipped
        self.assertEqual(mail['subject'], '[Alert] Disk full')
        self.assertIn('&lt;b&gt;sda1&lt;/b&gt;', mail['message'])
        self.assertIn('https://erp.example.com/admin-alerts', mail['message'])

    def test_repeat_updates_without_mail(self):
        reset()
        name = send()['name']
        later()
        self.assertEqual(send(title='Disk still full', detail='99%')['name'], name)
        row = STATE['rows'][name]
        self.assertEqual((row['repeat_count'], row['title'], row['last_seen'], row['status']),
                         (2, 'Disk still full', STATE['now'], 'Open'))
        self.assertEqual(len(STATE['mails']), 1)

    def test_warning_and_info_never_mail_on_open(self):
        reset()
        send(severity='warning')
        send(key='other', severity='info')
        self.assertEqual(STATE['mails'], [])

    def test_open_alert_turning_critical_mails(self):
        reset()
        send(severity='warning')
        send(severity='warning')
        send(severity='critical')
        self.assertEqual([m['subject'] for m in STATE['mails']], ['[Alert] Disk full'])

    def test_resolve_closes_and_mails_only_for_critical(self):
        reset()
        name = send()['name']
        later()
        result = send(state='resolved')
        self.assertEqual(result, {'ok': True, 'name': name, 'status': 'Resolved'})
        self.assertEqual(STATE['rows'][name]['resolved_at'], STATE['now'])
        self.assertEqual(STATE['mails'][-1]['subject'], '[Resolved] Disk full')
        send(state='resolved')  # already resolved: nothing more
        self.assertEqual(len(STATE['mails']), 2)
        send(key='warn', severity='warning')
        send(key='warn', severity='warning', state='resolved')
        self.assertEqual(len(STATE['mails']), 2)

    def test_resolve_of_unknown_key_does_nothing(self):
        reset()
        self.assertEqual(send(state='resolved'), {'ok': True, 'name': None, 'status': None})
        self.assertEqual(STATE['rows'], {})

    def test_reopen_counts_clears_resolved_and_seen_and_mails(self):
        reset()
        name = send()['name']
        api.mark_seen([name], 'admin@example.com')
        send(state='resolved')
        later(61)  # past the hourly mail limit (see FlappingTests)
        send(detail='again')
        row = STATE['rows'][name]
        self.assertEqual((row['status'], row['repeat_count'], row['resolved_at'], row['_seen']), ('Open', 2, None, None))
        self.assertFalse(row['modified_touched'])
        self.assertEqual([m['subject'] for m in STATE['mails']], ['[Alert] Disk full', '[Resolved] Disk full', '[Alert] Disk full'])

    def test_mail_switch_off(self):
        reset()
        frappe.conf['cloud_alerts']['mail'] = False
        send()
        send(state='resolved')
        self.assertEqual(STATE['mails'], [])

    def test_recipients_follow_the_configured_role(self):
        reset()
        self.assertEqual(api.recipients(), ['admin@example.com'])
        frappe.conf['cloud_alerts']['role'] = 'Ops Admin'
        self.assertEqual(api.recipients(), ['ops@example.com'])
        frappe.conf['cloud_alerts']['role'] = 'Nobody'
        self.assertEqual(api.recipients(), [])


class FlappingTests(unittest.TestCase):
    def test_a_flapping_critical_check_mails_at_most_once_an_hour(self):
        reset()
        send()                      # opens: mailed
        later(); send(state='resolved')   # told about the opening: resolved mail
        later(); send()             # reopens within the hour: no mail
        later(); send(state='resolved')   # the admin's last news was "resolved": no mail
        self.assertEqual([m['subject'] for m in STATE['mails']], ['[Alert] Disk full', '[Resolved] Disk full'])
        later(61); send()           # an hour after the last mail: mailed again
        self.assertEqual(STATE['mails'][-1]['subject'], '[Alert] Disk full')
        self.assertEqual(len(STATE['mails']), 3)

    def test_turning_critical_is_mailed_even_within_the_hour(self):
        reset()
        send(severity='critical'); later(); send(state='resolved')
        later(); send(severity='warning')      # reopened as a warning: no mail
        later(); send(severity='critical')     # turns critical: mailed at once
        self.assertEqual([m['subject'] for m in STATE['mails']],
                         ['[Alert] Disk full', '[Resolved] Disk full', '[Alert] Disk full'])


class DigestTests(unittest.TestCase):
    def test_no_open_alerts_no_mail(self):
        reset()
        send()
        send(state='resolved')
        STATE['mails'].clear()
        api.daily_digest()
        self.assertEqual(STATE['mails'], [])

    def test_open_alerts_of_any_severity_are_summarised_once(self):
        reset()
        send(key='a', severity='info', title='Info <x>')
        send(key='b', severity='warning', title='Backup late', host='nas')
        STATE['mails'].clear()
        api.daily_digest()
        self.assertEqual(len(STATE['mails']), 1)
        mail = STATE['mails'][0]
        self.assertEqual(mail['subject'], '[Alerts] 2 still open')
        self.assertLess(mail['message'].index('Backup late'), mail['message'].index('Info &lt;x&gt;'))  # warning first
        self.assertIn('since 2026-11-27 09:00', mail['message'])


class SeenTests(unittest.TestCase):
    def test_unread_count_and_mark_seen_without_touching_modified(self):
        reset()
        first, second = send(key='a')['name'], send(key='b', severity='info')['name']
        send(key='c', severity='info')
        send(key='c', severity='info', state='resolved')
        self.assertEqual(api.unread_count('admin@example.com'), 2)
        api.mark_seen([first], 'admin@example.com')
        api.mark_seen([first], 'admin@example.com')
        self.assertEqual(json.loads(STATE['rows'][first]['_seen']), ['admin@example.com'])
        self.assertFalse(STATE['rows'][first]['modified_touched'])
        self.assertEqual(api.unread_count('admin@example.com'), 1)
        self.assertEqual(api.unread_count('ops@example.com'), 2)
        open_alerts, resolved = api.page_alerts('admin@example.com')
        self.assertEqual({a['name']: a['unread'] for a in open_alerts}, {first: False, second: True})
        self.assertEqual(len(resolved), 1)

    def test_is_admin_uses_the_role(self):
        reset()
        self.assertTrue(api.is_admin('admin@example.com'))
        self.assertTrue(api.is_admin('Administrator'))
        self.assertFalse(api.is_admin('staff@example.com'))
        frappe.conf['cloud_alerts']['role'] = 'Ops Admin'
        self.assertTrue(api.is_admin('ops@example.com'))
        self.assertFalse(api.is_admin('admin@example.com'))


class ShapeTests(unittest.TestCase):
    def test_doctype_and_hooks(self):
        meta = json.loads((ROOT / 'erpnext_drive_integrations/admin_alerts/doctype/system_alert/system_alert.json').read_text())
        self.assertEqual((meta['module'], meta['autoname'], meta['track_seen'], meta['sort_field']),
                         ('Admin Alerts', 'hash', 1, 'last_seen'))
        fields = {f['fieldname']: f for f in meta['fields']}
        self.assertEqual(fields['alert_key']['unique'], 1)
        self.assertEqual(set(meta['field_order']), set(fields))
        perm = meta['permissions'][0]
        self.assertEqual((perm['role'], perm['read'], perm['create'], perm['write'], perm['delete']),
                         ('System Manager', 1, 0, 0, 1))
        self.assertIn('Admin Alerts', (ROOT / 'erpnext_drive_integrations/modules.txt').read_text().splitlines())
        from erpnext_drive_integrations.admin_alerts import hooks
        self.assertIn('erpnext_drive_integrations.admin_alerts.api.daily_digest', hooks.scheduler_events['daily'])


if __name__ == '__main__':
    unittest.main()
