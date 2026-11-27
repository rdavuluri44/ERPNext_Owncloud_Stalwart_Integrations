"""custom-hr face attendance switch (P95; owner, 27 November 2026).

Face attendance runs only where the site config says `custom_hr_face` -> `enabled: true`. Everything that takes in or
uses a face refuses before it reads or stores anything; withdrawing consent and deleting face data never depend on
the switch. No live site: the switch itself runs against the real module with a minimal stand-in for Frappe, and
the order of the checks is read from the source. The live part (nothing stored while off) is
`custom_hr/face_queue_integration_tests.py`, run on the test site.
"""
import ast
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HR = ROOT / 'erpnext_drive_integrations' / 'custom_hr'


class Refused(Exception):
    pass


def _stand_in_frappe():
    frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
    if not hasattr(frappe, 'conf'):
        frappe.conf = {}
    for name, value in (('_', lambda text: text), ('PermissionError', Refused), ('ValidationError', Exception)):
        if not hasattr(frappe, name):
            setattr(frappe, name, value)
    utils = sys.modules.setdefault('frappe.utils', types.ModuleType('frappe.utils'))
    if not hasattr(utils, 'now_datetime'):
        utils.now_datetime = lambda: None
    password = sys.modules.setdefault('frappe.utils.password', types.ModuleType('frappe.utils.password'))
    for name in ('encrypt', 'decrypt'):
        if not hasattr(password, name):
            setattr(password, name, lambda value: value)
    return frappe


FRAPPE = _stand_in_frappe()
from erpnext_drive_integrations.custom_hr import face_service  # noqa: E402

SOURCES = {name: (HR / f'{name}.py').read_text(encoding='utf-8') for name in ('face_service', 'face_queue', 'api')}


def body(module, name):
    tree = ast.parse(SOURCES[module])
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    statements = node.body
    if statements and isinstance(statements[0], ast.Expr) and isinstance(getattr(statements[0], 'value', None), ast.Constant):
        statements = statements[1:]
    return node, statements


def calls_require_enabled(statement):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return False
    func = statement.value.func
    return (isinstance(func, ast.Name) and func.id == 'require_enabled') or (
        isinstance(func, ast.Attribute) and func.attr == 'require_enabled')


GATED = [('face_service', 'enrol'), ('face_service', 'identify'), ('face_queue', 'add'), ('face_queue', 'pending'),
         ('face_queue', 'mine'), ('face_queue', '_decide')]
ALWAYS = [('face_service', 'withdraw'), ('face_service', 'delete_templates'), ('face_service', 'end_consent'),
          ('face_service', 'on_employee_update'), ('face_service', 'on_employee_trash'), ('face_queue', 'purge_rejected'),
          ('face_queue', '_drop_photo')]


class Switch(unittest.TestCase):
    def setUp(self):
        self.saved_conf, self.saved_throw = dict(FRAPPE.conf), getattr(FRAPPE, 'throw', None)

        def throw(message, exc=Exception):
            raise exc(message)
        FRAPPE.throw = throw

    def tearDown(self):
        FRAPPE.conf.clear()
        FRAPPE.conf.update(self.saved_conf)
        if self.saved_throw is None:
            del FRAPPE.throw
        else:
            FRAPPE.throw = self.saved_throw

    def test_off_unless_the_site_config_says_exactly_true(self):
        for value in (None, {}, {'engine': 'some.Engine'}, {'enabled': 'true'}, {'enabled': 1}, {'enabled': False}):
            FRAPPE.conf.clear()
            if value is not None:
                FRAPPE.conf['custom_hr_face'] = value
            self.assertFalse(face_service.enabled(), value)
        FRAPPE.conf['custom_hr_face'] = {'enabled': True}
        self.assertTrue(face_service.enabled())

    def test_refusal_is_a_permission_error_with_a_plain_message(self):
        FRAPPE.conf.clear()
        with self.assertRaises(Refused) as refused:
            face_service.require_enabled()
        self.assertEqual(str(refused.exception), 'Face attendance is switched off on this site.')
        FRAPPE.conf['custom_hr_face'] = {'enabled': True}
        face_service.require_enabled()


class WhereItApplies(unittest.TestCase):
    def test_every_face_intake_checks_the_switch_before_anything_else(self):
        for module, name in GATED:
            _, statements = body(module, name)
            self.assertTrue(statements and calls_require_enabled(statements[0]), f'{module}.{name}')

    def test_withdrawal_and_deletion_never_depend_on_the_switch(self):
        for module, name in ALWAYS:
            node, _ = body(module, name)
            self.assertNotIn('enabled', ast.get_source_segment(SOURCES[module], node), f'{module}.{name}')

    def test_every_face_endpoint_reaches_a_gated_function_except_withdrawal(self):
        targets = {'face_enrol': 'enrol', 'face_identify': 'identify', 'face_capture': 'add',
                   'face_queue_pending': 'pending', 'face_queue_mine': 'mine', 'face_queue_resolve': 'resolve',
                   'face_queue_reject': 'reject'}
        tree = ast.parse(SOURCES['api'])
        endpoints = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('face_')}
        self.assertEqual(endpoints, set(targets) | {'face_withdraw'}, 'a new face endpoint needs a decision here')
        for endpoint, target in targets.items():
            node, _ = body('api', endpoint)
            self.assertIn(f'.{target}(', ast.get_source_segment(SOURCES['api'], node), endpoint)
        for name in ('resolve', 'reject'):
            node, _ = body('face_queue', name)
            self.assertIn('_decide(', ast.get_source_segment(SOURCES['face_queue'], node), name)


if __name__ == '__main__':
    unittest.main()
