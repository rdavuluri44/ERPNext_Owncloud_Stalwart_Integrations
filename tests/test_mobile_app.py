"""mobile-app module: the public source stays tenant-neutral and matches the server API.

The app's name, app ID, link scheme, ERP address and OAuth client ID belong to one deployment and
come from the private mobile/.env. These checks fail if a real value is written into the source.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / 'mobile'


class MobileAppTests(unittest.TestCase):
    def test_app_identity_defaults_are_neutral(self):
        expo = json.loads((MOBILE / 'app.json').read_text())['expo']
        self.assertEqual(expo['ios']['bundleIdentifier'], 'com.example.erp')
        self.assertEqual(expo['android']['package'], 'com.example.erp')
        self.assertEqual(expo['name'], 'ERP')

    def test_no_plugin_blocks_the_camera(self):
        # `"cameraPermission": false` in an Expo plugin removes the CAMERA permission for the whole app on
        # Android and deletes the iPhone camera text: check-in selfies and worker photos then can't open.
        for plugin in json.loads((MOBILE / 'app.json').read_text())['expo']['plugins']:
            if isinstance(plugin, list):
                self.assertIsNot(plugin[1].get('cameraPermission'), False, f'{plugin[0]} blocks the camera')

    def test_source_names_no_real_host(self):
        for path in list((MOBILE / 'src').rglob('*.ts*')) + [MOBILE / 'app.config.ts', MOBILE / '.env.example']:
            for host in re.findall(r'https?://([A-Za-z0-9.-]+)', path.read_text()):
                self.assertTrue(host.endswith('example.com'), f'{path.relative_to(ROOT)} names {host}')

    def test_oauth_client_id_is_not_built_in(self):
        session = (MOBILE / 'src/auth/session.tsx').read_text()
        self.assertIn("process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? ''", session)
        self.assertIn('EXPO_PUBLIC_OAUTH_CLIENT_ID=\n', (MOBILE / '.env.example').read_text())

    def test_bootstrap_path_matches_a_whitelisted_server_method(self):
        path = re.search(r"BOOT_PATH = '/api/method/([\w.]+)'", (MOBILE / 'src/lib/erp.ts').read_text()).group(1)
        module, func = path.rsplit('.', 1)
        source = (ROOT / (module.replace('.', '/') + '.py')).read_text()
        self.assertRegex(source, r'@frappe\.whitelist\([^)]*\)\s*\ndef ' + func + r'\(')

    def test_install_scripts_stay_blocked(self):
        settings = (MOBILE / 'pnpm-workspace.yaml').read_text()
        self.assertIn('onlyBuiltDependencies: []', settings)
        self.assertTrue((MOBILE / 'pnpm-lock.yaml').is_file())


class BuildGuideTests(unittest.TestCase):
    """The build guide is what agents follow: it must exist, be the first thing they read, and name only server
    methods that exist."""
    GUIDE = (MOBILE / 'BUILD-GUIDE.md').read_text(encoding='utf-8')

    def test_agents_read_the_guide_first_and_never_run_unpinned_eas(self):
        agents = (MOBILE / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('BUILD-GUIDE.md', agents.split('## ')[0], 'the pointer belongs at the top')
        self.assertNotIn('or `npx eas-cli@latest <command>` otherwise', agents, 'the unpinned instruction is back')
        self.assertIn('never `npx eas-cli@latest`', agents)
        self.assertIn('pin `eas-cli`', self.GUIDE)

    def test_field_methods_named_in_the_guide_exist(self):
        # The HR part was renamed from field/ to custom_hr/ (PR #38); accept either while both PRs are open.
        path = next(p for p in (ROOT / 'erpnext_drive_integrations/custom_hr/api.py', ROOT / 'erpnext_drive_integrations/field/api.py') if p.is_file())
        api = path.read_text(encoding='utf-8')
        whitelisted = set(re.findall(r'@frappe\.whitelist[^\n]*\n\s*def (\w+)\(', api))
        section = self.GUIDE.split('whitelisted methods in `custom_hr/api.py` (formerly `field/api.py`; ')[1].split(').')[0]
        named = set(re.findall(r'`(\w+)`', section))
        self.assertGreaterEqual(len(named), 10)
        self.assertEqual(named - whitelisted, set(), 'the guide names a field method that does not exist')

    def test_attendance_calls_in_the_guide_exist_once_the_hr_part_is_merged(self):
        # Section 7a names the calls of PR #39 (custom_hr); checked as soon as that code is on the branch.
        api_path = ROOT / 'erpnext_drive_integrations/custom_hr/api.py'
        section = self.GUIDE.split('### 7a. Attendance calls')[1].split('\n## ')[0]
        named = set(re.findall(r'^\| `(\w+)`(?:, `(\w+)`)?', section, re.M))
        named = {n for pair in named for n in pair if n}
        self.assertGreaterEqual(len(named), 9)
        if not api_path.is_file() or 'def self_check_in(' not in api_path.read_text(encoding='utf-8'):
            self.skipTest('custom_hr self check-in not merged yet (PR #38, #39)')
        whitelisted = set(re.findall(r'@frappe\.whitelist[^\n]*\n\s*def (\w+)\(', api_path.read_text(encoding='utf-8')))
        self.assertEqual(named - whitelisted, set(), 'section 7a names a call that does not exist')

    def test_guide_points_at_the_real_sign_in_and_workflow_code(self):
        for path in ('erpnext_drive_integrations/portal/mobile.py', 'erpnext_drive_integrations/onboarding/api.py'):
            self.assertTrue((ROOT / path).is_file(), path)
        self.assertIn('frappe.model.workflow.apply_workflow', self.GUIDE)
        self.assertIn('send_message_with_attachments', self.GUIDE)
        self.assertIn('frappe.integrations.oauth2', (MOBILE / 'src/auth/session.tsx').read_text(encoding='utf-8'))

    def test_passkey_trial_is_neutral_and_keeps_its_lock_rules(self):
        # P82 trial app: a key that signs only after a strong fingerprint/face match, is destroyed when one is
        # added, has no PIN fallback, and is refused when the phone gives less than asked.
        trial = MOBILE / 'trials/passkey-android'
        source = trial / 'src/main/java/com/example/passkeytrial'
        self.assertIn('applicationId = "com.example.passkeytrial"', (trial / 'build.gradle.kts').read_text())
        keys = (source / 'Keys.kt').read_text()
        for rule in ('setUserAuthenticationRequired(true)', 'setInvalidatedByBiometricEnrollment(true)',
                     'AUTH_BIOMETRIC_STRONG', 'throw Refused('):
            self.assertIn(rule, keys)
        everything = ''.join(p.read_text() for p in source.glob('*.kt'))
        self.assertNotIn('DEVICE_CREDENTIAL', everything, 'no PIN fallback for the key')
        self.assertIn('setAllowedAuthenticators(BIOMETRIC_STRONG)', (source / 'Biometric.kt').read_text())
        self.assertIn('android:allowBackup="false"', (trial / 'src/main/AndroidManifest.xml').read_text())
        for path in source.glob('*.kt'):
            for host in re.findall(r'https?://([A-Za-z0-9.-]+)', path.read_text()):
                self.assertEqual(host, 'www.gstatic.com', f'{path.name} names {host}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
