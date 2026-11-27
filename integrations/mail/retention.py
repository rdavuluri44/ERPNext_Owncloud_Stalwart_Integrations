#!/usr/bin/env python3
"""Company mail retention on Stalwart Community (P69).

Keeps every company message and stops users from deleting mail for good:

- a system Sieve script copies every message that passes the SMTP DATA stage
  (inbound, authenticated submission and webmail/JMAP submission) to an archive
  account that has no sign-in and may only receive mail;
- the built-in User and Group roles lose the permissions that destroy mail or
  folders (IMAP EXPUNGE/DELETE, JMAP destroy, POP3 DELE) and Trash/Junk are no
  longer emptied automatically;
- one named reader account gets read-only access to the archive Inbox; its
  sign-ins (``auth.success``) are the access log, written to a log folder on the
  data volume so the log is kept and backed up;
- ``backfill`` copies mail that existed before the journal started into the
  archive once; ``purge`` removes mail older than the retention period from
  every account, the archive included (administrator only).

Run on the mail host with a private profile (never in Git)::

    {"tier": "test"|"production", "admin_url": "http://127.0.0.1:PORT",
     "recovery_credential": "admin:...", "container": "stalwart-...",
     "archive_address": "archive@example.com", "reader_account": "archive-reader",
     "retention_days": 2557, "log_path": "/var/lib/stalwart/logs/"}

Subcommands: apply, rollback, backfill, purge, status. ``apply`` records the
settings it replaces in a receipt before changing anything; ``rollback`` puts
them back from that receipt. The archive account and its mail are never
removed by this tool, except by ``purge`` for mail past the retention period.
Output never contains credentials or message contents.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stalwart_bootstrap import Client, NativeError  # noqa: E402

SCRIPT = "p69-retention-journal"
DELETION_PERMISSIONS = ("imapDelete", "imapExpunge", "jmapEmailDestroy", "jmapMailboxDestroy", "pop3Dele")
UNRESTRICTED_DATA_STAGE = {"else": "false", "match": {}}
JOURNAL_DATA_STAGE = {"else": f"'{SCRIPT}'", "match": {}}
ARCHIVE_PERMISSIONS = {
    "@type": "Replace",
    "enabledPermissions": {"emailReceive": True},
    "disabledPermissions": {"authenticate": True},
}
ARCHIVE_ROLES = {"@type": "Custom", "roleIds": {}}
READ_ONLY = {"mayReadItems": True}
DEFAULT_RETENTION_DAYS = 2557  # seven years, including leap days
DEFAULT_LOG_PATH = "/var/lib/stalwart/logs/"
MAIL = ("urn:ietf:params:jmap:core", "urn:ietf:params:jmap:mail")
SHARING = MAIL + ("urn:ietf:params:jmap:principals",)
PAGE = 100


def journal_script(address):
    return ('require ["envelope", "copy"];\n'
            f'if not envelope :is "to" "{address}" {{ redirect :copy "{address}"; }}\n')


def check_profile(profile):
    if profile.get("tier") not in {"test", "production"}:
        raise ValueError("Unknown deployment tier")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*@[a-z0-9.-]+\.[a-z]+", profile.get("archive_address", "")):
        raise ValueError("archive_address must be a plain lowercase mail address")
    reader = profile.get("reader_account")
    if reader is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@-]*", reader):
        raise ValueError("reader_account must be an account name")
    days = profile.get("retention_days", DEFAULT_RETENTION_DAYS)
    if not isinstance(days, int) or days < 365:
        raise ValueError("retention_days must be a whole number of at least 365")
    path = profile.get("log_path", DEFAULT_LOG_PATH)
    if not (path.startswith("/var/lib/stalwart/") and path.endswith("/")):
        raise ValueError("log_path must be a folder on the Stalwart data volume")


def client_for(profile):
    return Client(profile["admin_url"], profile["recovery_credential"])


def singleton(client, name, prop):
    return client.call(f"x:{name}/get", {"ids": ["singleton"], "properties": [prop]})["list"][0][prop]


def set_singleton(client, name, prop, value):
    client.call(f"x:{name}/set", {"update": {"singleton": {prop: value}}})


def builtin_roles(client):
    roles = [row for row in client.call("x:Role/get", {})["list"]
             if row["description"] in {"User", "Group"} and not row.get("memberTenantId")]
    if len(roles) != 2 or {row["description"] for row in roles} != {"User", "Group"}:
        raise ValueError("Built-in User and Group roles could not be identified")
    return roles


def log_tracers(client):
    return [row for row in client.call("x:Tracer/get", {})["list"] if row.get("@type") == "Log"]


def accounts(client):
    return client.call("x:Account/get", {})["list"]


def archive_account(client, address):
    rows = [row for row in accounts(client) if row.get("emailAddress") == address]
    if not rows:
        return None
    row = rows[0]
    if (len(rows) != 1 or row.get("@type") != "User" or row.get("credentials") or row.get("memberGroupIds")
            or row.get("roles") != ARCHIVE_ROLES or row.get("permissions") != ARCHIVE_PERMISSIONS):
        raise ValueError("The archive address already belongs to another kind of account")
    return row


def reader_row(client, name, archive_id):
    rows = [row for row in accounts(client) if row.get("name") == name]
    if len(rows) != 1 or rows[0].get("@type") != "User" or rows[0]["id"] == archive_id:
        raise ValueError("reader_account must name exactly one existing user account")
    return rows[0]


def archive_inbox(client, archive_id):
    boxes = client.call("Mailbox/get", {"accountId": archive_id, "properties": ["role", "shareWith"]}, SHARING)["list"]
    inbox = [box for box in boxes if box.get("role") == "inbox"]
    if len(inbox) != 1:
        raise ValueError("The archive account has no single Inbox")
    return inbox[0]


def restart(profile, client, log_path=None):
    """Stalwart applies a changed DATA stage and tracers only after a restart."""
    if log_path:
        # The log tracer does not create its folder; without it nothing is logged.
        subprocess.run(["docker", "exec", profile["container"], "mkdir", "-p", log_path], check=True)
    subprocess.run(["docker", "restart", profile["container"]], check=True, stdout=subprocess.DEVNULL)
    for attempt in range(60):
        try:
            client.call("x:Domain/get", {})
            return
        except OSError:
            if attempt == 59:
                raise
            time.sleep(1)


def apply(profile, receipt_path, restart_server=True):
    check_profile(profile)
    client = client_for(profile)
    address = profile["archive_address"]
    log_path = profile.get("log_path", DEFAULT_LOG_PATH)
    domains = {row["name"]: row["id"] for row in client.call("x:Domain/get", {})["list"]}
    domain = address.split("@", 1)[1]
    if domain not in domains:
        raise ValueError("The archive address's domain is not served by this mail server")
    roles = builtin_roles(client)
    tracers = log_tracers(client)
    if len(tracers) != 1:
        raise ValueError("Expected exactly one log tracer")
    contents = journal_script(address)
    scripts = [row for row in client.call("x:SieveSystemScript/get", {})["list"] if row["name"] == SCRIPT]
    if scripts and (len(scripts) != 1 or scripts[0]["contents"].strip() != contents.strip()):
        raise ValueError("An existing journal script differs")
    archive = archive_account(client, address)
    if profile.get("reader_account"):
        # Validate before changing anything, so a wrong name leaves the server untouched.
        reader_row(client, profile["reader_account"], archive["id"] if archive else None)

    if receipt_path.exists():
        # A rerun keeps the original before-state; it never records the policy as "before".
        previous = json.loads(receipt_path.read_text())
    else:
        stage = singleton(client, "MtaStageData", "script")
        if stage not in (UNRESTRICTED_DATA_STAGE, JOURNAL_DATA_STAGE):
            raise ValueError("The DATA stage already runs another filter")
        previous = {
            "applied_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tier": profile["tier"],
            "archive_address": address,
            "roles": {row["id"]: row["disabledPermissions"] for row in roles},
            "expungeTrashAfter": singleton(client, "DataRetention", "expungeTrashAfter"),
            "dataStage": stage,
            "tracer": {"id": tracers[0]["id"], "path": tracers[0].get("path"), "ansi": tracers[0].get("ansi")},
        }
        with receipt_path.open("x") as handle:
            json.dump(previous, handle, indent=2)

    if archive is None:
        created = client.call("x:Account/set", {"create": {"archive": {
            "@type": "User", "name": address.split("@", 1)[0], "domainId": domains[domain],
            "description": "Company mail archive (P69): receive only, no sign-in",
            "roles": ARCHIVE_ROLES, "permissions": ARCHIVE_PERMISSIONS,
        }}})
        archive_id = created["created"]["archive"]["id"]
    else:
        archive_id = archive["id"]
    if not scripts:
        client.call("x:SieveSystemScript/set", {"create": {"journal": {
            "name": SCRIPT, "isActive": True, "contents": contents}}})
    elif not scripts[0]["isActive"]:
        client.call("x:SieveSystemScript/set", {"update": {scripts[0]["id"]: {"isActive": True}}})
    try:
        client.call("x:Role/set", {"update": {
            row["id"]: {"disabledPermissions": {**row["disabledPermissions"], **dict.fromkeys(DELETION_PERMISSIONS, True)}}
            for row in roles}})
        set_singleton(client, "DataRetention", "expungeTrashAfter", None)
        # Plain text (no colour codes) so the access log can be searched and kept.
        client.call("x:Tracer/set", {"update": {tracers[0]["id"]: {"path": log_path, "ansi": False}}})
        set_singleton(client, "MtaStageData", "script", JOURNAL_DATA_STAGE)
    except Exception:
        restore(client, previous)
        raise
    if profile.get("reader_account"):
        reader = reader_row(client, profile["reader_account"], archive_id)
        inbox = archive_inbox(client, archive_id)
        client.call("Mailbox/set", {"accountId": archive_id, "update": {inbox["id"]: {
            "shareWith": {**(inbox.get("shareWith") or {}), reader["id"]: READ_ONLY}}}}, SHARING)
    if restart_server:
        restart(profile, client, log_path)
    problems = check(profile, client)
    if problems:
        raise RuntimeError("Retention settings did not verify: " + "; ".join(problems))
    if "journal_started_at" not in previous:
        # The journal copies only after the restart. The backfill covers everything
        # received before this moment, so no message falls between the two.
        previous["journal_started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        tmp = receipt_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(previous, indent=2))
        os.replace(tmp, receipt_path)
    return archive_id


def restore(client, previous):
    set_singleton(client, "MtaStageData", "script", previous["dataStage"])
    set_singleton(client, "DataRetention", "expungeTrashAfter", previous["expungeTrashAfter"])
    client.call("x:Role/set", {"update": {
        role: {"disabledPermissions": values} for role, values in previous["roles"].items()}})
    client.call("x:Tracer/set", {"update": {previous["tracer"]["id"]: {
        "path": previous["tracer"]["path"], "ansi": previous["tracer"].get("ansi", True)}}})


def rollback(profile, receipt_path):
    """Restore the recorded settings; keep the archive account, its mail and the reader's access."""
    check_profile(profile)
    client = client_for(profile)
    previous = json.loads(receipt_path.read_text())
    restore(client, previous)
    for row in client.call("x:SieveSystemScript/get", {})["list"]:
        if row["name"] == SCRIPT and row["isActive"]:
            client.call("x:SieveSystemScript/set", {"update": {row["id"]: {"isActive": False}}})
    restart(profile, client)


