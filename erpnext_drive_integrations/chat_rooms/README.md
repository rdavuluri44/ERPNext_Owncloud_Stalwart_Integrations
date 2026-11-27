# Chat rooms from sites and teams (`chat-rooms`)

The business system's bot keeps the chat rooms in step with the field sites: a room per site, a room per supervisor's team, and a read-only Notices room per person.

## Purpose

People should find themselves in the right chat rooms without anyone managing rooms by hand (P73; owner, 27 November 2026). When someone is assigned to a site they are in its room; when the assignment ends they leave it. Nothing about rooms is stored in the business system: a room is found by its fixed address, and its members are read from the chat server every time, so this module can be replaced without moving data.

| Room | Address | Who is in it | Who may write |
|---|---|---|---|
| Site | `#site-<site record>` | every enabled member of an enabled Field Site | members |
| Team | `#team-<site record>-<supervisor's chat name>` | the supervisor, the engineer assigned to them (while an active engineer of the site) and the site's approvers | members |
| Notices | `#notices-<chat name>` | that person | only the bot |

Rules that follow from this:

- Only the bot invites, removes, renames or changes a room's rules.
- A person takes part only when their User record has a **chat name** (`firstname.initial`, as held by the sign-in service). People without one are counted and left out, never guessed.
- A person is put into rooms only once they have **signed in to chat once**: their chat account is made at the first sign-in, and an invitation is accepted automatically only at the moment it is made. The hourly run adds them afterwards (within the hour), and makes any invitation that is still pending again.
- A disabled site keeps its rooms, with nobody in them. A disabled person leaves their site and team rooms.
- An empty room is not created.

## Contents

- `erpnext_drive_integrations/chat_rooms/**`
- `tests/test_chat_rooms.py`

`rules.py` (which rooms, who belongs: no Frappe, no network), `matrix.py` (the bot's few calls to the chat server), `sync.py` (reads the sites and applies the rules), `hooks.py`.

## Requirements

Modules: `erp-addon-shell`, `custom-hr`, `chat`.

A Matrix server on which this business system has a bot registered as an application service, with invitations from the same server accepted automatically (module `chat` sets both up). The bot needs no admin right.

## Reuse

Install with the add-on. `bench migrate` adds the field **Chat name** to User. Give the site the private setting below. Rooms then follow every saved change of a Field Site or of a person's chat name, and an hourly run repairs anything missed. `sync.notify(user, key, text)` posts one informing message into a person's Notices room; a repeat with the same key posts nothing new.

## Configuration

Site config, private, never in Git:

```json
"chat_rooms": {"url": "http://chat-synapse:8008", "server_name": "chat.example.com", "token": "<the bot's token>"}
```

- `url`: the chat server inside the private network, not its public address.
- `token`: the chat stack's `CI_CHAT_CONFIGURE_BRIDGE_AS_TOKEN`.
- Without all three, the module does nothing.
- Switch the whole feature off with `cloud_features` -> `"chat_rooms": false`.

A problem with the chat server never stops a save in the business system: it is written to the Error Log as "Chat room not updated", without any credential, and tried again at the next run.

The chat name on a User cannot be changed once set, because a chat address cannot be renamed. Until the sign-up service makes chat names (P82), an administrator enters the one the sign-in service holds.

## Tests

- `tests/test_chat_rooms.py` (offline: the rules, the bot's calls against recorded answers, the applying run against a chat server kept in memory)

Run all suites offline with `python tools/run_unit_tests.py` in the matching ERP Python environment.

## Licenses

- Synapse — AGPL-3.0 — https://github.com/element-hq/synapse (the server this module talks to; no code of it is included)

Upstream licenses are as published by each project; verify them at the pinned version before redistributing (LICENSES.md).

## AI-assisted development

Development of this module is assisted by AI agents (Anthropic's Claude); changes follow the repository → permanent test → production workflow and are accepted by the owner (see AGENTS.md).
