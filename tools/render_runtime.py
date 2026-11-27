#!/usr/bin/env python3
"""Render public deployment URLs into a build tree; never edit the Git checkout.

Runtime secrets remain in site/environment/secret files, not rendered browser assets.
"""
import argparse
import json
import pathlib
import re
import shutil

# The tenant supplies these through the private profile (company_favicon_dir).
FAVICON_FILES = ("favicon.svg", "favicon-16.png", "favicon-32.png", "favicon-48.png",
                 "favicon-180.png", "favicon-192.png", "favicon-512.png")

def public_mappings(values):
    """Include dotted-host regex forms as well as ordinary public literals."""
    result=dict(values)
    for before,after in values.items():
        if '.' in before:
            result[before.replace('.', '[.]')]=after.replace('.', '[.]')
            result[re.escape(before)]=re.escape(after)
    return result

def render(source, destination, config):
    source, destination = pathlib.Path(source).resolve(), pathlib.Path(destination).resolve()
    if destination == source or source in destination.parents:
        raise ValueError("The build destination must be outside the source checkout")
    domain = config["domain"]
    if not re.fullmatch(r"[A-Za-z0-9.-]+", domain) or "." not in domain:
        raise ValueError("domain must be a DNS name")
    mappings = {"example.com": domain, "/var/lib/cloud-integration": config.get("session_state_path", "/var/lib/cloud-integration")}
    landing = config.get("landing_url")
    if landing:
        # Where every logout ends (the company website); default https://www.<domain>/.
        if not re.fullmatch(r"https://[A-Za-z0-9.-]+/", landing):
            raise ValueError("landing_url must look like https://host/")
        mappings["https://www.example.com/"] = landing
    for key, value in config.get("public_replacements", {}).items():
        if not isinstance(key, str) or not isinstance(value, str) or any(c in value for c in ["\n", "\r", "\x00"]):
            raise ValueError("Invalid public replacement")
        mappings[key] = value
    mappings=public_mappings(mappings)
    version=config.get('asset_version')
    if version and not re.fullmatch(r'[a-f0-9]{7,64}',version):
        raise ValueError('asset_version must be a Git commit hash')
    destination.mkdir(parents=True, exist_ok=True)
    # Everything deployment/erp/Dockerfile.addon copies must be here: the rendered folder is its build context
    # (a test compares the two). The face model list and its fetch tool were missing at first (P95 test build).
    for relative in ["erpnext_drive_integrations", "pyproject.toml", "MANIFEST.in", "integrations",
                     "tools/fetch_face_models.py", "deployment/face-models.json"]:
        src, dst = source / relative, destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
        else:
            shutil.copy2(src, dst)
    for p in destination.rglob("*"):
        if not p.is_file() or p.suffix not in {".py", ".mjs", ".js", ".tsx", ".ts", ".html", ".json", ".yaml", ".yml", ".css", ".toml", ".svg"}:
            continue
        text = p.read_text()
        # Longer public identifiers win over their containing base domain.
        for before, after in sorted(mappings.items(), key=lambda item: len(item[0]), reverse=True):
            text = text.replace(before, after)
        if version:
            text=re.sub(r'(/assets/erpnext_drive_integrations/[A-Za-z0-9_./-]+\.(?:js|css))(?:\?v=[A-Za-z0-9_.-]+)?',
                        lambda match:match.group(1)+'?v='+version,text)
        if version:
            # Logo and favicon files keep their names, so a version parameter makes browsers refresh them.
            text=re.sub(r'(/assets/erpnext_drive_integrations/(?:company-logo-approved-v6\.svg|company-favicon[A-Za-z0-9._-]*\.(?:svg|png)))(?:\?v=[A-Za-z0-9_.-]+)?',
                        lambda match:match.group(1)+'?v='+version,text)
        if version and p.suffix in {".html", ".mjs"}:
            text=re.sub(r'(\.mjs)(?:\?v=[A-Za-z0-9_.-]+)?(?=[\"\'])',
                        lambda match:match.group(1)+'?v='+version,text)
        if version and p.name == "index.html" and p.parent.parts[-2:] == ("invite-recovery", "public"):
            text = text.replace('href="./style.css"', f'href="./style.css?v={version}"')
        p.write_text(text)
    logo = config.get("company_logo")
    if logo:
        shutil.copy2(logo, destination / "erpnext_drive_integrations/public/company-logo-approved-v6.svg")
    favicons = config.get("company_favicon_dir")
    if favicons:
        folder = pathlib.Path(favicons)
        missing = [name for name in FAVICON_FILES if not (folder / name).is_file()]
        if missing:
            raise ValueError("company_favicon_dir is missing: " + ", ".join(missing))
        public = destination / "erpnext_drive_integrations/public"
        for name in FAVICON_FILES:
            # favicon.svg -> company-favicon.svg, favicon-32.png -> company-favicon-32.png
            shutil.copy2(folder / name, public / ("company-" + name))
    return destination

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(pathlib.Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print(render(args.source, args.output, json.loads(pathlib.Path(args.config).read_text())))
