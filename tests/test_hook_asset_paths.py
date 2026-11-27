"""P93: every script or style a hook names must exist in the app.

Frappe skips a missing `doctype_js` file without an error, so a wrong path only
shows up as a button that never appears (the Job Offer "Request response" button,
found 26 November 2026). `/assets/<app>/...` include paths are served from the
app's `public` folder (register entry BUILD-5)."""
from pathlib import Path
import sys
import types
import unittest

fake = types.ModuleType('frappe'); fake.conf = {}; sys.modules.setdefault('frappe', fake)
from erpnext_drive_integrations import hooks

APP = Path(hooks.__file__).resolve().parent
ASSETS = '/assets/erpnext_drive_integrations/'
INCLUDE_HOOKS = ('app_include_js', 'app_include_css', 'web_include_js', 'web_include_css')
DOCTYPE_HOOKS = ('doctype_js', 'doctype_list_js', 'doctype_tree_js', 'doctype_calendar_js', 'page_js')


def _paths(value):
    return [value] if isinstance(value, str) else list(value)


class HookAssetPathTests(unittest.TestCase):
    def test_doctype_scripts_exist(self):
        for hook in DOCTYPE_HOOKS:
            for doctype, value in (getattr(hooks, hook, None) or {}).items():
                for path in _paths(value):
                    with self.subTest(hook=hook, doctype=doctype, path=path):
                        self.assertTrue((APP / path).is_file(), f'{hook}[{doctype!r}] names a missing file: {path}')

    def test_included_assets_exist(self):
        for hook in INCLUDE_HOOKS:
            for url in getattr(hooks, hook, None) or []:
                path = url.split('?', 1)[0]
                if not path.startswith(ASSETS):
                    continue
                with self.subTest(hook=hook, url=url):
                    self.assertTrue((APP / 'public' / path[len(ASSETS):]).is_file(), f'{hook} names a missing file: {url}')

    def test_job_offer_and_purchase_order_share_the_request_script(self):
        self.assertEqual(hooks.doctype_js['Job Offer'], 'onboarding/client/request_response.js')
        self.assertEqual(hooks.doctype_js['Purchase Order'], 'onboarding/client/request_response.js')


if __name__ == '__main__':
    unittest.main()
