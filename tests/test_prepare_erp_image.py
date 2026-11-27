"""P91: every change we make to frappe_docker's Containerfile must find its upstream line.

Before P91 six of the seven replacements were plain str.replace calls, so an
upstream rewording silently dropped our pins (register entry BUILD-1)."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_erp_image', ROOT / 'tools/prepare_erp_image.py')
prepare = importlib.util.module_from_spec(spec); spec.loader.exec_module(prepare)

LOCK = {'python_image': 'python@sha256:abc', 'node_version': '24.1.2', 'yarn_version': '1.2.3', 'bench_version': '5.6.7'}
# The seven upstream lines we change, as they appear in the pinned Containerfile.
UPSTREAM = """ARG PYTHON_VERSION=3.14
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_BASE} AS base
ARG NODE_VERSION=24
RUN npm install -g yarn
RUN pip3 install frappe-bench
USER frappe

ARG FRAPPE_BRANCH=version-16
ARG FRAPPE_PATH=https://github.com/frappe/frappe
"""
ANCHORS = ['FROM python:${PYTHON_VERSION}-slim-${DEBIAN_BASE} AS base', 'ARG NODE_VERSION=24',
           'npm install -g yarn', 'pip3 install frappe-bench', 'USER frappe\n\nARG FRAPPE_BRANCH',
           'ARG FRAPPE_BRANCH=version-16', 'ARG FRAPPE_PATH=https://github.com/frappe/frappe']


class ContainerfileRewriteTests(unittest.TestCase):
    def test_pins_and_local_sources_are_applied(self):
        text = prepare.rewrite_containerfile(UPSTREAM, LOCK)
        for expected in ('FROM python@sha256:abc AS base', 'ARG NODE_VERSION=24.1.2', 'npm install -g yarn@1.2.3',
                         'pip3 install frappe-bench==5.6.7', 'ENV PIP_CONSTRAINT=/opt/build/python-constraints.txt',
                         'ENV NODE_OPTIONS=--max-old-space-size=3072', 'ARG FRAPPE_BRANCH=rebuild-pinned',
                         'ARG FRAPPE_PATH=file:///opt/source/frappe'):
            self.assertIn(expected, text)
        self.assertNotIn('https://github.com/frappe/frappe', text)

    def test_every_changed_upstream_line_stops_the_build(self):
        for anchor in ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, UPSTREAM)
                with self.assertRaisesRegex(RuntimeError, 'build template changed'):
                    prepare.rewrite_containerfile(UPSTREAM.replace(anchor, '#' + anchor[1:]), LOCK)

    def test_a_duplicated_line_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'found 2'):
            prepare.rewrite_containerfile(UPSTREAM + 'RUN npm install -g yarn\n', LOCK)


if __name__ == '__main__':
    unittest.main()
