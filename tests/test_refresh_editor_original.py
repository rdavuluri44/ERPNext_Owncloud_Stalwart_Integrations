"""P91: the ONLYOFFICE original is refreshed from the image itself, without starting it."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_editor_original', ROOT / 'tools/refresh_editor_original.py')
tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
NEW = 'onlyoffice/documentserver@sha256:' + 'b' * 64
PAGE = b'<html>new upstream start page</html>\n'


def tar_of(content):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as tar:
        info = tarfile.TarInfo('editor-wopi.ejs'); info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class FakeDocker:
    def __init__(self):
        self.calls = []

    def __call__(self, args, check, capture_output):
        self.calls.append(args[1:])
        out = {'create': b'c0ffee\n', 'cp': tar_of(PAGE), 'rm': b''}[args[1]]
        return subprocess.CompletedProcess(args, 0, out, b'')


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.record = self.dir / 'upstream.json'
        self.record.write_text((ROOT / 'integrations/onlyoffice/upstream.json').read_text())
        self.original = self.dir / 'editor-wopi.original.ejs'

    def test_copies_the_page_without_starting_the_image_and_updates_the_record(self):
        fake = FakeDocker()
        data = tool.refresh(NEW, '10.0.1 build 23', run=fake, record=self.record, original=self.original,
                            today=datetime.date(2026, 12, 1))
        self.assertEqual(self.original.read_bytes(), PAGE)
        self.assertEqual(data['original_sha256'], hashlib.sha256(PAGE).hexdigest())
        self.assertEqual(json.loads(self.record.read_text())['image'], NEW)
        self.assertTrue(data['checked'].startswith('1 December 2026'))
        self.assertEqual([c[0] for c in fake.calls], ['create', 'cp', 'rm'])
        self.assertIn('--network', fake.calls[0])
        self.assertNotIn('start', [c[0] for c in fake.calls])

    def test_refuses_an_image_not_pinned_by_digest(self):
        with self.assertRaises(ValueError):
            tool.refresh('onlyoffice/documentserver:latest', 'x', run=FakeDocker(), record=self.record,
                         original=self.original)


if __name__ == '__main__':
    unittest.main()
