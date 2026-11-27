"""custom-hr face attendance for field teams (P95): matching rules, consent, the engine slot and the stored records.

No live site and no face model: the rules are framework independent and run on plain vectors; the records are
checked from their definitions (templates readable by no role, no version history, permanent deletion).
"""
import ast
import json
import math
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HR = ROOT / 'erpnext_drive_integrations' / 'custom_hr'

_frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
if not hasattr(_frappe, 'conf'):
    _frappe.conf = {}
from erpnext_drive_integrations.custom_hr import face, face_engine  # noqa: E402
from erpnext_drive_integrations.custom_hr.domain import RuleError  # noqa: E402


def unit(*values):
    length = math.sqrt(sum(v * v for v in values))
    return [v / length for v in values]


def near(base, wobble):
    """A vector close to `base` (another angle of the same face)."""
    return unit(*[b + w for b, w in zip(base, wobble)])


ALICE = unit(1, 0, 0, 0)
BOB = unit(0, 1, 0, 0)
CAROL = unit(0, 0, 1, 0)
ALICE_TWIN = unit(0.97, 0.24, 0, 0)  # very close to ALICE


class Settings(unittest.TestCase):
    def test_defaults_and_overrides(self):
        self.assertEqual(face.settings()['match'], 0.363)
        self.assertEqual(face.settings({'match': 0.5, 'candidates': 2})['candidates'], 2)

    def test_refuses_unknown_and_out_of_bounds_values(self):
        for overrides in ({'unknown': 1}, {'match': 0.01}, {'match': 1.5}, {'margin': -1}, {'candidates': 9},
                          {'match': 0.3, 'floor': 0.4}, {'match': float('nan')}):
            with self.assertRaises(RuleError, msg=overrides):
                face.settings(overrides)


class Templates(unittest.TestCase):
    def test_normalise_refuses_bad_vectors(self):
        for bad in ([], [0, 0], ['x'], [float('inf'), 1], None):
            with self.assertRaises(RuleError):
                face.normalise(bad)
        with self.assertRaises(RuleError):
            face.normalise([1, 2, 3], dimension=4)
        self.assertAlmostEqual(sum(x * x for x in face.normalise([3, 4])), 1.0)

    def test_enrolment_needs_enough_angles_of_one_person(self):
        angles = [ALICE, near(ALICE, (0, .2, 0, 0)), near(ALICE, (0, 0, .2, 0))]
        self.assertEqual(len(face.validate_enrolment(angles)), 3)
        with self.assertRaises(RuleError):
            face.validate_enrolment(angles[:2])
        with self.assertRaises(RuleError):
            face.validate_enrolment([ALICE, BOB, CAROL])
        with self.assertRaises(RuleError):
            face.validate_enrolment([ALICE, ALICE, [1, 0, 0]])
        with self.assertRaises(RuleError):
            face.validate_enrolment([ALICE] * (face.MAXIMUM_ANGLES + 1))


class Identify(unittest.TestCase):
    roster = {'EMP-A': [ALICE], 'EMP-B': [BOB], 'EMP-C': [CAROL]}

    def test_confident_match(self):
        result = face.identify(near(ALICE, (0, .1, .1, 0)), self.roster)
        self.assertEqual(result['decision'], 'match')
        self.assertEqual(result['employee'], 'EMP-A')
        self.assertEqual(result['candidates'][0][0], 'EMP-A')

    def test_two_similar_workers_are_never_decided_automatically(self):
        roster = dict(self.roster, **{'EMP-T': [ALICE_TWIN]})
        result = face.identify(near(ALICE, (0, .12, 0, 0)), roster)
        self.assertEqual(result['decision'], 'uncertain')
        self.assertIsNone(result['employee'])
        self.assertEqual({c[0] for c in result['candidates'][:2]}, {'EMP-A', 'EMP-T'})

    def test_stranger_and_empty_roster(self):
        self.assertEqual(face.identify(unit(0, 0, 0, 1), self.roster)['decision'], 'none')
        self.assertEqual(face.identify(ALICE, {}), {'decision': 'none', 'employee': None, 'candidates': []})

    def test_candidates_are_limited_sorted_and_above_the_floor(self):
        rules = face.settings({'match': 0.95, 'floor': 0.2, 'candidates': 2})
        probe = unit(1, 0.9, 0.3, 0)
        result = face.identify(probe, self.roster, rules)
        self.assertEqual(result['decision'], 'uncertain')
        self.assertEqual([c[0] for c in result['candidates']], ['EMP-A', 'EMP-B'])
        self.assertTrue(all(score >= 0.2 for _, score in result['candidates']))

    def test_best_angle_counts(self):
        roster = {'EMP-A': [BOB, ALICE], 'EMP-C': [CAROL]}
        self.assertEqual(face.identify(ALICE, roster)['employee'], 'EMP-A')

    def test_templates_from_another_model_are_refused(self):
        with self.assertRaises(RuleError):
            face.identify([1, 0, 0], self.roster)


