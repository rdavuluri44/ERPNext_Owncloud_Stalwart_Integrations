"""P91: the webmail overlay is tied to the upstream files it was made from (register WEBMAIL-1).

The overlay replaces whole upstream files, so a commit bump alone would silently
undo upstream's changes to them."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


prepare_mail = load('prepare_mail', 'tools/prepare_mail.py')
refresh = load('refresh_webmail_overlay_base', 'tools/refresh_webmail_overlay_base.py')
LOCK = json.loads((ROOT / 'integrations/mail/upstream.json').read_text())
OVERLAY = ROOT / 'integrations/mail/overlay'


def fake_upstream(lock, overlay):
    """A tree whose replaced files match the recorded checksums (contents faked via the overlay itself)."""
    tree = Path(tempfile.mkdtemp())
    new_lock = json.loads(json.dumps(lock))
    for name in lock['overlay_base']['replaced']:
        target = tree / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'upstream ' + name.encode())
        new_lock['overlay_base']['replaced'][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    return tree, new_lock


class OverlayBaseTests(unittest.TestCase):
    def test_record_belongs_to_the_pinned_commit_and_lists_every_overlay_file(self):
        self.assertEqual(LOCK['overlay_base']['commit'], LOCK['commit'],
                         'webmail commit changed: run tools/refresh_webmail_overlay_base.py and merge the overlay')
        files = sorted(p.relative_to(OVERLAY).as_posix() for p in OVERLAY.rglob('*') if p.is_file())
        self.assertEqual(files, sorted([*LOCK['overlay_base']['replaced'], *LOCK['overlay_base']['added']]))

    def test_build_accepts_the_recorded_base(self):
        tree, lock = fake_upstream(LOCK, OVERLAY)
        prepare_mail.check_overlay_base(lock, OVERLAY, tree)

    def test_build_stops_when_upstream_changed_a_file_we_replace(self):
        tree, lock = fake_upstream(LOCK, OVERLAY)
        (tree / 'stores/auth-store.ts').write_text('upstream changed this file')
        with self.assertRaisesRegex(ValueError, 'stores/auth-store.ts'):
            prepare_mail.check_overlay_base(lock, OVERLAY, tree)

    def test_build_stops_when_upstream_adds_a_file_we_add(self):
        tree, lock = fake_upstream(LOCK, OVERLAY)
        (tree / 'lib').mkdir(exist_ok=True); (tree / 'lib/cloud-session.ts').write_text('x')
        with self.assertRaisesRegex(ValueError, 'lib/cloud-session.ts'):
            prepare_mail.check_overlay_base(lock, OVERLAY, tree)

    def test_build_stops_when_only_the_commit_was_bumped(self):
        tree, lock = fake_upstream(LOCK, OVERLAY)
        lock['commit'] = 'f' * 40
        with self.assertRaisesRegex(ValueError, 'commit changed'):
            prepare_mail.check_overlay_base(lock, OVERLAY, tree)

    @unittest.skipUnless(shutil.which('git'), 'git not installed')
    def test_refresh_lists_changed_files_and_writes_only_when_asked(self):
        tree, lock = fake_upstream(LOCK, OVERLAY)
        (tree / 'app/(main)/layout.tsx').write_text('new upstream layout')
        for args in (['init', '-q'], ['-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q',
                                      '--allow-empty', '-m', 'x']):
            subprocess.run(['git', '-C', str(tree), *args], check=True)
        lock_file = Path(tempfile.mkdtemp()) / 'upstream.json'
        lock_file.write_text(json.dumps(lock))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = refresh.main(['--checkout', str(tree)], lock_path=lock_file, overlay=OVERLAY)
        self.assertEqual(code, 1)
        self.assertIn('merge needed: app/(main)/layout.tsx', out.getvalue())
        self.assertEqual(json.loads(lock_file.read_text()), lock)
        with contextlib.redirect_stdout(io.StringIO()):
            refresh.main(['--checkout', str(tree), '--version', '9.9.9', '--write'], lock_path=lock_file, overlay=OVERLAY)
        written = json.loads(lock_file.read_text())
        self.assertEqual(written['version'], '9.9.9')
        self.assertEqual(written['commit'], written['overlay_base']['commit'])
        self.assertEqual(written['overlay_base']['replaced']['app/(main)/layout.tsx'],
                         hashlib.sha256(b'new upstream layout').hexdigest())


if __name__ == '__main__':
    unittest.main()
