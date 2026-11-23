"""P61: editor file safety. Parked edits are copied out and never deleted, a stuck document is closed
only on request, failed saves raise an alarm, and the editor's secret never leaves memory.
A fake Docker plays the editor (sample data shaped like the incident of 20 November 2026)."""
import base64
import contextlib
import hashlib
import hmac
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import editor_safety as es  # noqa: E402

es.WAIT = 0
SECRET = 'sample-editor-secret'
OUT_LOG = '/var/log/onlyoffice/documentserver/docservice/out.log'
ERR_LOG = '/var/log/onlyoffice/documentserver/docservice/err.log'
INCIDENT = '\n'.join([
    '[2026-11-20T11:03:55.101] [ERROR] [localhost] [doc-shared-1] [uid-1] nodeJS - wopi PutFile error: statusCode 500',
    '[2026-11-20T11:03:55.300] [INFO] [localhost] [doc-shared-1] [uid-1] nodeJS - storeForgotten',
    '[2026-11-20T11:07:01.000] [ERROR] [localhost] [doc-shared-1] [uid-2] nodeJS - changesError: '
    "Cannot read properties of null (reading 'IU')",
    '[2026-11-20T11:08:00.000] [INFO] [localhost] [doc-other] [uid-3] nodeJS - PutFile success statusCode 200',
]) + '\n'


class FakeDocker:
    def __init__(self, containers=('onlyoffice-abc', 'collaboration-abc', 'ocis-abc', 'db-abc'), forgotten=None,
                 logs=None, used=40, cache_kb=200 * 1024, bridge_log=''):
        self.containers = list(containers)
        self.parked = dict(forgotten if forgotten is not None else {'doc-shared-1': b'PK workbook with edits'})
        self.logs = dict(logs if logs is not None else {OUT_LOG: INCIDENT, ERR_LOG: ''})
        self.used, self.cache_kb, self.bridge_log = used, cache_kb, bridge_log
        self.calls, self.commands = [], []

    def __call__(self, args, data=None):
        self.calls.append((list(args), data))
        if args[:2] == ['docker', 'ps']:
            return '\n'.join(self.containers).encode()
        if args[:2] == ['docker', 'inspect']:
            return json.dumps(['PATH=/usr/bin', 'JWT_SECRET=' + SECRET, 'JWT_HEADER=Authorization']).encode()
        if args[0] == 'sh' and 'docker logs' in args[2]:
            return self.bridge_log.encode()
        if args[:2] == ['docker', 'exec']:
            return self.exec(args[args.index('-i') + 2 if '-i' in args else 3:], data)
        raise AssertionError('unexpected command ' + ' '.join(args))

    def exec(self, inner, data):
        if inner[0] == 'curl' and es.COMMAND_URL in inner:
            header = data.decode()
            assert header.startswith('Authorization: Bearer ') and header.endswith('\n')
            token = header.split()[2]
            body = json.loads(inner[inner.index('--data-binary') + 1])
            head, payload, signature = token.split('.')
            expected = hmac.new(SECRET.encode(), (head + '.' + payload).encode(), hashlib.sha256).digest()
            if base64.urlsafe_b64decode(signature + '==') != expected:
                return json.dumps({'error': 6}).encode()
            assert json.loads(base64.urlsafe_b64decode(payload + '=='))['payload'] == body
            self.commands.append(body)
            return json.dumps(self.answer(body)).encode()
        if inner[0] == 'curl':
            key = unquote(re.search(r'/forgotten/([^/]+)/', inner[-1]).group(1))
            assert inner[-1].startswith('http://localhost/'), inner[-1]
            return self.parked[key]
        if inner[:2] == ['sh', '-c']:
            return str(len(self.logs.get(inner[-1], '').encode())).encode()
        if inner[0] == 'tail':
            return self.logs[inner[-1]].encode()[int(inner[2][1:]) - 1:]
        if inner[0] == 'df':
            rows = ['Filesystem 1024-blocks Used Available Capacity Mounted on']
            rows += ['/dev/sda1 100 %d %d %d%% %s' % (self.used, 100 - self.used, self.used, p) for p in inner[2:]]
            return '\n'.join(rows).encode()
        if inner[0] == 'du':
            return ('%d\t%s' % (self.cache_kb, inner[-1])).encode()
        raise AssertionError('unexpected exec ' + ' '.join(inner))

    def answer(self, body):
        c = body['c']
        if c == 'getForgottenList':
            return {'error': 0, 'keys': list(self.parked)}
        if c == 'getForgotten':
            return {'error': 0, 'key': body['key'],
                    'url': 'https://office.example.com/cache/files/forgotten/%s/output.xlsx/output.xlsx?md5=x&expires=1' % quote(body['key'], safe='')}
        if c == 'info':
            return {'error': 0, 'key': body['key'], 'users': ['uid-1', 'uid-2']}
        if c in ('forcesave', 'drop'):
            return {'error': 0, 'key': body['key']}
        raise AssertionError('command not expected: ' + c)


class EditorSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = {**es.DEFAULTS, 'state_dir': self.tmp.name + '/state', 'recovery_dir': self.tmp.name + '/recovery'}
        self.real_run = es.run

    def tearDown(self):
        es.run = self.real_run
        self.tmp.cleanup()

    def use(self, docker):
        es.run = docker
        return docker

    def editor(self, docker):
        self.use(docker)
        return es.Editor(es.container('onlyoffice-'))

    def test_token_is_signed_wrapped_and_short_lived(self):
        token = es.jwt({'payload': {'c': 'version'}}, SECRET, lifetime=300)
        head, payload, signature = token.split('.')
        self.assertEqual(json.loads(base64.urlsafe_b64decode(head + '==')), {'alg': 'HS256', 'typ': 'JWT'})
        claims = json.loads(base64.urlsafe_b64decode(payload + '=='))
        self.assertEqual(claims['payload'], {'c': 'version'})
        self.assertEqual(claims['exp'] - claims['iat'], 300)
        self.assertEqual(base64.urlsafe_b64decode(signature + '=='),
                         hmac.new(SECRET.encode(), (head + '.' + payload).encode(), hashlib.sha256).digest())

    def test_secret_and_token_never_on_a_command_line_or_in_output(self):
        docker = FakeDocker()
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.use(docker)
            es.watch(self.config)
            es.unstick(es.Editor(es.container('onlyoffice-')), 'doc-shared-1', self.config['recovery_dir'], close=True)
        for args, data in docker.calls:
            self.assertFalse(any(SECRET in a or 'Bearer' in a for a in args), args)
        self.assertNotIn(SECRET, printed.getvalue())
        for path in Path(self.tmp.name).rglob('*'):
            if path.is_file() and path.suffix != '.xlsx':
                self.assertNotIn(SECRET, path.read_text())

    def test_rescue_copies_parked_edits_once_privately_and_deletes_nothing(self):
        docker = FakeDocker(forgotten={'doc-shared-1': b'PK edits one', 'doc/odd key': b'PK edits two'})
        editor = self.editor(docker)
        first = es.rescue(editor, self.config['recovery_dir'])
        self.assertEqual(len(first), 2)
        saved = Path(first[0]['file'])
        self.assertEqual(saved.read_bytes(), b'PK edits one')
        self.assertEqual(saved.suffix, '.xlsx')
        self.assertTrue(saved.parent.name.startswith('doc'))
        self.assertNotIn('/', Path(first[1]['file']).parent.name)
        self.assertEqual(es.rescue(editor, self.config['recovery_dir']), [], 'the same content is not copied twice')
        manifest = (Path(self.config['recovery_dir']) / 'manifest.jsonl').read_text().splitlines()
        self.assertEqual(len(manifest), 2)
        self.assertEqual(json.loads(manifest[0])['sha256'], hashlib.sha256(b'PK edits one').hexdigest())
        self.assertNotIn('deleteForgotten', [c['c'] for c in docker.commands])
        if sys.platform != 'win32':
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(self.config['recovery_dir']).stat().st_mode & 0o777, 0o700)

    def test_unstick_closes_the_document_only_when_asked(self):
        docker = FakeDocker()
        lines = []
        es.unstick(self.editor(docker), 'doc-shared-1', self.config['recovery_dir'], close=False, say=lines.append)
        self.assertEqual([c['c'] for c in docker.commands if c.get('key') == 'doc-shared-1'], ['info', 'forcesave', 'getForgotten'])
        self.assertTrue(any('--yes' in line for line in lines))
        docker.commands.clear()
        es.unstick(es.Editor('onlyoffice-abc'), 'doc-shared-1', self.config['recovery_dir'], close=True, say=lines.append)
        order = [c['c'] for c in docker.commands]
        self.assertLess(order.index('forcesave'), order.index('drop'))
        self.assertLess(order.index('getForgottenList'), order.index('drop'), 'rescue before closing')
        self.assertEqual(order[-2:], ['getForgottenList', 'getForgotten'], 'and again after closing')
        self.assertIn({'c': 'drop', 'key': 'doc-shared-1'}, docker.commands, 'everyone: no user list')

    def test_watch_raises_alarms_for_the_incident_and_names_the_document(self):
        docker = self.use(FakeDocker(bridge_log='{"level":"error","msg":"PutFile failed","status":500}\n'))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = es.watch(self.config)
        self.assertEqual(code, 2)
        status = json.loads((Path(self.config['state_dir']) / 'status.json').read_text())
        self.assertEqual(status['save_failed'], 2, 'one in the editor log, one in the Drive bridge log')
        self.assertEqual(status['apply_failed'], 1)
        self.assertEqual(status['parked'], 1)
        self.assertEqual(status['documents'], ['doc-shared-1'], 'a successful save is not an alarm')
        self.assertEqual(len(status['rescued']), 1)
        self.assertIn('editor-safety ALERT: 2 failed save(s) to Drive', printed.getvalue())
        self.assertIn('documents: doc-shared-1', printed.getvalue())

    def test_watch_reads_only_new_log_lines_and_survives_rotation(self):
        docker = self.use(FakeDocker(forgotten={}))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(es.watch(self.config), 2)
            self.assertEqual(es.watch(self.config), 0, 'same lines are not counted twice')
            docker.logs[OUT_LOG] += '[2026-11-20T12:54:00.000] [ERROR] [localhost] [doc-b] [u] nodeJS - changesError: x\n'
            self.assertEqual(es.watch(self.config), 2)
            docker.logs[OUT_LOG] = '[2026-11-21T00:00:00.000] [INFO] [localhost] [doc-c] [u] nodeJS - started\n'
            self.assertEqual(es.watch(self.config), 0, 'a shorter file (rotated or recreated) is read from the start')
        bridge_calls = [a for a, d in docker.calls if a[0] == 'sh' and 'docker logs' in a[2]]
        self.assertTrue(all(re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', a[4]) for a in bridge_calls))

    def test_disk_and_cache_alarms(self):
        self.use(FakeDocker(forgotten={}, logs={OUT_LOG: '', ERR_LOG: ''}, used=85, cache_kb=3 * 1024 * 1024))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.assertEqual(es.watch(self.config), 2)
        text = printed.getvalue()
        self.assertIn('disk /var/lib/onlyoffice 85% full', text)
        self.assertIn('disk /var/lib/ocis 85% full', text)
        self.assertIn('editor cache 3072 MB', text)

    def test_a_missing_bridge_is_reported_not_fatal(self):
        self.use(FakeDocker(containers=['onlyoffice-abc', 'ocis-abc'], forgotten={}, logs={OUT_LOG: '', ERR_LOG: ''}))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(es.watch(self.config), 1)
        status = json.loads((Path(self.config['state_dir']) / 'status.json').read_text())
        self.assertTrue(status['problems'][0].startswith('Drive editor bridge log'))

    def test_two_matching_editor_containers_are_refused(self):
        self.use(FakeDocker(containers=['onlyoffice-a', 'onlyoffice-b']))
        with self.assertRaises(RuntimeError):
            es.container('onlyoffice-')

    def test_a_wrong_secret_is_reported(self):
        docker = FakeDocker()
        editor = self.editor(docker)
        editor.secret = 'wrong'
        with self.assertRaisesRegex(RuntimeError, 'error 6'):
            es.forgotten(editor)


class InstallTests(unittest.TestCase):
    def test_timer_runs_the_watch_every_five_minutes(self):
        folder = ROOT / 'integrations/onlyoffice'
        service = (folder / 'editor-safety.service.example').read_text()
        timer = (folder / 'editor-safety.timer.example').read_text()
        self.assertIn('tools/editor_safety.py --config /etc/cloud-editor-safety/config.json watch', service)
        self.assertIn('OnUnitActiveSec=5min', timer)
        example = json.loads((folder / 'editor-safety.example.json').read_text())
        self.assertLessEqual(set(example) - {'_comment'}, set(es.DEFAULTS))

    def test_editor_gets_time_to_save_open_documents_when_stopped(self):
        stack = json.loads((ROOT / 'deployment/stacks/editor-onlyoffice.compose.json').read_text())
        grace = stack['services']['onlyoffice'].get('stop_grace_period', '0s')
        self.assertGreaterEqual(int(grace.rstrip('ms')) * (60 if grace.endswith('m') else 1), 300)
        entry = ' '.join(stack['services']['onlyoffice']['entrypoint'])
        self.assertIn('exec /app/ds/run-document-server.sh', entry,
                      "the image's own start script must receive the stop signal (it runs the shutdown save)")


if __name__ == '__main__':
    unittest.main(verbosity=2)
