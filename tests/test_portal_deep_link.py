"""A desk page opened on its own opens inside the portal at the same page.

The portal (place_holder) shows apps in frames with a left-edge app menu. A
right-click "new tab" or pasted link loaded the ERP page alone, without that
menu. Top-level document requests for /desk/... are redirected to
/?open=<path>; the portal opens that path in the ERP frame. Frame requests
(Sec-Fetch-Dest: iframe) are never redirected, so there is no loop.
"""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SSO = (ROOT / 'erpnext_drive_integrations/portal/sso.py').read_text()
PORTAL = (ROOT / 'erpnext_drive_integrations/www/place_holder.html').read_text()


def load(name):
    tree = ast.parse(SSO)
    wanted = {'portal_app_path', 'portal_open_target', 'PORTAL_APP_ROOTS'}
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in wanted)
             or (isinstance(n, ast.Assign) and getattr(n.targets[0], 'id', '') in wanted)]
    scope = {}
    exec(compile(ast.Module(nodes, []), 'sso', 'exec'), scope)
    return scope[name]


class PortalDeepLinkTests(unittest.TestCase):
    def test_target_keeps_path_and_query_and_rejects_others(self):
        target = load('portal_open_target')
        self.assertEqual(target('/desk/assets/asset', b'status=Draft'), '/desk/assets/asset?status=Draft')
        self.assertEqual(target('/desk/stock/item', b''), '/desk/stock/item')
        self.assertEqual(target('/insights', b''), '/insights')
        for bad in ['/api/method/x', '//evil.example/desk/x', '/desk/x\\\\y', '/login', '/raven/channel/general', '/insightsx/y']:
            with self.assertRaises(ValueError):
                target(bad)

    def test_redirect_only_for_top_level_signed_in_desk_documents(self):
        block = SSO[SSO.index('portal_app_path(path) and path != "/desk/cloud-apps"') - 200:]
        block = block[:block.index('redirect("/?"') + 80]
        self.assertIn('Sec-Fetch-Dest") == "document"', block)
        self.assertIn('frappe.session.user != "Guest"', block)
        self.assertIn('cloud_combined_site', block)

    def test_portal_accepts_only_desk_paths_and_opens_them_in_the_frame(self):
        self.assertIn("pendingOpen.path:app.url", PORTAL)
        pattern = re.search(r"open&&/(\^.*?\$)/\.test\(open\)", PORTAL).group(1)
        rx = re.compile(pattern)
        self.assertTrue(rx.match('/desk/assets/asset?x=1'))
        for good in ['/insights', '/insights/dashboard/x', '/insights?x=1']:
            self.assertTrue(rx.match(good), good)
        for bad in ['https://evil.example/', '//evil.example/x', '/api/method/x', 'javascript:alert(1)', '/raven', '/insightsx']:
            self.assertFalse(rx.match(bad), bad)


class ClientGuardTests(unittest.TestCase):
    """A single-page app's service worker can fetch navigations itself, so the server cannot
    tell a whole tab from a frame; session.js (on every HTML page) decides."""
    def test_session_guard_reopens_top_level_app_pages_in_the_portal(self):
        js = (ROOT / 'erpnext_drive_integrations/public/session.js').read_text()
        block = js[js.index('const portalApp'):js.index('const portalApp') + 700]
        self.assertIn('window.self === window.top', block)
        self.assertIn("display-mode: standalone", block)
        self.assertIn("/^\\/insights(\\/|$)/", block)
        self.assertIn("path !== '/desk/cloud-apps'", block)
        self.assertIn("location.replace('/?' + new URLSearchParams({ open: location.pathname + location.search }))", block)


if __name__ == '__main__':
    unittest.main(verbosity=2)
