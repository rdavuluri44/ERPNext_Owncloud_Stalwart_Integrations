#!/usr/bin/env python3
"""Prepare an ERP build entirely from pinned public sources, with no private image.

Output is a new external directory. Git repositories are fetched at exact commits;
the generated official-derived Dockerfile clones those local pinned sources.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess


def git_source(url, commit, directory):
    directory.mkdir(parents=True)
    for args in (["init", str(directory)],
                 ["-C", str(directory), "remote", "add", "origin", url],
                 ["-C", str(directory), "fetch", "--depth", "1", "origin", commit],
                 ["-C", str(directory), "checkout", "-b", "rebuild-pinned", "FETCH_HEAD"]):
        subprocess.run(["git", *args], check=True)
    actual = subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
    if actual != commit:
        raise RuntimeError("Fetched source differs from locked commit")


def replace_once(text, old, new):
    """Replace one upstream anchor; stop the build if it is missing or ambiguous (P91).

    A plain str.replace silently does nothing when upstream rewords the line, so the
    pins would not apply (register entry BUILD-1)."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Pinned official build template changed: expected 1 x {old!r}, found {count}")
    return text.replace(old, new, 1)


def rewrite_containerfile(text, lock):
    """frappe_docker's Containerfile with our pins and local sources (register BUILD-1)."""
    for old, new in (
        ("FROM python:${PYTHON_VERSION}-slim-${DEBIAN_BASE} AS base", "FROM " + lock["python_image"] + " AS base"),
        ("ARG NODE_VERSION=24", "ARG NODE_VERSION=" + lock["node_version"]),
        ("npm install -g yarn", "npm install -g yarn@" + lock["yarn_version"]),
        ("pip3 install frappe-bench", "pip3 install frappe-bench==" + lock["bench_version"]),
        ("USER frappe\n\nARG FRAPPE_BRANCH",
         "COPY --chown=frappe:0 app-sources /opt/source\n"
         "COPY python-constraints.txt /opt/build/python-constraints.txt\n"
         "ENV PIP_CONSTRAINT=/opt/build/python-constraints.txt\n"
         "ENV UV_CONSTRAINT=/opt/build/python-constraints.txt\n"
         "ENV NODE_OPTIONS=--max-old-space-size=3072\n"
         "USER frappe\n\nARG FRAPPE_BRANCH"),
        ("ARG FRAPPE_BRANCH=version-16", "ARG FRAPPE_BRANCH=rebuild-pinned"),
        ("ARG FRAPPE_PATH=https://github.com/frappe/frappe", "ARG FRAPPE_PATH=file:///opt/source/frappe"),
    ):
        text = replace_once(text, old, new)
    return text


def prepare(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.exists() or output == source or source in output.parents:
        raise ValueError("Output must be a new directory outside the checkout")
    output.mkdir(parents=True)
    lock = json.loads((source / "deployment/build-lock.json").read_text())
    upstream = output / "official"
    git_source(lock["frappe_docker"]["url"], lock["frappe_docker"]["commit"], upstream)
    apps = json.loads((source / "deployment/upstream-lock.json").read_text())
    for name, entry in apps.items():
        git_source(entry["url"], entry["commit"], output / "app-sources" / name)
    shutil.copytree(upstream / "resources", output / "resources")
    shutil.copy2(upstream / "LICENSE", output / "LICENSE.frappe-docker")
    shutil.copy2(source / "deployment/python-constraints.txt", output / "python-constraints.txt")
    shutil.copy2(source / "deployment/erp/frappe.conf.template", output / "resources/core/nginx/nginx-template.conf")
    text = rewrite_containerfile((upstream / "images/custom/Containerfile").read_text(), lock)
    (output / "Dockerfile").write_text(text)
    (output / "apps.json").write_text(json.dumps([
        {"url": "file:///opt/source/" + name, "branch": "rebuild-pinned"}
        for name in apps if name != "frappe"
    ], indent=2) + "\n")
    (output / ".dockerignore").write_text("official/\n*.log\n")
    (output / "source-lock.json").write_text(json.dumps({"build": lock, "apps": apps}, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.output))
