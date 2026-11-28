"""Request IDs on the app's saves, and decisions made on the revision the person saw (P103).

The request log runs for real against a small fake frappe: these checks fail if a save sent twice with one ID
could be carried out twice, if an ID could show one person what another did, or if a refused save could use its ID
up. The rules inside the attendance service are read from the source, as the other custom-hr tests do; they run
for real in `custom_hr/integration_tests.py` on the test site.
"""
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HR = ROOT / 'erpnext_drive_integrations' / 'custom_hr'


class Row(dict):
    __getattr__ = dict.get


class Refused(Exception):
    pass


class Duplicate(Exception):
    pass


frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
if not hasattr(frappe, 'conf'):
    frappe.conf = {}
from erpnext_drive_integrations.custom_hr import request_log  # noqa: E402

RID = 'r' * 20
OTHER = 's' * 20


class Site:
    """Just enough frappe for the log: its table with a unique request ID, attendance entries, and who is signed in."""

    def __init__(self, user='pm@x'):
        self.log, self.entries, self.notices, self.cleared = {}, {}, {}, 0
        frappe.session = types.SimpleNamespace(user=user)
        frappe.UniqueValidationError = Duplicate
        frappe.throw = self.throw
        frappe.clear_messages = self.clear
        frappe.get_doc = self.get_doc
        frappe.db = types.SimpleNamespace(get_value=self.get_value, set_value=self.set_value, count=self.count)
        self.racing = None

    def throw(self, message, exc=None):
        raise Refused(message)

    def clear(self):
        self.cleared += 1

    def get_doc(self, values):
        site = self

        class Doc:
            flags = types.SimpleNamespace()

            def insert(self, ignore_permissions=False):
                assert self.flags.field_service is True, 'only the service writes the log'
                if site.racing:  # another call with the same ID committed while this one was on its way
                    site.log['R0'] = Row(site.racing, name='R0')
                    site.racing = None
                if any(r.request_id == values['request_id'] for r in site.log.values()):
                    raise Duplicate()
                self.name = f'R{len(site.log) + 1}'
                site.log[self.name] = Row(values, name=self.name, outcome=None, creation='2026-11-28 10:00:00')
                return self
        return Doc()

    def get_value(self, doctype, filters, fields, as_dict=False):
        if doctype == request_log.LOG:
            rows = [r for r in self.log.values() if all(r.get(k) == v for k, v in filters.items())]
            return rows[0] if rows else None
        if isinstance(filters, dict):
            rows = [e for e in self.entries.values() if all(e.get(k) == v for k, v in filters.items())]
            return rows[0] if rows else None
        entry = self.entries.get(filters)
        return entry and entry.get(fields)

    def set_value(self, doctype, name, values, update_modified=True):
        self.log[name].update(values)

    def count(self, doctype, filters):
        return self.notices.get(filters['document_name'], 0)


