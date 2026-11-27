#!/usr/bin/env python3
"""Daily upstream watch (P62): new releases, security advisories, end of life and licence changes.

Reads the pinned inventory from a checkout of this repository (the locks, every image digest in the
stack files, build lock and Dockerfiles, and deployment/upstream-watch.json) plus the versions of host
components from a private profile. Asks public sources only: GitHub (releases, tags, repository
advisories, licence), OSV.dev, NVD, endoflife.date and the CISA list of actively exploited flaws.
Writes into the given output folder only: a baseline on the first run, a daily digest when something
is new, a weekly roll-up, state.json and status.json. It never upgrades, commits, pushes or sends
anything. Signals: the exit code (0 fine, 1 a source failed, 2 an urgent finding is open), status.json
and one summary line. Recommendations are rule-based advice; the owner decides.
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GITHUB = 'https://api.github.com'
OSV = 'https://api.osv.dev/v1/query'
NVD = 'https://services.nvd.nist.gov/rest/json/cves/2.0'
EOL = 'https://endoflife.date/api/'
KEV = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
NVD_DELAY = 6.5  # NVD allows five requests per 30 seconds without an API key
PRE = re.compile(r'rc|beta|alpha|dev|preview|nightly', re.I)
IMAGE = re.compile(r'([a-z0-9][a-z0-9./_-]*(?::[\w.-]+)?)@(sha256:[0-9a-f]{64})')
RANK = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'unknown': 0, 'info': 0}
RECOMMENDATIONS = [('Upgrade now', 'upgrade now'), ('Schedule', 'schedule'), ('Ignore for now', 'ignore')]


def fetch(url, data=None, headers=None):
    """GET, or POST JSON, one public URL and parse the JSON answer. Tests replace this function."""
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(url, data=body, headers={
        'User-Agent': 'upstream-watch', 'Accept': 'application/json',
        **({'Content-Type': 'application/json'} if body else {}), **(headers or {})})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def nums(text):
    match = re.search(r'\d+(?:\.\d+)*', str(text or ''))
    return tuple(int(x) for x in match.group().split('.')) if match else ()


def vkey(text):
    """Comparable version: 'v1.1' equals '1.1.0'; prefixes such as 'version/' are ignored."""
    n = nums(text)
    return n + (0,) * (6 - len(n)) if n else ()


def line(key):
    """Release line: calendar versions (2026.8.x) and 0.x by two numbers, others by the major number."""
    return key[:2] if key and (key[0] >= 1000 or key[0] == 0) else key[:1]


def in_range(version, text):
    """Whether a published range ('>= 1.2, < 1.4.1', '<= 2.0', '3.0–3.3.2', '0.15.4') contains our version.
    None when either cannot be read: reported as 'check by hand', never dropped."""
    ours, text = vkey(version), (text or '').strip()
    if not ours or not text:
        return None
    span = re.fullmatch(r'v?([\d.]+)\s*(?:–|-|to)\s*v?([\d.]+)', text)
    parts = ['>=' + span[1], '<=' + span[2]] if span else [p for p in re.split(r'\s*,\s*', text) if p]
    result = True
    for part in parts:
        match = re.fullmatch(r'(>=|<=|>|<|==|=)?\s*v?(\d[\w.+-]*)', part.strip())
        if not match:
            return None
        k, op = vkey(match[2]), match[1] or '='
        result &= {'>=': ours >= k, '<=': ours <= k, '>': ours > k, '<': ours < k, '=': ours == k, '==': ours == k}[op]
    return result


def by_fix(version, fixed):
    """Affected or not from the patched versions alone: a fix in our line decides; fixes only in older
    lines mean a later line has it; otherwise None."""
    ours, keys = vkey(version), [vkey(f) for f in fixed if vkey(f)]
    if not ours or not keys:
        return None
    mine = [k for k in keys if line(k) == line(ours)]
    if mine:
        return ours < min(mine)
    return None if any(k > ours for k in keys) else False


def osv_hit(vuln, version):
    """Evaluate OSV's published ranges ourselves (its version match can be loose)."""
    ours, verdict = vkey(version), None
    for affected in vuln.get('affected', []):
        if version in affected.get('versions', []):
            return True
        for r in affected.get('ranges', []):
            if r.get('type') == 'GIT':
                continue
            verdict, start = False, None
            for e in r.get('events', []):
                if 'introduced' in e:
                    start = vkey(e['introduced'])
                elif 'fixed' in e or 'last_affected' in e:
                    end = vkey(e.get('fixed') or e['last_affected'])
                    if start is not None and start <= ours and (ours < end if 'fixed' in e else ours <= end):
                        return True
                    start = None
            if start is not None and start <= ours:
                return True
    return verdict


