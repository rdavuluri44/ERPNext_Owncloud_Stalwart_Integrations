"""Explicit provider identifiers; no unknown/all-zero fallback.

Identifiers are provider-reported, not cryptographic proof of vendor origin.
Inventory and test the live Authentik metadata before setting stage relations.
"""
from uuid import UUID

ALLOWED_PROVIDERS = {
    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd": "Apple Passwords (iCloud Keychain)",
    "dd4ec289-e01d-41c9-bb89-70fa845d4bf2": "Apple Passwords (managed iCloud Keychain)",
    "d548826e-79b4-db40-a3d8-11116f7e8349": "Bitwarden (also with Vaultwarden)",
    "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4": "Google Password Manager",
    "adce0002-35bc-c60a-648b-0b25f1f05503": "Chrome on Mac",
}


def allowed_provider(aaguid):
    try:
        return str(UUID(str(aaguid))) in ALLOWED_PROVIDERS
    except (ValueError, TypeError, AttributeError):
        return False
