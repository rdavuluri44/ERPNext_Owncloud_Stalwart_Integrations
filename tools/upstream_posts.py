#!/usr/bin/env python3
"""Upstream posts: the list of what we posted on other projects, and a check for replies (P35).

Working agreements (owner, 26 November 2026): every post we make upstream (bug report, feature request, comment,
workaround) is listed in `docs/upstream-posts.json` with a log of every check and follow-up. At the start of a
session, and daily through the upstream watch (P62), the open posts are checked for replies and state changes; a
post stops being watched only when we no longer use that project, with the reason recorded.

    python3 tools/upstream_posts.py check --gh            # read-only: what is new since the last recorded check
    python3 tools/upstream_posts.py check --gh --record   # the same, and log the check in the list
    python3 tools/upstream_posts.py render           # write docs/upstream-posts.md from the list

The check asks GitHub's public API only and never posts anything. It also searches for threads the account
posted on that the list does not have yet, so a post nobody recorded is found. Private reports (security
advisories) are not allowed in this public list; they stay in the private companion.
"""
import argparse
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / 'docs' / 'upstream-posts.json'
PAGE = ROOT / 'docs' / 'upstream-posts.md'
GITHUB = 'https://api.github.com'
THREAD = re.compile(r'^https://github\.com/([\w.-]+/[\w.-]+)/(issues|pull)/(\d+)(?:#issuecomment-\d+)?$')
STATUSES = ('waiting', 'answered', 'fixed', 'closed', 'stopped')


