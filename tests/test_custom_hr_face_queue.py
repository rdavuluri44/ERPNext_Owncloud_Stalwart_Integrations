"""custom-hr face capture queue (P95): what the queue may do in whose name, who may decide a capture, how its
photographs are kept, and that the web page reaches it. No live site: the definitions and the source are checked,
and the framework-independent notes are run."""
import ast
import json
import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'erpnext_drive_integrations'
HR = APP / 'custom_hr'

_frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
if not hasattr(_frappe, 'conf'):
    _frappe.conf = {}
from erpnext_drive_integrations.custom_hr import face_queue_rules as rules  # noqa: E402

QUEUE = (HR / 'face_queue.py').read_text(encoding='utf-8')
SERVICE = (HR / 'service.py').read_text(encoding='utf-8')
API = (HR / 'api.py').read_text(encoding='utf-8')


def function(source, name):
    tree = ast.parse(source)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)


class Notes(unittest.TestCase):
    def test_roster_note_tells_the_project_manager_why_nobody_matched(self):
        self.assertEqual(rules.roster_note(0, 0, 0), 'No workers are rostered to this supervisor for the shift.')
        self.assertEqual(rules.roster_note(8, 0, 0), '')
        self.assertEqual(rules.roster_note(8, 3, 0), '3 of 8 rostered workers have no face enrolled.')
        self.assertIn('enrol again', rules.roster_note(8, 3, 2))

    def test_notes_are_joined_and_bounded(self):
        self.assertEqual(rules.join_notes('a ', '', None, 'b'), 'a b')
        self.assertEqual(len(rules.join_notes('x' * 2000)), 1000)


class ActingForTheSupervisor(unittest.TestCase):
    def test_only_the_queue_can_name_an_actor_and_never_from_a_request(self):
        for name in ('capture', 'submit_entry'):
            self.assertIn('actor=None', function(SERVICE, name).split(':')[0] + ':')
        # No whitelisted function passes an actor or evidence on: both come only from a stored queue record.
        self.assertNotIn('actor', API)
        self.assertNotIn('evidence', API)
        record = function(QUEUE, '_record')
        self.assertIn('actor=doc.captured_by', record)
        self.assertEqual(record.count('actor='), 2, 'capture and submit, both in the capturing supervisor\'s name')
        others = [p for p in HR.glob('*.py') if p.name not in ('face_queue.py', 'service.py')]
        for path in others:
            self.assertNotRegex(path.read_text(encoding='utf-8'), r'\b(capture|submit_entry)\([^)]*actor=', path.name)

    def test_place_and_time_are_validated_once_when_the_capture_arrives(self):
        add = function(QUEUE, 'add')
        for check in ('domain.validate_location', 'service.moment(payload, with_gps=True)', 'service.decode_photo',
                      'service.shift_details'):
            self.assertIn(check, add)
        capture = function(SERVICE, 'capture')
        self.assertIn("evidence['captured_at'] if evidence else moment(data)", capture)
        self.assertIn("photo=evidence['photo'] if evidence else", capture)

    def test_a_recognised_worker_still_passes_every_capture_rule(self):
        record = function(QUEUE, '_record')
        self.assertIn('service.capture(', record)
        self.assertIn('service.submit_entry(', record)
        add = function(QUEUE, 'add')
        self.assertIn("frappe.db.savepoint('face_queue_record')", add)
        self.assertIn("rollback(save_point='face_queue_record')", add, 'a refused capture waits for a person')


