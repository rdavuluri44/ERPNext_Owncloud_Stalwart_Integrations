"""custom-hr: the HR part of the one app, renamed from the field-attendance part (22 November 2026).

These checks fail if the rename left a dangling reference, if the module gained a desk app icon, or if the
rename patch could damage a site. No live site: a small fake frappe.
"""
import ast
import importlib.util
import json
import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'erpnext_drive_integrations'
HR = APP / 'custom_hr'

fake = types.ModuleType('frappe')
fake.conf = {}
sys.modules.setdefault('frappe', fake)
from erpnext_drive_integrations import hooks  # noqa: E402


def defined(dotted):
    """Does `erpnext_drive_integrations.custom_hr.x.y` name a function or class that exists in the source?"""
    module, _, name = dotted.rpartition('.')
    path = ROOT / (module.replace('.', '/') + '.py')
    if not path.is_file():
        return False
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name for n in tree.body)


class NoDeskIcon(unittest.TestCase):
    def test_hr_adds_no_app_icon_and_no_workspace(self):
        fragment = (HR / 'hooks.py').read_text(encoding='utf-8')
        self.assertNotIn('add_to_apps_screen', fragment)
        self.assertEqual([a['name'] for a in getattr(hooks, 'add_to_apps_screen', [])], ['onboarding'],
                         'the app keeps exactly the one existing desk icon')
        self.assertFalse((HR / 'workspace').exists(), 'a workspace would create a desk icon')


class Rename(unittest.TestCase):
    def test_feature_switch_keeps_the_former_key(self):
        enabled = hooks._feature_enabled
        self.assertTrue(enabled('custom_hr', {}))
        self.assertFalse(enabled('custom_hr', {'field': False}))
        self.assertFalse(enabled('custom_hr', {'custom_hr': False}))
        self.assertTrue(enabled('custom_hr', {'custom_hr': True, 'field': False}))
        self.assertTrue(enabled('portal', {'field': False}))

    def test_doctypes_and_page_belong_to_the_custom_hr_module(self):
        files = list(HR.glob('doctype/*/*.json')) + list(HR.glob('page/*/*.json'))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')).get('module'), 'Custom HR', path.name)
        modules = (APP / 'modules.txt').read_text(encoding='utf-8').split('\n')
        self.assertIn('Custom HR', modules)
        self.assertNotIn('Cloud Field', modules)
        leftovers = [p for d in ('field', 'cloud_field') for p in (APP / d).rglob('*') if p.suffix in ('.py', '.json', '.js')]
        self.assertEqual(leftovers, [], 'source left in the former folders')

    def test_every_hook_points_at_existing_code(self):
        values = []
        for name in dir(hooks):
            value = getattr(hooks, name)
            if isinstance(value, (str, list, dict)) and not name.startswith('_'):
                values.append(json.dumps(value, default=str))
        paths = set(re.findall(r'erpnext_drive_integrations\.custom_hr\.[A-Za-z0-9_.]+', ' '.join(values)))
        self.assertGreaterEqual(len(paths), 15)
        for path in sorted(paths):
            self.assertTrue(defined(path), path + ' does not exist')

    def test_web_page_calls_whitelisted_functions_at_the_new_address(self):
        script = (APP / 'public/custom_hr/field.js').read_text(encoding='utf-8')
        self.assertIn("'/api/method/erpnext_drive_integrations.custom_hr.api.'", script)
        api = (HR / 'api.py').read_text(encoding='utf-8')
        whitelisted = set(re.findall(r'@frappe\.whitelist[^\n]*\n\s*def (\w+)\(', api))
        called = set(re.findall(r"\bapi\(\s*'(\w+)'", script)) | set(re.findall(r'\bapi\(\s*"(\w+)"', script))
        self.assertGreaterEqual(len(called), 5)
        self.assertEqual(called - whitelisted, set())
        page = (APP / 'www/field_team.html').read_text(encoding='utf-8')
        self.assertIn('/assets/erpnext_drive_integrations/custom_hr/field.js', page)
        self.assertNotIn('/assets/erpnext_drive_integrations/field/', page)

    def test_patch_runs_before_the_doctypes_are_synced(self):
        patches = (APP / 'patches.txt').read_text(encoding='utf-8').split('\n')
        self.assertEqual(patches[:2], ['[pre_model_sync]', 'erpnext_drive_integrations.custom_hr.patches.rename_module'])
        self.assertIn("[post_model_sync]", patches)