def clean(text, limit=200):
    """Public text goes into the digest as data: one line, no HTML, bounded."""
    return re.sub(r'\s+', ' ', str(text or '')).strip()[:limit].replace('<', '&lt;')


def advise(severity, exploited, exposure, affected):
    unsure = '' if affected else 'check whether our version is affected; '
    where = severity + ' severity on ' + ('an ' if exposure[0] in 'aeiou' else 'a ') + exposure + ' component'
    if exploited:
        return 'upgrade now', unsure + 'listed as actively exploited (CISA KEV)'
    if severity == 'critical' or (severity == 'high' and exposure == 'public'):
        return 'upgrade now', unsure + where
    return 'schedule', unsure + where


class Watch:
    def __init__(self, token=None):
        self.token, self.errors, self.github_blocked, self.nvd_next = token, [], False, 0.0

    def github(self, path):
        if self.github_blocked:
            raise RuntimeError('skipped: GitHub request limit reached earlier in this run')
        auth = {'Authorization': 'Bearer ' + self.token} if self.token else {}
        try:
            return fetch(GITHUB + path, headers={'Accept': 'application/vnd.github+json', **auth})
        except urllib.error.HTTPError as exc:
            if exc.code == 429 or (exc.code == 403 and (exc.headers or {}).get('X-RateLimit-Remaining') == '0'):
                self.github_blocked = True
                raise RuntimeError('GitHub request limit reached (a read-only token file raises it)') from None
            raise

    def nvd(self, url):
        wait = self.nvd_next - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self.nvd_next = time.monotonic() + NVD_DELAY
        return fetch(url)


def inventory(source, profile):
    """Every pinned component: (items, notices). Notices list what cannot be checked."""
    source = Path(source)
    catalog = json.loads((source / 'deployment/upstream-watch.json').read_text())
    sources, items, notices = catalog['sources'], [], []

    def add(key, **fields):
        spec = {**sources.get(key, {}), **{k: v for k, v in fields.items() if v is not None}}
        spec.setdefault('name', key)
        spec['key'] = key
        spec['exposure'] = (profile.get('exposure') or {}).get(key, spec.get('exposure', 'internal'))
        items.append(spec)

    def repo(url):
        return re.sub(r'^https://github\.com/|\.git$', '', url)

    def read(path):
        return json.loads((source / path).read_text())

    for key, pin in read('deployment/upstream-lock.json').items():
        tagged = bool(nums(pin['ref']))
        add(key, github=repo(pin['url']), version=pin['ref'] if tagged else None,
            branch=None if tagged else pin['ref'], commit=pin['commit'])
    mail = read('integrations/mail/upstream.json')
    add('bulwark-webmail', name='Bulwark Webmail', github=repo(mail['repository']), version=mail['version'],
        commit=mail['commit'])
    build = read('deployment/build-lock.json')
    add('frappe_docker', github=repo(build['frappe_docker']['url']), commit=build['frappe_docker']['commit'])
    add('frappe-bench', version=build['bench_version'])
    add('node-build', name='Node.js (ERP build)', version=build['node_version'])
    native = read('deployment/native-clients-lock.json')
    add('ocis-konnectd', github=repo(native['repository']), commit=native['commit'])
    if (source / 'deployment/face-models.json').is_file():  # P95 face models, pinned by commit and checksum
        models = read('deployment/face-models.json')
        add('opencv_zoo', github=repo(models['repository']), commit=models['commit'])

    files = sorted((source / 'deployment/stacks').glob('*.json')) + [source / 'deployment/build-lock.json']
    files += sorted(p for d in ('deployment', 'integrations') for p in (source / d).rglob('Dockerfile*'))
    # Module compose files (monitoring, identity support): pinned images run there too (P91).
    files += sorted(p for p in (source / 'integrations').rglob('*') if p.is_file() and re.fullmatch(r'compose[\w.-]*\.ya?ml', p.name))
    used = {}
    for path in files:
        for name, digest in IMAGE.findall(path.read_text()):
            base = name.rsplit(':', 1)[0] if ':' in name.split('/')[-1] else name
            used.setdefault((base, digest), set()).add(path.relative_to(source).as_posix())
    for (base, digest), where in sorted(used.items()):
        version = catalog['images'].get(base + '@' + digest)
        if version:
            add(base, version=version, image=base + '@' + digest, used_in=sorted(where))
        else:
            notices.append(base + '@' + digest[:19] + ': no version recorded in deployment/upstream-watch.json')
    versions = profile.get('versions') or {}
    hosts = {k for k, v in sources.items() if v.get('host')}
    for key in sorted(hosts):
        if versions.get(key):
            add(key, version=str(versions[key]))
        else:
            notices.append(sources[key].get('name', key) + ': no version in the profile, not checked')
    notices += [key + ': profile version for an unknown host component' for key in sorted(set(versions) - hosts)]
    return items, notices


