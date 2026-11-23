"""P62: the upstream watch reads the pins, asks public sources (sample answers here, no network) and only
writes digests into its output folder. It never upgrades anything."""
import contextlib
import datetime
import io
import json
import re
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import upstream_watch as uw  # noqa: E402

uw.NVD_DELAY = 0
DIGEST = 'sha256:' + 'a' * 64
TOKEN = 'sample-token-value'
TODAY = datetime.date(2026, 11, 23)  # a Monday


def sample_source(root):
    """A minimal checkout: one ERP app, the mail pin, the build lock, one stack image, one host component."""
    def write(path, value):
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(value if isinstance(value, str) else json.dumps(value))
    write('deployment/upstream-lock.json', {
        'frappe': {'url': 'https://github.com/frappe/frappe.git', 'ref': 'v16.1.0', 'commit': 'f' * 40},
        'payments': {'url': 'https://github.com/example/payments.git', 'ref': 'develop', 'commit': 'c' * 40}})
    write('integrations/mail/upstream.json', {'repository': 'https://github.com/example/webmail', 'commit': 'e' * 40,
                                              'version': '1.2.0'})
    write('deployment/build-lock.json', {'frappe_docker': {'url': 'https://github.com/frappe/frappe_docker.git',
                                                           'commit': 'd' * 40}, 'bench_version': '5.0.0',
                                         'node_version': '24.1.0', 'python_image': 'python@' + DIGEST})
    write('deployment/native-clients-lock.json', {'repository': 'https://github.com/example/konnectd', 'commit': 'b' * 40})
    write('deployment/stacks/db.compose.json', {'services': {'db': {'image': 'postgres@' + DIGEST}}})
    write('integrations/mail/overlay/Dockerfile', 'FROM node:24-alpine@' + DIGEST + ' AS builder\n')
    write('deployment/upstream-watch.json', {
        'images': {'postgres@' + DIGEST: '16.2', 'python@' + DIGEST: '3.13.1', 'node@' + DIGEST: '24.1.0'},
        'sources': {
            'frappe': {'osv': {'ecosystem': 'PyPI', 'name': 'frappe'}, 'exposure': 'public',
                       'workaround': 'integrations/example/'},
            'bulwark-webmail': {'exposure': 'public'}, 'frappe_docker': {'branch': 'main', 'exposure': 'build'},
            'frappe-bench': {'exposure': 'build'}, 'node-build': {'exposure': 'build'},
            'ocis-konnectd': {'branch': 'master', 'exposure': 'build'},
            'postgres': {'name': 'PostgreSQL', 'endoflife': 'postgresql', 'nvd': 'cpe:2.3:a:postgresql:postgresql',
                         'exposure': 'internal'},
            'python': {'name': 'Python', 'exposure': 'internal'}, 'node': {'name': 'Node.js', 'exposure': 'build'},
            'coolify': {'name': 'Coolify', 'host': True, 'github': 'coollabsio/coolify', 'exposure': 'tailnet'},
            'ubuntu': {'name': 'Ubuntu', 'host': True, 'exposure': 'public'}}})


