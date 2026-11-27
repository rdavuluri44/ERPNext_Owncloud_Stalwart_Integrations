#!/usr/bin/env python3
"""Keep every approved-passkey list equal to integrations/authentik/passkey-providers.json (P79).

The JSON file is the one setting. Authentik runs some checks as standalone policy
text and the blueprint stores literal lists, so this tool rewrites those copies:

  * invite-recovery/native_recovery.py  ALLOWED_AAGUIDS
  * invite-recovery/provider_policy.py  ALLOWED_PROVIDERS
  * invite-recovery/install_native.py   allowed
  * configuration.json                  webauthn_allowed_device_types, and the
                                        embedded copies of native_recovery.py

    python3 tools/sync_passkey_providers.py          # rewrite the copies
    python3 tools/sync_passkey_providers.py --check  # exit 1 if any copy differs
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "integrations/authentik"
SETTING = AUTH / "passkey-providers.json"
NATIVE = AUTH / "invite-recovery/native_recovery.py"
POLICY = AUTH / "invite-recovery/provider_policy.py"
INSTALL = AUTH / "invite-recovery/install_native.py"
BLUEPRINT = AUTH / "configuration.json"
EMBED_SPLIT = "\ntry:\n"


def providers():
    items = json.loads(SETTING.read_text())["providers"]
    seen = [p["aaguid"].lower() for p in items]
    if len(seen) != len(set(seen)) or not seen:
        raise SystemExit("passkey-providers.json must list each provider once")
    return [(p["aaguid"].lower(), p["name"]) for p in items]


def replace_block(text, pattern, block, label):
    new, count = re.subn(pattern, lambda _: block, text, flags=re.S)
    if count != 1:
        raise SystemExit(f"could not find the provider list in {label}")
    return new


def rendered():
    items = providers()
    aaguids = [a for a, _ in items]
    native = replace_block(NATIVE.read_text(), r"ALLOWED_AAGUIDS = \{\n.*?\n\}",
                           "ALLOWED_AAGUIDS = {\n" + "".join(f'    "{a}",\n' for a in aaguids) + "}",
                           NATIVE.name)
    policy = replace_block(POLICY.read_text(), r"ALLOWED_PROVIDERS = \{\n.*?\n\}",
                           "ALLOWED_PROVIDERS = {\n" + "".join(f'    "{a}": {json.dumps(n)},\n' for a, n in items) + "}",
                           POLICY.name)
    install = replace_block(INSTALL.read_text(), r"allowed = \[[^\]]*\]",
                            "allowed = " + json.dumps(aaguids), INSTALL.name)
    graph = json.loads(BLUEPRINT.read_text())
    old_native = NATIVE.read_text().strip()
    for entry in graph["entries"]:
        attrs = entry.get("attrs", {})
        if "webauthn_allowed_device_types" in attrs:
            attrs["webauthn_allowed_device_types"] = list(aaguids)
        expression = attrs.get("expression")
        if isinstance(expression, str) and EMBED_SPLIT in expression:
            head, tail = expression.split(EMBED_SPLIT, 1)
            if head.strip() in (old_native, native.strip()) or "ALLOWED_AAGUIDS" in head:
                attrs["expression"] = native.rstrip("\n") + "\n" + EMBED_SPLIT.lstrip("\n") + tail
    blueprint = json.dumps(graph, indent=2, ensure_ascii=False) + "\n"
    return {NATIVE: native, POLICY: policy, INSTALL: install, BLUEPRINT: blueprint}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    # native_recovery.py first, so embedded copies use its rewritten text.
    first = rendered()
    if not args.check:
        NATIVE.write_text(first[NATIVE])
    files = rendered() if not args.check else first
    drift = [path for path, text in files.items() if path.read_text() != text]
    if args.check:
        for path in drift:
            print("differs from passkey-providers.json:", path.relative_to(ROOT))
        return 1 if drift else 0
    for path in drift:
        path.write_text(files[path])
        print("updated", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
