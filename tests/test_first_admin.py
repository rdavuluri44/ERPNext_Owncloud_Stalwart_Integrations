"""First administrator setup (P77): packaging and safety checks; no live identity changes."""
import ast
import json
import re
import subprocess
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "integrations/authentik/first-admin"
REQUIRED = {
    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd",  # Apple Passwords
    "dd4ec289-e01d-41c9-bb89-70fa845d4bf2",  # Apple Passwords (managed)
    "d548826e-79b4-db40-a3d8-11116f7e8349",  # Bitwarden / Vaultwarden
    "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4",  # Google Password Manager
    "adce0002-35bc-c60a-648b-0b25f1f05503",  # Chrome on Mac
}


def constant(tree, name):
    return next(n.value.value for n in tree.body if isinstance(n, ast.Assign)
                and getattr(n.targets[0], "id", None) == name)


class FirstAdmin(unittest.TestCase):
    def setUp(self):
        self.source = (MODULE / "first_admin.py").read_text()
        self.tree = ast.parse(self.source)

    def test_provider_list_is_the_approved_set(self):
        providers = json.loads((MODULE.parent / "passkey-providers.json").read_text())["providers"]
        aaguids = [p["aaguid"].lower() for p in providers]
        self.assertEqual(set(aaguids), REQUIRED)
        self.assertEqual(len(aaguids), len(set(aaguids)))
        for value in aaguids:
            self.assertRegex(value, r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

    def test_policies_compile(self):
        for name in ("LOAD_IDENTITY", "PASSKEY_READY"):
            body = constant(self.tree, name).replace("__ALLOWED__", "set()")
            compile("def policy():\n" + "\n".join("    " + l for l in body.splitlines()), name, "exec")

    def test_link_is_single_use_expiring_and_scoped(self):
        self.assertIn("single_use=True, expiring=True", self.source)
        self.assertEqual(constant(self.tree, "LINK_HOURS"), 24)
        load = constant(self.tree, "LOAD_IDENTITY")
        self.assertIn('invite.flow.slug != "first-admin-passkey-setup"', load)
        self.assertIn("user.has_usable_password()", load)

    def test_administrator_is_passkey_only(self):
        self.assertIn("admin.set_unusable_password()", self.source)
        self.assertIn('"user_verification": "required"', self.source)
        self.assertIn("passkey.device_type_restrictions.set(types)", self.source)

    def test_akadmin_is_switched_off_not_deleted(self):
        body = self.source[self.source.index("def switch_off_akadmin"):self.source.index("@transaction.atomic")]
        self.assertNotRegex(body, r"\.delete\(\)\s*$|akadmin\.delete")
        for step in ("akadmin.is_active = False", "akadmin.set_password(", "akadmin.groups.clear()",
                     "Token.objects.filter(user=akadmin).delete()", "not akadmin.has_usable_password()"):
            self.assertIn(step, body)

    def test_akadmin_only_mode_keeps_an_administrator(self):
        body = self.source[self.source.index("def akadmin_only"):self.source.index("def run")]
        self.assertIn("no other active administrator with a passkey", body)
        self.assertIn("switch_off_akadmin()", body)
        self.assertNotIn("set_unusable_password", body)
        self.assertIn('os.environ.get("FIRST_ADMIN_MODE") == "akadmin-only"', self.source)
        script = (MODULE / "first-admin.sh").read_text()
        self.assertIn("--akadmin-only", script)
        self.assertIn("-e FIRST_ADMIN_MODE=akadmin-only", script)

    def test_wrapper_never_echoes_secrets_or_traces(self):
        script = (MODULE / "first-admin.sh").read_text()
        subprocess.run(["sh", "-n", str(MODULE / "first-admin.sh")], check=True)
        self.assertIn("set -eu", script)
        self.assertNotRegex(script, r"set -[a-z]*x")
        self.assertIn("</dev/tty", script)
        self.assertTrue((MODULE / "first-admin.sh").stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
