"""P80: the office editor stays registered with Drive (signed-in check, repair, restart step, setup)."""
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import host_check as hc  # noqa: E402
import render_host_checks as rh  # noqa: E402

LOG = []
hc.log = LOG.append

T0 = 1_800_000_000.0
OCIS, BRIDGE = 'ocis-abc', 'collaboration-abc'
TOKEN = 'T' * 40


def iso(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.0Z')


class Drive:
    """Docker, Drive's app list, its CLI and the token file, scripted per test."""

    def __init__(self, registered=True, registers_on_restart=True, health='healthy', ocis_uptime=600,
                 token_valid=True, cli_works=True, account_exists=False, stored=None):
        self.t = T0
        self.registered, self.registers_on_restart = registered, registers_on_restart
        self.health, self.ocis_started = health, T0 - ocis_uptime
        self.bridge_started = T0 - 3600
        self.token_valid, self.cli_works, self.account_exists = token_valid, cli_works, account_exists
        self.secrets = {} if stored is None else {'/etc/cloud-host-check/drive-editor.json': stored}
        self.restarted, self.tokens_made, self.requests, self.created = [], [], [], []

    def now(self):
        return self.t

    def boot_id(self):
        # The boot check also compares with the containers saved before a reboot (P57); same boot here.
        return 'boot-1'

    def send_mail(self, alert, subject, body):
        self.mails = getattr(self, 'mails', []) + [(subject, body)]

    def sleep(self, seconds):
        self.t += seconds

    def run(self, command, timeout=60):
        if command[:2] == ['docker', 'ps']:
            return 0, OCIS + '\n' + BRIDGE + '\n'
        if command[:2] == ['docker', 'inspect']:
            if command[-1] == OCIS:
                return 0, 'running %s %s\n' % (self.health, iso(self.ocis_started))
            return 0, 'running %s\n' % iso(self.bridge_started)
        if command[:2] == ['docker', 'restart']:
            self.restarted.append(command[2])
            self.bridge_started = self.t
            if self.registers_on_restart:
                self.registered = True
            return 0, ''
        if command[:2] == ['docker', 'logs']:
            return 0, 'registered\n'
        if command[:2] == ['docker', 'exec'] and command[3:6] == ['ocis', 'auth-app', 'create']:
            if not self.cli_works:
                return 1, 'error: secret ' + 'S' * 30
            user = command[6].split('=', 1)[1]
            self.tokens_made.append(user)
            self.token_valid = True
            return 0, 'App token created for %s\n token: %s\n' % (user, TOKEN + str(len(self.tokens_made)))
        return 1, ''

    def request_json(self, method, url, headers=None, body=None, timeout=15):
        self.requests.append((method, url))
        if url.endswith('/app/list'):
            if not self.token_valid:
                return 401, None
            if not self.registered:
                return 200, {'mime-types': []}
            return 200, {'mime-types': [{'ext': e, 'app_providers': [{'name': 'OnlyOffice'}]}
                                        for e in ('docx', 'xlsx', 'pptx', 'pdf')]}
        if url.endswith('/graph/v1.0/users/editor-check') and method == 'GET':
            return (200, {'id': 'u1'}) if self.account_exists else (404, {'error': {}})
        if url.endswith('/graph/v1.0/users') and method == 'POST':
            self.created.append(body)
            return 201, {'id': 'u1'}
        return 404, None

    def read_secret(self, path):
        return self.secrets.get(path)

    def write_secret(self, path, value):
        self.secrets[path] = value


def config(**editor):
    value = json.loads(json.dumps(hc.DEFAULTS))
    value.update({'state_dir': tempfile.mkdtemp(), 'interval_seconds': 15, 'timeout_seconds': 120,
                  'http': [], 'containers': [], 'tcp': []})
    value['editor'].update({'url': 'https://drive.example.com'}, **editor)
    return value


STORED = {'login': 'editor-check', 'token': 'stored-token-value-0000'}


def status(cfg):
    return json.loads((Path(cfg['state_dir']) / 'editor-status.json').read_text())


class EditorCheckTests(unittest.TestCase):
    def setUp(self):
        LOG.clear()

    def test_registered_editor_passes_without_touching_anything(self):
        cfg, drive = config(), Drive(stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 0)
        self.assertEqual(drive.restarted, []); self.assertEqual(drive.tokens_made, [])
        self.assertTrue(status(cfg)['registered'])

    def test_missing_editor_with_healthy_drive_is_repaired_once_and_still_reported(self):
        """The 25 November case: ocis recreated alone, the bridge kept running, no error in its log."""
        cfg, drive = config(), Drive(registered=False, stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 1)
        self.assertEqual(drive.restarted, [BRIDGE])
        self.assertTrue(status(cfg)['repaired']); self.assertTrue(status(cfg)['registered'])
        self.assertTrue(any('repaired by restarting the editor bridge' in line for line in LOG), LOG)
        self.assertEqual(hc.editor_check(cfg, drive), 0)             # next run: all well again

    def test_repair_is_not_repeated_within_the_interval(self):
        cfg, drive = config(), Drive(registered=False, registers_on_restart=False, stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 1)
        self.assertFalse(status(cfg)['registered'])
        drive.t += 300
        self.assertEqual(hc.editor_check(cfg, drive), 1)
        self.assertEqual(drive.restarted, [BRIDGE])                   # once, not every five minutes
        self.assertTrue(any('not again yet' in line for line in LOG), LOG)
        drive.t += 1800
        hc.editor_check(cfg, drive)
        self.assertEqual(drive.restarted, [BRIDGE, BRIDGE])

    def test_no_repair_while_drive_itself_is_not_ready(self):
        for drive in [Drive(registered=False, health='starting', stored=dict(STORED)),
                      Drive(registered=False, ocis_uptime=20, stored=dict(STORED))]:
            cfg = config()
            self.assertEqual(hc.editor_check(cfg, drive), 1)
            self.assertEqual(drive.restarted, [])

    def test_repair_can_be_switched_off(self):
        cfg, drive = config(repair=False), Drive(registered=False, stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 1)
        self.assertEqual(drive.restarted, [])

    def test_expired_token_is_renewed_by_drive_cli_and_never_logged(self):
        cfg, drive = config(), Drive(token_valid=False, stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 0)
        self.assertEqual(drive.tokens_made, ['editor-check'])
        self.assertEqual(drive.secrets[cfg['editor']['token_file']]['token'], TOKEN + '1')
        self.assertFalse(any(TOKEN in line for line in LOG))

    def test_check_that_cannot_sign_in_alerts_without_restarting_the_bridge(self):
        cfg, drive = config(), Drive(token_valid=False, cli_works=False, stored=dict(STORED))
        self.assertEqual(hc.editor_check(cfg, drive), 1)
        self.assertEqual(drive.restarted, [])
        self.assertTrue(any('cannot sign in' in line for line in LOG), LOG)
        self.assertFalse(any('S' * 30 in line for line in LOG), 'CLI output is redacted')

    def test_partial_registration_counts_as_missing(self):
        cfg, drive = config(extensions=['docx', 'xlsx', 'odt']), Drive(stored=dict(STORED))
        state = hc.editor_registered(cfg, drive)
        self.assertFalse(state['ok']); self.assertIn('odt', state['why'])

    def test_not_configured_is_a_quiet_no_op(self):
        cfg = config(); cfg['editor']['url'] = ''
        self.assertEqual(hc.editor_check(cfg, Drive()), 0)


class EditorRestartTests(unittest.TestCase):
    def test_waits_for_drive_then_restarts_the_bridge_and_confirms_registration(self):
        drive = Drive(registered=False, health='starting', stored=dict(STORED))
        original = drive.sleep

        def sleep(seconds):
            original(seconds)
            if drive.t - T0 > 30:
                drive.health = 'healthy'
        drive.sleep = sleep
        self.assertEqual(hc.editor_restart(config(), drive), 0)
        self.assertEqual(drive.restarted, [BRIDGE])
        self.assertGreater(drive.t - T0, 30, 'the bridge was not restarted before Drive was healthy')

    def test_fails_clearly_when_drive_never_becomes_healthy(self):
        LOG.clear()
        drive = Drive(health='unhealthy', stored=dict(STORED))
        self.assertEqual(hc.editor_restart(config(drive_wait_seconds=60), drive), 1)
        self.assertEqual(drive.restarted, [])
        self.assertTrue(any(line.startswith('EDITOR RESTART FAILED: Drive is not ready') for line in LOG), LOG)

    def test_fails_when_the_editor_does_not_come_back(self):
        drive = Drive(registered=False, registers_on_restart=False, stored=dict(STORED))
        self.assertEqual(hc.editor_restart(config(registration_wait_seconds=60), drive), 1)

    def test_without_the_signed_in_check_it_falls_back_to_the_bridge_log(self):
        cfg = config(); cfg['editor']['url'] = ''
        drive = Drive(stored=dict(STORED))
        self.assertEqual(hc.editor_restart(cfg, drive), 0)
        self.assertEqual(drive.restarted, [BRIDGE])


class BootTests(unittest.TestCase):
    def test_boot_repairs_a_bridge_that_logs_nothing_but_never_registered(self):
        cfg, drive = config(), Drive(registered=False, stored=dict(STORED))
        drive.bridge_started = T0 - 600
        self.assertEqual(hc.boot(cfg, drive), 0)
        self.assertEqual(drive.restarted, [BRIDGE])


class SetupTests(unittest.TestCase):
    def test_creates_the_account_once_and_stores_a_token_root_only(self):
        cfg, drive = config(), Drive()
        self.assertEqual(hc.editor_setup(cfg, drive), 0)
        self.assertEqual(drive.tokens_made, ['admin', 'editor-check'])
        self.assertEqual(len(drive.created), 1)
        created = drive.created[0]
        self.assertEqual(created['onPremisesSamAccountName'], 'editor-check')
        self.assertNotIn('appRoleAssignments', json.dumps(created))      # no admin or space role
        self.assertEqual(drive.secrets[cfg['editor']['token_file']]['login'], 'editor-check')
        drive2 = Drive(account_exists=True)
        self.assertEqual(hc.editor_setup(config(), drive2), 0)
        self.assertEqual(drive2.created, [])

    def test_real_environment_writes_the_token_file_mode_600(self):
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / 'sub' / 'drive-editor.json')
            hc.Environment().write_secret(path, {'login': 'x', 'token': 'y'})
            self.assertEqual(Path(path).stat().st_mode & 0o777, 0o600)
            self.assertEqual(hc.Environment().read_secret(path), {'login': 'x', 'token': 'y'})


