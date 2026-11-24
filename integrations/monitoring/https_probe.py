#!/usr/bin/env python3
"""Probe HTTPS and private TCP services without logging endpoint addresses."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
import socket
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def certificate_days(url):
    endpoint = urlsplit(url)
    with socket.create_connection((endpoint.hostname, endpoint.port or 443), timeout=5) as connection:
        with ssl.create_default_context().wrap_socket(connection, server_hostname=endpoint.hostname) as tls:
            certificate = tls.getpeercert()
    return (ssl.cert_time_to_seconds(certificate["notAfter"]) - time.time()) / 86400


def check(target):
    name = target["name"]
    if target.get("kind") == "tcp":
        try:
            with socket.create_connection((target["host"], target["port"]), timeout=7):
                return name, True, "TCP reachable"
        except OSError:
            return name, False, "TCP unreachable"
    url = target["url"]
    try:
        with build_opener(NoRedirect()).open(url, timeout=7) as response:
            status = response.status
    except HTTPError as error:
        with closing(error):
            status = error.code
    except (OSError, URLError):
        return name, False, "connection failed"
    minimum_days = target.get("minimum_certificate_days")
    if status in target["statuses"] and minimum_days is not None:
        try:
            days = certificate_days(url)
        except (OSError, ValueError, KeyError):
            return name, False, "certificate check failed"
        if days < minimum_days:
            return name, False, f"certificate expires in {days:.1f} days"
    return name, status in target["statuses"], f"HTTP {status}"


def targets(path):
    items = json.loads(path.read_text())
    names = set()
    if not isinstance(items, list) or not items:
        raise ValueError("Configure at least one target")
    for item in items:
        name = item["name"]
        if not name or len(name) > 64 or not name.isprintable() or name in names:
            raise ValueError("Invalid or duplicate monitor target name")
        if item.get("kind") == "tcp":
            if not item["host"] or type(item["port"]) is not int or not 0 < item["port"] <= 65535:
                raise ValueError("Invalid TCP monitor target")
        else:
            url = urlsplit(item["url"])
            statuses = item["statuses"]
            minimum_days = item.get("minimum_certificate_days", 14)
            if (item.get("kind", "https") != "https" or url.scheme != "https" or not url.hostname
                    or url.username is not None or url.password is not None or url.fragment
                    or type(minimum_days) is not int or not 1 <= minimum_days <= 90
                    or not statuses or any(type(code) is not int or not 200 <= code < 400 for code in statuses)):
                raise ValueError("Invalid HTTPS monitor target")
        names.add(name)
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", type=Path)
    args = parser.parse_args()
    try:
        items = targets(args.targets)
    except (OSError, KeyError, TypeError, ValueError):
        parser.exit(2, "Invalid monitor configuration.\n")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(check, items))
    for name, ok, detail in results:
        print(f"{'OK' if ok else 'DOWN'} {name} ({detail})")
    return 0 if all(result[1] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
