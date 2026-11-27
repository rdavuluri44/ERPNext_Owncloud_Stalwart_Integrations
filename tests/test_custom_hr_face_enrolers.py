"""custom-hr: who may enrol or remove a worker's face (P95; owner, 27 November 2026).

HR, a Field Attendance Manager and the project manager (approver) of the worker's site, as before; and now also the
worker's own team: their responsible supervisor, or the engineer assigned to that supervisor at that site. Another
team's supervisor or engineer, and anyone at another site, is refused. The rule runs against the real module with a
minimal stand-in for Frappe; the live part is `custom_hr/face_queue_integration_tests.py`, run on the test site.
"""
import sys
import types
import unittest


class Refused(Exception):
    pass


def _stand_in_frappe():
    frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
    if not hasattr(frappe, 'conf'):
        frappe.conf = {}
    for name, value in (('_', lambda text: text), ('ValidationError', Exception)):
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

# One site, two teams. Supervisor `sup` leads `worker`; `other-sup` leads another team; engineer `eng` is assigned to
# `sup`, engineer `other-eng` to `other-sup`. `pm` approves the site; `elsewhere` approves another site.
MEMBERS = {
    ('site-1', 'Approver'): {'pm'},
    ('site-1', 'Supervisor'): {'sup', 'other-sup'},
    ('site-2', 'Approver'): {'elsewhere'},
}
ENGINEERS = {('site-1', 'eng'): ['sup'], ('site-1', 'other-eng'): ['other-sup']}
ROLES = {'hr': {'HR User'}, 'hr-manager': {'HR Manager'}}
ASSIGNMENT = {'worker': ('site-1', 'sup'), 'unassigned': (None, None)}


class WhoMayEnrol(unittest.TestCase):
    def setUp(self):
        self.saved = {name: getattr(face_service, name) for name in
                      ('is_manager', 'site_access', 'supervised_users', 'worker_site', 'worker_supervisor')}
        self.saved_frappe = {name: getattr(FRAPPE, name, None) for name in ('throw', 'get_roles', 'PermissionError')}
        FRAPPE.PermissionError = Refused  # only while these tests run, so other suites keep their own stand-in
        face_service.is_manager = lambda user: user == 'manager'
        face_service.site_access = lambda site, role, user: user in MEMBERS.get((site, role), set())
        face_service.supervised_users = lambda site, user: ENGINEERS.get((site, user), [])
        face_service.worker_site = lambda employee: ASSIGNMENT[employee][0]
        face_service.worker_supervisor = lambda employee: ASSIGNMENT[employee][1]

        def throw(message, exc=Exception):
            raise exc(message)
        FRAPPE.throw = throw
        FRAPPE.get_roles = lambda user: ROLES.get(user, set())

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(face_service, name, value)
        for name, value in self.saved_frappe.items():
            if value is None:
                delattr(FRAPPE, name)
            else:
                setattr(FRAPPE, name, value)

    def allowed(self, user, employee='worker'):
        try:
            face_service.require_enroller(employee, user)
        except Refused:
            return False
        return True

    def test_hr_the_manager_and_the_sites_project_manager_as_before(self):
        for user in ('hr', 'hr-manager', 'manager', 'pm'):
            self.assertTrue(self.allowed(user), user)

    def test_the_workers_own_supervisor_and_their_engineer(self):
        self.assertTrue(self.allowed('sup'))
        self.assertTrue(self.allowed('eng'))

    def test_another_teams_supervisor_or_engineer_is_refused(self):
        self.assertFalse(self.allowed('other-sup'))
        self.assertFalse(self.allowed('other-eng'))

    def test_another_sites_project_manager_and_strangers_are_refused(self):
        self.assertFalse(self.allowed('elsewhere'))
        self.assertFalse(self.allowed('nobody'))

    def test_a_worker_without_a_site_only_hr_or_the_manager(self):
        for user in ('pm', 'sup', 'eng'):
            self.assertFalse(self.allowed(user, 'unassigned'), user)
        self.assertTrue(self.allowed('hr', 'unassigned'))
        self.assertTrue(self.allowed('manager', 'unassigned'))

    def test_the_refusal_names_who_may(self):
        with self.assertRaises(Refused) as refused:
            face_service.require_enroller('worker', 'other-sup')
        self.assertIn('own supervisor or engineer', str(refused.exception))

    def test_withdrawal_uses_the_same_rule(self):
        import inspect
        self.assertIn('require_enroller(employee, user)', inspect.getsource(face_service.withdraw))


if __name__ == '__main__':
    unittest.main()
