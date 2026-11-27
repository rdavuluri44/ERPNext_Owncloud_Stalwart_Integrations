"""P35: the list of our upstream posts is valid, the check finds replies and unlisted posts (sample answers, no
network), records every check, never posts, and the daily upstream watch reports each reply once."""
import contextlib
import copy
import datetime
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import upstream_posts as up  # noqa: E402
import upstream_watch as uw  # noqa: E402

ME = 'our-account'
LEDGER = {'account': ME, 'posts': [
    {'id': 'bug', 'url': 'https://github.com/example/app/issues/7', 'posted': '2026-11-20', 'summary': 'a bug',
     'p_items': ['P1'], 'status': 'waiting', 'watch': True, 'last_seen': '2026-11-20T10:00:00Z', 'thread_state': 'open'},
    {'id': 'note', 'url': 'https://github.com/example/lib/pull/3#issuecomment-99', 'posted': '2026-11-21',
     'summary': 'a comment', 'p_items': ['P2'], 'status': 'waiting', 'watch': True,
     'last_seen': '2026-11-21T09:00:00Z', 'thread_state': 'open'},
    {'id': 'old', 'url': 'https://github.com/example/gone/issues/1', 'posted': '2026-11-01', 'summary': 'retired app',
     'p_items': ['P3'], 'status': 'stopped', 'watch': False, 'stop_reason': 'we no longer use it'},
]}


def comment(who, when, text, n):
    return {'user': {'login': who}, 'created_at': when, 'body': text, 'html_url': f'https://github.com/c/{n}'}


ANSWERS = {
    'https://api.github.com/repos/example/app/issues/7': {'state': 'closed', 'state_reason': 'completed',
                                                           'closed_at': '2026-11-22T08:00:00Z'},
    'https://api.github.com/repos/example/app/issues/7/comments?per_page=100': [
        comment(ME, '2026-11-20T10:00:00Z', 'our report', 1),
        comment('maintainer', '2026-11-22T07:00:00Z', 'Fixed in\nmain, thanks', 2)],
    'https://api.github.com/repos/example/lib/issues/3': {'state': 'open', 'pull_request': {}},
    'https://api.github.com/repos/example/lib/issues/3/comments?per_page=100': [
        comment('someone', '2026-11-19T00:00:00Z', 'before our comment', 3), comment(ME, '2026-11-21T09:00:00Z', 'ours', 4)],
    'https://api.github.com/repos/example/lib/pulls/3/comments?per_page=100': [],
}


class Fake:
    def __init__(self, answers=ANSWERS, search=()):
        self.answers, self.search, self.calls = answers, list(search), []

    def __call__(self, url, token=None):
        self.calls.append((url, token))
        if '/search/issues' in url:
            return {'items': self.search if 'author' in url else []}
        if 'example/gone' in url:
            raise AssertionError('a post no longer watched is not checked')
        return copy.deepcopy(self.answers[url])


class Validate(unittest.TestCase):
    def test_sample_and_the_real_list_are_valid(self):
        self.assertEqual(up.validate(LEDGER), [])
        self.assertEqual(up.validate(up.load()), [], 'docs/upstream-posts.json')

    def test_refuses_private_reports_bad_links_and_silent_stops(self):
        bad = copy.deepcopy(LEDGER)
        bad['posts'][0]['url'] = 'https://github.com/example/app/security/advisories/GHSA-xxxx'
        bad['posts'][1]['url'] = 'https://example.com/forum/1'
        bad['posts'][2]['stop_reason'] = ''
        bad['posts'].append(dict(LEDGER['posts'][0]))
        errors = ' '.join(up.validate(bad))
        for expected in ('private companion', 'not a GitHub', 'only with a reason', 'listed twice'):
            self.assertIn(expected, errors)