def check(profile, client=None):
    """Return a list of problems; empty when the policy is fully in place."""
    client = client or client_for(profile)
    address = profile["archive_address"]
    problems = []
    for row in builtin_roles(client):
        missing = [p for p in DELETION_PERMISSIONS if not row["disabledPermissions"].get(p)]
        if missing:
            problems.append(f"role {row['description']} may still use {', '.join(missing)}")
    if singleton(client, "DataRetention", "expungeTrashAfter") is not None:
        problems.append("Trash and Junk are still emptied automatically")
    if singleton(client, "MtaStageData", "script") != JOURNAL_DATA_STAGE:
        problems.append("the DATA stage does not run the journal script")
    scripts = [row for row in client.call("x:SieveSystemScript/get", {})["list"] if row["name"] == SCRIPT]
    # Stalwart stores the script without its trailing newline.
    if (len(scripts) != 1 or not scripts[0]["isActive"]
            or scripts[0]["contents"].strip() != journal_script(address).strip()):
        problems.append("the journal script is missing, inactive or different")
    archive = archive_account(client, address)
    if archive is None:
        problems.append("the archive account is missing")
    if [(row.get("path"), row.get("ansi")) for row in log_tracers(client)] != [(profile.get("log_path", DEFAULT_LOG_PATH), False)]:
        problems.append("the log tracer does not write plain text to the data volume")
    if archive is not None and profile.get("reader_account"):
        reader = reader_row(client, profile["reader_account"], archive["id"])
        share = (archive_inbox(client, archive["id"]).get("shareWith") or {}).get(reader["id"]) or {}
        if not share.get("mayReadItems") or any(v for k, v in share.items() if k != "mayReadItems"):
            problems.append("the reader does not have read-only access to the archive Inbox")
    return problems


