"""Approved passkey providers are one setting (P79); every copy must match it."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTING = ROOT / "integrations/authentik/passkey-providers.json"
APPROVED = {
    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd",  # Apple Passwords
    "dd4ec289-e01d-41c9-bb89-70fa845d4bf2",  # Apple Passwords (managed)
    "d548826e-79b4-db40-a3d8-11116f7e8349",  # Bitwarden / Vaultwarden
    "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4",  # Google Password Manager
    "adce0002-35bc-c60a-648b-0b25f1f05503",  # Chrome on Mac
}


class PasskeyProviders(unittest.TestCase):
    def test_owner_approved_list(self):
        providers = json.loads(SETTING.read_text())["providers"]
        self.assertEqual({p["aaguid"] for p in providers}, APPROVED)
        self.assertTrue(all(p["name"].strip() for p in providers))

    def test_every_copy_matches_the_setting(self):
        result = subprocess.run([sys.executable, str(ROOT / "tools/sync_passkey_providers.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_no_stray_provider_lists(self):
        # Literal provider lists belong only in the setting and the files the sync tool maintains.
        allowed = {"integrations/authentik/passkey-providers.json", "integrations/authentik/configuration.json",
                   "integrations/authentik/invite-recovery/native_recovery.py",
                   "integrations/authentik/invite-recovery/provider_policy.py",
                   "integrations/authentik/invite-recovery/install_native.py"}
        marker = "adce0002-35bc-c60a-648b-0b25f1f05503"
        found = {str(p.relative_to(ROOT)) for p in (ROOT / "integrations").rglob("*")
                 if p.is_file() and p.suffix in {".py", ".json", ".mjs", ".js"} and marker in p.read_text(errors="ignore")}
        self.assertEqual(found - allowed, set())

    def test_user_facing_text_names_the_approved_providers(self):
        templates = ROOT / "integrations/authentik/invite-recovery/templates/email"
        for path in templates.glob("cloud-*"):
            text = path.read_text()
            self.assertNotIn("Google Password Manager and other providers are not accepted", text, path.name)
            self.assertNotIn("do not save to Google Password Manager", text, path.name)


if __name__ == "__main__":
    unittest.main()
