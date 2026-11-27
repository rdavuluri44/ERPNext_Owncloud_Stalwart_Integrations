#!/usr/bin/env python3
"""Apply local session and workbook navigation changes to pinned Insights."""

from pathlib import Path
import re
import sys


def _replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("Pinned Insights sidebar changed; review the adapter")
    return text.replace(old, new, 1)


def patch_session(frontend):
    file = frontend / "session.ts"
    source = file.read_text()
    marker = "// cloud-integrations: native verified session bootstrap"
    if marker in source:
        return

    start = source.index("async function initialize(")
    stop = source.index("\nasync function fetchSessionInfo()", start)
    if "Object.assign(session.user, getSessionFromCookies())" not in source[start:stop]:
        raise ValueError("Pinned Insights session initialization changed; review the adapter")
    source = source[:start] + f"""async function initialize(force: boolean = false) {{
	if (session.initialized && !force) return
	{marker}
	await Promise.all([
		fetchSiteInfo(),
		fetchSessionInfo().catch(() => resetSession()),
	])
	session.initialized = true
}}
""" + source[stop:]

    guard = "\tif (!session.isLoggedIn) return\n"
    if source.count(guard) != 1:
        raise ValueError("Pinned Insights session guard changed; review the adapter")
    source = source.replace(guard, "")
    source, count = re.subn(
        r"\nfunction getSessionFromCookies\(\) \{.*?\n\}\n", "", source, flags=re.DOTALL
    )
    if count != 1:
        raise ValueError("Pinned Insights cookie reader changed; review the adapter")
    file.write_text(source)


def patch_workbook_navigation(frontend):
    router = frontend / "router.ts"
    routes = router.read_text()
    marker = "// cloud-integrations: keep the Insights menu in workbooks"
    workbook_route = "\t\tcomponent: () => import('./workbook/Workbook.vue'),\n"
    if marker not in routes:
        hidden_workbook_route = workbook_route + "\t\tmeta: { hideSidebar: true },\n"
        if routes.count(hidden_workbook_route) != 1:
            raise ValueError("Pinned Insights workbook route changed; review the adapter")
        routes = routes.replace(hidden_workbook_route, workbook_route + f"\t\t{marker}\n")

    sidebar = frontend / "components/AppSidebar.vue"
    links = sidebar.read_text()
    active_binding = ':isActive="link.to === \'WorkbookList\' && isWorkbookRoute"'
    if active_binding not in links:
        target = ':to="link.to"'
        # Every sidebar change must find exactly one upstream line (P91, register INSIGHTS-1):
        # a missed import would leave useRoute undefined at runtime, which the build does not catch.
        links = _replace_once(links, target, target + "\n\t\t\t\t\t\t" + active_binding)
        links = _replace_once(
            links,
            "import { computed, ref } from 'vue'",
            "import { computed, ref } from 'vue'\nimport { useRoute } from 'vue-router'",
        )
        links = _replace_once(
            links,
            "const links = ref([",
            "const route = useRoute()\n"
            "const isWorkbookRoute = computed(() => route.matched.some(record => record.name === 'Workbook'))\n\n"
            "const links = ref([",
        )
    router.write_text(routes)
    sidebar.write_text(links)


def patch(root):
    frontend = Path(root) / "frontend/src2"
    patch_session(frontend)
    patch_workbook_navigation(frontend)


if __name__ == "__main__":
    patch(sys.argv[1])
