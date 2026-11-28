"""The notification service (P108) on a small fake site: the real `service` and `events` modules, a fake frappe, a
fake phone channel and a fake chat.

These checks fail if an event could be sent twice, if a decision's alert or mail could carry content, if a phone
could ring for information, if a reminder could go out at night or more often than every 4 hours, if a decided
thing could stay on a phone, or if a waiting record could be removed.
"""
import datetime
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HERE = ROOT / 'erpnext_drive_integrations/notifications'
RECORD = 'Notification Record'


class Row(dict):
    __getattr__ = dict.get


class Duplicate(Exception):
    pass


fake = types.ModuleType('frappe')
fake.conf = {}
fake.session = types.SimpleNamespace(user='actor@x')
fake.flags = Row()
fake.whitelist = lambda **_: (lambda f: f)
fake._ = lambda s: s
fake.UniqueValidationError = Duplicate
fake.AuthenticationError = type('AuthenticationError', (Exception,), {})
sys.modules['frappe'] = fake
phone = types.ModuleType('erpnext_drive_integrations.mobile_push.sender')
chat = types.ModuleType('erpnext_drive_integrations.chat_rooms.sync')
sys.modules[phone.__name__], sys.modules[chat.__name__] = phone, chat
workflow_module = types.ModuleType('frappe.model.workflow')
sys.modules['frappe.model'], sys.modules['frappe.model.workflow'] = types.ModuleType('frappe.model'), workflow_module

from erpnext_drive_integrations import hooks  # noqa: E402
from erpnext_drive_integrations.notifications import api, events, rules, service  # noqa: E402


def at(day, hour, minute=0):
    return datetime.datetime(2026, 11, day, hour, minute)


def matches(row, filters):
    for field, want in (filters or {}).items():
        have = row.get(field)
        if isinstance(want, list):
            op, value = want
            if not {'is': lambda: have is not None, '<': lambda: have is not None and have < value,
                    'in': lambda: have in value}[op]():
                return False
        elif have != want:
            return False
    return True


