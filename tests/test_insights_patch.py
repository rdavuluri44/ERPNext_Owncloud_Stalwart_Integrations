"""P91: the Insights source patch stops the build when an upstream line it changes is missing.

Register entry INSIGHTS-1. The fixtures hold only the upstream lines the patch
touches; the real files come from the pinned Insights commit at build time."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('patch_session', ROOT / 'integrations/insights/patch_session.py')
patch = importlib.util.module_from_spec(spec); spec.loader.exec_module(patch)

SESSION = """async function initialize(force: boolean = false) {
\tif (session.initialized && !force) return
\tObject.assign(session.user, getSessionFromCookies())
\tawait fetchSessionInfo()
}

async function fetchSessionInfo() {
\tif (!session.isLoggedIn) return
\treturn {}
}

function getSessionFromCookies() {
\treturn {}
}
"""
ROUTER = """\t{
\t\tname: 'Workbook',
\t\tcomponent: () => import('./workbook/Workbook.vue'),
\t\tmeta: { hideSidebar: true },
\t},
"""
SIDEBAR = """<template>
\t<router-link v-for="link in links" :to="link.to">
</template>
<script setup lang="ts">
import { computed, ref } from 'vue'

const links = ref([
\t{ to: 'WorkbookList' },
])
</script>
"""


def tree(session=SESSION, router=ROUTER, sidebar=SIDEBAR):
    root = Path(tempfile.mkdtemp())
    front = root / 'frontend/src2'
    (front / 'components').mkdir(parents=True)
    (front / 'session.ts').write_text(session)
    (front / 'router.ts').write_text(router)
    (front / 'components/AppSidebar.vue').write_text(sidebar)
    return root, front


class InsightsPatchTests(unittest.TestCase):
    def test_patch_applies_and_is_idempotent(self):
        root, front = tree()
        patch.patch(root)
        once = {p: (front / p).read_text() for p in ('session.ts', 'router.ts', 'components/AppSidebar.vue')}
        self.assertIn("import { useRoute } from 'vue-router'", once['components/AppSidebar.vue'])
        self.assertIn('const route = useRoute()', once['components/AppSidebar.vue'])
        self.assertNotIn('hideSidebar', once['router.ts'])
        self.assertNotIn('getSessionFromCookies', once['session.ts'])
        patch.patch(root)
        self.assertEqual(once, {p: (front / p).read_text() for p in once})

    def test_each_changed_sidebar_line_must_exist_once(self):
        for line in (':to="link.to"', "import { computed, ref } from 'vue'", 'const links = ref(['):
            with self.subTest(line=line):
                root, _ = tree(sidebar=SIDEBAR.replace(line, '#' + line[1:]))
                with self.assertRaisesRegex(ValueError, 'sidebar changed'):
                    patch.patch(root)
                root, _ = tree(sidebar=SIDEBAR + line + '\n')
                with self.assertRaisesRegex(ValueError, 'sidebar changed'):
                    patch.patch(root)

    def test_changed_session_or_route_stops_the_build(self):
        root, _ = tree(session=SESSION.replace('\tif (!session.isLoggedIn) return\n', ''))
        with self.assertRaisesRegex(ValueError, 'session guard changed'):
            patch.patch(root)
        root, _ = tree(router=ROUTER.replace('\t\tmeta: { hideSidebar: true },\n', ''))
        with self.assertRaisesRegex(ValueError, 'workbook route changed'):
            patch.patch(root)


if __name__ == '__main__':
    unittest.main()