def answers(extra_release=False):
    """Public answers keyed by URL fragment, in the shape each source publishes."""
    releases = [{'tag_name': 'v16.2.0', 'html_url': 'https://github.com/frappe/frappe/releases/tag/v16.2.0',
                 'body': 'Security fix for CVE-2026-0001. Breaking: renamed hook.'},
                {'tag_name': 'v16.3.0-rc.1', 'prerelease': True, 'body': ''},
                {'tag_name': 'v17.0.0', 'html_url': 'https://github.com/frappe/frappe/releases/tag/v17.0.0', 'body': ''},
                {'tag_name': 'v15.9.0', 'body': ''}]
    if extra_release:
        releases.insert(0, {'tag_name': 'v16.2.1', 'html_url': 'u', 'body': ''})
    return {
        'known_exploited_vulnerabilities': {'vulnerabilities': [{'cveID': 'CVE-2026-0001'}]},
        '/repos/frappe/frappe/releases': releases,
        '/repos/frappe/frappe/security-advisories': [
            {'ghsa_id': 'GHSA-crit-0001-aaaa', 'cve_id': 'CVE-2026-0001', 'summary': 'Remote code\nexecution <b>',
             'severity': 'critical', 'html_url': 'https://github.com/advisories/GHSA-crit-0001-aaaa',
             'vulnerabilities': [{'vulnerable_version_range': '>= 16.0.0, < 16.1.5', 'patched_versions': '16.1.5'}]},
            {'ghsa_id': 'GHSA-old0-0002-bbbb', 'severity': 'high', 'summary': 'Old flaw',
             'vulnerabilities': [{'vulnerable_version_range': '< 16.0.5', 'patched_versions': '16.0.5'}]},
            {'ghsa_id': 'GHSA-odd0-0003-cccc', 'severity': 'moderate', 'summary': 'Range we cannot read',
             'vulnerabilities': [{'vulnerable_version_range': 'all before the spring release', 'patched_versions': ''}]},
            {'ghsa_id': 'GHSA-past-0004-dddd', 'severity': 'high', 'summary': 'Fixed in an older line only',
             'vulnerabilities': [{'vulnerable_version_range': 'unreadable', 'patched_versions': '15.2.0'}]},
            {'ghsa_id': 'GHSA-open-0007-ffff', 'severity': 'high', 'summary': 'Range without an upper end',
             'vulnerabilities': [{'vulnerable_version_range': '>=16.0.0', 'patched_versions': '16.0.9'}]},
            {'ghsa_id': 'GHSA-unfx-0008-gggg', 'severity': 'medium', 'summary': 'Open range and no fix yet',
             'vulnerabilities': [{'vulnerable_version_range': '>= 15.0.0', 'patched_versions': ''}]},
            {'ghsa_id': 'GHSA-gone-0005-eeee', 'severity': 'critical', 'withdrawn_at': '2026-01-01', 'summary': 'x',
             'vulnerabilities': [{'vulnerable_version_range': '< 99'}]}],
        'api.osv.dev': {'vulns': [
            {'id': 'GHSA-crit-0001-aaaa', 'aliases': ['CVE-2026-0001'], 'summary': 'duplicate of the GitHub advisory',
             'affected': [{'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '0'}, {'fixed': '16.1.5'}]}]}]},
            {'id': 'PYSEC-2026-7', 'summary': 'Only in OSV', 'database_specific': {'severity': 'LOW'},
             'affected': [{'ranges': [{'type': 'ECOSYSTEM', 'events': [{'introduced': '16.0.0'}, {'fixed': '16.4.0'}]}]}]},
            {'id': 'GHSA-loose-0006', 'summary': 'OSV matched loosely; its ranges say fixed long ago',
             'affected': [{'ranges': [{'type': 'SEMVER', 'events': [{'introduced': '1.0.0'}, {'fixed': '12.0.0'}]}]}]}]},
        '/repos/example/payments/compare/': {'ahead_by': 4, 'html_url': 'https://github.com/example/payments/compare'},
        '/repos/frappe/frappe_docker/compare/': {'ahead_by': 0},
        '/repos/example/konnectd/compare/': {'ahead_by': 0},
        '/repos/example/webmail/releases': [{'tag_name': 'v1.2.0', 'body': ''}],
        '/repos/coollabsio/coolify/releases': [],
        '/repos/coollabsio/coolify/git/matching-refs/tags': [{'ref': 'refs/tags/v4.0.1'}, {'ref': 'refs/tags/v4.1.0-beta.2'}],
        '/security-advisories': [],
        'endoflife.date/api/postgresql.json': [
            {'cycle': '18', 'latest': '18.1', 'eol': '2030-11-14'},
            {'cycle': '16', 'latest': '16.3', 'eol': '2026-12-01'}],
        'services.nvd.nist.gov': {'vulnerabilities': [{'cve': {
            'id': 'CVE-2026-0100', 'descriptions': [{'lang': 'en', 'value': 'Database flaw'}],
            'metrics': {'cvssMetricV31': [{'cvssData': {'baseSeverity': 'MEDIUM'}}]},
            'configurations': [{'nodes': [{'cpeMatch': [{'vulnerable': True, 'versionEndExcluding': '16.3',
                                                         'criteria': 'cpe:2.3:a:postgresql:postgresql:*'}]}]}]}}]},
        '/repos/': {'license': {'spdx_id': 'MIT'}},
    }


class FakeHTTP:
    def __init__(self, routes, fail=()):
        self.routes, self.fail, self.calls = routes, fail, []

    def __call__(self, url, data=None, headers=None):
        self.calls.append((url, data, headers or {}))
        for fragment in self.fail:
            if fragment in url:
                raise urllib.error.URLError('connection refused')
        if data and 'commit' in data:
            return {}  # OSV knows nothing about the sample branch commits
        for fragment, value in self.routes.items():  # first matching fragment wins
            if fragment in url:
                return json.loads(json.dumps(value))
        raise AssertionError('unexpected request ' + url)


class UpstreamWatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / 'checkout'
        self.out = Path(self.tmp.name) / 'watch'
        sample_source(self.source)
        self.profile = {'versions': {'coolify': '4.0.0'}}
        self.real_fetch = uw.fetch

    def tearDown(self):
        uw.fetch = self.real_fetch
        self.tmp.cleanup()

    def run_watch(self, http, today=TODAY, profile=None, **kw):
        uw.fetch = http
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = uw.run(self.source, self.out, profile or self.profile, today=today, **kw)
        return code, printed.getvalue()

    def test_versions_compare_and_ranges_are_read(self):
        self.assertGreater(uw.vkey('version/2026.8.6'), uw.vkey('2026.8.5'))
        self.assertEqual(uw.vkey('v1.1'), uw.vkey('1.1.0'))
        self.assertEqual(uw.line(uw.vkey('2026.8.5')), uw.line(uw.vkey('2026.8.6')))
        self.assertNotEqual(uw.line(uw.vkey('16.9')), uw.line(uw.vkey('17.0')))
        self.assertNotEqual(uw.line(uw.vkey('0.15.4')), uw.line(uw.vkey('0.16.0')))
        cases = [('1.3.0', '>= 1.2.0, < 1.4.1', True), ('1.4.1', '>= 1.2.0, < 1.4.1', False),
                 ('1.21.2', '<= 1.21.1', False), ('3.1.0', '3.0–3.3.2', True), ('3.4.0', '3.0 - 3.3.2', False),
                 ('0.15.4', '0.15.4', True), ('0.15.5', '0.15.4', False), ('v16.55.0', '< 16.37.0', False),
                 ('1.0', 'every version', None), ('1.0', '', None), (None, '< 2', None)]
        for version, text, expected in cases:
            self.assertIs(uw.in_range(version, text), expected, (version, text))
        self.assertIs(uw.by_fix('16.56.0', ['15.127.1', '16.60.1']), True)
        self.assertIs(uw.by_fix('1.21.2', ['1.10.0']), False)
        self.assertIs(uw.by_fix('3.4.2', ['v2.20.11']), False)
        self.assertIsNone(uw.by_fix('8.40.0', ['9.4.0']))

    def test_baseline_lists_findings_with_advice_and_writes_only_its_folder(self):
        http = FakeHTTP(answers())
        code, printed = self.run_watch(http)
        self.assertEqual(code, 2, 'an exploited critical flaw on a public component is urgent')
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ['2026-11-23-baseline.md', 'state.json', 'status.json'])
        self.assertEqual(sorted(p.relative_to(self.source).as_posix() for p in self.source.rglob('*') if p.is_file()),
                         sorted(['deployment/upstream-lock.json', 'integrations/mail/upstream.json',
                                 'deployment/build-lock.json', 'deployment/native-clients-lock.json',
                                 'deployment/stacks/db.compose.json', 'integrations/mail/overlay/Dockerfile',
                                 'deployment/upstream-watch.json']), 'the checkout is never written')
        text = (self.out / '2026-11-23-baseline.md').read_text()
        upgrade_now = text.split('## Upgrade now')[1].split('## Schedule')[0]
        self.assertIn('URGENT: frappe v16.1.0: GHSA-crit-0001-aaaa CVE-2026-0001: Remote code execution &lt;b>', upgrade_now)
        self.assertIn('ACTIVELY EXPLOITED (CISA KEV)', upgrade_now)
        self.assertIn('fixed in: 16.1.5', upgrade_now)
        self.assertEqual(text.count('GHSA-crit-0001-aaaa CVE'), 1, 'OSV duplicate of a GitHub advisory is merged')
        self.assertNotIn('GHSA-old0', text, 'advisory for older versions only is not ours')
        self.assertNotIn('GHSA-past', text, 'fixed only in an older line: a later line has it')
        self.assertNotIn('GHSA-gone', text, 'withdrawn advisories are skipped')
        self.assertNotIn('GHSA-open', text, "an open range with a fix listed ends at the fix")
        self.assertIn('GHSA-unfx-0008-gggg: Open range and no fix yet', text)
        self.assertNotIn('GHSA-loose', text, 'OSV ranges are evaluated, not its loose match')
        self.assertIn('GHSA-odd0-0003-cccc: Range we cannot read', text)
        self.assertIn('our version affected: unknown, check by hand', text)
        self.assertIn('PYSEC-2026-7: Only in OSV', text)
        self.assertIn('newer release in our line: v16.2.0', text)
        self.assertIn('release notes mention breaking changes', text)
        self.assertIn('release notes mention security fixes', text)
        self.assertIn('check whether this retires our workaround: integrations/example/', text)
        self.assertNotIn('rc.1', text, 'pre-releases are not offered')
        ignore_now = text.split('## Ignore for now')[1]
        self.assertIn('new release line: v17.0.0', ignore_now)
        self.assertIn('PostgreSQL 16.2: release line 16 reaches end of life on 2026-12-01', text)
        self.assertIn('PostgreSQL 16.2: newer release in our line: 16.3', text)
        self.assertIn('newer release line: 18', text)
        self.assertIn('CVE-2026-0100: Database flaw', text)
        self.assertIn('fixed in: 16.3', text)
        self.assertIn('Used in: deployment/stacks/db.compose.json', text)
        self.assertIn('4 newer commits on develop', text)
        self.assertIn('Coolify 4.0.0: newer release in our line: v4.0.1', text, 'tags when a project has no releases')
        self.assertNotIn('beta', text)
        self.assertIn('Ubuntu: no version in the profile, not checked', text)
        status = json.loads((self.out / 'status.json').read_text())
        self.assertEqual(status['urgent'], ['advisory:frappe@v16.1.0:GHSA-crit-0001-aaaa'])
        self.assertEqual(status['errors'], [])
        self.assertIn('upstream-watch 2026-11-23:', printed)
        self.assertIn('1 urgent', printed)

    def test_daily_digest_only_when_something_is_new_and_weekly_roll_up(self):
        self.run_watch(FakeHTTP(answers()))
        before = set(p.name for p in self.out.iterdir())
        self.run_watch(FakeHTTP(answers()), today=TODAY + datetime.timedelta(days=1))
        self.assertEqual(set(p.name for p in self.out.iterdir()), before, 'nothing new: no digest')
        self.run_watch(FakeHTTP(answers(extra_release=True)), today=TODAY + datetime.timedelta(days=2))
        daily = (self.out / '2026-11-25.md').read_text()
        self.assertIn('newer release in our line: v16.2.1', daily)
        self.assertNotIn('GHSA-crit', daily, 'the daily digest holds only new findings')
        self.run_watch(FakeHTTP(answers(extra_release=True)), today=TODAY + datetime.timedelta(days=7))
        weekly = (self.out / '2026-W49.md').read_text()
        self.assertIn('weekly roll-up', weekly)
        self.assertIn('GHSA-crit-0001-aaaa', weekly, 'the roll-up shows everything still open')

    def test_false_positive_list_moves_findings_aside(self):
        profile = dict(self.profile, ignore=[{'id': 'CVE-2026-0001', 'reason': 'feature not enabled here'}])
        code, printed = self.run_watch(FakeHTTP(answers()), profile=profile)
        self.assertEqual(code, 0)
        text = (self.out / '2026-11-23-baseline.md').read_text()
        self.assertNotIn('URGENT', text)
        self.assertIn('## Ignored (false-positive list)', text)
        self.assertIn('`advisory:frappe@v16.1.0:GHSA-crit-0001-aaaa`: feature not enabled here', text)

    def test_dry_run_writes_nothing(self):
        code, printed = self.run_watch(FakeHTTP(answers()), dry_run=True)
        self.assertFalse(self.out.exists())
        self.assertIn('=== 2026-11-23-baseline.md', printed)
        self.assertIn('dry run: nothing written', printed)

    def test_a_failing_source_is_reported_and_the_rest_still_checked(self):
        code, printed = self.run_watch(FakeHTTP(answers(), fail=['endoflife.date']))
        self.assertEqual(code, 2)
        status = json.loads((self.out / 'status.json').read_text())
        self.assertEqual(status['errors'], ['PostgreSQL (endoflife.date): <urlopen error connection refused>'.replace('<', '&lt;')])
        self.assertIn('CVE-2026-0100', (self.out / '2026-11-23-baseline.md').read_text())
        self.assertIn('## Sources that failed', (self.out / '2026-11-23-baseline.md').read_text())

    def test_github_limit_stops_github_requests_for_the_run(self):
        http = FakeHTTP(answers())

        def limited(url, data=None, headers=None):
            if 'api.github.com' in url:
                http.calls.append((url, data, headers))
                raise urllib.error.HTTPError(url, 403, 'rate limit exceeded', {'X-RateLimit-Remaining': '0'}, None)
            return http(url, data, headers)
        code, printed = self.run_watch(limited)
        github_calls = [c for c in http.calls if 'api.github.com' in c[0]]
        self.assertEqual(len(github_calls), 1, 'one refused request; the rest are skipped')
        errors = json.loads((self.out / 'status.json').read_text())['errors']
        self.assertTrue(any('request limit reached' in e for e in errors))
        self.assertEqual(code, 2, 'OSV and the exploited list still catch the urgent flaw without GitHub')

    def test_token_is_sent_to_github_only_and_never_written_or_printed(self):
        http = FakeHTTP(answers())
        code, printed = self.run_watch(http, token=TOKEN)
        for url, data, headers in http.calls:
            if 'api.github.com' in url:
                self.assertEqual(headers.get('Authorization'), 'Bearer ' + TOKEN)
            else:
                self.assertNotIn('Authorization', headers, url)
        self.assertNotIn(TOKEN, printed)
        for path in self.out.iterdir():
            self.assertNotIn(TOKEN, path.read_text())

    def test_output_inside_the_checkout_is_refused(self):
        with self.assertRaises(ValueError):
            uw.run(self.source, self.source / 'docs/upstream-watch', self.profile)


class RepositoryInventoryTests(unittest.TestCase):
    def test_every_pinned_image_has_a_recorded_version_and_a_source(self):
        catalog = json.loads((ROOT / 'deployment/upstream-watch.json').read_text())
        items, notices = uw.inventory(ROOT, {'versions': {k: '1.0' for k, v in catalog['sources'].items() if v.get('host')}})
        self.assertEqual(notices, [], 'a digest changed without its version in deployment/upstream-watch.json')
        used = {c['image'] for c in items if c.get('image')}
        self.assertEqual(set(catalog['images']) - used, set(), 'stale image versions in the catalog')
        for c in items:
            self.assertTrue(any(c.get(k) for k in ('github', 'endoflife', 'osv', 'nvd')), c['key'] + ' has no source')
            self.assertIn(c['exposure'], {'public', 'tailnet', 'internal', 'build'}, c['key'])
        names = {c['key'] for c in items}
        for key in ['frappe', 'erpnext', 'bulwark-webmail', 'onlyoffice/documentserver', 'ghcr.io/goauthentik/server',
                    'stalwartlabs/stalwart', 'owncloud/ocis', 'postgres', 'node', 'coolify']:
            self.assertIn(key, names)

    def test_service_runs_unprivileged_and_daily(self):
        service = (ROOT / 'deployment/upstream-watch.service.example').read_text()
        timer = (ROOT / 'deployment/upstream-watch.timer.example').read_text()
        self.assertIn('DynamicUser=yes', service)
        self.assertIn('tools/upstream_watch.py', service)
        self.assertIn('LoadCredential=github-token:', service)
        self.assertNotIn('push', service)
        self.assertRegex(timer, r'OnCalendar=\*-\*-\* \d\d:\d\d')
        self.assertIn('Persistent=true', timer)
        example = json.loads((ROOT / 'deployment/upstream-watch.example.json').read_text())
        catalog = json.loads((ROOT / 'deployment/upstream-watch.json').read_text())
        hosts = {k for k, v in catalog['sources'].items() if v.get('host')}
        self.assertEqual(set(example['versions']), hosts)
        self.assertFalse(re.search(r'(?:ghp_|github_pat_)', json.dumps(example)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