def mail_accounts(client, archive_id):
    return [row for row in accounts(client) if row.get("@type") in {"User", "Group"} and row["id"] != archive_id]


def query_ids(client, account_id, filter_, position=0, limit=PAGE):
    result = client.call("Email/query", {"accountId": account_id, "filter": filter_, "position": position,
                                         "limit": limit, "sort": [{"property": "receivedAt"}],
                                         "calculateTotal": True}, MAIL)
    return result["ids"], result.get("total", 0)


def backfill(profile, receipt_path, state_path):
    """Copy mail received before the journal started into the archive Inbox, once per message."""
    check_profile(profile)
    client = client_for(profile)
    previous = json.loads(receipt_path.read_text())
    if "journal_started_at" not in previous:
        raise ValueError("Apply the policy (including the restart) before the backfill")
    archive = archive_account(client, profile["archive_address"])
    if archive is None:
        raise ValueError("Apply the policy before the backfill")
    target = archive_inbox(client, archive["id"])["id"]
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    copied_total = 0
    for row in mail_accounts(client, archive["id"]):
        done = set(state.get(row["id"], []))
        position = 0
        while True:
            ids, _ = query_ids(client, row["id"], {"before": previous["journal_started_at"]}, position)
            if not ids:
                break
            position += len(ids)
            todo = [i for i in ids if i not in done]
            if todo:
                try:
                    client.call("Email/copy", {"fromAccountId": row["id"], "accountId": archive["id"], "create": {
                        f"c{n}": {"id": i, "mailboxIds": {target: True}} for n, i in enumerate(todo)}}, MAIL)
                except NativeError as error:
                    # The same message in several mailboxes (a group and its members) is
                    # archived once; the server refuses the later copies as alreadyExists.
                    if error.kind or set(error.item_types) - {"alreadyExists"}:
                        raise
                done.update(todo)
                copied_total += len(todo)
                state[row["id"]] = sorted(done)
                tmp = state_path.with_suffix(".tmp")
                tmp.write_text(json.dumps(state))
                os.replace(tmp, state_path)
    return copied_total


