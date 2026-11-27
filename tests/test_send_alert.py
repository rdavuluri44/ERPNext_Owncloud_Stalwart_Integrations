"""P72, P53: the alert sender every check uses. The ERP endpoint, the network and mail are faked; the wrapped checks
are small local Python commands."""
import contextlib
import io
import json
import socket
import ssl
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import send_alert as sa  # noqa: E402

TOKEN = 'secret-token-for-tests'
SENT, MAILS = [], []


class FakeConnection:
    """Records each POST; `status` or `error` decide the answer."""
    status, error = 200, None

    def __init__(self, host, address, port, timeout):
        self.target = (host, address, port, timeout)

    def request(self, method, path, body, headers):
        SENT.append({'method': method, 'path': path, 'body': json.loads(body), 'headers': headers, 'target': self.target})

    def getresponse(self):
        if FakeConnection.error:
            raise FakeConnection.error
        return types.SimpleNamespace(status=FakeConnection.status, read=lambda: b'{}')

    def close(self):
        pass


class FakeEnvironment:
    def send_mail(self, alert, subject, body):
        MAILS.append({'alert': alert, 'subject': subject, 'body': body})


sa.host_check.Environment = FakeEnvironment


class SenderTests(unittest.TestCase):
    def setUp(self):
        SENT.clear()
        MAILS.clear()
        FakeConnection.status, FakeConnection.error = 200, None
        self.dir = tempfile.TemporaryDirectory()
        base = Path(self.dir.name)
        (base / 'token').write_text(TOKEN + '\n')
        (base / 'host-checks.json').write_text(json.dumps({'alert': {
            'smtp_host': 'mail.example.com', 'smtp_port': 465, 'security': 'ssl', 'username': 'alerts@example.com',
            'password_file': str(base / 'mail-password'), 'sender': 'alerts@example.com', 'to': ['admin@example.com']}}))
        self.config = base / 'config.json'
        self.config.write_text(json.dumps({
            'url': 'https://erp.example.com/api/method/erpnext_drive_integrations.admin_alerts.api.report',
            'source': 'web', 'token_file': str(base / 'token'), 'host': 'web-1', 'address': '100.64.0.5',
            'fallback_mail': str(base / 'host-checks.json')}))

    def tearDown(self):
        self.dir.cleanup()

    def main(self, *argv):
        out, err, notes = io.BytesIO(), io.BytesIO(), io.StringIO()
        with contextlib.redirect_stderr(notes), contextlib.redirect_stdout(io.StringIO()) as printed:
            code = sa.main(['--config', str(self.config), *argv], FakeConnection, out, err)
        everything = out.getvalue().decode() + err.getvalue().decode() + notes.getvalue() + printed.getvalue()
        self.assertNotIn(TOKEN, everything)
        return code, out.getvalue().decode(), err.getvalue().decode(), notes.getvalue()

    def check(self, script):
        return ['--', sys.executable, '-c', script]

    def test_send_posts_json_with_the_token_header_to_the_address(self):
        code, *_ = self.main('send', '--key', 'disk', '--severity', 'warning', '--title', 'Disk 85%', '--detail', 'sda1')
        self.assertEqual(code, 0)
        sent = SENT[0]
        self.assertEqual((sent['method'], sent['path']), ('POST', '/api/method/erpnext_drive_integrations.admin_alerts.api.report'))
        self.assertEqual(sent['headers']['X-Alert-Token'], TOKEN)
        self.assertNotIn('Authorization', sent['headers'])
        self.assertEqual(sent['body'], {'source': 'web', 'key': 'disk', 'severity': 'warning', 'state': 'open',
                                        'title': 'Disk 85%', 'detail': 'sda1', 'host': 'web-1'})
        self.assertEqual(sent['target'], ('erp.example.com', '100.64.0.5', 443, 10.0))

    def test_run_success_resolves_and_passes_output_and_exit_code_through(self):
        code, out, err, _ = self.main('run', '--key', 'boot', '--title', 'Boot check',
                                      *self.check('import sys; print("all fine"); print("note", file=sys.stderr)'))
        self.assertEqual((code, out, err), (0, 'all fine\n', 'note\n'))
        self.assertEqual(SENT[0]['body']['state'], 'resolved')
        self.assertEqual(SENT[0]['body']['key'], 'boot')

    def test_run_failure_opens_with_the_marked_lines(self):
        script = ('print("checking"); print("2026-11-27 06:00:01 DOWN erp: HTTP 502"); print("ok mail");'
                  'print("FAIL backup: no snapshot"); raise SystemExit(1)')
        code, out, _, _ = self.main('run', '--key', 'boot', '--title', 'Boot check', *self.check(script))
        self.assertEqual(code, 1)
        self.assertIn('ok mail', out)
        body = SENT[0]['body']
        self.assertEqual((body['state'], body['severity']), ('open', 'critical'))
        self.assertEqual(body['detail'], '2026-11-27 06:00:01 DOWN erp: HTTP 502\nFAIL backup: no snapshot')

    def test_run_failure_without_marked_lines_sends_the_last_ten(self):
        code, *_ = self.main('run', '--key', 'k', '--title', 'T',
                             *self.check('[print("line", i) for i in range(15)]; raise SystemExit(3)'))
        self.assertEqual(code, 3)
        self.assertEqual(SENT[0]['body']['detail'].splitlines(), [f'line {i}' for i in range(5, 15)])

    def test_warn_exit_codes_map_to_warning(self):
        code, *_ = self.main('run', '--key', 'k', '--title', 'T', '--warn-exit', '2', '4',
                             *self.check('raise SystemExit(4)'))
        self.assertEqual((code, SENT[0]['body']['severity']), (4, 'warning'))
        code, *_ = self.main('run', '--key', 'k', '--title', 'T', '--warn-exit', '2', *self.check('raise SystemExit(5)'))
        self.assertEqual((code, SENT[1]['body']['severity']), (5, 'critical'))

    def test_detail_lines_and_length_are_capped(self):
        script = '[print("ERROR " + "x" * 300) for i in range(30)]; raise SystemExit(1)'
        self.main('run', '--key', 'k', '--title', 'T' * 200, *self.check(script))
        body = SENT[0]['body']
        self.assertEqual(len(body['title']), 140)
        self.assertLessEqual(len(body['detail']), 2000)
        self.assertTrue(all(len(line) <= 200 for line in body['detail'].splitlines()))

    def test_unreachable_inbox_mails_a_critical_alert_directly(self):
        FakeConnection.error = socket.timeout('timed out')
        code, _, _, notes = self.main('send', '--key', 'erp', '--severity', 'critical', '--title', 'ERP down')
        self.assertEqual(code, 0)
        self.assertEqual(MAILS[0]['subject'], '[Alert, ERP unreachable] ERP down')
        self.assertEqual(MAILS[0]['alert']['smtp_host'], 'mail.example.com')
        self.assertIn('mailed the alert directly', notes)
        FakeConnection.error, FakeConnection.status = None, 502
        self.assertEqual(self.main('send', '--key', 'erp', '--severity', 'critical', '--title', 'ERP down')[0], 0)
        self.assertEqual(len(MAILS), 2)

    def test_no_fallback_for_warnings_resolves_or_refusals(self):
        FakeConnection.error = ConnectionRefusedError()
        self.assertEqual(self.main('send', '--key', 'k', '--severity', 'warning', '--title', 'T')[0], 1)
        self.assertEqual(self.main('send', '--key', 'k', '--severity', 'critical', '--title', 'T', '--resolved')[0], 1)
        code, *_ = self.main('run', '--key', 'k', '--title', 'T', *self.check('pass'))
        self.assertEqual(code, 0)  # a resolve that cannot be delivered does not change the check's result
        FakeConnection.error, FakeConnection.status = None, 403
        self.assertEqual(self.main('send', '--key', 'k', '--severity', 'critical', '--title', 'T')[0], 1)
        self.assertEqual(MAILS, [])

    def test_failed_fallback_still_reports_and_keeps_the_exit_code(self):
        FakeConnection.error = OSError('no route')
        original = FakeEnvironment.send_mail
        FakeEnvironment.send_mail = lambda self, alert, subject, body: (_ for _ in ()).throw(OSError('smtp down'))
        try:
            code, _, _, notes = self.main('run', '--key', 'k', '--title', 'T', *self.check('raise SystemExit(2)'))
        finally:
            FakeEnvironment.send_mail = original
        self.assertEqual(code, 2)
        self.assertIn('fallback mail failed', notes)


