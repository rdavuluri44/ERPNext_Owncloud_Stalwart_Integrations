#!/usr/bin/env python3
"""Rehearse a Community mail journal and deletion policy on an isolated test domain."""

import argparse
import json
import os
from pathlib import Path
import re

from stalwart_bootstrap import Client

SCRIPT = "p69-retention-journal"
DELETION_PERMISSIONS = {
    "imapDelete", "imapExpunge", "jmapEmailDestroy", "jmapMailboxDestroy", "pop3Dele",
}
UNRESTRICTED_DATA_STAGE = {"else": "false", "match": {}}
JOURNAL_DATA_STAGE = {"else": f"'{SCRIPT}'", "match": {}}
ARCHIVE_PERMISSIONS = {
    "@type": "Replace",
    "enabledPermissions": {"emailReceive": True},
    "disabledPermissions": {"authenticate": True},
}
ARCHIVE_ROLES = {"@type": "Custom", "roleIds": {}}


def singleton(client, name, property_name):
    rows = client.call(f"x:{name}/get", {
        "ids": ["singleton"], "properties": [property_name],
    })["list"]
    return rows[0][property_name]


def update_singleton(client, name, property_name, value):
    client.call(f"x:{name}/set", {"update": {"singleton": {property_name: value}}})


def configure(profile, receipt):
    domain = profile["mail_domain"]
    local = profile["archive_localpart"]
    if (profile["tier"] != "test" or not re.fullmatch(r"[a-z0-9.-]+\.test", domain)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", local)):
        raise ValueError("P69 rehearsal requires an isolated .test mail domain")
    client = Client(profile["admin_url"], profile["recovery_credential"])
    domain_rows = client.call("x:Domain/get", {})["list"]
    if len(domain_rows) != 1 or domain_rows[0]["name"] != domain:
        raise ValueError("The target must contain only the isolated test mail domain")
    domain_id = domain_rows[0]["id"]
    roles = [row for row in client.call("x:Role/get", {})["list"]
             if row["description"] in {"User", "Group"} and not row["memberTenantId"]]
    if len(roles) != 2 or {row["description"] for row in roles} != {"User", "Group"}:
        raise ValueError("Built-in User and Group roles could not be identified")
    disabled = {row["id"]: row["disabledPermissions"] for row in roles}
    previous = {
        "roles": disabled,
        "expungeTrashAfter": singleton(client, "DataRetention", "expungeTrashAfter"),
        "script": singleton(client, "MtaStageData", "script"),
    }
    if previous["script"] not in (UNRESTRICTED_DATA_STAGE, JOURNAL_DATA_STAGE):
        raise ValueError("The DATA stage already runs another filter")

    address = f"{local}@{domain}"
    contents = (
        'require ["envelope", "copy"];\n'
        f'if not envelope :is "to" "{address}" {{ redirect :copy "{address}"; }}\n'
    )
    scripts = [row for row in client.call("x:SieveSystemScript/get", {})["list"]
               if row["name"] == SCRIPT]
    if scripts and (len(scripts) != 1 or scripts[0]["contents"] != contents or not scripts[0]["isActive"]):
        raise ValueError("The existing journal script differs")
    accounts = [row for row in client.call("x:Account/get", {})["list"]
                if row["emailAddress"] == address]
    if accounts and (len(accounts) != 1 or accounts[0].get("@type") != "User"
                     or accounts[0]["credentials"] or accounts[0]["memberGroupIds"]
                     or accounts[0]["roles"] != ARCHIVE_ROLES
                     or accounts[0]["permissions"] != ARCHIVE_PERMISSIONS):
        raise ValueError("The archive address already belongs to another kind of account")

    with receipt.open("x") as handle:
        json.dump(previous, handle, indent=2)
    if not accounts:
        client.call("x:Account/set", {"create": {"journal": {
            "@type": "User", "name": local, "domainId": domain_id,
            "description": "Administrator-accessible mail journal",
            "roles": ARCHIVE_ROLES, "permissions": ARCHIVE_PERMISSIONS,
        }}})
    if not scripts:
        client.call("x:SieveSystemScript/set", {"create": {"journal": {
            "name": SCRIPT, "isActive": True, "contents": contents,
        }}})
    try:
        client.call("x:Role/set", {"update": {
            role: {"disabledPermissions": {**values, **dict.fromkeys(DELETION_PERMISSIONS, True)}}
            for role, values in disabled.items()
        }})
        update_singleton(client, "DataRetention", "expungeTrashAfter", None)
        update_singleton(client, "MtaStageData", "script", JOURNAL_DATA_STAGE)
    except Exception:
        update_singleton(client, "MtaStageData", "script", previous["script"])
        update_singleton(client, "DataRetention", "expungeTrashAfter", previous["expungeTrashAfter"])
        client.call("x:Role/set", {"update": {
            role: {"disabledPermissions": values} for role, values in disabled.items()
        }})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    configure(json.loads(args.profile.read_text()), args.receipt)
    print("Community retention configured on the isolated test domain")
