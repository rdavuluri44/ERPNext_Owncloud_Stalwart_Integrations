import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from recovery_guard import RECOVERY_FLOW, RecoveryProof, old_keys_to_delete
from provider_policy import ALLOWED_PROVIDERS, allowed_provider


class RecoveryDeletionTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 6, tzinfo=timezone.utc)
        self.proof = RecoveryProof(RECOVERY_FLOW, 7, "test@example.invalid",
                                   self.now + timedelta(hours=1), frozenset({"old-a", "old-b"}),
                                   True, "new-key", True, "d548826e-79b4-db40-a3d8-11116f7e8349")
        self.args = dict(user_id=7, email=self.proof.email, active=True, approved=True,
                         confirmed_keys={"old-a", "old-b", "new-key"}, now=self.now)

    def test_replacement_survives_and_old_keys_are_selected(self):
        self.assertEqual(old_keys_to_delete(self.proof, **self.args), {"old-a", "old-b"})

    def test_concurrent_new_key_is_preserved(self):
        self.args["confirmed_keys"].add("concurrent-key")
        self.assertNotIn("concurrent-key", old_keys_to_delete(self.proof, **self.args))

    def test_missing_proof_abandonment_or_replay_cannot_delete(self):
        for patch in [dict(email_verified=False), dict(replacement_verified=False),
                      dict(replacement_key=""), dict(replacement_key="old-a"),
                      dict(completed=True), dict(flow="ordinary-add-passkey"),
                      dict(replacement_aaguid="bada5566-a7aa-401f-bd96-45619a55120d"),
                      dict(expires=self.now), dict(user_id=8), dict(email="changed@example.invalid")]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                old_keys_to_delete(replace(self.proof, **patch), **self.args)

    def test_revoked_approval_inactive_or_removed_replacement_cannot_delete(self):
        for patch in [dict(approved=False), dict(active=False), dict(confirmed_keys={"old-a", "old-b"})]:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                old_keys_to_delete(self.proof, **{**self.args, **patch})

    def test_approved_providers_allowed(self):
        for aaguid in ALLOWED_PROVIDERS:
            self.assertTrue(allowed_provider(aaguid.upper()))

    def test_other_unknown_and_missing_providers_denied(self):
        for aaguid in ["08987058-cadc-4b81-b6e1-30de50dcbe96",  # Windows Hello
                       "bada5566-a7aa-401f-bd96-45619a55120d",  # 1Password
                       "00000000-0000-0000-0000-000000000000", "", None, "Apple"]:
            with self.subTest(aaguid=aaguid):
                self.assertFalse(allowed_provider(aaguid))


if __name__ == "__main__":
    unittest.main()
