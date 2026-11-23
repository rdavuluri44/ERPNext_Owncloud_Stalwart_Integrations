#!/usr/bin/env python3
"""Promotion plan (P59): which stacks, setup steps, live settings and restarts a change reaches.

    promotion_plan.py FROM TO             git revisions, e.g. the commit production runs and main
    promotion_plan.py --files PATH...     an explicit list of changed files

Prints Markdown for the pull request and the release record, from deployment/promotion-map.json.
Exit status 1 when a changed file matches no rule (classify it in the map first).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pattern(glob):
    """modules.json glob: ** any path (also none), * within one folder."""
    out, i = '', 0
    while i < len(glob):
        if glob.startswith('**/', i):
            out, i = out + '(?:.*/)?', i + 3
        elif glob.startswith('**', i):
            out, i = out + '.*', i + 2
        elif glob[i] == '*':
            out, i = out + '[^/]*', i + 1
        else:
            out, i = out + re.escape(glob[i]), i + 1
    return re.compile(out + r'\Z')


def load(source=ROOT):
    rules = json.loads((Path(source) / 'deployment/promotion-map.json').read_text())['rules']
    for rule in rules:
        rule['_patterns'] = [pattern(g) for g in rule['paths']]
    return rules


def rules_for(path, rules):
    matched = [r for r in rules if any(p.match(path) for p in r['_patterns'])]
    # Markdown is documentation: it changes no running behaviour, so it reaches no stack.
    return [r for r in matched if not r['stacks']] if path.endswith('.md') else matched


def plan(files, rules):
    """Per stack: files, steps, restarts, live settings, what test cannot cover; plus unclassified files."""
    stacks, unclassified, live, not_covered = {}, [], [], []
    for path in sorted(set(files)):
        matched = rules_for(path, rules)
        if not matched:
            unclassified.append(path)
        for rule in matched:
            for stack in rule['stacks']:
                entry = stacks.setdefault(stack, {'files': [], 'steps': [], 'restart': []})
                entry['files'].append(path)
                for key in ('steps', 'restart'):
                    entry[key] += [s for s in rule.get(key, []) if s not in entry[key]]
            live += [s for s in rule.get('live', []) if s not in live]
            if rule.get('not_covered'):
                item = rule['not_covered'] + ' (' + rule['name'] + ')'
                if item not in not_covered:
                    not_covered.append(item)
    return {'stacks': stacks, 'live': live, 'not_covered': not_covered, 'unclassified': unclassified}


def changed(source, old, new):
    out = subprocess.run(['git', '-C', str(source), 'diff', '--name-only', '--no-renames', old, new],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


def render(result, title):
    lines = ['## Promotion plan: ' + title, '']
    if not result['stacks'] and not result['live']:
        lines.append('No running stack is reached.')
    for stack, entry in sorted(result['stacks'].items()):
        lines += ['### ' + stack, '- Files: ' + ', '.join('`' + f + '`' for f in entry['files'][:15]) +
                  (' and %d more' % (len(entry['files']) - 15) if len(entry['files']) > 15 else '')]
        lines += ['- Step: ' + s for s in entry['steps']]
        lines += ['- Restart: ' + s for s in entry['restart']]
        lines.append('')
    if result['live']:
        lines += ['### Live settings (not in any stack)'] + ['- ' + s for s in result['live']] + ['']
    if result['not_covered']:
        lines += ['### Not covered by the test site'] + ['- ' + s for s in result['not_covered']] + ['']
    lines += ['### After promotion', '- Run `tools/drift_check.py` on production: every stack above must be clean.']
    if result['unclassified']:
        lines += ['', '### Files no rule covers (add them to deployment/promotion-map.json)'] + \
                 ['- `' + f + '`' for f in result['unclassified']]
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Promotion plan (P59) from deployment/promotion-map.json.')
    parser.add_argument('revisions', nargs='*', help='FROM TO (git revisions)')
    parser.add_argument('--files', nargs='+', help='changed files instead of a git range')
    parser.add_argument('--source', default=str(ROOT))
    args = parser.parse_args(argv)
    if args.files:
        files, title = args.files, 'listed files'
    elif len(args.revisions) == 2:
        short = [r[:12] if re.fullmatch(r'[0-9a-f]{13,40}', r) else r for r in args.revisions]
        files, title = changed(args.source, *args.revisions), short[0] + ' → ' + short[1]
    else:
        parser.error('give FROM TO or --files')
    result = plan(files, load(args.source))
    print(render(result, title), end='')
    return 1 if result['unclassified'] else 0


if __name__ == '__main__':
    sys.exit(main())
