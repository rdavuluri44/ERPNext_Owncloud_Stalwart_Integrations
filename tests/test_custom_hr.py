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


if __name__ == '__main__':
    unittest.main(verbosity=2)
