"""P99: the drift check sees the runtime files mounted into the containers, not only image tags and notes.

After P97 the ERP web server template on production equalled main, yet the check listed it as behind because
the ERP image was older; the opposite case was worse: a mounted file changed by hand was never noticed. Sample
git history in a temporary repository; Docker is faked, no network.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import drift_check as dc  # noqa: E402
import runtime_mounts as rm  # noqa: E402

TEMPLATE = 'deployment/erp/frappe.conf.template'
SITE = 'integrations/website/site'


class MountedFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'test')
        for path in ('deployment/promotion-map.json', 'deployment/stacks/mounts.json'):
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / path, self.repo / path)
        self.write(TEMPLATE, 'old rule\n')
        self.write(SITE + '/index.html', '<p>__SITE_NAME__</p>\n')
        self.write('erpnext_drive_integrations/hooks.py', 'a = 1\n')
        self.old = self.commit('old template')
        self.write(TEMPLATE, 'new rule\n')
        self.write('erpnext_drive_integrations/hooks.py', 'a = 2\n')
        self.main = self.commit('new template and an image change')
        self.runtime = base / 'runtime'
        (self.runtime / 'mounts').mkdir(parents=True)
        self.profile = base / 'erp.json'
        self.profile.write_text(json.dumps({'commit': self.old}))
        self.mounts = {}
        self.real = dc.run
        self.calls = []

        def fake_run(args):
            if args[0] == 'git':
                return self.real(args)
            self.calls.append(args)
            if args[:2] == ['docker', 'ps']:
                return '\n'.join(self.mounts) + '\n'
            if args[:2] == ['docker', 'inspect'] and '{{json .Mounts}}' in args:
                return json.dumps(self.mounts.get(args[-1], []))
            raise AssertionError(args)
        dc.run = fake_run

    def tearDown(self):
        dc.run = self.real
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, text=True, check=True).stdout.strip()

    def write(self, path, text):
        (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / path).write_bytes(text.encode())

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def mount(self, container, name, content=None, rw=False, folder=None):
        path = self.runtime / 'mounts' / name
        if folder is not None:
            for relative, text in folder.items():
                (path / relative).parent.mkdir(parents=True, exist_ok=True)
                (path / relative).write_bytes(text.encode())
        elif content is not None:
            path.write_bytes(content.encode())
        self.mounts.setdefault(container, []).append(
            {'Type': 'bind', 'Source': str(path), 'Destination': '/x', 'RW': rw})
        return path

    def record(self, name, commit, path):
        rm.record_entries(self.runtime, {name: {'source': rm.source_of(
            next(m for m in json.loads((ROOT / 'deployment/stacks/mounts.json').read_text()) if m['path'] == name)),
            'commit': commit, 'sha256': rm.digest(path)}}, lambda p, text: p.write_text(text))

    def check(self, **extra):
        config = {'source': str(self.repo), 'branch': 'main', 'fetch': False,
                  'stacks': {'erp': {'commit_from': {'profile': str(self.profile)}}}, **extra}
        return dc.check(config)

    def row(self, status, name):
        return next(r for r in status['mounts'] if r['mount'] == name)

    def test_a_mounted_file_equal_to_main_no_longer_counts_as_behind(self):
        # P97: the image is older than main, the mounted template was replaced by main's file.
        self.mount('frontend-1', 'erp_frontend_2', 'new rule\n')
        status = self.check()
        self.assertEqual(self.row(status, 'erp_frontend_2')['state'], 'equal to main')
        self.assertEqual(status['stacks']['erp']['files'], ['erpnext_drive_integrations/hooks.py'],
                         'the template is equal to main; only the image change is left')
        self.assertEqual(status['stacks']['erp']['equal_mounts'], ['erp_frontend_2'])

    def test_the_stack_is_clean_when_the_mounted_file_was_the_only_difference(self):
        self.profile.write_text(json.dumps({'commit': self.old}))
        self.write('erpnext_drive_integrations/hooks.py', 'a = 1\n')
        self.commit('image change undone')
        self.mount('frontend-1', 'erp_frontend_2', 'new rule\n')
        status = self.check()
        self.assertEqual(status['stacks']['erp']['state'], 'clean')
        self.assertEqual(status['drift'], [])

    def test_an_old_mounted_file_is_behind_even_when_the_image_is_current(self):
        self.profile.write_text(json.dumps({'commit': self.main}))
        path = self.mount('frontend-1', 'erp_frontend_2', 'old rule\n')
        self.assertEqual(self.row(self.check(), 'erp_frontend_2')['state'], 'not compared',
                         'no record: it cannot tell')
        self.record('erp_frontend_2', self.old, path)
        status = self.check()
        self.assertEqual(self.row(status, 'erp_frontend_2')['state'], 'behind')
        self.assertEqual(status['stacks']['erp'], dict(status['stacks']['erp'], state='behind', files=[TEMPLATE]))
        self.assertEqual(status['drift'], ['erp is behind main (1 file(s), e.g. ' + TEMPLATE + ')'])

    def test_a_file_changed_by_hand_is_drift(self):
        self.profile.write_text(json.dumps({'commit': self.main}))
        path = self.mount('frontend-1', 'erp_frontend_2', 'new rule rendered\n')
        self.record('erp_frontend_2', self.main, path)
        self.assertEqual(self.row(self.check(), 'erp_frontend_2')['state'], 'equal to main',
                         'rendered from main and unchanged since')
        path.write_text('new rule rendered, then edited on the server\n')
        status = self.check()
        self.assertEqual(self.row(status, 'erp_frontend_2')['state'], 'changed by hand')
        self.assertEqual(len(status['drift']), 1)
        self.assertIn('erp: mounted erp_frontend_2 (' + TEMPLATE + ') differs from what was deployed', status['drift'][0])
        config = Path(self.tmp.name) / 'config.json'
        config.write_text(json.dumps({'source': str(self.repo), 'branch': 'main', 'fetch': False,
                                      'state_dir': self.tmp.name + '/state',
                                      'stacks': {'erp': {'commit_from': {'profile': str(self.profile)}}}}))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(dc.main(['--config', str(config)]), 2)
        self.assertIn('changed by hand', json.loads((Path(self.tmp.name) / 'state/status.json').read_text())['mounts'][0]['state'])
        self.assertIn('DRIFT', out.getvalue())

    def test_a_branded_folder_is_compared_through_its_record(self):
        folder = self.mount('web-1', 'website_web_0', folder={'index.html': '<p>Company</p>\n', 'front/logo.svg': '<svg/>'})
        self.record('website_web_0', self.old, folder)
        status = self.check(stacks={'website': {'commit_from': {'profile': str(self.profile)}}})
        self.assertEqual(self.row(status, 'website_web_0')['state'], 'equal to main', 'the site source did not change')
        (folder / 'front/extra.js').write_text('added on the server')
        self.assertEqual(self.row(self.check(), 'website_web_0')['state'], 'changed by hand')

    def test_data_secrets_and_writable_mounts_are_never_read(self):
        missing = self.runtime / 'mounts'
        self.mounts['configurator-1'] = [{'Type': 'bind', 'Source': str(missing / 'erp_configurator_1'), 'RW': True}]
        self.mounts['worker-1'] = [{'Type': 'bind', 'Source': str(missing / 'processing_document_worker_1'), 'RW': False},
                                   {'Type': 'volume', 'Source': '/var/lib/docker/volumes/x', 'RW': False},
                                   {'Type': 'bind', 'Source': '/etc/hosts', 'RW': False}]
        status = self.check()
        self.assertEqual(status['mounts'], [], 'none of these exist on disk; reading one would have failed')
        self.assertEqual(status['problems'], [])

    def test_one_file_mounted_by_several_containers_is_compared_once(self):
        path = self.mount('websocket-1', 'erp_websocket_0', 'x\n')
        self.mounts['websocket-2'] = list(self.mounts['websocket-1'])
        rows = [r for r in self.check()['mounts'] if r['mount'] == 'erp_websocket_0']
        self.assertEqual(len(rows), 1)
        self.assertTrue(path.exists())

    def test_it_only_reads(self):
        path = self.mount('frontend-1', 'erp_frontend_2', 'new rule\n')
        before = rm.digest(self.runtime), self.git('status', '--porcelain'), self.git('rev-parse', 'HEAD')
        self.check()
        self.assertEqual((rm.digest(self.runtime), self.git('status', '--porcelain'), self.git('rev-parse', 'HEAD')), before)
        self.assertTrue(path.exists())
        for args in self.calls:
            self.assertIn(args[1], ('ps', 'inspect'))

    def test_the_mount_comparison_can_be_switched_off(self):
        self.mount('frontend-1', 'erp_frontend_2', 'new rule\n')
        status = self.check(mounts=False)
        self.assertEqual(status['mounts'], [])
        self.assertIn(TEMPLATE, status['stacks']['erp']['files'])

    def test_record_command_after_a_one_file_promotion(self):
        path = self.mount('frontend-1', 'erp_frontend_2', 'new rule\n')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(rm.main(['record', '--runtime', str(self.runtime), '--mount', 'erp_frontend_2',
                                      '--commit', self.main[:12], '--repository', str(self.repo)]), 0)
        self.assertIn('same bytes as the file at that commit', out.getvalue())
        record = rm.read_record(self.runtime)['erp_frontend_2']
        self.assertEqual(record, {'source': TEMPLATE, 'commit': self.main,
                                  'sha256': hashlib.sha256(b'new rule\n').hexdigest()})
        if os.name == 'posix':
            self.assertEqual((self.runtime / rm.RECORD).stat().st_mode & 0o777, 0o600)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(rm.main(['record', '--runtime', str(self.runtime), '--mount', 'erp_configurator_1',
                                      '--commit', self.main, '--repository', str(self.repo)]), 1, 'data mount refused')
        self.assertTrue(path.exists())


class RecordAtDeploymentTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, 'geteuid'), 'prepare_runtime runs on the Linux host')
    def test_prepare_runtime_records_every_mount_it_makes_from_the_repository(self):
        from prepare_runtime import prepare
        profile = {'instance': 'isolated', 'tier': 'test', 'domain': 'example.com', 'commit': 'a' * 40,
                   'hosts': {k: 'test-' + k + '.example.com' for k in ['erp', 'sso', 'drive', 'office', 'mail', 'dms', 'respond']},
                   'network': 'isolated-workspace', 'network_subnet': '10.45.0.0/24',
                   'erp_image': 'example/erp:test', 'mail_image': 'example/mail:test', 'projects': ['erp', 'website'],
                   'settings': {'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID': 'office-mail'}}
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'runtime'
            prepare(ROOT, output, profile)
            record = rm.read_record(output)
            self.assertEqual(record['erp_frontend_2']['source'], TEMPLATE)
            self.assertEqual(record['erp_frontend_2']['commit'], 'a' * 40)
            self.assertEqual(record['erp_frontend_2']['sha256'], rm.digest(output / 'mounts/erp_frontend_2'))
            self.assertEqual(record['website_web_0']['sha256'], rm.digest(output / 'mounts/website_web_0'))
            self.assertNotIn('erp_configurator_1', record, 'data folders are not recorded')
            self.assertEqual((output / rm.RECORD).stat().st_mode & 0o777, 0o600)


class SharedTableTests(unittest.TestCase):
    def test_every_repository_mount_has_a_source_that_exists(self):
        mounts = json.loads((ROOT / 'deployment/stacks/mounts.json').read_text())
        sourced = {m['path']: rm.source_of(m) for m in mounts if rm.source_of(m)}
        self.assertEqual(len(sourced), 14, 'six copied files, two proxies, four folders, two editor files')
        for name, relative in sourced.items():
            self.assertTrue((ROOT / relative).exists(), name + ': ' + relative)
        for name in ('erp_configurator_1', 'processing_document_worker_1', 'drive_ocis_1', 'private_dns_private_dns_0'):
            self.assertNotIn(name, sourced, name + ' is data, a secret or operator-owned')

    def test_the_nightly_run_updates_its_own_checkout_to_main_first(self):
        unit = (ROOT / 'deployment/drift-check.service.example').read_text()
        lines = [line for line in unit.splitlines() if line.startswith('ExecStartPre=')]
        self.assertEqual(len(lines), 2)
        self.assertIn('fetch --quiet origin', lines[0])
        self.assertIn('checkout --quiet --detach origin/main', lines[1])
        self.assertLess(unit.index('ExecStartPre='), unit.index('ExecStart=/usr/bin/python3'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