class Once(unittest.TestCase):
    def test_a_save_sent_twice_is_carried_out_once_and_answers_the_same(self):
        site, done = Site(), []
        action = lambda: done.append(1) or {'name': 'FAE-1', 'state': 'Approved'}  # noqa: E731
        first = request_log.once('review', RID, action, 'FAE-1')
        self.assertEqual(first, {'name': 'FAE-1', 'state': 'Approved', 'request_id': RID})
        again = request_log.once('review', RID, action, 'FAE-1')
        self.assertEqual(again, {'name': 'FAE-1', 'state': 'Approved', 'request_id': RID, 'repeated': True})
        self.assertEqual(len(done), 1, 'the second call changes nothing')
        row = list(site.log.values())[0]
        self.assertEqual((row.user, row.method, row.reference_doctype, row.reference_name),
                         ('pm@x', 'review', 'Field Attendance Entry', 'FAE-1'))

    def test_a_list_answer_is_wrapped_so_the_id_has_a_place(self):
        Site()
        results = [{'name': 'FAE-1', 'ok': True}, {'name': 'FAE-2', 'ok': False, 'code': 'changed'}]
        self.assertEqual(request_log.once('review_many', RID, lambda: results),
                         {'results': results, 'request_id': RID})
        self.assertEqual(request_log.once('review_many', RID, lambda: self.fail('carried out twice')),
                         {'results': results, 'request_id': RID, 'repeated': True})

    def test_without_an_id_the_call_runs_as_before(self):
        site = Site()
        for none in (None, ''):
            self.assertEqual(request_log.once('submit', none, lambda: {'name': 'FAE-1'}), {'name': 'FAE-1'})
        self.assertEqual(site.log, {}, 'nothing is written down, and the answer is unchanged')

    def test_something_that_is_not_an_id_is_refused_before_anything_runs(self):
        Site()
        for bad in ('short', 'x' * 81, 'has space ' * 3, 'semi;colon' * 3, 12345678901234567890, ['r' * 20]):
            with self.assertRaises(Refused, msg=repr(bad)[:30]):
                request_log.once('submit', bad, lambda: self.fail('ran'))

    def test_an_id_belongs_to_the_person_and_the_call_that_used_it_first(self):
        Site()
        request_log.once('review', RID, lambda: {'name': 'FAE-1', 'state': 'Approved'})
        with self.assertRaises(Refused):
            request_log.once('verify', RID, lambda: self.fail('another call under the same ID'))
        frappe.session.user = 'other@x'
        with self.assertRaises(Refused) as refused:
            request_log.once('review', RID, lambda: self.fail('someone else under the same ID'))
        self.assertEqual(str(refused.exception), request_log.USED)
        self.assertNotIn('FAE-1', str(refused.exception), 'the refusal says nothing about what the ID did')

    def test_a_refused_save_does_not_use_its_id_up(self):
        source = (HR / 'request_log.py').read_text(encoding='utf-8')
        body = source.split('def once(')[1].split('\ndef ')[0]
        self.assertLess(body.index('row.insert('), body.index('result = action()'),
                        'the ID is written first, in the same transaction: a refusal rolls it back with the rest')
        self.assertNotIn('commit', body)
        self.assertNotIn('except Exception', body)

    def test_two_calls_at_the_same_moment_the_later_one_gets_the_first_answer(self):
        site = Site()
        site.racing = dict(request_id=RID, user='pm@x', method='review', creation='2026-11-28 10:00:00',
                           outcome=json.dumps({'name': 'FAE-1', 'state': 'Approved'}))
        answer = request_log.once('review', RID, lambda: self.fail('carried out twice'))
        self.assertEqual(answer, {'name': 'FAE-1', 'state': 'Approved', 'request_id': RID, 'repeated': True})
        self.assertEqual(site.cleared, 1, "the database's own duplicate message is not shown to the person")


class Status(unittest.TestCase):
    def test_my_own_id_answers_the_call_the_record_and_the_notices(self):
        site = Site(user='sup@x')
        site.entries['FAE-1'] = Row(name='FAE-1', request_id=OTHER, captured_by='sup@x', state='Returned', revision=3,
                                    creation='2026-11-28 09:00:00')
        site.notices['FAE-1'] = 2
        request_log.once('submit', RID, lambda: {'name': 'FAE-1', 'state': 'Submitted'}, 'FAE-1')
        self.assertEqual(request_log.status(RID), {'request_id': RID, 'found': [
            {'what': 'call', 'method': 'submit', 'at': '2026-11-28 10:00:00', 'entry': 'FAE-1',
             'answer': {'name': 'FAE-1', 'state': 'Submitted'}, 'state_now': 'Returned'}]})
        self.assertEqual(request_log.status(OTHER), {'request_id': OTHER, 'found': [
            {'what': 'record', 'entry': 'FAE-1', 'at': '2026-11-28 09:00:00', 'state_now': 'Returned', 'revision': 3,
             'notices': 2}]})

    def test_someone_else_s_id_and_an_unknown_id_look_the_same(self):
        site = Site(user='sup@x')
        site.entries['FAE-1'] = Row(name='FAE-1', request_id=OTHER, captured_by='sup@x', state='Draft', revision=1)
        request_log.once('submit', RID, lambda: {'name': 'FAE-1', 'state': 'Submitted'}, 'FAE-1')
        frappe.session.user = 'curious@x'
        for request_id in (RID, OTHER, 'u' * 20):
            self.assertEqual(request_log.status(request_id), {'request_id': request_id, 'found': []})
        for bad in (None, '', 'short'):
            with self.assertRaises(Refused):
                request_log.status(bad)