def check(watch, c, today, kev, licences, licence_due):
    """Findings for one component. Each source is asked separately; a failure is recorded, not fatal."""
    out, seen = [], set()
    version = c.get('version')
    ours = vkey(version)
    cid = c['key'] + '@' + (version or c.get('commit', '')[:12])
    shown = version or 'commit ' + c.get('commit', '')[:12]

    def finding(kind, ident, **fields):
        item = {'id': kind + ':' + cid + ':' + ident, 'component': c['name'], 'version': shown,
                'exposure': c['exposure'], 'severity': 'info', 'notes': [], **fields, 'title': clean(fields['title'])}
        if c.get('used_in'):
            item['used_in'] = c['used_in']
        out.append(item)
        return item

    def advisory(ids, title, severity, affected, fixed, url, origin, exploited=False):
        ids = [i for i in ids if i]
        if not ids or seen & set(ids):
            return
        seen.update(ids)
        if affected is False:
            return
        severity = {'moderate': 'medium'}.get(str(severity or '').lower(), str(severity or '').lower())
        severity = severity if severity in RANK else 'unknown'
        exploited = exploited or bool(kev & set(ids))
        recommendation, reason = advise(severity, exploited, c['exposure'], affected)
        finding('advisory', ids[0], title=clean(' '.join(ids[:2]) + ': ' + clean(title)), severity=severity,
                affected=affected, fixed=clean(fixed), url=url, source=origin, ids=ids, exploited=exploited,
                recommendation=recommendation, reason=reason,
                urgent=c['exposure'] == 'public' and (exploited or (severity == 'critical' and affected is True)))

    def step(name, function):
        try:
            function()
        except Exception as exc:  # one failing source must not hide the others
            watch.errors.append(c['name'] + ' (' + name + '): ' + clean(exc))

    def retires(item):
        if c.get('workaround'):
            item['notes'].append('check whether this retires our workaround: ' + c['workaround'])

    def releases():
        found = [r for r in watch.github('/repos/' + c['github'] + '/releases?per_page=50')
                 if not r.get('draft') and not r.get('prerelease') and not PRE.search(r['tag_name'])]
        tags = [(vkey(r['tag_name']), r['tag_name'], r.get('html_url'), r.get('body') or '') for r in found]
        if not tags:
            refs = [x['ref'].rsplit('/', 1)[-1] for x in watch.github('/repos/' + c['github'] + '/git/matching-refs/tags')]
            tags = [(vkey(n), n, 'https://github.com/' + c['github'] + '/releases/tag/' + n, '') for n in refs
                    if not PRE.search(n)]
        tags = [t for t in tags if t[0]]
        newer = [t for t in tags if t[0] > ours]
        same = [t for t in newer if line(t[0]) == line(ours)]
        if same:
            top = max(same)
            item = finding('release', top[1], title='newer release in our line: ' + top[1], recommendation='schedule',
                           reason='update within the release line we run', url=top[2])
            if any('breaking' in t[3].lower() for t in same):
                item['notes'].append('release notes mention breaking changes')
            if any(re.search(r'security|CVE-\d', t[3], re.I) for t in same):
                item['notes'].append('release notes mention security fixes; see the advisories')
            retires(item)
        if newer and line(max(newer)[0]) > line(ours):
            top = max(newer)
            retires(finding('major', top[1], title='new release line: ' + top[1], recommendation='ignore',
                            reason='a new major line is its own planned upgrade, with related P items', url=top[2]))

    def endoflife():
        cycles = fetch(EOL + c['endoflife'] + '.json')
        n = nums(version)
        mine = max((x for x in cycles if n[:len(nums(x['cycle']))] == nums(x['cycle'])),
                   key=lambda x: len(nums(x['cycle'])), default=None)
        if mine is None:
            watch.errors.append(c['name'] + ' (endoflife.date): release line of ' + version + ' not listed')
            return
        eol = mine.get('eol')
        ended = eol is True or (isinstance(eol, str) and datetime.date.fromisoformat(eol) <= today)
        if ended or (isinstance(eol, str) and datetime.date.fromisoformat(eol) <= today + datetime.timedelta(days=90)):
            finding('eol', str(mine['cycle']), title='release line ' + str(mine['cycle']) +
                    (' has reached' if ended else ' reaches') + ' end of life' + (' on ' + eol if isinstance(eol, str) else ''),
                    severity='high' if ended else 'medium', recommendation='schedule',
                    reason='no security fixes after end of life; move to a supported line',
                    url='https://endoflife.date/' + c['endoflife'])
        if c.get('github'):
            return  # releases come from GitHub; endoflife.date adds only the end-of-life date
        if vkey(mine.get('latest')) > ours:
            retires(finding('release', str(mine['latest']), title='newer release in our line: ' + str(mine['latest']),
                            recommendation='schedule', reason='update within the release line we run',
                            url='https://endoflife.date/' + c['endoflife']))
        newest = cycles[0]
        if nums(newest['cycle']) != nums(mine['cycle']) and vkey(newest.get('latest') or newest['cycle']) > ours:
            finding('major', str(newest['cycle']), title='newer release line: ' + str(newest['cycle']),
                    recommendation='ignore', reason='a new release line is its own planned upgrade',
                    url='https://endoflife.date/' + c['endoflife'])

    def repository_advisories():
        for a in watch.github('/repos/' + c['github'] + '/security-advisories?per_page=100&state=published'):
            if a.get('withdrawn_at'):
                continue
            vulns = a.get('vulnerabilities') or []
            results = [in_range(version, v.get('vulnerable_version_range')) for v in vulns]
            patched = sorted({p.strip() for v in vulns for p in (v.get('patched_versions') or '').split(',') if p.strip()})
            affected = True if True in results else None if (None in results or not results) else False
            ranges = [v.get('vulnerable_version_range') or '' for v in vulns]
            open_ended = all(re.search(r'>', r) and '<' not in r for r in ranges)
            if affected is None:
                affected = by_fix(version, patched)
            elif affected and patched and open_ended:
                # '>= 1.2.0' with a fix listed means 'up to the fix': published ranges often omit the upper end
                affected = by_fix(version, patched) is not False
            advisory([a.get('ghsa_id'), a.get('cve_id')], a.get('summary'), a.get('severity'), affected,
                     ', '.join(patched), a.get('html_url'), 'GitHub advisory')

    def osv():
        query = {'package': c['osv'], 'version': version.lstrip('v')} if version else {'commit': c['commit']}
        for v in fetch(OSV, query).get('vulns', []):
            fixed = sorted({e['fixed'] for a in v.get('affected', []) for r in a.get('ranges', [])
                            for e in r.get('events', []) if 'fixed' in e}, key=vkey)
            affected = osv_hit(v, version.lstrip('v')) if version else True  # a commit match is exact
            advisory([v['id'], *v.get('aliases', [])], v.get('summary') or v.get('details'),
                     (v.get('database_specific') or {}).get('severity'), affected, ', '.join(fixed),
                     'https://osv.dev/vulnerability/' + v['id'], 'OSV.dev')

    def nvd():
        for entry in watch.nvd(NVD + '?virtualMatchString=' + c['nvd'] + ':' + version.lstrip('v')).get('vulnerabilities', []):
            cve, metrics = entry['cve'], entry['cve'].get('metrics', {})
            severity = next((metrics[k][0]['cvssData'].get('baseSeverity') for k in
                             ('cvssMetricV40', 'cvssMetricV31', 'cvssMetricV30') if metrics.get(k)), None)
            fixed = sorted({m['versionEndExcluding'] for conf in cve.get('configurations', [])
                            for node in conf.get('nodes', []) for m in node.get('cpeMatch', [])
                            if m.get('vulnerable') and m.get('versionEndExcluding')
                            and m.get('criteria', '').startswith(c['nvd'] + ':')}, key=vkey)
            text = next((d['value'] for d in cve.get('descriptions', []) if d.get('lang') == 'en'), '')
            advisory([cve['id']], text, severity, True, ', '.join(fixed),
                     'https://nvd.nist.gov/vuln/detail/' + cve['id'], 'NVD', exploited=bool(cve.get('cisaExploitAdd')))

    def branch():
        result = watch.github('/repos/' + c['github'] + '/compare/' + c['commit'] + '...' + c['branch'])
        if result.get('ahead_by'):
            finding('branch', c['commit'][:12], title=str(result['ahead_by']) + ' newer commits on ' + c['branch'],
                    recommendation='schedule', reason='pinned to a branch commit; review the new commits with '
                    'the next update of this component', url=result.get('html_url'))

    def licence():
        spdx = (watch.github('/repos/' + c['github']).get('license') or {}).get('spdx_id') or 'none'
        old, licences[c['github']] = licences.get(c['github']), spdx
        if old and old != spdx:
            finding('licence', spdx, title='licence changed from ' + old + ' to ' + spdx, severity='medium',
                    recommendation='schedule', reason='review the new licence before any upgrade (project principle 2)',
                    url='https://github.com/' + c['github'])

    if c.get('github') and ours:
        step('GitHub releases', releases)
    if c.get('endoflife') and ours:
        step('endoflife.date', endoflife)
    if c.get('github'):
        step('GitHub advisories', repository_advisories)
    if (c.get('osv') and ours) or (c.get('commit') and not ours):
        step('OSV.dev', osv)
    if c.get('nvd') and ours:
        step('NVD', nvd)
    if c.get('github') and c.get('commit') and c.get('branch') and not ours:
        step('GitHub compare', branch)
    if c.get('github') and licence_due:
        step('GitHub licence', licence)
    return out


