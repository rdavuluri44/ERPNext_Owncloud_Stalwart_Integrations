"""P59: container logs are saved before a recreate, root-only, compressed, kept 30 days."""
import datetime
import gzip
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import archive_container_logs as tool  # noqa: E402


def fake_docker(calls):
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[:2] == ["docker", "ps"]:
            return SimpleNamespace(stdout="a1 ocis-abc\nb2 collaboration-abc\nc3 web/odd name\n")
        return SimpleNamespace(stdout=b"2026-11-26T10:00:00Z out " + cmd[-1].encode() + b"\n", stderr=b"err line\n")
    return run


class ArchiveLogs(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp()) / "logs"
        self.now = datetime.datetime(2026, 11, 26, 14, 30, 5)

    def test_every_container_is_saved_with_stdout_and_stderr(self):
        calls = []
        written, size, removed = tool.archive(self.dest, (), 30, self.now, fake_docker(calls))
        self.assertEqual(written, 3)
        files = sorted((self.dest / "2026-11-26").iterdir())
        self.assertEqual([f.name for f in files], ["143005-collaboration-abc.log.gz", "143005-ocis-abc.log.gz",
                                                   "143005-web_odd_name.log.gz"])
        text = gzip.decompress(files[1].read_bytes())
        self.assertIn(b"out a1", text)
        self.assertIn(b"err line", text)
        self.assertIn(["docker", "logs", "--timestamps", "a1"], calls)

    def test_name_filter(self):
        written, _, _ = tool.archive(self.dest, ["ocis"], 30, self.now, fake_docker([]))
        self.assertEqual(written, 1)

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_root_only_permissions(self):
        tool.archive(self.dest, (), 30, self.now, fake_docker([]))
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.dest / "2026-11-26").stat().st_mode), 0o700)
        for f in (self.dest / "2026-11-26").iterdir():
            self.assertEqual(stat.S_IMODE(f.stat().st_mode), 0o600)

    def test_old_folders_are_removed_and_others_kept(self):
        for name in ("2026-10-26", "2026-10-27", "notes"):
            (self.dest / name).mkdir(parents=True)
        _, _, removed = tool.archive(self.dest, (), 30, self.now, fake_docker([]))
        self.assertEqual(removed, 1)
        self.assertFalse((self.dest / "2026-10-26").exists())
        self.assertTrue((self.dest / "2026-10-27").exists())
        self.assertTrue((self.dest / "notes").exists())

    def test_promotion_plan_starts_with_archiving(self):
        import promotion_plan as pp
        result = {"stacks": {"erp": {"files": ["x"], "steps": [], "restart": []}}, "live": [], "not_covered": [],
                  "unclassified": []}
        text = pp.render(result, "sample")
        self.assertLess(text.index("archive_container_logs.py"), text.index("### erp"))
        none = {"stacks": {}, "live": [], "not_covered": [], "unclassified": []}
        self.assertNotIn("archive_container_logs.py", pp.render(none, "docs"))


if __name__ == "__main__":
    unittest.main()