class Site:
    """Just enough frappe: the record table, people, phones, chat, workflows and documents; what was sent."""

    def __init__(self, now=at(27, 10), phones=(), in_chat=(), workflows=None, documents=None, roles=None, readable=(),
                 key=True):
        self.now, self.phones, self.in_chat, self.key = now, set(phones), set(in_chat), key
        self.workflows, self.documents = workflows or {}, documents or {}
        self.roles, self.readable = roles or {}, set(readable)
        self.records, self.jobs, self.pushes, self.signals, self.mails, self.notices, self.queries = {}, [], [], [], [], [], 0
        fake.conf, fake.session.user = {}, 'actor@x'
        fake.utils = types.SimpleNamespace(now_datetime=lambda: self.now, escape_html=lambda s: s.replace('<', '&lt;'),
                                           get_url_to_form=lambda d, n: f'https://erp.example/desk/{d}/{n}')
        fake.db = types.SimpleNamespace(exists=self.exists, get_value=self.get_value, set_value=self.set_value,
                                        delete=self.delete)
        fake.get_all, fake.get_doc, fake.enqueue = self.get_all, self.get_doc, self.enqueue
        fake.sendmail = lambda **mail: self.mails.append(mail)
        fake.log_error = lambda *a: None
        fake.has_permission = lambda doctype, ptype, name, user: (user, name) in self.readable
        fake.get_cached_value = lambda doctype, name, field: self.workflows[name][field]
        workflow_module.get_workflow_name = lambda doctype: doctype if doctype in self.workflows else None
        phone.configured = lambda: self.key
        phone.deliver, phone.send = self.push, self.signal
        chat.notify = self.notice

    # the phone channel and chat
    def push(self, users, kind, doctype=None, docname=None, site=None, site_label=None, extra=None):
        reached = [u for u in users if u in self.phones]
        if reached:
            self.pushes.append((reached, kind, doctype, docname, site, site_label, extra))
        return len(reached)

    def signal(self, users, kind, doctype=None, docname=None, site=None, site_label=None, extra=None, include_actor=False):
        self.signals.append((sorted(users), kind, doctype, docname, include_actor))

    def notice(self, user, key, text):
        if user in self.in_chat:
            self.notices.append((user, text))
        return user in self.in_chat

    # frappe
    def rows(self, doctype, filters):
        self.queries += 1
        if doctype == RECORD:
            return [r for r in self.records.values() if matches(r, filters)]
        raise AssertionError(doctype)

    def exists(self, doctype, filters):
        if doctype == RECORD:
            return bool(self.rows(doctype, filters))
        if doctype == 'Mobile Device':
            return filters['user'] in self.phones
        return filters in self.documents.get(doctype, {})

    def get_value(self, doctype, name, fields, as_dict=False):
        if doctype == RECORD:
            return self.records.get(name)
        if doctype == 'User':
            return name['name'] if isinstance(name, dict) else 1
        if doctype == 'Field Site':
            return 'Site A'
        if doctype == 'Workflow':
            return self.workflows.get(name['document_type'], {}).get(fields)
        document = self.documents.get(doctype, {}).get(name)
        if document is None:
            return None
        return Row(document) if as_dict else document.get(fields)

    def set_value(self, doctype, name, values, update_modified=True):
        self.records[name].update(values)

    def delete(self, doctype, filters):
        for name in [r.name for r in self.rows(doctype, filters)]:
            del self.records[name]

    def get_all(self, doctype, filters=None, fields=None, pluck=None, distinct=False):
        if doctype == 'Has Role':
            return sorted(u for u, own in self.roles.items() if set(own) & set(filters['role'][1]))
        rows = self.rows(doctype, filters)
        return [r[pluck] for r in rows] if pluck else rows

    def get_doc(self, values):
        site = self

        class Doc:
            def insert(self, ignore_permissions=False):
                if values.get('open_key') and site.rows(RECORD, {'open_key': values['open_key']}):
                    raise Duplicate()
                self.name = f'R{len(site.records) + 1}'
                site.records[self.name] = Row(values, name=self.name, channel=None, last_reminder=None, reminders=0)
                return self
        return Doc()

    def enqueue(self, method, **job):
        assert job.pop('enqueue_after_commit') is True, 'nothing goes out before the save is committed'
        self.jobs.append((method, job))

    def commit(self):
        """What the background worker does after the save committed."""
        jobs, self.jobs = self.jobs, []
        for method, job in jobs:
            job.pop('queue')
            getattr(service, method.rsplit('.', 1)[1])(**job)

    def record(self, user):
        return [r for r in self.records.values() if r.user == user]


def decide(site, users, name='PO-1', state='Pending', **more):
    made = service.notify(users, rules.DECIDE, 'Purchase Order', name, reason='approval', state=state, **more)
    site.commit()
    return made


