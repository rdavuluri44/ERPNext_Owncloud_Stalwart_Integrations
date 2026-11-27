"""P90: Coolify's proxy image is pinned by tag and digest, and only the Traefik image line changes."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import coolify_proxy_image as tool  # noqa: E402

COMPOSE = """name: coolify-proxy
networks:
  coolify:
    external: true
services:
  traefik:
    container_name: coolify-proxy
    image: 'traefik:v3.7'
    restart: unless-stopped
    command:
      - '--entrypoints.https.address=:443'
"""
PIN = "traefik:v3.7.20@sha256:" + "a" * 64


class ProxyImage(unittest.TestCase):
    def test_repository_pin_is_tag_and_digest(self):
        pin = tool.pinned()
        self.assertRegex(pin["image"], r"^traefik:v\d+\.\d+\.\d+@sha256:[0-9a-f]{64}$")
        self.assertIn("v" + pin["version"] + "@", pin["image"])

    def test_pin_must_match_its_version(self):
        path = Path(tempfile.mkdtemp()) / "pin.json"
        path.write_text('{"image": "traefik:v3.7.19@sha256:' + "b" * 64 + '", "version": "3.7.20"}')
        with self.assertRaises(ValueError):
            tool.pinned(path)
        path.write_text('{"image": "traefik:v3.7", "version": "3.7"}')
        with self.assertRaises(ValueError):
            tool.pinned(path)

    def test_only_the_image_line_changes(self):
        out = tool.apply(COMPOSE, PIN)
        self.assertIn("    image: '" + PIN + "'\n", out)
        before = [l for l in COMPOSE.splitlines() if "image:" not in l]
        after = [l for l in out.splitlines() if "image:" not in l]
        self.assertEqual(before, after)
        self.assertEqual(tool.apply(out, PIN), out)          # idempotent
        self.assertEqual(tool.current(out), PIN)

    def test_unquoted_and_double_quoted_lines(self):
        for line in ("    image: traefik:v3.7\n", '    image: "traefik:v3.6.2"\n'):
            self.assertIn(PIN, tool.apply("services:\n  traefik:\n" + line, PIN))

    def test_refuses_a_compose_without_or_with_two_traefik_images(self):
        with self.assertRaises(ValueError):
            tool.apply("services:\n  x:\n    image: nginx\n", PIN)
        with self.assertRaises(ValueError):
            tool.apply(COMPOSE + "  other:\n    image: traefik:v2\n", PIN)


if __name__ == "__main__":
    unittest.main()
