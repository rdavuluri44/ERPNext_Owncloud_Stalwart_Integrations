#!/usr/bin/env python3
"""Refresh the ONLYOFFICE original start page from a pinned image (P91, register OFFICE-1).

Run on a host with Docker when the ONLYOFFICE image changes:

    tools/refresh_editor_original.py --image onlyoffice/documentserver@sha256:<digest> --version "10.0.1 build 23"

It creates a stopped container (no network, never started), copies the image's own
start page to integrations/onlyoffice/editor-wopi.original.ejs, removes the container
and writes the image, version and checksum to integrations/onlyoffice/upstream.json.
Then re-apply the marked cloud-integrations changes to editor-wopi.ejs against the new
original, and change the image pin in the stack and the upstream watch: the tests fail
until all three agree.
"""
import argparse
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'integrations/onlyoffice/upstream.json'
ORIGINAL = ROOT / 'integrations/onlyoffice/editor-wopi.original.ejs'
IMAGE = re.compile(r'^onlyoffice/documentserver@sha256:[0-9a-f]{64}$')


def docker(*args, run=subprocess.run):
    return run(['docker', *args], check=True, capture_output=True).stdout


def extract(image, path, run=subprocess.run):
    """The file at `path` inside `image`, without starting the image."""
    container = docker('create', '--network', 'none', image, run=run).decode().strip()
    try:
        archive = docker('cp', f'{container}:{path}', '-', run=run)
    finally:
        docker('rm', container, run=run)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        member = next(m for m in tar.getmembers() if m.isfile())
        return tar.extractfile(member).read()


def refresh(image, version, run=subprocess.run, record=RECORD, original=ORIGINAL, today=None):
    if not IMAGE.match(image):
        raise ValueError('Pin the image by digest: onlyoffice/documentserver@sha256:<64 hex>')
    data = json.loads(record.read_text())
    content = extract(image, data['start_page'], run=run)
    original.write_bytes(content)
    data.update(image=image, version=version, original_sha256=hashlib.sha256(content).hexdigest(),
                checked=f"{(today or datetime.date.today()).strftime('%d %B %Y').lstrip('0')}: "
                        'extracted from the pinned image with tools/refresh_editor_original.py')
    record.write_text(json.dumps(data, indent=2) + '\n')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--image', required=True)
    parser.add_argument('--version', required=True, help='for example "10.0.1 build 23"')
    args = parser.parse_args()
    result = refresh(args.image, args.version)
    print(f"original start page {result['original_sha256']} from {result['image']}")
    print('Next: re-apply the cloud-integrations changes to editor-wopi.ejs, change the image in '
          'deployment/stacks/editor-onlyoffice.compose.json and deployment/upstream-watch.json, run the tests.')
