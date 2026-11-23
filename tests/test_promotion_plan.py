"""P59: the promotion plan names every stack a change reaches, and the drift check finds a stack left
behind (the website stack missed on 21 November 2026). Sample git history in a temporary repository;
Docker and Coolify are faked, no network."""
import ast
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import drift_check as dc  # noqa: E402
import promotion_plan as pp  # noqa: E402

RULES = pp.load(ROOT)
STACKS = {p.name.replace('.compose.json', '') for p in (ROOT / 'deployment/stacks').glob('*.compose.json')}
STACKS = {'editor' if s == 'editor-onlyoffice' else s for s in STACKS}
PSEUDO = {'proxy', 'host', 'test', 'mobile'}


def tracked():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.split('\0') if p]


class PromotionPlanTests(unittest.TestCase):
    def test_every_tracked_file_is_classified(self):
        self.assertEqual(pp.plan(tracked(), RULES)['unclassified'], [], 'add a rule in deployment/promotion-map.json')

    def test_rules_name_known_stacks(self):
        for rule in RULES:
            self.assertLessEqual(set(rule['stacks']), STACKS | PSEUDO, rule['name'])
        self.assertLessEqual(STACKS, {s for r in RULES for s in r['stacks']}, 'every stack has a rule')

    def test_map_agrees_with_the_files_prepare_runtime_mounts(self):
        tree = ast.parse((ROOT / 'tools/prepare_runtime.py').read_text())
        literals = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and \
                    node.targets[0].id in ('copy_files', 'copy_dirs'):
                literals.update(ast.literal_eval(node.value))
        mounts = json.loads((ROOT / 'deployment/stacks/mounts.json').read_text())
        files = tracked()
        checked = 0
        for target, source in literals.items():
            stacks = {m['stack'] for m in mounts if m['target'] == target}
            examples = [f for f in files if (f == source or f.startswith(source + '/')) and not f.endswith('.md')]
            self.assertTrue(examples, source)
            for stack in stacks:
                reached = {s for r in pp.rules_for(examples[0], RULES) for s in r['stacks']}
                self.assertIn(stack, reached, examples[0] + ' is mounted into ' + stack)
                checked += 1
        for path in ('integrations/onlyoffice/editor-wopi.ejs', 'deployment/config/onlyoffice-local-production-linux.json'):
            self.assertIn('editor', {s for r in pp.rules_for(path, RULES) for s in r['stacks']})
        self.assertGreaterEqual(checked, 8)

    def test_the_missed_website_change_is_in_the_plan(self):
        result = pp.plan(['integrations/website/site/index.html', 'erpnext_drive_integrations/www/place_holder.py'], RULES)
        self.assertEqual(sorted(result['stacks']), ['erp', 'website'])
        text = pp.render(result, 'sample')
        self.assertIn('### website', text)
        self.assertIn('bench migrate', text)
        self.assertIn('tools/drift_check.py', text)

    def test_live_settings_and_what_test_cannot_cover(self):
        result = pp.plan(['integrations/authentik/configuration.json', 'deployment/production/website.traefik.yaml'], RULES)
        self.assertEqual(sorted(result['stacks']), ['proxy'])
        self.assertTrue(any('authentik' in s for s in result['live']))
        self.assertEqual(len(result['not_covered']), 2)

    def test_documentation_reaches_no_stack(self):
        result = pp.plan(['integrations/website/README.md', 'docs/decisions.md', 'tests/test_website.py'], RULES)
        self.assertEqual(result['stacks'], {})
        self.assertIn('No running stack is reached.', pp.render(result, 'docs'))

    def test_unclassified_file_fails(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pp.main(['--files', 'new-folder/thing.py']), 1)
        self.assertIn('`new-folder/thing.py`', out.getvalue())

    def test_pull_request_template_asks_for_the_plan(self):
        template = (ROOT / '.github/pull_request_template.md').read_text()
        self.assertIn('## Promotion plan', template)
        self.assertIn('tools/promotion_plan.py', template)


class DriftCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'test')
        (self.repo / 'deployment').mkdir()
        shutil.copy(ROOT / 'deployment/promotion-map.json', self.repo / 'deployment/promotion-map.json')
        self.write('erpnext_drive_integrations/hooks.py', 'a = 1\n')
        self.write('integrations/website/site/index.html', '<p>one</p>\n')
        self.write('docs/notes.md', 'one\n')
        self.a = self.commit('first')
        self.write('integrations/website/site/index.html', '<p>two</p>\n')
        self.b = self.commit('website fix')
        self.write('docs/notes.md', 'two\n')
        self.c = self.commit('docs only')
        self.git('checkout', '-q', '-b', 'side', self.a)
        self.write('integrations/drive/workspace.js', 'x\n')
        self.side = self.commit('unmerged branch')
        self.git('checkout', '-q', 'main')
        self.profile = Path(self.tmp.name) / 'erp-profile.json'
        self.profile.write_text(json.dumps({'commit': self.a, 'secret_key': 'not read'}))
        self.page = Path(self.tmp.name) / 'index.html'
        self.page.write_bytes(b'<p>two</p>\n')
        self.real = dc.run, dc.fetch
        self.docker_calls = []

        def fake_run(args):
            if args[0] == 'git':
                return self.real[0](args)
            self.docker_calls.append(args)
            if 'psql' in args:
                return {'website': 'Source commit ' + self.a + '\n', 'mail': 'Source commit ' + self.side + '\n',
                        'dms': 'Source commit 0123456789abcdef0123456789abcdef01234567\n'}[args[-1].split("'")[1]]
            if args[:2] == ['docker', 'ps']:
                return 'drive-ocis-1\ndrive-collab-1\nother\n'
            if args[:2] == ['docker', 'inspect']:
                return 'cloud/drive:' + self.c[:12] + '-runtime <no value>\n'
            raise AssertionError(args)
        dc.run = fake_run
        dc.fetch = lambda url: b'<p>two</p>\n' if url.endswith('/same') else b'<p>old</p>\n'

    def tearDown(self):
        dc.run, dc.fetch = self.real
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, text=True, check=True).stdout.strip()

    def write(self, path, text):
        (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / path).write_text(text)

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def config(self, **extra):
        return {'source': str(self.repo), 'branch': 'main', 'fetch': False, 'state_dir': self.tmp.name + '/state',
                'stacks': {'erp': {'commit_from': {'profile': str(self.profile)}},
                           'website': {'commit_from': {'coolify_service': 'website'}},
                           'drive': {'commit_from': {'container': 'drive-'}},
                           'mail': {'commit_from': {'coolify_service': 'mail'}},
                           'dms': {'commit_from': {'coolify_service': 'dms'}}},
                'served': [{'url': 'https://www.example.com/same', 'file': str(self.page)},
                           {'url': 'https://www.example.com/stale', 'file': str(self.page)}], **extra}

    def test_finds_the_stack_left_behind_and_keeps_the_others_clean(self):
        status = dc.check(self.config())
        stacks = status['stacks']
        self.assertEqual(stacks['erp']['state'], 'clean', 'only docs and the website changed since its commit')
        self.assertEqual(stacks['website']['state'], 'behind')
        self.assertEqual(stacks['website']['files'], ['integrations/website/site/index.html'])
        self.assertEqual(stacks['drive']['state'], 'clean', 'runs main itself (short tag resolved)')
        self.assertEqual(stacks['mail']['state'], 'not on main')
        self.assertEqual(stacks['dms']['state'], 'unknown')
        self.assertEqual(status['served'], [{'url': 'https://www.example.com/same', 'same': True},
                                            {'url': 'https://www.example.com/stale', 'same': False}])
        self.assertEqual(len(status['drift']), 3)
        self.assertEqual(len(status['problems']), 1)

    def test_signals_and_status_file(self):
        path = Path(self.tmp.name) / 'config.json'
        path.write_text(json.dumps(self.config()))
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(dc.main(['--config', str(path)]), 2)
        line = out.getvalue()
        self.assertIn('DRIFT: ', line)
        self.assertIn('website is behind main (1 file(s), e.g. integrations/website/site/index.html)', line)
        self.assertIn('clean: drive, erp', line)
        self.assertNotIn('not read', (Path(self.tmp.name) / 'state/status.json').read_text())
        clean = self.config(stacks={'erp': {'commit_from': {'profile': str(self.profile)}}},
                            served=[{'url': 'https://www.example.com/same', 'file': str(self.page)}])
        path.write_text(json.dumps(clean))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dc.main(['--config', str(path)]), 0)

    def test_it_only_reads(self):
        before = self.git('status', '--porcelain'), self.git('rev-parse', 'HEAD')
        dc.check(self.config())
        self.assertEqual((self.git('status', '--porcelain'), self.git('rev-parse', 'HEAD')), before)
        for args in self.docker_calls:
            self.assertIn(args[1], ('exec', 'ps', 'inspect'))
            if 'psql' in args:
                self.assertTrue(args[-1].lower().startswith('select '))

    def test_unsafe_service_name_is_refused(self):
        with self.assertRaises(ValueError):
            dc.deployed_commit({'coolify_service': "x'; drop table services; --"}, {})

    def test_examples_install_nightly(self):
        example = json.loads((ROOT / 'deployment/drift-check.example.json').read_text())
        self.assertTrue(example['stacks'])
        for spec in example['stacks'].values():
            self.assertEqual(len(set(spec['commit_from']) & {'coolify_service', 'profile', 'container'}), 1)
        timer = (ROOT / 'deployment/drift-check.timer.example').read_text()
        self.assertIn('OnCalendar=*-*-* 03:', timer)
        self.assertIn('tools/drift_check.py --config', (ROOT / 'deployment/drift-check.service.example').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