class RenderTests(unittest.TestCase):
    PROFILE = {'projects': ['drive'], 'hosts': {'drive': 'drive.example.com', 'office': 'office.example.com'},
               'host_checks': {}}

    def rendered(self, profile):
        with tempfile.TemporaryDirectory() as temp:
            names = rh.render(profile, temp)
            cfg = json.loads((Path(temp) / 'config.json').read_text())
            timer = (Path(temp) / 'cloud-editor-check.timer').read_text() if 'cloud-editor-check.timer' in names else ''
            service = (Path(temp) / 'cloud-editor-check.service').read_text() if timer else ''
            return names, cfg, timer, service

    def test_hosts_with_drive_get_the_editor_check_every_five_minutes(self):
        names, cfg, timer, service = self.rendered(self.PROFILE)
        self.assertEqual(cfg['editor'], {'url': 'https://drive.example.com'})
        self.assertIn('OnUnitActiveSec=5min', timer)
        self.assertIn('host_check.py editor --config', service)

    def test_switched_off_or_without_drive_there_is_no_editor_check(self):
        for profile in [dict(self.PROFILE, host_checks={'editor': False}), dict(self.PROFILE, projects=['erp'])]:
            names, cfg, _, _ = self.rendered(profile)
            self.assertNotIn('editor', cfg); self.assertNotIn('cloud-editor-check.timer', names)

    def test_overrides_and_bad_values(self):
        _, cfg, _, _ = self.rendered(dict(self.PROFILE, host_checks={'editor': {'url': 'https://files.example.com:8443',
                                                                             'repair': False}}))
        self.assertEqual(cfg['editor'], {'url': 'https://files.example.com:8443', 'repair': False})
        for bad in [{'url': 'http://drive.example.com'}, {'account': 'a b'}, {'unknown': 1}, 'yes']:
            with self.assertRaises(ValueError):
                self.rendered(dict(self.PROFILE, host_checks={'editor': bad}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