class Decisions(unittest.TestCase):
    def test_a_decision_rings_the_phone_once_and_carries_no_content(self):
        site = Site(phones={'pm@x'})
        service.notify(['pm@x'], rules.DECIDE, 'Purchase Order', 'PO-1', reason='approval', state='Pending')
        self.assertEqual(site.pushes, [], 'nothing leaves before the save is committed')
        site.commit()
        self.assertEqual(site.pushes, [(['pm@x'], 'approval', 'Purchase Order', 'PO-1', None, None, {'needs': 'decide'})])
        self.assertEqual(site.mails, [])
        record = site.record('pm@x')[0]
        self.assertEqual((record.channel, record.kind, record.resolved_at), ('phone', 'decide', None))
        self.assertEqual(decide(site, ['pm@x']), [], 'the same event again makes no second record')
        self.assertEqual(len(site.pushes), 1)

    def test_without_a_phone_the_decision_goes_by_mail_without_content(self):
        site = Site()
        decide(site, ['clerk@x'])
        self.assertEqual(site.pushes, [])
        mail = site.mails[0]
        self.assertEqual((mail['recipients'], mail['subject']), (['clerk@x'], 'Something waits for your decision'))
        self.assertNotIn('Pending', mail['message'])
        self.assertIn('https://erp.example/desk/Purchase Order/PO-1', mail['message'], 'only the link to the document')
        self.assertEqual(site.record('clerk@x')[0].channel, 'mail')

    def test_no_second_mail_where_the_workflow_mails_its_approvers_itself(self):
        site = Site(workflows={'Purchase Order': {'send_email_alert': 1}})
        decide(site, ['clerk@x'])
        self.assertEqual(site.mails, [])
        self.assertEqual(site.record('clerk@x')[0].channel, 'workflow mail')

    def test_no_key_or_the_phone_channel_switched_off_means_mail(self):
        for key, conf in ((False, {}), (True, {'cloud_features': {'mobile_push': False}})):
            site = Site(phones={'pm@x'}, key=key)
            fake.conf = conf
            decide(site, ['pm@x'])
            self.assertEqual((site.pushes, len(site.mails)), ([], 1))

    def test_the_person_who_caused_it_and_system_users_get_nothing(self):
        site = Site(phones={'actor@x', 'pm@x'})
        decide(site, ['actor@x', 'pm@x', 'pm@x', 'Guest', 'Administrator', None])
        self.assertEqual([r.user for r in site.records.values()], ['pm@x'])

    def test_decided_before_it_went_out_sends_nothing(self):
        site = Site(phones={'pm@x'})
        service.notify(['pm@x'], rules.DECIDE, 'Purchase Order', 'PO-1', reason='approval', state='Pending')
        service.resolve('Purchase Order', 'PO-1', 'Approved')
        site.commit()
        self.assertEqual((site.pushes, site.mails, site.signals), ([], [], []))

    def test_a_kind_that_does_not_exist_is_refused(self):
        Site()
        with self.assertRaises(rules.RuleError):
            service.notify(['pm@x'], 'urgent', 'Purchase Order', 'PO-1')


class Information(unittest.TestCase):
    def inform(self, site, state='Approved', text='Your leave was approved.'):
        made = service.notify(['a@x'], rules.INFORM, 'Leave Application', 'LAP-1', state=state, text=text)
        site.commit()
        return made

    def test_information_goes_to_the_notices_room_and_never_rings(self):
        site = Site(phones={'a@x'}, in_chat={'a@x'})
        self.inform(site)
        self.assertEqual((site.notices, site.pushes, site.mails), ([('a@x', 'Your leave was approved.')], [], []))
        record = site.record('a@x')[0]
        self.assertEqual((record.channel, record.open_key, record.resolved_at), ('chat', None, site.now),
                         'information waits for nobody: recorded and closed at once')

    def test_not_in_chat_means_mail_with_the_text_made_safe(self):
        for in_chat, conf in ((set(), {}), ({'a@x'}, {'cloud_features': {'chat_rooms': False}})):
            site = Site(phones={'a@x'}, in_chat=in_chat)
            fake.conf = conf
            self.inform(site, text='Returned <b>today</b>')
            self.assertEqual((site.pushes, site.notices), ([], []))
            self.assertIn('Returned &lt;b>today', site.mails[0]['message'])
            self.assertEqual(site.record('a@x')[0].channel, 'mail')

    def test_the_same_notice_is_sent_once_and_a_new_state_is_a_new_notice(self):
        site = Site(in_chat={'a@x'})
        self.inform(site)
        self.assertEqual(self.inform(site), [])
        self.assertEqual(len(self.inform(site, state='Cancelled', text='Cancelled.')), 1)
        self.assertEqual(len(site.notices), 2)


