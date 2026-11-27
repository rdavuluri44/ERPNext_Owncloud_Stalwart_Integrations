"""Invitation form page: the script can start, and every element it uses exists (P78 regression)."""
import re
import unittest
from pathlib import Path

PUBLIC = Path(__file__).resolve().parents[1] / "integrations/authentik/invite-recovery/public"


class InvitationPage(unittest.TestCase):
    def setUp(self):
        self.script = (PUBLIC / "page.mjs").read_text()
        self.html = (PUBLIC / "index.html").read_text()

    def test_helper_is_defined_before_first_use(self):
        # A top-level use of $ before `const $ =` stops the module, and the page
        # stays on "Checking your administrator session…".
        definition = self.script.index("const $ = ")
        self.assertNotRegex(self.script[:definition], r"\$\(", "the $ helper is used before it is defined")

    def test_every_element_the_script_uses_exists(self):
        used = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', self.script))
        present = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', self.html))
        self.assertEqual(used - present, set())

    def test_back_returns_one_step_or_to_administration(self):
        link = re.search(r'<header><a href="([^"]+)" id="back">([^<]+)</a>', self.html)
        self.assertIsNotNone(link)
        self.assertEqual(link.group(1), "/if/admin/")
        self.assertIn("Back", link.group(2))
        self.assertNotIn(">Cloud<", self.html)
        self.assertIn("history.back()", self.script)
        self.assertIn("new URL(document.referrer).origin === location.origin", self.script)


if __name__ == "__main__":
    unittest.main()
