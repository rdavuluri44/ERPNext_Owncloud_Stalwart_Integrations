# Chat (Matrix: Synapse and its authentication service) (`chat`)

The internal chat server: Synapse with the Matrix Authentication Service, signing in through the sign-in service; its stack and the script that writes both configurations.

## Purpose

The company's own chat (P73; owner, 27 November 2026): a Matrix server that replaces Raven and is used from inside the phone app. People sign in with the same passkey as everywhere else: Synapse hands sign-in to the Matrix Authentication Service (MAS), and MAS sends people to the sign-in service (authentik).

Fixed choices, set in `configure.py`:

- **Sign-in only through the sign-in service.** No passwords, no registration; people cannot change the name or mail address that comes from the sign-in service, or deactivate their account.
- **No federation at first.** No other Matrix server is contacted or answered.
- **Rooms are not encrypted by default,** so the company can keep, search and export them.
- **The business system has a bot, `@erp`, and no admin right.** It signs in with its own token (an application service registration without a call-back address), creates the rooms, invites people and posts. Invitations from this server are accepted automatically (`auto_accept_invites`), so a person is in their site room, or in a one-to-one chat a colleague opened, without a tap. The bot cannot act as a person, and people cannot take its name.
- **The server name is permanent.** It is part of every address (`@name:chat.<domain>`) and Matrix does not allow renaming a server. Choose it before the first start.

## Contents

- `integrations/chat/**`
- `deployment/stacks/chat.compose.json`
- `tests/test_chat_stack.py`

Services of the stack:

| Service | What it is | Reachable |
|---|---|---|
| `configure` | runs once before the others; writes both configuration files and, the first time, MAS's signing key | no |
| `synapse` | the chat server | `chat-synapse:8008` on the workspace network |
| `mas` | the sign-in service for chat | `chat-mas:8080` on the workspace network |
| `alerts` | optional: the alert gateway (Sygnal), which passes chat alerts to Google for the phone app | `alerts-gateway:5000` inside the stack only |
| `database-synapse`, `database-mas` | one PostgreSQL each (Synapse needs the `C` locale) | inside the stack only |

## Requirements

Modules: `authentik-identity`.

Two host names (`chat` and `chat-auth` in the profile's `hosts`), and an OAuth2/OpenID provider in the sign-in service for MAS: confidential client, redirect address `https://<chat-auth host>/upstream/callback/<UPSTREAM_ID>`, scopes `openid profile email chat`. The `chat` scope is a scope mapping that returns the person's `chat_name` attribute (`deployment/scope-mappings.example.json`).

## Reuse

Add `chat` to the profile's `projects`, name the two hosts, supply the provider's client secret, render with `tools/prepare_runtime.py` and register the stack like any other (`tools/coolify_native.py`). The proxy sends the chat host's `/_matrix`, `/_synapse/client` and `/_synapse/mas` to Synapse, the three delegated paths `/_matrix/client/*/login`, `logout` and `refresh` to MAS, and the whole `chat-auth` host to MAS (`tools/prepare_ingress.py` does this for a test site). Synapse's admin interface (`/_synapse/admin`) is not routed.

## Configuration

Settings are in `deployment/stacks/inputs.json` as `CI_CHAT_CONFIGURE_*`:

- **Names:** `CHAT_SERVER_NAME`, `CHAT_PUBLIC_URL`, `CHAT_AUTH_URL` (defaults follow the `chat` and `chat-auth` hosts).
- **Sign-in service:** `UPSTREAM_ISSUER`, `UPSTREAM_CLIENT_ID`, `UPSTREAM_CLIENT_SECRET` (required, never generated), `UPSTREAM_ID` (a fixed ULID; it is part of the redirect address), `UPSTREAM_NAME`.
- **`LOCALPART_TEMPLATE`:** how a person's chat name is made from what the sign-in service says about them. It must give a valid Matrix name (lower-case letters, digits and `._=-/+`) that never changes for that person. The default is the `chat_name` claim (owner, 27 November 2026: `firstname.initial`, with a number on a clash, made once at onboarding), because sign-in user names are mail addresses, which Matrix does not accept. A person without a chat name cannot sign in to chat.
- **Secrets made by the renderer:** the two database passwords, the secret Synapse and MAS share, Synapse's macaroon and form secrets, and the secret MAS's encryption key is derived from. Do not change the last one after the first start.

The `configure` service rewrites both files at every deployment and keeps the signing key. Private ports: `CI_CHAT_SYNAPSE_HOST_PORT` (8040) and `CI_CHAT_MAS_HOST_PORT` (8050), on 127.0.0.1 only.

**For the business system** (the module that makes rooms from sites and teams; not in this module): the bot's token is `CI_CHAT_CONFIGURE_BRIDGE_AS_TOKEN` in the runtime's private inputs. It reaches Synapse inside the workspace network at `http://chat-synapse:8008` and uses only the client interface: create a room (alias `#site-…`, `#team-…` or `#notices-…`; give everyone else no right to invite, rename or change rules), invite, post, remove. A read-only room is one where writing needs a higher level than members have. Rooms use the server's default room version, in which the creator has full rights and must not be listed in the power levels.

After the `configure` service has rewritten the files, restart `synapse` and `mas` so they read them. When a client or provider is removed from the authentication service's configuration, run its `config sync --prune` once.

**Phone alerts (optional).** Put Google's service-account key for the app's Firebase project into the stack's key folder as `fcm-key.json` (`<runtime>/mounts/chat_configure_1/`, readable by root only), deploy, and start the stack with the `alerts` profile (`COMPOSE_PROFILES=alerts`). The `configure` service then writes the gateway's configuration for the app `CI_CHAT_CONFIGURE_ALERTS_APP_ID` and copies the key next to it; without a key it writes nothing and removes what was there. The app registers `http://alerts-gateway:5000/_matrix/push/v1/notify` as its push address with the format `event_id_only`, so an alert carries no name and no text. Synapse may call only this stack's own network (`CI_CHAT_CONFIGURE_NETWORK_SUBNET`, default `172.30.250.0/24`; change it where that range is taken). The gateway has no port on the host and no public route. It is the only service on the stack's `outbound` network, its way to Google; it is not on the workspace network, so a site that blocks outbound connections from that network (a test site) keeps doing so.

Backups: both databases (`pg_dumpall` in each database container) and the volumes `synapse-data` (media and Synapse's signing key) and `mas-config` (MAS's signing key).

## Tests

- `tests/test_chat_stack.py`

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Synapse — AGPL-3.0 — https://github.com/element-hq/synapse
- Matrix Authentication Service — AGPL-3.0 — https://github.com/element-hq/matrix-authentication-service

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
