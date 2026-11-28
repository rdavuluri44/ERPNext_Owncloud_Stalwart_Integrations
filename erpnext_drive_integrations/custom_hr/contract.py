"""The version handshake between the server and the mobile apps (P104; owner, 27 November 2026).

An app that is older than the server's functions should say "update needed" instead of showing strange errors.
`bootstrap` therefore tells the app three things: the server's `version`, the `contract` below, and the oldest app
version this site still accepts (`minimum_app_version`).

The contract is a short fingerprint of what the apps depend on: every function they may call in the modules listed
below (its name, what it takes and what it does in the function itself) and the fields of the records they read.
It is written down here as `FINGERPRINT`, and `tests/test_mobile_contract.py` computes it again from the code: a
change to a mobile-facing function or field fails that test until the fingerprint here is renewed. Whoever renews
it decides, in the same change, whether older apps still work; if they do not, the site's
`mobile_minimum_app_version` is raised when the change is released.

This module needs no Frappe for the fingerprint, so the test and any tool can compute it from a checkout.
"""
import ast
import hashlib
import json
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
# The modules whose whitelisted functions the mobile apps call, and the records whose fields they read.
MODULES = ('custom_hr/api.py', 'drive_store/api.py')
RECORDS = ('custom_hr/doctype/field_attendance_entry/field_attendance_entry.json',
           'custom_hr/doctype/field_face_capture/field_face_capture.json',
           'drive_store/doctype/drive_photo/drive_photo.json')
FINGERPRINT = '90675fcadb3a'
VERSION = re.compile(r'\d{1,4}\.\d{1,4}\.\d{1,4}')
NO_MINIMUM = '0.0.0'


def _whitelisted(node):
    return isinstance(node, ast.FunctionDef) and any('whitelist' in ast.unparse(d) for d in node.decorator_list)


def _function_text(lines, node):
    """The function as written, from its first decorator to its last line, without comment-only lines, blank lines
    and trailing spaces: so a comment or an empty line does not change the fingerprint, and code does."""
    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
    kept = [line.rstrip() for line in lines[start - 1:node.end_lineno]]
    return '\n'.join(line for line in kept if line.strip() and not line.strip().startswith('#'))


def parts(app=APP):
    """What the fingerprint is made of, in a fixed order: (what, text) pairs."""
    found = []
    for module in MODULES:
        source = (Path(app) / module).read_text(encoding='utf-8')
        lines = source.splitlines()
        for node in sorted((n for n in ast.parse(source).body if _whitelisted(n)), key=lambda n: n.name):
            found.append((f'{module}:{node.name}', _function_text(lines, node)))
    for record in RECORDS:
        fields = json.loads((Path(app) / record).read_text(encoding='utf-8'))['fields']
        text = '\n'.join(sorted(f"{f['fieldname']}:{f['fieldtype']}" for f in fields if f.get('fieldname')))
        found.append((record, text))
    return found


def compute(app=APP):
    digest = hashlib.sha256()
    for what, text in parts(app):
        digest.update(what.encode() + b'\0' + text.encode() + b'\0')
    return digest.hexdigest()[:12]


def minimum(value):
    """The oldest app version a site accepts, from its setting. Anything that is not `number.number.number` counts
    as no minimum, so a mistyped setting can never lock every phone out."""
    value = str(value or '').strip()
    return value if VERSION.fullmatch(value) else NO_MINIMUM

