# Admin alert inbox (`admin-alerts`, P72, P53)

One place in ERP where every check on every server reports, and where the admin sees what needs acting on.

## Purpose

The servers check themselves (sites reachable, backups made, restore drills, stacks in step with `main`, editor
saves, upstream advisories), but a result nobody reads protects nothing. The owner decided on 26 November 2026
that the admin receives the alerts and sees them on the Desk. This module is that inbox:

- **One record per problem.** Each check reports with a key (`source:key`, one source per server). A repeat
  updates the same record and counts it; the check passing again resolves it; failing again later reopens it
  and shows it as unread again.
- **Mail at once for critical alerts** (when one opens, reopens, or an open alert turns critical, and when it is
  resolved), and **one summary mail a day** while anything is open. Plain repeats send no mail. A check that keeps
  failing and passing mails at most once an hour per alert (turning critical is always mailed), and a "resolved"
  mail goes out only when the admin was told about the opening.
- **The page `/admin-alerts`**: open alerts newest first (unread ones marked "New"), those resolved in the last
  seven days, and a panel of admin tool links. The Desk shows an **Alerts** entry with the unread count to the
  admins only.
- **The sender `tools/send_alert.py`**, which every check uses. When ERP cannot be reached it mails critical
  alerts directly through the host-check mail sender, so "ERP is down" still reaches the admin.

Stage 1 (this module) builds the inbox and the sender. **Stage 2** wires the existing checks to the sender on each
server and opens a narrow proxy route for the report method only (the ERP address is otherwise behind the
sign-in gateway, so a server cannot reach the method yet).

## Contents

- `erpnext_drive_integrations/admin_alerts/**`: `api.py` (report endpoint, mail, daily summary, seen tracking),
  `hooks.py` (the `/admin-alerts` route and the daily job), the **System Alert** DocType (read, report and
  delete for System Manager; nothing is created or edited in the UI).
- `erpnext_drive_integrations/www/admin_alerts.py` and `.html`: the page (plain HTML, no outside assets).
- `erpnext_drive_integrations/public/app-logos/alerts.svg`: the Desk entry's icon. The entry itself is added in
  `www/place_holder.py` (portal module), guarded so an error here never breaks the Desk.
- `tools/send_alert.py`: the sender (standard library, Python 3.9 or newer).
- Tests: `tests/admin_alerts/**`, `tests/test_send_alert.py`.

The report method (`erpnext_drive_integrations.admin_alerts.api.report`, POST, guest, 240 a minute) takes JSON:
`source`, `key` (`a-z 0-9 . _ : -`, up to 80), `severity` (`critical`, `warning`, `info`), `title` (up to 140),
optional `detail` (up to 2000), `host` (up to 64), `link` (an https or http address, or a path starting with `/`,
up to 300) and `state` (`open`, the default, or `resolved`). Anything else is refused; control characters are
removed. The token goes in the **`X-Alert-Token`** header. It is not sent as `Authorization: Bearer`, because
Frappe treats any two-part Authorization header as an OAuth or API-key sign-in and refuses the request before a
guest method runs.

## Requirements

Modules: `erp-addon-shell` (hook composition), `portal-sso` (the Desk page and its sign-in), `deployment` (the
host-check mail sender, `tools/host_check.py`, used for the fallback). ERP outgoing mail for the alert mails.

## Reuse

Copy this folder, the two `www/admin_alerts.*` files, the icon and `tools/send_alert.py` (with
`tools/host_check.py`). Add `admin_alerts` to the feature list in `hooks.py` and `Admin Alerts` to `modules.txt`.
Add the Desk entry block from `www/place_holder.py` to your own portal page, or open `/admin-alerts` directly. Run
`bench migrate`.

## Configuration

Private site config (never in Git), `cloud_alerts` (neutral example in `deployment/erp/site-config.example.json`):

```json
"cloud_alerts": {
  "sources": {"web-1": "<sha256 hex of web-1's token>"},
  "role": "System Manager",
  "links": [{"label": "Monitoring", "url": "https://monitoring.example.com/", "note": "dashboards"}],
  "mail": true
}
```

- `sources`: one entry per server; only the SHA-256 of each token is stored, so a copy of the site config cannot
  report. Make a token on the server and keep it in a root-only file:
  `umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > /etc/cloud-alerts/token`, then
  `sha256sum` of the token text (without the newline:
  `tr -d '\n' < /etc/cloud-alerts/token | sha256sum`) goes into `sources`. Never paste the token itself anywhere.
- `role` (default System Manager): who receives the mail, sees the page and the Desk entry. ERP roles are not
  mapped from sign-in groups, so this is set here. The Desk list of System Alert records stays System Manager.
- `links`: the admin tools panel; only http(s) addresses are shown. The page says they are reachable only from
  devices on the company tailnet and that each tool has its own administrator sign-in for now.
- `mail` (default true): false stops all alert and summary mail (the inbox still records).
- Switch the feature off with `cloud_features: {"admin_alerts": false}`.

Sender config on each server, `/etc/cloud-alerts/config.json` (root-only; `--config` for another path):

```json
{"url": "https://erp.example.com/api/method/erpnext_drive_integrations.admin_alerts.api.report",
 "source": "web-1", "token_file": "/etc/cloud-alerts/token", "host": "web-1",
 "address": "100.64.0.10", "timeout": 10, "fallback_mail": "/etc/cloud-host-check/config.json"}
```

`address` (optional) connects to that address while still verifying the certificate for the URL's host name.
`fallback_mail` is the host-check config whose `alert` section `tools/host_check.py` mails with. Use:
`send_alert.py send --key disk --severity warning --title "Disk 85% full"` or wrap a check:
`send_alert.py run --key boot --title "Boot check" --warn-exit 2 -- /usr/local/bin/host_check.py boot`.

## Tests

- `tests/admin_alerts/test_api.py` (fake Frappe): token accepted only for a configured source with its token;
  strict validation; new, repeat, turn-critical, resolve and reopen; mail only when due; recipients; daily
  summary; unread count and marking seen without changing `modified`.
- `tests/admin_alerts/test_desk_entry.py`: the Alerts entry only for admins, with the count, and the Desk survives
  an error; the page sends guests to sign-in, refuses others and marks what it showed as seen.
- `tests/test_send_alert.py`: the run wrapper (resolve on success, marked lines on failure, `--warn-exit`, exit
  code passed through), the fallback mail for critical alerts only, the token never in output, and the address
  connection verifying the URL's host name.
- To prove on the test site: the migrate creates the DocType; a report from a server reaches it once stage 2's
  route exists; mail delivery; the Desk entry and page in the portal frame.

## Licenses

- Frappe Framework — MIT — https://github.com/frappe/frappe

This module's code was written with AI assistance (Claude Code); the maintainers review and test it before use.