class RenamePatch(unittest.TestCase):
    def run_patch(self, existing, target=None):
        calls = []
        db = types.SimpleNamespace(
            exists=lambda doctype, name: name in existing,
            get_value=lambda doctype, name, field, **kwargs: target if name == 'Custom HR' else 0,
            set_value=lambda doctype, name, *a, **k: calls.append(('set', name, a)))
        frappe = types.SimpleNamespace(db=db, rename_doc=lambda *a, **k: calls.append(('rename', a, k)),
                                       clear_cache=lambda: calls.append(('clear',)))
        spec = importlib.util.spec_from_file_location('rename_module', HR / 'patches/rename_module.py')
        module = importlib.util.module_from_spec(spec)
        saved = sys.modules.get('frappe')
        sys.modules['frappe'] = frappe
        try:
            spec.loader.exec_module(module)
            module.execute()
        finally:
            sys.modules['frappe'] = saved
        return calls

    def test_renames_once_with_frappes_own_rename_and_restores_the_flag(self):
        calls = self.run_patch({'Cloud Field'})
        renames = [c for c in calls if c[0] == 'rename']
        self.assertEqual(renames, [('rename', ('Module Def', 'Cloud Field', 'Custom HR'), {'force': True, 'merge': False})])
        self.assertEqual(calls[-2], ('set', 'Custom HR', ({'custom': 0, 'app_name': 'erpnext_drive_integrations'},)))

    def test_does_nothing_when_already_renamed(self):
        self.assertEqual(self.run_patch({'Custom HR'}), [])

    def test_merges_into_frappe_registered_module(self):
        target = types.SimpleNamespace(custom=0, app_name='erpnext_drive_integrations')
        calls = self.run_patch({'Cloud Field', 'Custom HR'}, target)
        self.assertIn(
            ('rename', ('Module Def', 'Cloud Field', 'Custom HR'), {'force': True, 'merge': True}),
            calls,
        )
        self.assertEqual(calls[-2], ('set', 'Custom HR', ({'custom': 0, 'app_name': 'erpnext_drive_integrations'},)))

    def test_refuses_a_custom_or_differently_owned_target(self):
        for target in (
            types.SimpleNamespace(custom=1, app_name='erpnext_drive_integrations'),
            types.SimpleNamespace(custom=0, app_name='another_app'),
        ):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.run_patch({'Cloud Field', 'Custom HR'}, target)


from datetime import datetime, timedelta  # noqa: E402
from erpnext_drive_integrations.custom_hr import domain  # noqa: E402

NOW = datetime(2026, 11, 22, 10, 0, 0)


class CaptureTime(unittest.TestCase):
    """Owner, 22 November 2026: online the server's time; offline the phone's time corrected by its measured clock
    difference, for at most a day, and marked for the approver."""

    def test_online_uses_the_server_clock_not_the_phone(self):
        at, gps = domain.capture_time(NOW, NOW - timedelta(minutes=2), offline=False,
                                      device_time=NOW - timedelta(days=5), clock_offset_s=999)
        self.assertEqual(at, NOW)
        self.assertEqual(gps, NOW - timedelta(minutes=2))

    def test_offline_applies_the_measured_clock_difference(self):
        phone = NOW - timedelta(hours=3)
        at, gps = domain.capture_time(NOW, phone - timedelta(minutes=1), offline=True, device_time=phone, clock_offset_s=90)
        self.assertEqual(at, phone + timedelta(seconds=90))
        self.assertEqual(gps, phone + timedelta(seconds=30))

    def test_offline_limits(self):
        for device, offset, message in [
            (NOW - timedelta(days=1, minutes=1), 0, 'older than one day'),
            (NOW + timedelta(minutes=10), 0, 'in the future'),
            (NOW, 2 * 86400, 'clock difference'),
            (NOW, True, 'clock difference'),
            (NOW, float('nan'), 'clock difference'),
            (None, 0, 'time it was taken'),
        ]:
            with self.assertRaisesRegex(domain.RuleError, message):
                domain.capture_time(NOW, device or NOW, offline=True, device_time=device, clock_offset_s=offset)

    def test_location_must_be_fresh_for_the_capture(self):
        with self.assertRaisesRegex(domain.RuleError, 'older than five minutes'):
            domain.capture_time(NOW, NOW - timedelta(minutes=6))
        with self.assertRaisesRegex(domain.RuleError, 'fresh GPS'):
            domain.capture_time(NOW, None)
        phone = NOW - timedelta(hours=2)
        with self.assertRaisesRegex(domain.RuleError, 'older than five minutes'):
            domain.capture_time(NOW, phone - timedelta(minutes=10), offline=True, device_time=phone)

    def test_checkout_window(self):
        check_in = NOW - timedelta(hours=8)
        self.assertEqual(domain.checkout_time(check_in, NOW), NOW)
        with self.assertRaisesRegex(domain.RuleError, 'before check-in'):
            domain.checkout_time(check_in, check_in - timedelta(minutes=1))
        with self.assertRaisesRegex(domain.RuleError, '12 hours'):
            domain.checkout_time(check_in, check_in + timedelta(hours=12, minutes=1))

    def test_fence_refuses_outside_and_inaccurate(self):
        self.assertEqual(domain.validate_location(17, 78, 10, 17, 78, 500, 200)[:2], (17.0, 78.0))
        with self.assertRaisesRegex(domain.RuleError, 'outside'):
            domain.validate_location(17.1, 78, 10, 17, 78, 500, 200)
        with self.assertRaisesRegex(domain.RuleError, 'not accurate'):
            domain.validate_location(17, 78, 250, 17, 78, 500, 200)