class Decided(unittest.TestCase):
    def test_a_decided_thing_is_closed_and_removed_from_the_phones(self):
        site = Site(phones={'pm@x', 'actor@x'})
        decide(site, ['pm@x', 'clerk@x'])
        fake.session.user = 'other@x'
        decide(site, ['actor@x'])  # the actor of this test also holds an alert, from someone else's action
        fake.session.user = 'actor@x'
        self.assertEqual(service.resolve('Purchase Order', 'PO-1', 'Approved'), 3)
        self.assertTrue(all(r.resolved_at == site.now and r.open_key is None for r in site.records.values()))
        self.assertEqual(site.signals, [(['actor@x', 'pm@x'], 'remove', 'Purchase Order', 'PO-1', True)],
                         'phones only, the deciding person included; a kind and a reference, nothing else')

    def test_records_of_the_current_state_stay(self):
        site = Site(phones={'pm@x', 'dir@x'})
        decide(site, ['pm@x'], state='Pending')
        decide(site, ['dir@x'], state='Pending Director')
        self.assertEqual(service.resolve('Purchase Order', 'PO-1', 'Pending Director'), 1)
        self.assertIsNotNone(site.record('pm@x')[0].resolved_at)
        self.assertIsNone(site.record('dir@x')[0].resolved_at)

    def test_it_can_wait_for_the_same_person_again_later(self):
        site = Site(phones={'pm@x'})
        decide(site, ['pm@x'])
        service.resolve('Purchase Order', 'PO-1', 'Returned')
        self.assertEqual(len(decide(site, ['pm@x'])), 1)
        self.assertEqual(len(site.pushes), 2)

    def test_a_disabled_person_waits_for_nothing(self):
        site = Site(phones={'pm@x'})
        decide(site, ['pm@x'])
        events.on_user_update(types.SimpleNamespace(name='pm@x', enabled=0))
        self.assertIsNotNone(site.record('pm@x')[0].resolved_at)
        self.assertEqual(site.signals, [])

    def test_the_hourly_run_closes_what_the_events_missed_and_only_its_own(self):
        site = Site(phones={'pm@x'}, workflows={'Purchase Order': {'workflow_state_field': 'workflow_state'}},
                    documents={'Purchase Order': {'PO-1': {'workflow_state': 'Approved'}, 'PO-2': {'workflow_state': 'Pending'}},
                               rules.ATTENDANCE: {'FAE-1': {'state': 'Submitted'}}})
        decide(site, ['pm@x'], 'PO-1')   # approved meanwhile
        decide(site, ['pm@x'], 'PO-2')   # still waits
        decide(site, ['pm@x'], 'PO-3')   # deleted
        service.notify(['pm@x'], rules.DECIDE, rules.ATTENDANCE, 'FAE-1', reason='verify', state='Pending Verification')
        service.notify(['pm@x'], rules.DECIDE, 'Task', 'T-1', reason='review', state='Open')  # another module's
        site.commit()
        self.assertEqual(service.heal(), 3)
        still = sorted(r.reference_name for r in site.records.values() if r.resolved_at is None)
        self.assertEqual(still, ['PO-2', 'T-1'])