class Surface(unittest.TestCase):
    API = (HR / 'api.py').read_text(encoding='utf-8')
    SERVICE = (HR / 'service.py').read_text(encoding='utf-8')

    def body(self, source, name):
        return source.split(f'def {name}(')[1].split('\ndef ')[0]

    def test_every_save_that_only_changes_a_record_goes_through_the_log(self):
        for name in ('verify', 'submit', 'review', 'review_many', 'self_check_out'):
            self.assertRegex(self.API, r"@frappe\.whitelist\(methods=\['POST'\]\)\s*def " + name + r'\(', name)
            self.assertIn(f"request_log.once('{name}', ", self.body(self.API, name), name)
        for name in ('save_capture', 'self_check_in'):
            self.assertIn('with_id(', self.body(self.API, name), 'the calls that make an entry answer with its ID too')
        self.assertRegex(self.API, r"@frappe\.whitelist\(methods=\['GET'\]\)\s*def request_status\(request_id\)")
        self.assertNotIn('user', self.body(self.API, 'request_status').replace('require_user()', ''),
                         'nobody asks about someone else')

    def test_a_decision_is_made_on_the_revision_the_person_saw(self):
        check = self.body(self.SERVICE, 'check_revision')
        self.assertIn('cint(revision) != doc.revision', check)
        self.assertIn('frappe.TimestampMismatchError', check)
        self.assertIn("if revision is None or revision == '':\n        return", check, 'older apps send none')
        for name, allowed in (('review_entry', 'A different approver must review'), ('verify_entry', 'Only the assigned engineer')):
            body = self.body(self.SERVICE, name)
            self.assertIn('check_revision(doc, revision)', body, name)
            self.assertLess(body.index(allowed), body.index('check_revision(doc, revision)'),
                            'who may decide comes first: a person who may not gets "not allowed", not the state')
            first_answer = body.index('return {')
            self.assertLess(body.index('check_revision(doc, revision)'), first_answer,
                            'also before "already decided": someone else may have decided it')
            self.assertLess(body.index('lock_'), body.index('check_revision(doc, revision)'), 'on the locked record')

    def test_the_lists_give_the_revision_to_send_back(self):
        self.assertIn("'verification_method', 'revision',", self.body(self.API, 'approvals'))
        self.assertIn("'captured_by', 'revision']", self.body(self.API, 'verifications'))

    def test_several_entries_each_say_what_happened_in_a_code(self):
        many = self.body(self.SERVICE, 'review_many')
        self.assertIn("ok=True,code='done'", many)
        self.assertIn('**refusal(name,exc)', many)
        self.assertIn("frappe.db.rollback(save_point='review_many')", many, 'one refusal does not undo the others')
        refusal = self.body(self.SERVICE, 'refusal')
        for code in ("'not_allowed'", "'refused'", "'changed'"):
            self.assertIn(code, refusal)
        self.assertLess(refusal.index('frappe.PermissionError'), refusal.index("frappe.db.get_value"),
                        'a person who may not decide is told nothing about the record')

    def test_the_log_is_read_only_kept_ninety_days_and_holds_no_text_of_its_own(self):
        doc = json.loads((HR / 'doctype/app_request/app_request.json').read_text(encoding='utf-8'))
        self.assertEqual([(p['role'], p['write'], p['create'], p['delete']) for p in doc['permissions']],
                         [('System Manager', 0, 0, 0)])
        fields = {f['fieldname']: f for f in doc['fields']}
        self.assertEqual(fields['request_id'].get('unique'), 1, 'the database itself refuses a second one')
        self.assertTrue(all(f.get('read_only') for f in fields.values()))
        self.assertEqual(doc['module'], 'Custom HR')
        self.assertIn('ControlledDocument', (HR / 'doctype/app_request/app_request.py').read_text(encoding='utf-8'))
        self.assertEqual(request_log.KEEP_DAYS, 90)
        hooks = (HR / 'hooks.py').read_text(encoding='utf-8')
        self.assertIn('erpnext_drive_integrations.custom_hr.request_log.purge', hooks.split('"daily"')[1])


if __name__ == '__main__':
    unittest.main()