class SelfAttendanceSurface(unittest.TestCase):
    API = (HR / 'api.py').read_text(encoding='utf-8')

    def test_writes_are_post_only_and_reads_exist(self):
        for name in ('self_check_in', 'self_check_out', 'review_many', 'save_capture', 'submit', 'review'):
            self.assertRegex(self.API, r"@frappe\.whitelist\(methods=\['POST'\]\)\s*def " + name + r'\(', name)
        self.assertRegex(self.API, r"@frappe\.whitelist\(methods=\['GET'\]\)\s*def my_attendance\(")
        self.assertIn('check_in_sites=check_in_sites', self.API)

    def test_entry_records_type_and_offline_capture(self):
        entry = json.loads((HR / 'doctype/field_attendance_entry/field_attendance_entry.json').read_text(encoding='utf-8'))
        fields = {f['fieldname']: f for f in entry['fields']}
        self.assertEqual(fields['entry_type']['options'], 'Team\nSelf')
        self.assertEqual(fields['entry_type']['default'], 'Team')
        for name in ('entry_type', 'captured_offline', 'device_captured_at', 'clock_offset_s'):
            self.assertTrue(fields[name].get('read_only'), name)
            self.assertIn(name, entry.get('field_order', list(fields)))
        member = json.loads((HR / 'doctype/field_site_member/field_site_member.json').read_text(encoding='utf-8'))
        role = next(f for f in member['fields'] if f['fieldname'] == 'team_role')
        self.assertEqual(role['options'], 'Supervisor\nApprover\nStaff')

    def test_self_check_in_rules_are_in_the_service(self):
        service = (HR / 'service.py').read_text(encoding='utf-8')
        body = service.split('def self_capture(')[1].split('\ndef ')[0]
        for rule in ("Take a selfie to check in.", "Your supervisor records your attendance.", "domain.validate_location",
                     "moment(data,with_gps=True)", "state='Submitted'", "entry_type='Self'", "notify_approvers(",
                     "approve_without_review(doc)"):
            self.assertIn(rule, body)
        self.assertNotIn("Attendance',", body, 'HR attendance is created only on approval')


