#!/usr/bin/env python3
"""Pin the image of Coolify's proxy (Traefik) to the version in deployment/coolify-proxy.json (P90).

Coolify writes its proxy as `traefik:v3.x`, a tag that moves with every release, so what a host runs depends on when
it last pulled. This tool writes the pinned image (tag plus digest) into Coolify's saved proxy configuration (so a
restart from the dashboard keeps it) and into the proxy compose file, like coolify_proxy_hosts.py. It keeps a copy of
the compose file first. `--restart` pulls the image, recreates the proxy and reattaches every network it had;
`--check` only reports what runs and what is pinned.

    python3 tools/coolify_proxy_image.py --check
    python3 tools/coolify_proxy_image.py --restart        # on the host, as root
"""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coolify_proxy_hosts import COMPOSE, psql  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT / "deployment/coolify-proxy.json"
IMAGE_LINE = re.compile(r"^(?P<indent>[ \t]*)image:[ \t]*['\"]?(?P<image>traefik[^\s'\"]*)['\"]?[ \t]*$", re.M)
PINNED = re.compile(r"^traefik:v(?P<version>\d+\.\d+\.\d+)@sha256:[0-9a-f]{64}$")


def pinned(path=PIN):
    pin = json.loads(Path(path).read_text())
    match = PINNED.fullmatch(pin["image"])
    if not match or match.group("version") != pin["version"]:
        raise ValueError("deployment/coolify-proxy.json: image must be traefik:v<version>@sha256:<digest> matching 'version'")
    return pin


def apply(text, image):
    """The compose text with the Traefik image line set to `image`; exactly one such line must exist."""
    lines = IMAGE_LINE.findall(text)
    if len(lines) != 1:
        raise ValueError(f"expected one traefik image line in the proxy compose, found {len(lines)}")
    return IMAGE_LINE.sub(lambda m: f"{m.group('indent')}image: '{image}'", text)


def current(text):
    found = IMAGE_LINE.search(text)
    return found.group("image") if found else None


def write(image, server_id=0, compose=COMPOSE):
    text = compose.read_text()
    new = apply(text, image)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = compose.parent / "backups" / f"docker-compose.yml.before-image-{stamp}"
    backup.parent.mkdir(exist_ok=True)
    shutil.copy2(compose, backup)
    proxy = json.loads(psql(f"select proxy from servers where id={server_id};"))
    if proxy.get("last_saved_proxy_configuration"):
        proxy["last_saved_proxy_configuration"] = apply(proxy["last_saved_proxy_configuration"], image)
        proxy["last_saved_settings"] = hashlib.md5(proxy["last_saved_proxy_configuration"].encode()).hexdigest()
        tag = "p" + hashlib.sha256(json.dumps(proxy).encode()).hexdigest()[:16]
        psql(f"update servers set proxy=${tag}${json.dumps(proxy)}${tag}$::json where id={server_id};")
    compose.write_text(new)
    return backup


def running_version(run=subprocess.run):
    out = run(["docker", "exec", "coolify-proxy", "traefik", "version"], capture_output=True, text=True).stdout
    found = re.search(r"^Version:\s*(\S+)", out, re.M)
    return found.group(1) if found else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--server-id", type=int, default=0)
    parser.add_argument("--check", action="store_true", help="report only")
    parser.add_argument("--restart", action="store_true", help="pull, recreate the proxy and keep its networks")
    args = parser.parse_args(argv)
    pin = pinned()
    print(f"pinned: {pin['version']}; compose: {current(COMPOSE.read_text())}; running: {running_version()}")
    if args.check:
        return 0 if running_version() == pin["version"] else 1
    backup = write(pin["image"], args.server_id)
    print(f"written to the saved proxy configuration and the compose file (copy: {backup})")
    if args.restart:
        from coolify_proxy_http3 import restart_keeping_networks
        subprocess.run(["docker", "pull", "-q", pin["image"]], check=True, stdout=subprocess.DEVNULL)
        print("proxy recreated; reattached networks:", restart_keeping_networks() or "none needed")
        version = running_version()
        print(f"running: {version}")
        return 0 if version == pin["version"] else 1
    print("restart the proxy to apply (--restart)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
