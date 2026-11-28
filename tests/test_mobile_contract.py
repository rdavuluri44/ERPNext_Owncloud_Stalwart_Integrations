"""The version handshake between the server and the mobile apps (P104; owner, 27 November 2026).

These checks fail when a function the mobile apps call, or a field of a record they read, changes without the
recorded fingerprint being renewed; when `bootstrap` stops telling the apps the version, the fingerprint and the
oldest accepted app version; or when a mistyped setting could turn every phone away. No live site.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
APP = ROOT / 'erpnext_drive_integrations'

from erpnext_drive_integrations.custom_hr import contract  # noqa: E402


class Fingerprint(unittest.TestCase):
    def test_the_recorded_fingerprint_is_the_one_the_code_gives(self):
        self.assertEqual(contract.FINGERPRINT, contract.compute(), (
            'A function the mobile apps call, or a field of a record they read, has changed. Decide whether older '
            'apps still work (if not, the release raises mobile_minimum_app_version), then set FINGERPRINT in '
            'custom_hr/contract.py to the value on the right.'))
        self.assertRegex(contract.FINGERPRINT, r'^[0-9a-f]{12}$')

    def test_it_covers_every_function_the_apps_call_and_the_records_they_read(self):
        names = [what for what, _ in contract.parts()]
        for expected in ('custom_hr/api.py:bootstrap', 'custom_hr/api.py:self_check_in', 'custom_hr/api.py:team',
                         'custom_hr/api.py:review_many', 'custom_hr/api.py:verify', 'custom_hr/api.py:entry_photo',
                         'custom_hr/api.py:face_enrol', 'custom_hr/api.py:face_queue_resolve',
                         'drive_store/api.py:upload_photo', 'drive_store/api.py:photos'):
            self.assertIn(expected, names)
        self.assertEqual(names[-len(contract.RECORDS):], list(contract.RECORDS))
        self.assertEqual(len(names), len(set(names)))

    def copy(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        for path in contract.MODULES + contract.RECORDS:
            (folder / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(APP / path, folder / path)
        return folder

    def change(self, folder, path, old, new):
        text = (folder / path).read_text(encoding='utf-8')
        self.assertIn(old, text)
        (folder / path).write_text(text.replace(old, new, 1), encoding='utf-8')

    def test_a_changed_function_or_field_changes_it_and_a_comment_does_not(self):
        folder = self.copy()
        before = contract.compute(folder)
        self.assertEqual(before, contract.compute(), 'the copy is the code')
        self.change(folder, 'custom_hr/api.py', 'def my_records():',
                    '# a comment for the next reader\n\ndef my_records():')
        self.assertEqual(contract.compute(folder), before, 'a comment or an empty line is not a change')
        self.change(folder, 'custom_hr/api.py', 'def my_records():',
                    'def my_records(limit=None):')
        argument = contract.compute(folder)
        self.assertNotEqual(argument, before, 'a new argument')
        self.change(folder, 'custom_hr/api.py', "version='0.2.0'", "version='0.3.0'")
        answer = contract.compute(folder)
        self.assertNotEqual(answer, argument, 'a changed answer')
        self.change(folder, contract.RECORDS[0], '"fieldname": "revision"', '"fieldname": "revision_number"')
        self.assertNotEqual(contract.compute(folder), answer, 'a renamed field')

    def test_a_function_that_is_not_for_the_apps_is_not_part_of_it(self):
        folder = self.copy()
        before = contract.compute(folder)
        self.change(folder, 'custom_hr/api.py', 'def data(value):', 'def data(value, strict=False):')
        self.assertEqual(contract.compute(folder), before, 'only whitelisted functions count')


class Minimum(unittest.TestCase):
    def test_a_mistyped_setting_is_no_minimum(self):
        for value in (None, '', 'latest', '1.2', '1.2.3.4', 'v1.2.3', '1.2.x', ' ', 12, '99999.1.1'):
            self.assertEqual(contract.minimum(value), '0.0.0', repr(value))
        self.assertEqual(contract.minimum(' 1.4.0 '), '1.4.0')


class Bootstrap(unittest.TestCase):
    SOURCE = (APP / 'custom_hr/api.py').read_text(encoding='utf-8')

    def test_bootstrap_tells_the_version_the_contract_and_the_minimum(self):
        body = self.SOURCE.split('def bootstrap():')[1].split('\n@frappe.whitelist')[0]
        self.assertIn("version='0.2.0'", body)
        self.assertIn('contract=contract.FINGERPRINT', body)
        self.assertIn("minimum_app_version=contract.minimum(frappe.conf.get('mobile_minimum_app_version'))", body)

    def test_the_handshake_is_documented_for_the_apps(self):
        readme = (APP / 'custom_hr/README.md').read_text(encoding='utf-8')
        for word in ('`contract`', '`minimum_app_version`', '`mobile_minimum_app_version`'):
            self.assertIn(word, readme)


if __name__ == '__main__':
    unittest.main()