class Check(unittest.TestCase):
    def test_reports_new_replies_and_state_changes_only(self):
        lines, errors = up.check(copy.deepcopy(LEDGER), get=Fake())
        text = '\n'.join(lines)
        self.assertEqual(errors, [])
        self.assertIn('example/app#7', text)
        self.assertIn('closed (completed)', text)
        self.assertIn('maintainer: Fixed in main, thanks', text, 'other people\'s text is one line')
        self.assertNotIn('example/lib#3', text, 'nothing after our comment there')
        self.assertNotIn('our report', text)

    def test_record_logs_every_check_and_moves_the_mark(self):
        ledger = copy.deepcopy(LEDGER)
        up.check(ledger, get=Fake(), today=datetime.date(2026, 11, 23), record=True)
        bug, note, old = ledger['posts']
        self.assertEqual(bug['checks'][-1], {'date': '2026-11-23', 'result': '1 new reply, thread closed (completed)'})
        self.assertEqual(bug['last_seen'], '2026-11-22T08:00:00Z')
        self.assertEqual(note['checks'][-1]['result'], 'nothing new')
        self.assertNotIn('checks', old)
        lines, _ = up.check(ledger, get=Fake())
        self.assertEqual(lines, [], 'a recorded reply is not reported again')

    def test_finds_threads_we_posted_on_that_the_list_lacks(self):
        search = [{'repository_url': 'https://api.github.com/repos/other/tool', 'number': 5, 'title': 'unlisted'},
                  {'repository_url': 'https://api.github.com/repos/example/app', 'number': 7, 'title': 'listed'}]
        lines, _ = up.check(copy.deepcopy(LEDGER), get=Fake(search=search))
        self.assertIn('- **not in the list:** other/tool#5: unlisted', lines)
        self.assertFalse(any('example/app#7: listed' in l for l in lines))

    def test_one_failing_thread_does_not_hide_the_others(self):
        answers = dict(ANSWERS)
        del answers['https://api.github.com/repos/example/lib/issues/3']
        lines, errors = up.check(copy.deepcopy(LEDGER), get=Fake(answers))
        self.assertTrue(any('example/app#7' in l for l in lines))
        self.assertEqual(len(errors), 1)

    def test_only_reads(self):
        fake = Fake()
        up.check(copy.deepcopy(LEDGER), get=fake, record=True)
        self.assertTrue(all(url.startswith('https://api.github.com/') for url, _ in fake.calls))
        source = (ROOT / 'tools' / 'upstream_posts.py').read_text(encoding='utf-8')
        for verb in ("method='POST'", 'method="POST"', 'data=', '.post('):
            self.assertNotIn(verb, source)


class Render(unittest.TestCase):
    def test_page_lists_every_post_and_its_log(self):
        ledger = copy.deepcopy(LEDGER)
        up.check(ledger, get=Fake(), today=datetime.date(2026, 11, 23), record=True)
        page = up.render(ledger)
        self.assertIn('[example/app#7](https://github.com/example/app/issues/7)', page)
        self.assertIn('stopped (not watched)', page)
        self.assertIn('Not watched any more: we no longer use it', page)
        self.assertIn('- 2026-11-23: 1 new reply, thread closed (completed)', page)

    def test_the_published_page_matches_the_list(self):
        self.assertEqual((ROOT / 'docs' / 'upstream-posts.md').read_text(encoding='utf-8'), up.render(up.load()),
                         'run: python3 tools/upstream_posts.py render')


class DailyWatch(unittest.TestCase):
    def test_the_watch_reports_each_reply_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, out = Path(tmp) / 'src', Path(tmp) / 'out'
            (source / 'docs').mkdir(parents=True)
            (source / 'docs' / 'upstream-posts.json').write_text(json.dumps(LEDGER), encoding='utf-8')
            fake = Fake()
            saved = uw.fetch, uw.inventory
            uw.fetch = lambda url, data=None, headers=None: (
                {'vulnerabilities': []} if 'cisa' in url else fake(url, (headers or {}).get('Authorization')))
            uw.inventory = lambda source, profile: ([], [])
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    uw.run(source, out, {}, today=datetime.date(2026, 11, 23))
                    uw.run(source, out, {}, today=datetime.date(2026, 11, 24))
            finally:
                uw.fetch, uw.inventory = saved
            self.assertIn('maintainer: Fixed in main', (out / '2026-11-23-posts.md').read_text())
            self.assertFalse((out / '2026-11-24-posts.md').exists(), 'the same reply is not reported twice')


if __name__ == '__main__':
    unittest.main()