class Reminders(unittest.TestCase):
    def waiting(self):
        site = Site(now=at(27, 9), phones={'pm@x', 'dir@x'},
                    workflows={'Purchase Order': {'workflow_state_field': 'workflow_state'}},
                    documents={'Purchase Order': {'PO-1': {'workflow_state': 'Pending'},
                                                  'PO-2': {'workflow_state': 'Pending'}}})
        decide(site, ['pm@x', 'clerk@x'], 'PO-1')
        site.now = at(27, 11)
        decide(site, ['pm@x', 'dir@x'], 'PO-2')
        site.pushes.clear()
        site.mails.clear()
        return site

    def test_one_reminder_per_person_with_a_count_and_hours_only(self):
        site = self.waiting()
        site.now = at(27, 13, 5)
        self.assertEqual(service.remind(), 1)
        self.assertEqual(site.pushes, [(['pm@x'], 'reminder', None, None, None, None, {'count': 2, 'oldest_hours': 4})],
                         'dir@x waits only two hours; clerk@x has no phone and got a mail at the start')
        self.assertEqual(site.mails, [])
        self.assertEqual({(r.last_reminder, r.reminders) for r in site.record('pm@x')}, {(site.now, 1)})

    def test_never_more_often_than_every_four_hours_per_person(self):
        site = self.waiting()
        site.now = at(27, 13, 5)
        service.remind()
        site.now = at(27, 15, 30)   # PO-2 now waits more than 4 hours, but pm@x was reminded at 13:05
        site.pushes.clear()
        service.remind()
        self.assertEqual([p[0] for p in site.pushes], [['dir@x']])
        site.now = at(27, 17, 5)
        site.pushes.clear()
        service.remind()
        self.assertEqual([p[0] for p in site.pushes], [['pm@x']])

    def test_never_at_night_and_then_at_seven(self):
        site = self.waiting()
        for hour in (21, 23):
            site.now = at(27, hour)
            self.assertEqual(service.remind(), 0)
        site.now = at(28, 6, 59)
        self.assertEqual(service.remind(), 0)
        site.now = at(28, 7)
        self.assertEqual(service.remind(), 2)

    def test_what_was_decided_is_not_reminded(self):
        site = self.waiting()
        service.resolve('Purchase Order', 'PO-1', 'Approved')
        service.resolve('Purchase Order', 'PO-2', 'Approved')
        site.now = at(27, 16)
        self.assertEqual(service.remind(), 0)


class Keeping(unittest.TestCase):
    def test_closed_records_go_after_ninety_days_and_waiting_ones_never(self):
        site = Site(now=at(1, 9), phones={'pm@x'})
        decide(site, ['pm@x'], 'PO-1')
        decide(site, ['pm@x'], 'PO-2')
        service.resolve('Purchase Order', 'PO-1', 'Approved')
        site.now = at(1, 9) + datetime.timedelta(days=90)
        service.purge()
        self.assertEqual(len(site.records), 2, 'ninety days exactly: still kept')
        site.now += datetime.timedelta(days=300)
        service.purge()
        self.assertEqual([r.reference_name for r in site.records.values()], ['PO-2'])


class WhatWaitsForMe(unittest.TestCase):
    def test_numbers_per_kind_and_site_for_the_signed_in_person_only(self):
        site = Site(now=at(27, 8), phones={'pm@x'})
        decide(site, ['pm@x', 'other@x'], 'PO-1')
        site.now = at(27, 10)
        decide(site, ['pm@x'], 'PO-2', deadline=at(29, 18))
        service.notify(['pm@x'], rules.DECIDE, rules.ATTENDANCE, 'FAE-1', reason='verify', state='Pending Verification',
                       site='S1')
        service.notify(['pm@x'], rules.INFORM, 'Leave Application', 'LAP-1', state='Approved', text='Approved.')
        site.commit()
        site.now = at(27, 13, 30)
        fake.session.user = 'pm@x'
        answer = api.waiting()
        self.assertEqual({k: answer[k] for k in ('count', 'waiting_since', 'longest_wait_hours', 'nearest_deadline')},
                         {'count': 3, 'waiting_since': '2026-11-27 08:00:00', 'longest_wait_hours': 5,
                          'nearest_deadline': '2026-11-29 18:00:00'})
        self.assertEqual([(k['reason'], k['doctype'], k['count'], k['longest_wait_hours']) for k in answer['kinds']],
                         [('approval', 'Purchase Order', 2, 5), ('verify', rules.ATTENDANCE, 1, 3)])
        self.assertEqual([(s['site'], s['count']) for s in answer['sites']], [('S1', 1)])
        self.assertNotIn('PO-1', json.dumps(answer), 'numbers only')
        fake.session.user = 'nobody@x'
        self.assertEqual(api.waiting(), {'count': 0, 'waiting_since': None, 'longest_wait_hours': 0,
                                         'nearest_deadline': None, 'kinds': [], 'sites': []})

    def test_the_call_is_read_only_and_refuses_a_guest(self):
        source = (HERE / 'api.py').read_text(encoding='utf-8')
        self.assertRegex(source, r"@frappe\.whitelist\(methods=\['GET'\]\)\s*def waiting\(\)")
        self.assertNotIn('user=', source.split('def waiting')[1], 'nobody asks for someone else')
        Site()
        fake.session.user = 'Guest'
        fake.throw = lambda message, error: (_ for _ in ()).throw(error(message))
        with self.assertRaises(fake.AuthenticationError):
            api.waiting()


