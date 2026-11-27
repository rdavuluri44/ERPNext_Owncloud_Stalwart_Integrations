#!/usr/bin/env python3
"""Fetch the face models of P95 into a folder, refusing any file whose SHA-256 differs from the pin.

    python3 tools/fetch_face_models.py --output /opt/face-models

Reads `deployment/face-models.json` (repository, exact commit, files with their checksums and licences). Runs at
ERP add-on image build (deployment/erp/Dockerfile.addon). A changed or replaced upstream file stops the build; the
pin is changed only through a pull request that repeats the adoption check (register BUILD-11).
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

PINS = Path(__file__).resolve().parents[1] / 'deployment' / 'face-models.json'


def url_for(pins, item):
    repo = pins['repository'].removeprefix('https://github.com/')
    host = 'https://media.githubusercontent.com/media/' if item['lfs'] else 'https://raw.githubusercontent.com/'
    return f"{host}{repo}/{pins['commit']}/{item['path']}"


def download(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'fetch-face-models'})
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def fetch(output, pins=None, get=download):
    pins = pins or json.loads(PINS.read_text(encoding='utf-8'))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for item in pins['files']:
        data = get(url_for(pins, item))
        digest = hashlib.sha256(data).hexdigest()
        if digest != item['sha256']:
            raise RuntimeError(f"{item['path']}: checksum {digest} differs from the pin {item['sha256']}")
        (output / item['target']).write_bytes(data)
    (output / 'model-id').write_text(pins['model_id'] + '\n', encoding='utf-8')
    (output / 'SOURCE').write_text(
        f"Face models from {pins['repository']} at commit {pins['commit']} (OpenCV Zoo). SFace is Apache-2.0\n"
        f"(LICENSE.sface), YuNet is MIT (LICENSE.yunet). Checksums: deployment/face-models.json.\n", encoding='utf-8')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch the pinned face models (P95).')
    parser.add_argument('--output', required=True)
    parser.add_argument('--pins', default=str(PINS), help='the pin file (inside the image build)')
    args = parser.parse_args()
    try:
        print('face models in ' + str(fetch(args.output, json.loads(Path(args.pins).read_text(encoding='utf-8')))))
    except Exception as error:
        print('face models refused: ' + str(error), file=sys.stderr)
        sys.exit(1)
