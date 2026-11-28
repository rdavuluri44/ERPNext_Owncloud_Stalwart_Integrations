#!/usr/bin/env python3
"""Write the list of applications the Desk's About popup shows, with their versions (P111).

The versions come from ``deployment/upstream-watch.json``, which records the version behind every pinned image
digest (a test fails when a digest changes without its version there), so About cannot name a version we do not
run. ``--check`` fails when the packaged list differs from what this tool would write.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCH = ROOT / 'deployment' / 'upstream-watch.json'
TARGET = ROOT / 'erpnext_drive_integrations' / 'portal' / 'components.json'
# What a person recognises as an application comes first; the machinery follows in the catalog's order.
FIRST = ['owncloud/ocis', 'onlyoffice/documentserver', 'stalwartlabs/stalwart', 'ghcr.io/paperless-ngx/paperless-ngx',
         'ghcr.io/goauthentik/server', 'ghcr.io/element-hq/synapse', 'ghcr.io/element-hq/element-web',
         'ghcr.io/element-hq/matrix-authentication-service']


def components():
    watch = json.loads(WATCH.read_text(encoding='utf-8'))
    versions = {}
    for image, version in watch['images'].items():
        versions.setdefault(image.split('@')[0], [])
        if version not in versions[image.split('@')[0]]:
            versions[image.split('@')[0]].append(version)
    rows = []
    for key in FIRST + [k for k in versions if k not in FIRST]:
        if key not in versions:
            continue
        source = watch['sources'].get(key, {})
        row = {'name': source.get('name') or key, 'version': ', '.join(sorted(versions[key]))}
        if source.get('github'):
            row['repository'] = 'https://github.com/' + source['github']
        rows.append(row)
    return {'note': 'Written by tools/about_components.py from deployment/upstream-watch.json; do not edit by hand.',
            'components': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = json.dumps(components(), indent=2, ensure_ascii=False) + '\n'
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding='utf-8') != text:
            raise SystemExit('components.json is out of date: run tools/about_components.py')
        return
    TARGET.write_text(text, encoding='utf-8', newline='\n')
    print('written', len(json.loads(text)['components']), 'components')


if __name__ == '__main__':
    main()