class AddressConnectionTests(unittest.TestCase):
    def test_connects_to_the_address_and_verifies_the_url_host(self):
        calls = {}

        class Context:
            verify_mode, check_hostname = ssl.CERT_REQUIRED, True

            def wrap_socket(self, raw, server_hostname):
                calls['wrap'] = (raw, server_hostname)
                return 'tls'

        original = sa.socket.create_connection
        sa.socket.create_connection = lambda address, timeout, source=None: calls.setdefault('connect', address) and 'raw'
        try:
            conn = sa.AddressHTTPSConnection('erp.example.com', '100.64.0.5', 443, timeout=5, context=Context())
            conn.connect()
        finally:
            sa.socket.create_connection = original
        self.assertEqual(calls['connect'], ('100.64.0.5', 443))
        self.assertEqual(calls['wrap'], ('raw', 'erp.example.com'))
        self.assertEqual(conn.sock, 'tls')

    def test_default_context_verifies_certificates(self):
        conn = sa.AddressHTTPSConnection('erp.example.com', '100.64.0.5', 443, timeout=5)
        self.assertEqual(conn.context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(conn.context.check_hostname)

    def test_config_must_use_https(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as handle:
            json.dump({'url': 'http://erp.example.com/x', 'source': 's', 'token_file': '/nonexistent'}, handle)
        with self.assertRaises(ValueError):
            sa.load_config(handle.name)
        Path(handle.name).unlink()


if __name__ == '__main__':
    unittest.main()