class Consent(unittest.TestCase):
    good = {'accepted': True, 'agreement_version': '2026-11', 'language': 'Telugu', 'identity_checked': True}

    def test_accepts_a_complete_record(self):
        self.assertEqual(face.validate_consent(self.good), {'agreement_version': '2026-11', 'language': 'Telugu'})

    def test_refuses_anything_less(self):
        for change in ({'accepted': False}, {'accepted': 'yes'}, {'agreement_version': ''}, {'language': ' '},
                       {'identity_checked': False}, {'agreement_version': 'x' * 41}):
            with self.assertRaises(RuleError, msg=change):
                face.validate_consent(dict(self.good, **change))
        with self.assertRaises(RuleError):
            face.validate_consent(None)


class EngineSlot(unittest.TestCase):
    def test_off_until_a_model_is_adopted(self):
        with self.assertRaises(face_engine.EngineMissing) as raised:
            face_engine.load({})
        self.assertIn('licence', str(raised.exception))

    def test_only_this_apps_code_and_complete_engines(self):
        for path in ('os.system', 'erpnext_drive_integrations.custom_hr.face.missing',
                     'erpnext_drive_integrations.custom_hr.face.settings'):
            with self.assertRaises(face_engine.EngineMissing, msg=path):
                face_engine.load({'engine': path})


def doctype(folder):
    return json.loads((HR / 'doctype' / folder / f'{folder}.json').read_text(encoding='utf-8'))


class Records(unittest.TestCase):
    def test_templates_are_readable_by_no_role_and_keep_no_history(self):
        enrolment = doctype('field_face_enrolment')
        field = next(f for f in enrolment['fields'] if f['fieldname'] == 'templates')
        self.assertEqual(field['permlevel'], 1)
        self.assertTrue(field['hidden'] and field['read_only'] and field['report_hide'] and field['print_hide'])
        self.assertFalse(any(p.get('permlevel') for p in enrolment['permissions']), 'no role may read level 1')
        self.assertFalse(enrolment['track_changes'], 'versions would copy the templates')
        for record in (enrolment, doctype('biometric_consent')):
            self.assertFalse(any(p.get(k) for p in record['permissions'] for k in ('write', 'create', 'delete')))
            self.assertEqual(record['module'], 'Custom HR')

    def test_records_are_written_only_through_the_service(self):
        for folder in ('field_face_enrolment', 'biometric_consent'):
            source = (HR / 'doctype' / folder / f'{folder}.py').read_text(encoding='utf-8')
            self.assertIn('ControlledDocument', source)

    def test_templates_are_deleted_permanently_and_photos_not_saved(self):
        source = (HR / 'face_service.py').read_text(encoding='utf-8')
        self.assertIn('delete_permanently=True', source)
        self.assertIn('encrypt(json.dumps(templates))', source)
        self.assertNotIn('save_file', source)

    def test_leavers_and_deleted_employees_lose_their_templates(self):
        from erpnext_drive_integrations.custom_hr import hooks
        events = hooks.doc_events['Employee']
        self.assertIn('erpnext_drive_integrations.custom_hr.face_service.on_employee_update', events['on_update'])
        self.assertEqual(events['on_trash'], 'erpnext_drive_integrations.custom_hr.face_service.on_employee_trash')

    def test_face_functions_are_post_only(self):
        tree = ast.parse((HR / 'api.py').read_text(encoding='utf-8'))
        found = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in ('face_enrol', 'face_identify', 'face_withdraw'):
                found[node.name] = ast.unparse(node.decorator_list[0])
        self.assertEqual(set(found), {'face_enrol', 'face_identify', 'face_withdraw'})
        for name, decorator in found.items():
            self.assertIn("methods=['POST']", decorator, name)


if __name__ == '__main__':
    unittest.main()