def action(**values):
    row = {'status': 'Open', 'reference_doctype': 'Purchase Order', 'reference_name': 'PO-1', 'user': None,
           'workflow_state': 'Pending', 'permitted_roles': [types.SimpleNamespace(role='Purchase Manager')]}
    row.update(values)
    return types.SimpleNamespace(get=row.get, **row)


class Triggers(unittest.TestCase):
    def test_an_approval_is_for_role_holders_who_may_read_it_phone_or_not(self):
        site = Site(phones={'pm@x', 'other@x'},
                    roles={'pm@x': ['Purchase Manager'], 'other@x': ['Purchase Manager'], 'clerk@x': ['Purchase Manager'],
                           'actor@x': ['Purchase Manager'], 'hr@x': ['HR Manager']},
                    readable={('pm@x', 'PO-1'), ('clerk@x', 'PO-1'), ('actor@x', 'PO-1')})
        events.on_workflow_action(action())
        site.commit()
        # other@x may not read it (user permissions), hr@x lacks the role, actor@x moved it there.
        self.assertEqual(sorted((r.user, r.channel, r.state, r.reason) for r in site.records.values()),
                         [('clerk@x', 'mail', 'Pending', 'approval'), ('pm@x', 'phone', 'Pending', 'approval')])
        events.on_workflow_action(action(status='Completed'))
        events.on_workflow_action(action(reference_name=None))
        events.on_workflow_action(action(user='hr@x'))  # named, but may not read it
        self.assertEqual(len(site.records), 2)

    def notice(self, state):
        site = Site(phones={'pm@x'}, documents={rules.ATTENDANCE: {'FAE-1': {'state': state, 'site': 'S1'}}})
        events.on_notification(types.SimpleNamespace(document_type=rules.ATTENDANCE, document_name='FAE-1', for_user='pm@x'))
        events.on_notification(types.SimpleNamespace(document_type='ToDo', document_name='T1', for_user='pm@x'))
        site.commit()
        return site

    def test_attendance_alerts_only_when_it_waits_or_was_returned_with_the_site(self):
        self.assertEqual(self.notice('Submitted').pushes,
                         [(['pm@x'], 'approval', rules.ATTENDANCE, 'FAE-1', 'S1', 'Site A', {'needs': 'decide'})])
        self.assertEqual(self.notice('Pending Verification').pushes[0][1], 'verify')
        self.assertEqual(self.notice('Returned').pushes[0][1], 'returned')
        for quiet in ('Approved', 'Draft'):
            self.assertEqual(self.notice(quiet).records, {})

    def test_a_saved_document_that_left_its_state_closes_its_records(self):
        site = Site(phones={'pm@x'}, workflows={'Purchase Order': {'workflow_state_field': 'workflow_state'}})
        decide(site, ['pm@x'])
        service.notify(['pm@x'], rules.DECIDE, rules.ATTENDANCE, 'FAE-1', reason='verify', state='Pending Verification')
        site.commit()
        saved = lambda doctype, name, **fields: types.SimpleNamespace(doctype=doctype, name=name, get=fields.get)  # noqa: E731
        events.on_document_update(saved('Purchase Order', 'PO-1', workflow_state='Pending'))
        self.assertEqual(site.signals, [], 'saved in the same state: it still waits')
        events.on_document_update(saved('Purchase Order', 'PO-1', workflow_state='Approved'))
        events.on_document_update(saved(rules.ATTENDANCE, 'FAE-1', state='Verified'))
        self.assertEqual([s[1:4] for s in site.signals], [('remove', 'Purchase Order', 'PO-1'),
                                                          ('remove', rules.ATTENDANCE, 'FAE-1')])
        decide(site, ['pm@x'], 'PO-9')
        events.on_document_trash(saved('Purchase Order', 'PO-9'))
        self.assertTrue(all(r.resolved_at for r in site.records.values()))

    def test_other_saves_cost_no_query_and_nothing_runs_during_a_migrate(self):
        site = Site(workflows={'Purchase Order': {'workflow_state_field': 'workflow_state'}})
        saved = types.SimpleNamespace(doctype='ToDo', name='T1', get={}.get)
        events.on_document_update(saved)
        events.on_document_update(types.SimpleNamespace(doctype=RECORD, name='R1', get={}.get))
        fake.flags = Row(in_migrate=True)
        try:
            events.on_document_update(types.SimpleNamespace(doctype='Purchase Order', name='PO-1', get={}.get))
            events.on_document_trash(saved)
        finally:
            fake.flags = Row()
        self.assertEqual(site.queries, 0)