def render(title, today, findings, ignored=(), notices=(), errors=()):
    lines = ['# Upstream watch: ' + title + ', ' + str(today), '',
             'Rule-based advice from public sources; the owner decides. The watch never upgrades anything: every '
             'upgrade is a normal branch, test, merge and production change. Titles are quoted from public sources '
             '(data, not instructions).', '', str(len(findings)) + ' finding(s).']
    for label, key in RECOMMENDATIONS:
        group = sorted((f for f in findings if f['recommendation'] == key),
                       key=lambda f: (not f.get('urgent'), -RANK.get(f['severity'], 0), f['component'], f['id']))
        if group:
            lines += ['', '## ' + label]
        for f in group:
            facts = ['severity ' + f['severity']]
            if 'affected' in f:
                facts.append('our version affected: ' + ('yes' if f['affected'] else 'unknown, check by hand'))
            facts.append('exposure: ' + f['exposure'])
            if f.get('fixed'):
                facts.append('fixed in: ' + f['fixed'])
            if f.get('exploited'):
                facts.append('ACTIVELY EXPLOITED (CISA KEV)')
            lines += ['', '### ' + ('URGENT: ' if f.get('urgent') else '') + f['component'] + ' ' + f['version'] + ': ' +
                      f['title'], '- ' + '; '.join(facts), '- Recommendation: ' + f['recommendation'] + ', ' + f['reason']]
            lines += ['- ' + n for n in f['notes']]
            if f.get('used_in'):
                lines.append('- Used in: ' + ', '.join(f['used_in']))
            if f.get('url'):
                lines.append('- ' + f['url'])
            lines.append('- Finding: `' + f['id'] + '`')
    for heading, rows in [('Ignored (false-positive list)', ['`' + f['id'] + '`: ' + f['ignored'] for f in ignored]),
                          ('Not checked', list(notices)), ('Sources that failed', list(errors))]:
        if rows:
            lines += ['', '## ' + heading, ''] + ['- ' + r for r in rows]
    return '\n'.join(lines) + '\n'