def fetch(url, token=None):
    """GET one GitHub API URL and parse the JSON answer. Tests replace this function."""
    headers = {'User-Agent': 'upstream-posts', 'Accept': 'application/vnd.github+json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return json.load(response)


def fetch_with_gh(url, token=None):
    """GET through the GitHub command line, which signs in by itself: the key never passes through this tool."""
    import shutil
    import subprocess
    if not shutil.which('gh'):
        raise RuntimeError('the gh command is not installed')
    out = subprocess.run(['gh', 'api', url.replace(GITHUB + '/', '', 1)], capture_output=True, text=True,
                         encoding='utf-8', timeout=120)
    if out.returncode:
        raise RuntimeError('gh api: ' + clean(out.stderr, 120))
    return json.loads(out.stdout)


def clean(text, limit=200):
    """Text written by others is data: one line, bounded."""
    return re.sub(r'\s+', ' ', str(text or '')).strip()[:limit]


def thread_of(url):
    match = THREAD.match(url or '')
    if not match:
        raise ValueError('not a GitHub issue or pull request link: ' + str(url))
    return match.group(1), int(match.group(3))


def validate(ledger):
    errors, seen = [], set()
    if not str(ledger.get('account') or '').strip():
        errors.append('the list names no account')
    for post in ledger.get('posts', []):
        name = post.get('id') or '?'
        if name in seen:
            errors.append(name + ': listed twice')
        seen.add(name)
        if 'security/advisories' in str(post.get('url')):
            errors.append(name + ': private reports belong in the private companion')
            continue
        try:
            thread_of(post.get('url'))
        except ValueError as error:
            errors.append(name + ': ' + str(error))
        if post.get('status') not in STATUSES:
            errors.append(name + ': status must be one of ' + ', '.join(STATUSES))
        if not post.get('watch', True) and not str(post.get('stop_reason') or '').strip():
            errors.append(name + ': a post stops being watched only with a reason')
        if not post.get('watch', True) and post.get('status') != 'stopped':
            errors.append(name + ': a post no longer watched has the status "stopped"')
        for field in ('posted', 'summary', 'p_items'):
            if not post.get(field):
                errors.append(name + ': ' + field + ' is missing')
    return errors


def activity(post, account, token=None, get=None):
    """New replies by others and state changes on one thread since the post's `last_seen`."""
    get = get or fetch
    repo, number = thread_of(post['url'])
    issue = get(f'{GITHUB}/repos/{repo}/issues/{number}', token)
    comments = get(f'{GITHUB}/repos/{repo}/issues/{number}/comments?per_page=100', token)
    if issue.get('pull_request'):
        comments = comments + get(f'{GITHUB}/repos/{repo}/pulls/{number}/comments?per_page=100', token)
    since = post.get('last_seen') or post['posted']
    replies = sorted(({'at': c['created_at'], 'by': c['user']['login'], 'url': c.get('html_url'),
                       'text': clean(c.get('body'))} for c in comments
                      if c['user']['login'] != account and c['created_at'] > since), key=lambda r: r['at'])
    state = issue['state'] + (' (' + issue['state_reason'] + ')' if issue.get('state_reason') else '')
    latest = max([since] + [c['created_at'] for c in comments] + [issue.get('closed_at') or ''])
    return {'id': post['id'], 'thread': f'{repo}#{number}', 'state': state,
            'state_changed': state != post.get('thread_state'), 'replies': replies, 'latest': latest}


def discover(ledger, token=None, get=None):
    """Threads on other people's repositories where the account wrote, that the list does not have."""
    get = get or fetch
    account = ledger['account']
    known = set()
    for post in ledger.get('posts', []):
        try:
            known.add('%s#%d' % thread_of(post['url']))
        except ValueError:
            pass
    found = {}
    for role in ('author', 'commenter'):
        query = urllib.parse.quote(f'{role}:{account} -user:{account}')
        for item in get(f'{GITHUB}/search/issues?q={query}&per_page=100', token).get('items', []):
            repo = item['repository_url'].split('/repos/', 1)[1]
            key = f'{repo}#{item["number"]}'
            if key not in known:
                found[key] = clean(item.get('title'), 120)
    return found


def check(ledger, token=None, get=None, today=None, record=False):
    """Check every watched post; return (report lines, errors). With `record`, log the check in the list."""
    today = str(today or datetime.date.today())
    lines, errors = [], []
    for post in ledger.get('posts', []):
        if not post.get('watch', True):
            continue
        try:
            news = activity(post, ledger['account'], token, get)
        except Exception as error:  # one unreachable thread must not hide the others
            errors.append(post['id'] + ': ' + clean(error))
            continue
        if news['replies'] or news['state_changed']:
            lines.append(f"- **{news['thread']}** ({post['summary']}): now {news['state']}")
            lines += [f"  - {r['at'][:16]} {r['by']}: {r['text']} ({r['url']})" for r in news['replies']]
        if record:
            result = (f"{len(news['replies'])} new repl{'y' if len(news['replies']) == 1 else 'ies'}, "
                      f"thread {news['state']}") if news['replies'] or news['state_changed'] else 'nothing new'
            post.setdefault('checks', []).append({'date': today, 'result': result})
            post['last_seen'], post['thread_state'] = news['latest'], news['state']
    try:
        for key, title in sorted(discover(ledger, token, get).items()):
            lines.append(f'- **not in the list:** {key}: {title}')
    except Exception as error:
        errors.append('search for unlisted posts: ' + clean(error))
    return lines, errors


def render(ledger):
    out = ['# Upstream posts', '',
           '> Generated from `docs/upstream-posts.json` by `tools/upstream_posts.py render`; edit the JSON, not this',
           '> page. What we posted on other projects (bug reports, feature requests, comments, workarounds), why, and',
           '> every check and follow-up since. Checked at the start of each session and daily by the upstream watch',
           '> (P35, P62). Private reports are kept in the private operations repository.', '',
           f"Account: `{ledger['account']}`.", '',
           '| Posted | Thread | What | P item | Status | Last check |', '|---|---|---|---|---|---|']
    posts = sorted(ledger.get('posts', []), key=lambda p: (p['posted'], p['id']))
    for p in posts:
        repo, number = thread_of(p['url'])
        last = (p.get('checks') or [{}])[-1]
        out.append(f"| {p['posted']} | [{repo}#{number}]({p['url']}) | {p['summary']} | {', '.join(p['p_items'])} | "
                   f"{p['status']}{'' if p.get('watch', True) else ' (not watched)'} | "
                   f"{last.get('date', '—')}: {last.get('result', '—')} |")
    out += ['', '## Log', '']
    for p in posts:
        repo, number = thread_of(p['url'])
        out.append(f"### {repo}#{number}: {p['summary']}")
        out.append('')
        if p.get('register'):
            out.append('Register: ' + ', '.join(p['register']) + '.')
        if p.get('next'):
            out.append('Next: ' + p['next'])
        if not p.get('watch', True):
            out.append('Not watched any more: ' + p['stop_reason'])
        if p.get('register') or p.get('next') or not p.get('watch', True):
            out.append('')
        for c in p.get('checks', []):
            out.append(f"- {c['date']}: {c['result']}" + (f" Follow-up: {c['follow_up']}" if c.get('follow_up') else ''))
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def load(path=LEDGER):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(ledger, path=LEDGER):
    Path(path).write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Upstream posts: list and reply check (P35). Never posts.')
    parser.add_argument('command', choices=('check', 'render', 'validate'))
    parser.add_argument('--ledger', default=str(LEDGER))
    parser.add_argument('--record', action='store_true', help='log the check in the list (and re-render the page)')
    parser.add_argument('--github-token-file', help='optional read-only GitHub token; missing file = no token')
    parser.add_argument('--gh', action='store_true', help='ask GitHub through the signed-in gh command (sessions)')
    args = parser.parse_args(argv)
    ledger = load(args.ledger)
    problems = validate(ledger)
    if problems:
        print('the list is not valid:\n  ' + '\n  '.join(problems))
        return 1
    if args.command == 'validate':
        print('upstream posts: %d listed, valid' % len(ledger['posts']))
        return 0
    page = Path(args.ledger).with_suffix('.md')
    if args.command == 'render':
        page.write_text(render(ledger), encoding='utf-8', newline='\n')
        print('wrote ' + str(page))
        return 0
    token_file = Path(args.github_token_file) if args.github_token_file else None
    token = token_file.read_text().strip() if token_file and token_file.is_file() else None
    lines, errors = check(ledger, token, get=fetch_with_gh if args.gh else None, record=args.record)
    print('\n'.join(lines) if lines else 'upstream posts: nothing new')
    for error in errors:
        print('could not check: ' + error)
    if args.record:
        save(ledger, args.ledger)
        page.write_text(render(ledger), encoding='utf-8', newline='\n')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