class Surface(unittest.TestCase):
    def test_the_record_list_is_read_only_for_system_managers(self):
        doc = json.loads((HERE / 'doctype/notification_record/notification_record.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['permissions'], [{'role': 'System Manager', 'read': 1, 'delete': 1, 'report': 1}])
        fields = {f['fieldname']: f for f in doc['fields']}
        self.assertEqual(set(fields), set(doc['field_order']))
        self.assertTrue(fields['open_key']['unique'], 'the database refuses a second open record')
        self.assertTrue(all(f.get('read_only') for f in fields.values()))
        self.assertFalse({'text', 'message', 'subject', 'content'} & set(fields), 'what was said is not kept')
        self.assertEqual(doc['module'], 'Notifications')
        self.assertIn('Notifications', (ROOT / 'erpnext_drive_integrations/modules.txt').read_text(encoding='utf-8').splitlines())

    def test_hooks_are_composed_and_the_phone_channel_has_no_triggers_of_its_own(self):
        base = 'erpnext_drive_integrations.notifications.'
        self.assertIn(base + 'events.on_workflow_action', hooks.doc_events['Workflow Action']['after_insert'])
        self.assertIn(base + 'events.on_notification', hooks.doc_events['Notification Log']['after_insert'])
        composed = json.dumps(hooks.doc_events)
        self.assertNotIn('mobile_push.events.on_workflow_action', composed, 'one trigger, or phones ring twice')
        self.assertNotIn('mobile_push.events.on_notification', composed)
        self.assertIn(base + 'events.on_user_update', hooks.doc_events['User']['on_update'])
        self.assertEqual(hooks.doc_events['*'], {'on_update': [base + 'events.on_document_update'],
                                                 'on_trash': [base + 'events.on_document_trash']})
        self.assertIn(base + 'service.remind', hooks.scheduler_events['hourly'])
        self.assertIn(base + 'service.purge', hooks.scheduler_events['daily'])

    def test_logs_and_the_removal_signal_carry_no_content(self):
        source = (HERE / 'service.py').read_text(encoding='utf-8')
        for line in (part.split('\n')[0] for part in source.split('frappe.log_error(')[1:]):
            self.assertNotIn('text', line)
            self.assertNotIn('user', line)
        self.assertIn('sender.send(phones, rules.REMOVE, doctype, name, include_actor=True)', source)


if __name__ == '__main__':
    unittest.main()
