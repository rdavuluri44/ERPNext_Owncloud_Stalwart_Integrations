# First administrator at setup (P77)

Choose the first administrator of a fresh authentik instance at setup time and
switch off the built-in `akadmin` account.

## What it does

`first-admin.sh <server container> [administrator folder]` asks the person setting
up the instance for the administrator's email and name (no password), asks for
confirmation, and then:

- creates or refreshes that administrator in the given folder (default
  `administrators`), in the administrator group, **without a password**;
- prints a one-time link, valid for 24 hours, that registers the administrator's
  passkey and signs them in. The passkey must come from an approved provider in
  [`passkey-providers.json`](../passkey-providers.json) (shared by every passkey check, P79) (Apple Passwords, Bitwarden
  or Vaultwarden, Google Password Manager, Chrome on Mac), with user verification;
- switches off `akadmin`: inactive, a random password nobody knows, no groups,
  roles or tokens.

Rerun the same command to issue a new link, for example after a lost passkey;
the previous link stops working. Remove the lost passkey under the user's MFA
devices in the admin interface.

## Existing instances: switch off `akadmin` only

    ./first-admin.sh --akadmin-only <authentik server container>

For an instance whose administrator already exists and is managed elsewhere
(for example a Google-linked account with a passkey). It only makes sure
`akadmin` exists and is switched off, recreating it switched off when it was
deleted, so upstream's bootstrap blueprint can never bring it back active. It
refuses when no other active administrator has a passkey.

## Lost passkey: getting an administrator back in

- **Administrator created by this tool:** rerun `first-admin.sh` for the same
  email; it prints a new one-time link to register a passkey.
- **Any administrator** (also Google-linked ones), from a root shell on the server:

      docker exec <authentik server container> ak create_recovery_key 10 <username>

  It prints a path `/recovery/use-token/…/`; open it on the instance's address
  within 10 minutes. It signs the administrator in once. Add a passkey from an
  approved provider under Settings, then remove the lost passkey under the user's
  MFA devices. The link works once; do not paste it into logs or tickets.

Keep the server's SSH access in the password manager: it is the way back in.

## Why `akadmin` is switched off, not deleted

Upstream's first-time setup page (`initial-setup`) opens whenever `akadmin` is
missing or has no usable password, and upstream's bootstrap blueprint creates
`akadmin` if it is absent. A present but inactive `akadmin` with an unknown
password keeps that page closed; the bootstrap blueprint only creates the
account and never reactivates it.

## Use

On a fresh install, keep upstream's `AUTHENTIK_BOOTSTRAP_PASSWORD` set until this
command has run, so the setup page is closed from the first start. Then remove
the bootstrap password from the environment.

    ./first-admin.sh <authentik server container> [administrator folder]

`FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_NAME` and `FIRST_ADMIN_YES=1` skip the questions
for automation. `FIRST_ADMIN_BASE_URL` overrides `AUTHENTIK_WEB__BASE_URL` for the
link. `DOCKER` selects the container command (default `docker`).

Send the link over a private channel; never put it into logs, tickets or Git.
The sign-in flow of the deployment must accept the administrator's passkey
(for example production's passkey sign-in, or a login policy that admits the
administrator folder after an approved passkey).

## Tests

`tests/test_first_admin.py` checks the provider list, the link and passkey rules
and that `akadmin` is switched off rather than deleted. The behaviour was
verified on a throwaway authentik 2026.8 instance: the setup page stays closed
before and after, a rerun invalidates the previous link, the link reaches passkey
registration once, `akadmin` stays off after the bootstrap blueprint is applied
again, and sign-in is admitted only after an approved passkey from the link.

Development was assisted by Claude Code.