class WhoDecides(unittest.TestCase):
    def test_only_another_approver_of_the_site_decides(self):
        decide = function(QUEUE, '_decide')
        self.assertIn("require_site(doc.site, 'Approver')", decide)
        self.assertIn('doc.captured_by == user', decide)
        self.assertIn("doc.state != 'Needs review'", decide)
        self.assertIn('FOR UPDATE', function(QUEUE, '_lock'))
        for name in ('resolve', 'reject'):
            self.assertIn('_decide(name, user)', function(QUEUE, name))
        self.assertIn("get_value('Employee', employee, 'user_id') == user", function(QUEUE, 'resolve'))
        self.assertIn('Say why', function(QUEUE, 'reject'))

    def test_reads_are_limited_to_approvers_and_the_capturing_supervisor(self):
        self.assertIn("require_site(site, 'Approver')", function(QUEUE, 'pending'))
        self.assertIn("'captured_by': user", function(QUEUE, 'mine'))
        permissions = (HR / 'permissions.py').read_text(encoding='utf-8')
        access = function(permissions, 'face_capture_access')
        self.assertIn('doc.captured_by==user', access)
        self.assertIn("site_ids(user,'Approver')", access)
        from erpnext_drive_integrations.custom_hr import hooks
        self.assertIn('Field Face Capture', hooks.permission_query_conditions)
        self.assertIn('Field Face Capture', hooks.has_permission)

    def test_functions_exist_and_writes_are_post_only(self):
        by_name = {name: args for args, name in
                   re.findall(r'@frappe\.whitelist\(([^\n]*)\)\ndef (face_capture|face_queue_\w+)\(', API)}
        self.assertEqual(set(by_name), {'face_capture', 'face_queue_pending', 'face_queue_mine', 'face_queue_resolve',
                                        'face_queue_reject'})
        for name in ('face_capture', 'face_queue_resolve', 'face_queue_reject'):
            self.assertIn("methods=['POST']", by_name[name], name)


class Photographs(unittest.TestCase):
    def test_record_is_written_only_by_the_service(self):
        folder = HR / 'doctype' / 'field_face_capture'
        definition = json.loads((folder / 'field_face_capture.json').read_text(encoding='utf-8'))
        self.assertEqual(definition['module'], 'Custom HR')
        self.assertFalse(any(p.get(k) for p in definition['permissions'] for k in ('write', 'create', 'delete')))
        self.assertIn('ControlledDocument', (folder / 'field_face_capture.py').read_text(encoding='utf-8'))
        states = next(f for f in definition['fields'] if f['fieldname'] == 'state')['options'].split('\n')
        self.assertEqual(tuple(states), rules.STATES)
        self.assertTrue(next(f for f in definition['fields'] if f['fieldname'] == 'capture_id')['unique'])

    def test_every_record_of_the_queued_photograph_is_removed(self):
        # Frappe keeps two File records per photo field (found in the first live run): delete all of them.
        drop = function(QUEUE, '_drop_photo')
        self.assertIn('for name in _photo_names(doc):', drop)
        self.assertIn("pluck='name'", function(QUEUE, '_photo_names'))

    def test_photograph_is_private_and_removed_once_recorded(self):
        self.assertIn('is_private=1', function(QUEUE, 'add'))
        for name in ('add', 'resolve', 'purge_rejected'):
            self.assertIn('_drop_photo(doc)', function(QUEUE, name), name)
        self.assertNotIn('_drop_photo', function(QUEUE, 'reject'), 'a rejected capture keeps its evidence for a while')
        self.assertEqual(rules.RETENTION_DAYS, 30)
        from erpnext_drive_integrations.custom_hr import hooks
        self.assertIn('erpnext_drive_integrations.custom_hr.face_queue.purge_rejected', hooks.scheduler_events['daily'])

    def test_files_of_the_queue_are_guarded_and_attendance_evidence_stays_undeletable(self):
        guard = function((HR / 'guards.py').read_text(encoding='utf-8'), 'protect_file')
        self.assertIn("'Field Face Capture'", guard)
        queued = guard.split('if queued and not protected:')[1].split('if not protected:return')[0]
        self.assertIn('if doc.flags.field_service:return', queued)
        rest = guard.split('if not protected:return')[1]
        self.assertNotIn('field_service', rest, 'no service flag opens attendance evidence')


class WebPage(unittest.TestCase):
    def test_approvers_get_the_queue_screen(self):
        script = (APP / 'public/custom_hr/field.js').read_text(encoding='utf-8')
        for part in ('data-view="facequeue"', "api('face_queue_pending'", "api('face_queue_resolve'",
                     "api('face_queue_reject'", 'async function faceQueue()'):
            self.assertIn(part, script)
        page = (APP / 'www/field_team.html').read_text(encoding='utf-8')
        self.assertIn('field.js?v=017', page, 'a changed script needs a new version in the page')


if __name__ == '__main__':
    unittest.main()
