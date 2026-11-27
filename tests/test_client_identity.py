"""P84: client identity stays out of the public repository; the check holds fingerprints, never the words."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_client_identity as check  # noqa: E402
from rehearse_cripple import audit_domains  # noqa: E402


def table(*terms):
    folder = tempfile.mkdtemp()
    path = Path(folder) / "fingerprints"
    path.write_text("# test\n" + "\n".join(f"{len(t)}:{check.fingerprint(t)}" for t in terms) + "\n")
    return check.load(path)


class ClientIdentity(unittest.TestCase):
    def test_fingerprints_do_not_contain_the_words(self):
        text = check.FINGERPRINTS.read_text()
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            length, digest = line.split(":")
            self.assertTrue(length.isdigit())
            self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_whole_word_any_case_and_inside_longer_names(self):
        t = table("acmebuild", "abc")
        self.assertEqual(check.hits("Built by AcmeBuild Ltd", t), [1])
        self.assertEqual(check.hits("x\nlogo: acmebuild_logo.svg", t), [2])
        self.assertEqual(check.hits("const acmebuildApp = 1", t), [1])
        self.assertEqual(check.hits("mail@acmebuild.in", t), [1])

    def test_short_identifiers_only_as_whole_words(self):
        t = table("abc")
        self.assertEqual(check.hits("ABC site", t), [1])
        self.assertEqual(check.hits("abcdef and xabc", t), [])

    def test_long_random_runs_do_not_match_by_chance(self):
        t = table("acmebuild")
        self.assertEqual(check.hits("sha512-" + "q" * 30 + "acmebuild" + "z" * 30, t), [])

    def test_clean_text_passes(self):
        self.assertEqual(check.hits("Unformat ERP for <tenant>", table("acmebuild")), [])

    def test_the_repository_is_clean(self):
        self.assertEqual(check.scan(check.load()), [])

    def test_rehearsal_takes_private_domains_from_the_profile(self):
        config = {"domain": "test.brand.example.net", "mail_domain": "brand.in",
                  "audit_mail_domains": ["client-co.in", "bad domain"]}
        domains = audit_domains(config)
        self.assertEqual(domains[:4], ["gmail", "yahoo", "outlook", "hotmail"])
        self.assertIn("client-co", domains)
        self.assertIn("brand", domains)
        self.assertNotIn("example", domains)
        self.assertFalse(any(" " in d for d in domains))
        self.assertEqual(audit_domains({}), ["gmail", "yahoo", "outlook", "hotmail"])


if __name__ == "__main__":
    unittest.main()