class OneAttendancePath(unittest.TestCase):
    def run_setup(self, stored, blocked):
        """Run setup.one_attendance_path against a fake site; `stored` = HR Settings already has our box saved."""
        writes = []
        meta = types.SimpleNamespace(has_field=lambda name: name == 'allow_employee_checkin_from_mobile_app')
        db = types.SimpleNamespace(
            exists=lambda doctype, name: True,
            sql=lambda query: [(1,)] if stored else [],
            get_single_value=lambda doctype, field: blocked,
            set_single_value=lambda doctype, field, value=None: writes.append((doctype, field, value)),
            get_value=lambda doctype, name, field: {'Site Day': 1, 'Site Night': 0}.get(name),
            set_value=lambda doctype, name, field, value: writes.append((doctype, name, field, value)))
        frappe = types.SimpleNamespace(db=db, get_meta=lambda doctype: meta, get_all=lambda doctype, **k: [
            types.SimpleNamespace(day_shift='Site Day', night_shift='Site Night')])
        fake_custom = types.ModuleType('frappe.custom.doctype.custom_field.custom_field')
        fake_custom.create_custom_fields = lambda *a, **k: None
        saved = {k: sys.modules.get(k) for k in ('frappe', 'frappe.custom.doctype.custom_field.custom_field')}
        sys.modules.update({'frappe': frappe, 'frappe.custom.doctype.custom_field.custom_field': fake_custom})
        try:
            spec = importlib.util.spec_from_file_location('hr_setup', HR / 'setup.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.one_attendance_path()
        finally:
            for k, v in saved.items():
                if v is None:
                    sys.modules.pop(k, None)
                else:
                    sys.modules[k] = v
        return writes

    SWITCH_OFF = [('HR Settings', 'allow_employee_checkin_from_mobile_app', 0),
                  ('Shift Type', 'Site Day', 'enable_auto_attendance', 0)]

    def test_first_install_blocks_and_switches_off_only_our_sites_shifts(self):
        self.assertEqual(self.run_setup(stored=False, blocked=1), [
            ('HR Settings', {'custom_block_frappe_hr_checkin': 1, 'custom_checkin_allowed_roles': 'System Manager'}, None),
            *self.SWITCH_OFF])

    def test_admin_choice_is_kept_on_every_migrate(self):
        self.assertEqual(self.run_setup(stored=True, blocked=1), self.SWITCH_OFF)
        self.assertEqual(self.run_setup(stored=True, blocked=0), [], 'unticked: Frappe HR settings are left alone')

    def test_hr_settings_offers_the_admin_the_choice(self):
        source = (HR / 'setup.py').read_text(encoding='utf-8')
        for field in ("fieldname='custom_block_frappe_hr_checkin'", "fieldname='custom_checkin_allowed_roles'"):
            self.assertIn(field, source.split("'HR Settings':[")[1].split("'Attendance':[")[0])


class FrappeHrCheckinBlock(unittest.TestCase):
    def test_rule(self):
        allowed = domain.checkin_allowed
        self.assertTrue(allowed(0, '', ['Employee']), 'not blocked: open to all')
        self.assertFalse(allowed(1, 'System Manager', ['Employee']))
        self.assertTrue(allowed(1, 'System Manager', ['Employee', 'System Manager']))
        self.assertTrue(allowed(1, 'HR Manager, System Manager', ['HR Manager']), 'comma-separated')
        self.assertTrue(allowed(1, 'System Manager\n  HR User  \n', ['HR User']), 'one per line, spaces ignored')
        self.assertFalse(allowed(1, '', ['System Manager']), 'blocked with no roles listed: nobody')
        self.assertFalse(allowed(1, 'HR', ['HR Manager']), 'whole role names only')
        self.assertTrue(allowed(1, '', [], 'Administrator'), 'background jobs')

    def test_every_route_is_blocked_on_the_server(self):
        self.assertIn('erpnext_drive_integrations.custom_hr.guards.block_frappe_hr_checkin',
                      hooks.doc_events['Employee Checkin']['validate'])
        guard = (HR / 'guards.py').read_text(encoding='utf-8').split('def block_frappe_hr_checkin(')[1]
        for part in ("custom_block_frappe_hr_checkin", "custom_checkin_allowed_roles", "frappe.session.user", "frappe.PermissionError"):
            self.assertIn(part, guard)


class SiteApproval(unittest.TestCase):
    SERVICE = (HR / 'service.py').read_text(encoding='utf-8')

    def body(self, name):
        return self.SERVICE.split(f'def {name}(')[1].split('\ndef ')[0]

    def test_sites_need_approval_unless_unticked(self):
        site = json.loads((HR / 'doctype/field_site/field_site.json').read_text(encoding='utf-8'))
        field = next(f for f in site['fields'] if f['fieldname'] == 'approval_required')
        self.assertEqual((field['fieldtype'], field['default']), ('Check', '1'))
        patches = (APP / 'patches.txt').read_text(encoding='utf-8')
        self.assertIn('[post_model_sync]\nerpnext_drive_integrations.custom_hr.patches.site_approval_required', patches)
        self.assertIn('SET approval_required=1', (HR / 'patches/site_approval_required.py').read_text(encoding='utf-8'))

    def test_only_online_entries_skip_approval(self):
        rule = self.body('approve_without_review')
        for part in ('doc.captured_offline', "'approval_required'", 'existing_attendance(doc)', 'hr_attendance(doc)'):
            self.assertIn(part, rule)
        self.assertLess(rule.index('doc.captured_offline'), rule.index('hr_attendance(doc)'))
        for caller in ('self_capture', 'submit_entry'):
            self.assertIn('if not approve_without_review(doc):notify_approvers(', self.body(caller), caller)
        self.assertIn('hr_attendance(doc)', self.body('review_entry'))
        self.assertEqual(self.SERVICE.count("doctype='Attendance'"), 1, 'one place creates HR attendance')


if __name__ == '__main__':
    unittest.main(verbosity=2)
