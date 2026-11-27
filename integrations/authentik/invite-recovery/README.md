# Authentik invitation and recovery companion

Selected source from the previous integration repository, compared with the retained deployment. This is a separate native-authentik integration; it is not an extra Frappe app.

## Deployment

Inventory and back up native flows, stage bindings, policies, provider metadata, brand CSS and persistent templates. Set the generic administrator identity and flow/group names for your installation; installer assertions deliberately fail if the baseline enrollment flow or required provider metadata is absent. Do not weaken assertions to make an unknown installation pass.

Mount the public directory into the restricted nginx companion; attach only the private proxy and authentik networks, with no public host port. Set AUTHENTIK_NETWORK for compose.yml. Adapt the exact hostname/service routing in traefik.yaml and nginx.conf. Requests use native administrator session/CSRF checks; no privileged browser API token is embedded.

Mount templates/ persistently into both authentik server and worker, preserving vendor template inheritance. Execute install_native.py in the native authentik shell only after inventory and backup. It invokes the targeted single-email migration last. Existing group membership and existing user passkeys must remain intact. The public administrator navigation adapter changes navigation only; backend checks remain authoritative.

## Retained guarantees

Invitation attempts (P78): the administrator chooses how many times a link may be opened, 1 to 5 (default 5) when the site's `invite-mode.mjs` sets `attemptsAvailable`. One attempt is a native single-use link. More attempts create a reusable link with `fixed_data.attempts`; the invitation policies count each opening once per flow in a server-side ledger, remove the link after the last attempt, and end it as soon as setup succeeds (recovery completes, or the user already has a passkey). Without `attemptsAvailable` the form keeps creating single-use links, so a site only offers attempts after its policies are updated.

Approved passkey providers (P79) come from one setting, [`../passkey-providers.json`](../passkey-providers.json): Apple Passwords, Bitwarden (also with Vaultwarden), Google Password Manager and Chrome on Mac. `tools/sync_passkey_providers.py` rewrites the copies Authentik needs as literal text (this module's policies, installer and the blueprint), and `tests/test_passkey_providers.py` fails if any copy differs.

One expiring, single-use native invitation link fixes the identity/email and serves as email-possession proof. Enrollment rejects an identity with existing keys. Recovery snapshots old keys after invitation validation, requires a fresh allowed replacement registration and assertion, then removes only that snapshot transactionally. Abandoned/failed recovery preserves old keys; concurrent newer keys are preserved. Provider AAGUID values are reported metadata, not cryptographic vendor attestation.

## Tests and upgrades

Run test_recovery_guard.py and test_invitations.mjs offline. test_native.py and smoke_single_email.py require a compatible native authentik environment and their documented outer rollback/mock-mail controls. Never treat a mocked send or a reached WebAuthn stage as a completed device ceremony. No test should send real invitation email unintentionally.

After authentik upgrades verify native invitation schemas, stage/FlowPlan context, exact identity and expiry checks, provider metadata, template inheritance and shadow-DOM navigation selectors. Test real enrollment/recovery with an approved test identity before rollout. Preserve unrelated brand CSS and native invitation APIs.

Current device acceptance and SMTP/inbox verification are tracked in the main pending list. Native object backups and passkeys are private runtime data and are excluded from Git.

See [retained invitation configuration](../../../docs/invitation-configuration.md) for shared-group, dual navigation, cache and SMTP rules.
