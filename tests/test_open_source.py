"""P35: every open-source project we use is credited and tracked, in one list that cannot drift from the upstream
watch, modules.json or the README acknowledgements."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import open_source as oss  # noqa: E402

WATCH = {'sources': {'app': {}, 'db': {}}}
MODULES = {'modules': [{'id': 'm', 'upstream': [{'name': 'App', 'url': 'https://github.com/example/app.git'}]}]}
LEDGER = {'projects': [
    {'name': 'App', 'repo': 'https://github.com/example/app', 'licence': 'MIT', 'used_in': ['m'], 'status': 'adopted',
     'watch': ['app']},
    {'name': 'DB', 'repo': 'https://example.org/db', 'licence': 'GPL-2.0', 'used_in': ['m'], 'status': 'adopted',
     'watch': ['db']},
    {'name': 'Icons', 'repo': 'https://github.com/example/icons', 'licence': 'MIT', 'used_in': ['m'],
     'status': 'borrowed', 'not_watched': 'copied once'},
    {'name': 'Maybe', 'repo': 'https://github.com/example/maybe', 'licence': 'Apache-2.0', 'used_in': ['P1'],
     'status': 'evaluating', 'note': 'for P1'},
    {'name': 'Old', 'repo': 'https://github.com/example/old', 'licence': 'MPL-2.0', 'used_in': ['m'],
     'status': 'retired', 'note': 'replaced'},
]}


class Validate(unittest.TestCase):
    def test_the_real_list_is_in_step_with_the_watch_modules_and_readme(self):
        ledger, watch, modules = oss.load_json(oss.LIST), oss.load_json(oss.WATCH), oss.load_json(oss.MODULES)
        self.assertEqual(oss.validate(ledger, watch, modules), [])
        readme = oss.README.read_text(encoding='utf-8')
        self.assertEqual(readme, oss.readme_with(readme, oss.readme_section(ledger)), 'run tools/open_source.py render')
        self.assertEqual(oss.PAGE.read_text(encoding='utf-8'), oss.page(ledger), 'run tools/open_source.py render')

    def test_sample_is_valid(self):
        self.assertEqual(oss.validate(LEDGER, WATCH, MODULES), [])

    def test_a_watched_component_without_credit_fails(self):
        watch = {'sources': dict(WATCH['sources'], cache={})}
        self.assertTrue(any('follows cache' in e for e in oss.validate(LEDGER, watch, MODULES)))

    def test_a_module_upstream_missing_from_the_list_fails(self):
        modules = copy.deepcopy(MODULES)
        modules['modules'][0]['upstream'].append({'name': 'Lib', 'url': 'https://github.com/example/lib'})
        self.assertTrue(any('names Lib' in e for e in oss.validate(LEDGER, WATCH, modules)))

    def test_adopted_needs_tracking_or_a_reason_and_evaluating_needs_a_note(self):
        ledger = copy.deepcopy(LEDGER)
        ledger['projects'][2].pop('not_watched')
        ledger['projects'][3].pop('note')
        ledger['projects'][1]['watch'] = ['missing']
        errors = ' '.join(oss.validate(ledger, WATCH, MODULES))
        for expected in ('neither watched nor a reason', 'say what is being evaluated', 'missing is not in',
                         'follows db'):
            self.assertIn(expected, errors)

    def test_two_projects_cannot_claim_one_watch_key(self):
        ledger = copy.deepcopy(LEDGER)
        ledger['projects'][1]['watch'] = ['app', 'db']
        self.assertTrue(any('claimed by' in e for e in oss.validate(ledger, WATCH, MODULES)))


class Credits(unittest.TestCase):
    def test_readme_credits_what_we_use_and_mentions_what_we_used(self):
        section = oss.readme_section(LEDGER)
        for name in ('App', 'DB', 'Icons', 'Old'):
            self.assertIn(name, section)
        self.assertNotIn('Maybe', section, 'nothing is credited as used before it is adopted')
        self.assertTrue(section.startswith(oss.START) and section.endswith(oss.END))

    def test_page_lists_everything_with_licence_and_tracking(self):
        text = oss.page(LEDGER)
        self.assertIn('| [App](https://github.com/example/app) | MIT | m | daily watch: `app` |', text)
        self.assertIn('## Being evaluated or chosen, not in the code yet', text)
        self.assertIn('copied once', text)


if __name__ == '__main__':
    unittest.main()
