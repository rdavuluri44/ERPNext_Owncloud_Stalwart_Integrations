"""Pure deletion gate; live Authentik adapter remains subject to installation checks.

Only trusted server-side flow state may supply these arguments. Do not expose
them as a public API or accept a browser's claim that a passkey was verified.
The adapter must lock the user and credential rows in a DB transaction and
persist completion/replay protection in the same transaction as deletion.
"""
from dataclasses import dataclass
from datetime import datetime
from provider_policy import allowed_provider

RECOVERY_FLOW = "cloud-passkey-recovery-invitation"


@dataclass(frozen=True)
class RecoveryProof:
    flow: str
    user_id: int
    email: str
    expires: datetime
    old_keys: frozenset[str]
    email_verified: bool
    replacement_key: str
    replacement_verified: bool
    replacement_aaguid: str
    completed: bool = False


def old_keys_to_delete(proof, *, user_id, email, active, approved,
                       confirmed_keys, now):
    """Return the exact old-key snapshot only after fresh proof of replacement.

    Concurrently added keys that are not in the recovery snapshot are preserved.
    In particular, never implement this as 'delete everything except newest'.
    """
    if proof.completed:
        raise ValueError("Recovery already completed")
    if proof.flow != RECOVERY_FLOW or proof.user_id != user_id or proof.email != email:
        raise ValueError("Recovery identity mismatch")
    if not active or not approved or proof.expires <= now:
        raise ValueError("Recovery is no longer allowed")
    if not proof.email_verified or not proof.replacement_verified:
        raise ValueError("Fresh email and replacement-key verification are required")
    if not allowed_provider(proof.replacement_aaguid):
        raise ValueError("Replacement passkey must come from an approved provider")
    if not proof.replacement_key or proof.replacement_key in proof.old_keys:
        raise ValueError("A new replacement passkey must be verified")
    if proof.replacement_key not in confirmed_keys:
        raise ValueError("Replacement passkey is not confirmed for this user")
    return proof.old_keys & frozenset(confirmed_keys)
