"""P57: the post-boot check, the crash-loop watch and the rendered systemd files."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import host_check as hc  # noqa: E402
import render_host_checks as rh  # noqa: E402

# The tool logs to the journal; tests capture the lines instead of printing them.
LOG = []
hc.log = LOG.append

BRIDGE = 'collaboration-abc'
STARTED = '2026-11-20T06:00:00.123456789Z'
T0 = hc.parse_started(STARTED)


class FakeEnv:
    """Docker, HTTP, TCP and the clock, scripted per test."""

    def __init__(self, containers=None, http=None, tcp=None, errors_until_restart=0, errors_forever=False,
                 uptime=600, restart_counts=None, status='running', ip_after=0):
        self.t = T0 + uptime
        self.containers = list(containers if containers is not None else [BRIDGE, 'ocis-abc', 'db-abc'])
        self.http_map = http or {}
        self.tcp_map = tcp or {}
        self.errors_forever = errors_forever
        self.errors_now = errors_until_restart
        self.status = status
        self.restarted = []
        self.restart_counts = restart_counts or {}
        self.ip_after, self.ip_calls = ip_after, 0
        self.log = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds

    def http(self, url, timeout=10):
        return self.http_map.get(url, 200)

    def tcp(self, host, port, timeout=5):
        return self.tcp_map.get((host, port), True)

    def run(self, command, timeout=60):
        if command[:2] == ['docker', 'ps'] and '-a' not in command:
            return 0, '\n'.join(self.containers) + '\n'
        if command[:3] == ['docker', 'ps', '-a']:
            return 0, '\n'.join(self.containers) + '\n'
        if command[:2] == ['docker', 'restart']:
            self.restarted.append(command[2])
            if not self.errors_forever:
                self.errors_now = 0
            return 0, ''
        if command[:2] == ['docker', 'inspect']:
            name = command[-1]
            if '{{.State.StartedAt}}' in command[3]:
                started = STARTED if not self.restarted else self._iso(self.t - 200)
                return 0, '%s %s\n' % (self.status, started)
            return 0, '%d running\n' % self.restart_counts.get(name, 0)
        if command[:2] == ['docker', 'logs']:
            return 0, ('{"message":"AddAppProvider failed"}\n' * self.errors_now) if self.errors_now else 'registered\n'
        if command[:2] == ['ip', '-4']:
            self.ip_calls += 1
            return 0, '2: eth0 inet 10.0.0.5/24\n' + ('3: ts0 inet 100.64.0.10/32\n' if self.ip_calls > self.ip_after else '')
        return 1, ''

    @staticmethod
    def _iso(epoch):
        import datetime
        return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.0Z')


def config(**changes):
    value = json.loads(json.dumps(hc.DEFAULTS))
    value.update({'http': [{'name': 'erp', 'url': 'https://erp.example.com/'},
                           {'name': 'office', 'url': 'https://office.example.com/healthcheck', 'ok': [200]}],
                  'containers': ['ocis-', 'db-'], 'tcp': [{'name': 'dns', 'host': '100.64.0.10', 'port': 53}],
                  'state_dir': tempfile.mkdtemp(), 'timeout_seconds': 120, 'interval_seconds': 15})
    value.update(changes)
    return value


class BootCheckTests(unittest.TestCase):
    def test_everything_up_passes_and_writes_status(self):
        cfg = config(); env = FakeEnv()
        self.assertEqual(hc.boot(cfg, env), 0)
        status = json.loads((Path(cfg['state_dir']) / 'status.json').read_text())
        self.assertTrue(status['ok']); self.assertFalse(status['bridge_restarted']); self.assertEqual(env.restarted, [])

    def test_bridge_with_registration_errors_is_restarted_once_and_recovers(self):
        cfg = config(); env = FakeEnv(errors_until_restart=5)
        self.assertEqual(hc.boot(cfg, env), 0)
        self.assertEqual(env.restarted, [BRIDGE])
        self.assertTrue(json.loads((Path(cfg['state_dir']) / 'status.json').read_text())['bridge_restarted'])

    def test_bridge_that_keeps_failing_is_restarted_only_once_then_reported(self):
        cfg = config(); env = FakeEnv(errors_until_restart=5, errors_forever=True)
        self.assertEqual(hc.boot(cfg, env), 1)
        self.assertEqual(env.restarted, [BRIDGE])
        problems = json.loads((Path(cfg['state_dir']) / 'status.json').read_text())['problems']
        self.assertTrue(any('registration errors' in p for p in problems), problems)

    def test_a_down_host_fails_with_a_clear_message_after_the_timeout(self):
        cfg = config(timeout_seconds=60); env = FakeEnv(http={'https://erp.example.com/': 502})
        self.assertEqual(hc.boot(cfg, env), 1)
        problems = json.loads((Path(cfg['state_dir']) / 'status.json').read_text())['problems']
        self.assertIn('erp answers 502 (https://erp.example.com/)', problems)
        self.assertTrue(any(line.startswith('BOOT CHECK FAILED: ') and 'erp answers 502' in line for line in LOG))

    def test_host_that_comes_up_during_the_wait_passes(self):
        cfg = config(); env = FakeEnv(); answers = iter([None, None, 200, 200, 200, 200])
        env.http = lambda url, timeout=10: next(answers) if 'erp' in url else 200
        self.assertEqual(hc.boot(cfg, env), 0)

    def test_missing_container_and_closed_port_are_reported(self):
        cfg = config(timeout_seconds=30)
        env = FakeEnv(containers=[BRIDGE, 'ocis-abc'], tcp={('100.64.0.10', 53): False})
        self.assertEqual(hc.boot(cfg, env), 1)
        problems = ' | '.join(json.loads((Path(cfg['state_dir']) / 'status.json').read_text())['problems'])
        self.assertIn('db-* is not running', problems); self.assertIn('dns is not listening on 100.64.0.10:53', problems)

    def test_docker_not_answering_is_a_failure_not_a_crash(self):
        cfg = config(timeout_seconds=30); env = FakeEnv()
        env.run = lambda command, timeout=60: (1, 'Cannot connect')
        self.assertEqual(hc.boot(cfg, env), 1)

    def test_bridge_check_can_be_switched_off_for_hosts_without_drive(self):
        cfg = config(check_bridge=False); env = FakeEnv(containers=['ocis-abc', 'db-abc'])
        self.assertEqual(hc.boot(cfg, env), 0)


class WatchTests(unittest.TestCase):
    def test_rising_restart_count_raises_an_alert_and_quiet_hosts_do_not(self):
        cfg = config(); state = Path(cfg['state_dir']) / 'restart-counts.json'
        env = FakeEnv(restart_counts={BRIDGE: 10, 'ocis-abc': 0, 'db-abc': 0})
        self.assertEqual(hc.watch(cfg, env), 0)          # first run only records
        env = FakeEnv(restart_counts={BRIDGE: 14, 'ocis-abc': 0, 'db-abc': 1})
        self.assertEqual(hc.watch(cfg, env), 1)
        alerts = json.loads((Path(cfg['state_dir']) / 'restart-alerts.json').read_text())['alerts']
        self.assertEqual(len(alerts), 1); self.assertIn(BRIDGE, alerts[0])
        self.assertTrue(state.exists())

    def test_ignored_prefixes_are_skipped(self):
        cfg = config(watch={'restart_increase': 3, 'ignore_prefixes': ['db-']})
        hc.watch(cfg, FakeEnv(restart_counts={'db-abc': 0}))
        self.assertEqual(hc.watch(cfg, FakeEnv(restart_counts={'db-abc': 50})), 0)


class TailnetWaitTests(unittest.TestCase):
    def test_waits_until_the_address_exists(self):
        env = FakeEnv(ip_after=3); self.assertEqual(hc.wait_tailnet(config(tailnet_ip='100.64.0.10'), env, 60), 0)
        self.assertGreaterEqual(env.ip_calls, 4)

    def test_gives_up_without_failing_boot(self):
        env = FakeEnv(ip_after=10 ** 6)
        self.assertEqual(hc.wait_tailnet(config(tailnet_ip='100.64.0.10'), env, 6), 0)

    def test_does_nothing_without_a_tailnet_address(self):
        self.assertEqual(hc.wait_tailnet(config(), FakeEnv(), 60), 0)


class RenderTests(unittest.TestCase):
    PROFILE = {'domain': 'example.com', 'projects': ['drive', 'erp'],
               'hosts': {k: k + '.example.com' for k in ['erp', 'sso', 'drive', 'office', 'mail', 'dms']},
               'host_checks': {'containers': ['ocis-', 'collaboration-'], 'tailnet_ip': '100.64.0.10',
                               'tcp': [{'name': 'private-dns', 'host': '100.64.0.10', 'port': 53}]}}

    def test_rendered_files(self):
        with tempfile.TemporaryDirectory() as temp:
            names = rh.render(self.PROFILE, temp)
            self.assertIn('docker.service.d/10-after-tailscale.conf', names)
            cfg = json.loads((Path(temp) / 'config.json').read_text())
            self.assertEqual({c['name'] for c in cfg['http']}, {'erp', 'sso', 'drive', 'mail', 'dms', 'office'})
            self.assertEqual([c for c in cfg['http'] if c['name'] == 'office'][0]['url'], 'https://office.example.com/healthcheck')
            dropin = (Path(temp) / 'docker.service.d/10-after-tailscale.conf').read_text()
            self.assertIn('Wants=tailscaled.service', dropin); self.assertIn('After=tailscaled.service', dropin)
            self.assertIn('wait-tailnet', dropin); self.assertIn('ExecStartPre=-', dropin)   # never blocks boot
            boot = (Path(temp) / 'cloud-boot-check.service').read_text()
            self.assertIn('After=docker.service tailscaled.service', boot); self.assertIn('Type=oneshot', boot)
            self.assertIn('WantedBy=multi-user.target', boot)
            self.assertIn('OnUnitActiveSec=5min', (Path(temp) / 'cloud-restart-watch.timer').read_text())

    def test_bad_input_is_rejected(self):
        for bad in [dict(self.PROFILE, hosts={'erp': 'evil host; rm'}),
                    dict(self.PROFILE, host_checks={'tailnet_ip': '1.2.3.4; x'}),
                    dict(self.PROFILE, host_checks={'tcp': [{'host': 'a b', 'port': '5'}]})]:
            with self.assertRaises(ValueError), tempfile.TemporaryDirectory() as temp:
                rh.render(bad, temp)

    def test_repository_sources_carry_no_real_hosts_or_addresses(self):
        for path in ['tools/host_check.py', 'tools/render_host_checks.py']:
            text = (ROOT / path).read_text()
            self.assertNotRegex(text, r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', path)
            self.assertIsNone(re.search(r'[A-Za-z0-9-]+\.(in|com|net|org)\b', text.replace('example.com', '')), path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