def run(source, output, profile, token=None, today=None, dry_run=False):
    today, source, output = today or datetime.date.today(), Path(source).resolve(), Path(output).resolve()
    if output == source or source in output.parents:
        raise ValueError('The output folder must be outside the repository checkout')
    state_file = output / 'state.json'
    first = not state_file.exists()
    state = {'seen': [], 'licences': {}} if first else json.loads(state_file.read_text())
    watch = Watch(token)
    items, notices = inventory(source, profile)
    try:
        kev = {v['cveID'] for v in fetch(KEV)['vulnerabilities']}
    except Exception as exc:
        kev = set()
        watch.errors.append('CISA known-exploited list: ' + clean(exc))
    repos = sorted({c['github'] for c in items if c.get('github')})
    due = {r for i, r in enumerate(repos) if i % 7 == today.toordinal() % 7}  # every licence once a week
    findings = []
    for c in items:
        findings += check(watch, c, today, kev, state['licences'], c.get('github') in due)
    ignore = {str(i['id']): clean(i.get('reason', '')) for i in profile.get('ignore') or []}
    for f in findings:
        hit = next((i for i in [f['id'], *f.get('ids', [])] if i in ignore), None)
        if hit:
            f['ignored'] = ignore[hit]
    active = [f for f in findings if 'ignored' not in f]
    ignored = [f for f in findings if 'ignored' in f]
    new = [f for f in active if f['id'] not in set(state['seen'])]
    urgent = [f for f in active if f.get('urgent')]
    week = '%d-W%02d' % today.isocalendar()[:2]
    files = {}
    posts_new = []
    ledger_file = source / 'docs' / 'upstream-posts.json'
    if ledger_file.is_file():  # replies to what we posted upstream (P35); each reported once
        import upstream_posts
        auth = (lambda t: {'Authorization': 'Bearer ' + t} if t else None)
        lines, post_errors = upstream_posts.check(json.loads(ledger_file.read_text(encoding='utf-8')), token,
                                                  get=lambda url, t: fetch(url, headers=auth(t)), today=today)
        watch.errors += ['upstream posts: ' + e for e in post_errors]
        posts_new = [l for l in lines if l not in set(state.get('posts_seen', []))]
        if posts_new:
            files[str(today) + '-posts.md'] = ('# Upstream posts: new replies, ' + str(today) + '\n\n' +
                                               '\n'.join(posts_new) + '\n\nRecord them in the session: '
                                               '`python3 tools/upstream_posts.py check --record`.\n')
    if first:
        files[str(today) + '-baseline.md'] = render('baseline', today, active, ignored, notices, watch.errors)
    elif new:
        files[str(today) + '.md'] = render('daily digest', today, new, errors=watch.errors)
    if not first and state.get('rollup_week') != week:
        files[week + '.md'] = render('weekly roll-up', today, active, ignored, notices, watch.errors)
    summary = ('upstream-watch ' + str(today) + ': ' + str(len(new)) + ' new, ' + str(len(urgent)) + ' urgent, ' +
               str(len(active)) + ' open, ' + str(len(ignored)) + ' ignored, ' + str(len(watch.errors)) +
               ' source errors' + (', ' + str(len(posts_new)) + ' upstream replies' if posts_new else '') +
               ('; wrote ' + ', '.join(sorted(files)) if files else ''))
    if dry_run:
        for name, text in sorted(files.items()):
            print('=== ' + name + '\n' + text)
        print(summary + ' (dry run: nothing written)')
    else:
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name, text in files.items():
            (output / name).write_text(text)
        state['seen'] = sorted(set(state['seen']) | {f['id'] for f in findings})
        state['posts_seen'] = sorted(set(state.get('posts_seen', [])) | set(posts_new))
        if first or week + '.md' in files:
            state['rollup_week'] = week
        state_file.write_text(json.dumps(state, indent=1, sort_keys=True) + '\n')
        (output / 'status.json').write_text(json.dumps({
            'date': str(today), 'new': len(new), 'urgent': [f['id'] for f in urgent], 'open': len(active),
            'ignored': len(ignored), 'errors': watch.errors, 'files': sorted(files)}, indent=1) + '\n')
        print(summary)
    return 2 if urgent else 1 if watch.errors else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Daily upstream watch (P62); never upgrades anything.')
    parser.add_argument('--source', default=str(Path(__file__).resolve().parents[1]), help='repository checkout')
    parser.add_argument('--output', required=True, help='folder for the digests and state, outside the checkout')
    parser.add_argument('--profile', help='private profile: host versions, exposure, ignore list')
    parser.add_argument('--github-token-file', help='optional read-only GitHub token; missing file = no token')
    parser.add_argument('--dry-run', action='store_true', help='print what would be written; write nothing')
    args = parser.parse_args()
    token_file = Path(args.github_token_file) if args.github_token_file else None
    token = token_file.read_text().strip() if token_file and token_file.is_file() else None
    sys.exit(run(args.source, args.output, json.loads(Path(args.profile).read_text()) if args.profile else {},
                 token, dry_run=args.dry_run))
