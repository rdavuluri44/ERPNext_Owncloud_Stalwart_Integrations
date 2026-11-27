#!/usr/bin/env python3
"""Prepare pinned upstream Mail plus the selected overlay and corresponding source.

Use a rendered release as --source for production URLs. Build context is new and
outside the repository; no deployment environment or secret files are copied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile


def check_overlay_base(lock, overlay, upstream):
    """Stop unless the overlay was made from exactly these upstream files (P91, register WEBMAIL-1).

    The overlay replaces whole files, so copying it over changed upstream files would
    silently undo upstream's changes to them."""
    base = lock["overlay_base"]
    if base["commit"] != lock["commit"]:
        raise ValueError("Webmail commit changed: run tools/refresh_webmail_overlay_base.py and merge the overlay")
    ours = sorted(p.relative_to(overlay).as_posix() for p in Path(overlay).rglob("*") if p.is_file())
    if ours != sorted([*base["replaced"], *base["added"]]):
        raise ValueError("Overlay files and overlay_base in integrations/mail/upstream.json differ")
    changed = [name for name, digest in base["replaced"].items()
               if not (Path(upstream) / name).is_file()
               or hashlib.sha256((Path(upstream) / name).read_bytes()).hexdigest() != digest]
    changed += [name for name in base["added"] if (Path(upstream) / name).exists()]
    if changed:
        raise ValueError("Upstream webmail files differ from the overlay's base: " + ", ".join(changed))


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source in output.parents or output.exists():
        raise ValueError("Output must be a new directory outside the source tree")
    lock = json.loads((source / "integrations/mail/upstream.json").read_text())
    if lock["repository"] != "https://github.com/bulwarkmail/webmail":
        raise ValueError("Unexpected upstream repository")
    subprocess.run(["git", "clone", "--no-checkout", lock["repository"], str(output)], check=True)
    subprocess.run(["git", "-C", str(output), "checkout", "--detach", lock["commit"]], check=True)
    check_overlay_base(lock, source / "integrations/mail/overlay", output)
    shutil.copytree(source / "integrations/mail/overlay", output, dirs_exist_ok=True)
    archive = output / "public/cloud-customization-source.zip"
    archive.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in output.rglob("*"):
            if not path.is_file() or path == archive:
                continue
            relative = path.relative_to(output)
            if any(p in {".git", "node_modules", ".next"} for p in relative.parts):
                continue
            if path.name.startswith(".env") or path.suffix in {".pem", ".key", ".zip"}:
                continue
            zipped.write(path, relative)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.output))