def purge(profile, apply_changes=False, now=None):
    """Remove mail received before the retention cut-off from every account, the archive included."""
    check_profile(profile)
    client = client_for(profile)
    days = profile.get("retention_days", DEFAULT_RETENTION_DAYS)
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime((now or time.time()) - days * 86400))
    report = {"cutoff": cutoff, "accounts": 0, "messages": 0, "removed": 0}
    for row in [r for r in accounts(client) if r.get("@type") in {"User", "Group"}]:
        ids, total = query_ids(client, row["id"], {"before": cutoff}, limit=PAGE)
        report["accounts"] += 1
        report["messages"] += total
        while apply_changes and ids:
            client.call("Email/set", {"accountId": row["id"], "destroy": ids}, MAIL)
            report["removed"] += len(ids)
            ids, _ = query_ids(client, row["id"], {"before": cutoff}, limit=PAGE)
    return report


def status(profile):
    check_profile(profile)
    client = client_for(profile)
    rows = [r for r in accounts(client) if r.get("@type") in {"User", "Group"}]
    archive = archive_account(client, profile["archive_address"])
    used = sum(r.get("usedDiskQuota") or 0 for r in rows)
    archived = sum(r.get("usedDiskQuota") or 0 for r in rows if archive and r["id"] == archive["id"])
    return {"problems": check(profile, client), "accounts": len(rows),
            "stored_bytes": used, "archive_bytes": archived}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["apply", "rollback", "backfill", "purge", "status"])
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, help="before-state receipt (apply, rollback, backfill)")
    parser.add_argument("--state", type=Path, help="backfill progress file")
    parser.add_argument("--apply", action="store_true", help="purge: remove the messages (default: count only)")
    args = parser.parse_args(argv)
    os.umask(0o077)
    profile = json.loads(args.profile.read_text())
    if args.command in {"apply", "rollback", "backfill"} and not args.receipt:
        parser.error("--receipt is required")
    if args.command == "apply":
        apply(profile, args.receipt)
        print("Retention policy applied and verified")
    elif args.command == "rollback":
        rollback(profile, args.receipt)
        print("Retention settings restored from the receipt; archive kept")
    elif args.command == "backfill":
        if not args.state:
            parser.error("--state is required")
        print(f"Copied {backfill(profile, args.receipt, args.state)} earlier messages into the archive")
    elif args.command == "purge":
        print(json.dumps(purge(profile, apply_changes=args.apply)))
    else:
        print(json.dumps(status(profile)))


if __name__ == "__main__":
    main()
