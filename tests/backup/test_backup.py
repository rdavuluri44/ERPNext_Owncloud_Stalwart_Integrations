"""P02 backups: secrets never on the command line, bounded stops always
restarted, consistent ordering, pinned images, restore drill restores locally."""
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'integrations/backup'))
import backup  # noqa: E402
import restore_drill  # noqa: E402

IMAGE = 'restic/restic@sha256:' + 'a' * 64


def profile(tmp):
    return {'tier': 'production', 'restic_image': IMAGE, 'repository': 's3:http://100.64.0.1:30292/b/production',
            'password_file': '/root/secret-password', 's3_credentials_file': '/root/s3.env',
            'staging': str(Path(tmp) / 'staging'), 'state': str(Path(tmp) / 'state'),
            'databases': [{'name': 'erp', 'kind': 'mariadb', 'container': 'db-1'},
                          {'name': 'dms', 'kind': 'postgres', 'container': 'pg-1'}],
            'stop_and_copy': [{'name': 'mail', 'containers': ['mail-1'], 'paths': [str(Path(tmp) / 'maildata')]}],
            'paths': ['/opt/company'], 'exclude': ['/opt/company/cache']}


class Recorder:
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on

    def __call__(self, argv, **kw):
        self.calls.append(argv)
        if self.fail_on and self.fail_on in argv: raise subprocess.CalledProcessError(1, argv)
        if argv[:2] == ['cp', '-a']: Path(argv[-1]).mkdir(parents=True, exist_ok=True)
        return types.SimpleNamespace(returncode=0)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.p = profile(self.tmp.name)
        (Path(self.tmp.name) / 'maildata').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_validation(self):
        backup.validate(self.p)
        for bad in [dict(self.p, restic_image='restic/restic:latest'), dict(self.p, repository='/local'),
                    dict(self.p, paths=['relative']), dict(self.p, paths=['/']), dict(self.p, tier='dev'),
                    dict(self.p, retention={'daily': 0, 'weekly': 4, 'monthly': 6}),
                    dict(self.p, repository='/srv/restic')]:  # local only on test
            with self.assertRaises(ValueError): backup.validate(bad)

    def test_local_repository_only_on_test_hosts(self):
        p = dict(self.p, tier='test', repository='/srv/restic-test', s3_credentials_file='')
        backup.validate(p)
        argv = backup.restic(p, ['snapshots'])
        self.assertIn('/srv/restic-test:/srv/restic-test', argv)
        self.assertNotIn('--env-file', argv)
        with self.assertRaises(ValueError): backup.validate(dict(p, repository='/'))
        with self.assertRaises(ValueError): backup.validate(dict(p, repository='/srv/../etc'))

    def test_secrets_only_as_files_and_sources_read_only(self):
        argv = backup.restic(self.p, ['backup', '/backup'], backup.mounts_for(self.p))
        joined = ' '.join(argv)
        self.assertIn('RESTIC_PASSWORD_FILE=/run/secrets/restic-password', joined)
        self.assertIn('/root/secret-password:/run/secrets/restic-password:ro', joined)
        self.assertNotIn('RESTIC_PASSWORD=', joined.replace('RESTIC_PASSWORD_FILE=', ''))
        self.assertIn('/opt/company:/backup/opt/company:ro', joined)
        self.assertEqual(argv[argv.index('--env-file') + 1], '/root/s3.env')

    def test_order_dumps_then_brief_stop_then_upload_then_retention(self):
        rec = Recorder()
        report = backup.run_backup(self.p, run=rec)
        kinds = [('dump' if c[:2] == ['docker', 'exec'] else 'stop' if c[:2] == ['docker', 'stop'] else
                  'start' if c[:2] == ['docker', 'start'] else 'copy' if c[0] == 'cp' else
                  'backup' if 'backup' in c and IMAGE in c else 'forget' if 'forget' in c else '?') for c in rec.calls]
        self.assertEqual(kinds, ['dump', 'dump', 'stop', 'copy', 'start', 'backup', 'forget'])
        self.assertEqual(report['result'], 'succeeded')
        self.assertFalse(Path(self.p['staging']).exists(), 'staging removed')
        self.assertIn('--exclude', rec.calls[5]); self.assertIn('/backup/opt/company/cache', rec.calls[5])

    def test_stopped_containers_restart_even_if_copy_fails(self):
        rec = Recorder(fail_on='--reflink=auto')
        with self.assertRaises(subprocess.CalledProcessError):
            backup.run_backup(self.p, run=rec)
        self.assertEqual(rec.calls[-1][:2], ['docker', 'start'])
        state = (Path(self.p['state']) / 'last-run.json').read_text()
        self.assertIn('failed', state)

    def test_drive_starts_before_its_editor_bridge_and_waits_for_health(self):
        """P80: the bridge registers with Drive at start, so it must not race Drive's own start."""
        answers = {'ocis-1': iter(['starting', 'starting', 'healthy'])}
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            if argv[:2] == ['docker', 'inspect']:
                return types.SimpleNamespace(returncode=0, stdout=next(answers[argv[-1]]) + '\n')
            return types.SimpleNamespace(returncode=0, stdout='')
        clock = iter(range(0, 1000, 2))
        backup.start_in_order(['ocis-1', 'collaboration-1'], run=run, clock=lambda: next(clock), sleep=lambda s: None)
        self.assertEqual([c[:2] + c[-1:] for c in calls],
                         [['docker', 'start', 'ocis-1'], ['docker', 'inspect', 'ocis-1'], ['docker', 'inspect', 'ocis-1'],
                          ['docker', 'inspect', 'ocis-1'], ['docker', 'start', 'collaboration-1']])

    def test_a_wait_that_times_out_or_a_failed_start_still_starts_everything(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            if argv[:2] == ['docker', 'start'] and argv[-1] == 'a':
                raise subprocess.CalledProcessError(1, argv)
            return types.SimpleNamespace(returncode=0, stdout='unhealthy\n')
        clock = iter(range(0, 10000, 30))
        with self.assertRaises(subprocess.CalledProcessError):
            backup.start_in_order(['a', 'b', 'c'], run=run, clock=lambda: next(clock), sleep=lambda s: None, wait=60)
        self.assertEqual([c[-1] for c in calls if c[:2] == ['docker', 'start']], ['a', 'b', 'c'])

    def test_start_wait_is_validated(self):
        group = self.p['stop_and_copy'][0]
        for bad in ['60', -1, 601, True]:
            with self.assertRaises(ValueError):
                backup.validate(dict(self.p, stop_and_copy=[dict(group, start_wait_seconds=bad)]))
        backup.validate(dict(self.p, stop_and_copy=[dict(group, start_wait_seconds=0)]))

    def test_dumps_are_consistent_online_snapshots(self):
        maria = ' '.join(backup.dump_command({'kind': 'mariadb', 'container': 'db'}))
        self.assertIn('--single-transaction', maria); self.assertIn('--all-databases', maria)
        self.assertIn('pg_dumpall', ' '.join(backup.dump_command({'kind': 'postgres', 'container': 'pg'})))

    def test_drill_restores_into_scratch_without_lock_and_network_less_db(self):
        p = dict(self.p, tier='test', scratch='/tmp/drill')
        argv = restore_drill._restore_argv(p, Path('/tmp/drill'))
        self.assertIn('/tmp/drill:/restore', argv); self.assertIn('--no-lock', argv)
        self.assertLess(argv.index('/tmp/drill:/restore'), argv.index(IMAGE))
        db = restore_drill.throwaway('mariadb', 'mariadb@sha256:' + 'b' * 64, 'x', 'pw')
        self.assertEqual(db[db.index('--network') + 1], 'none')


class SnapshotGuardTests(unittest.TestCase):
    """The guard removes only its own oldest snapshots and keeps at least 7."""
    def test_guard_prunes_only_its_own_snapshots(self):
        import os, subprocess
        script = ROOT / 'integrations/backup/zfs-snapshot-guard.sh'
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / 'log'
            snaps = ['pool/s3@other-1'] + ['pool/s3@backup-guard-2026-01-%02d_0500' % d for d in range(1, 11)]
            fake = Path(tmp) / 'zfs'
            fake.write_text('#!/bin/sh\necho "$@" >> %s\nif [ "$1" = list ] && [ "$3" = "-t" ]; then printf "%%s\\n" %s; fi\n'
                            % (log, ' '.join(snaps)))
            fake.chmod(0o755)
            env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'])
            subprocess.run(['sh', str(script), 'pool/s3', '8'], check=True, env=env)
            calls = log.read_text().splitlines()
            destroyed = [c.split()[1] for c in calls if c.startswith('destroy')]
            self.assertEqual(destroyed, ['pool/s3@backup-guard-2026-01-01_0500', 'pool/s3@backup-guard-2026-01-02_0500'])
            self.assertTrue(any(c.startswith('snapshot pool/s3@backup-guard-') for c in calls))
            self.assertNotIn('destroy pool/s3@other-1', calls)
            bad = subprocess.run(['sh', str(script), 'pool/s3', '3'], env=env, capture_output=True)
            self.assertNotEqual(bad.returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
