"""Tenant branding is supplied privately: logo and favicon set; the portal page keeps its name."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from render_runtime import FAVICON_FILES, render  # noqa: E402


def make_favicons(folder, names=FAVICON_FILES):
    for name in names:
        (Path(folder) / name).write_bytes(b"favicon:" + name.encode())


class BrandAssets(unittest.TestCase):
    def render(self, **extra):
        out = tempfile.mkdtemp()
        logo = Path(out) / "logo.svg"
        logo.write_text("<svg/>")
        config = {"domain": "example.net", "asset_version": "abcdef1", "company_logo": str(logo)}
        config.update(extra)
        return render(ROOT, Path(out) / "build", config)

    def test_default_brand_ships_with_the_repository(self):
        public = ROOT / "erpnext_drive_integrations/public"
        for name in FAVICON_FILES:
            self.assertTrue((public / ("company-" + name)).is_file(), name)

    def test_tenant_favicons_replace_the_placeholders(self):
        folder = tempfile.mkdtemp()
        make_favicons(folder)
        build = self.render(company_favicon_dir=folder)
        public = build / "erpnext_drive_integrations/public"
        for name in FAVICON_FILES:
            self.assertEqual((public / ("company-" + name)).read_bytes(), b"favicon:" + name.encode())

    def test_incomplete_favicon_set_is_refused(self):
        folder = tempfile.mkdtemp()
        make_favicons(folder, FAVICON_FILES[:-1])
        with self.assertRaises(ValueError) as caught:
            self.render(company_favicon_dir=folder)
        self.assertIn("favicon-512.png", str(caught.exception))

    def test_logo_and_favicon_urls_carry_the_release_version(self):
        build = self.render()
        page = (build / "erpnext_drive_integrations/www/place_holder.html").read_text()
        self.assertIn("/assets/erpnext_drive_integrations/company-favicon.svg?v=abcdef1", page)
        self.assertIn("/assets/erpnext_drive_integrations/company-favicon-180.png?v=abcdef1", page)
        code = (build / "erpnext_drive_integrations/www/place_holder.py").read_text()
        self.assertIn("company-logo-approved-v6.svg?v=abcdef1", code)
        push = (build / "erpnext_drive_integrations/portal/push.py").read_text()
        self.assertIn("company-favicon-192.png?v=abcdef1", push)
        blueprint = json.loads((build / "integrations/authentik/configuration.json").read_text()) \
            if (build / "integrations/authentik/configuration.json").exists() else None
        if blueprint is not None:
            self.assertIn("company-favicon-192.png?v=abcdef1", json.dumps(blueprint))

    def test_portal_page_keeps_its_name_and_shows_the_logo_in_the_menu(self):
        page = (ROOT / "erpnext_drive_integrations/www/place_holder.html").read_text()
        code = (ROOT / "erpnext_drive_integrations/www/place_holder.py").read_text()
        # Owner: same logo in the menu.
        self.assertIn("<title>Cloud</title>", page)
        self.assertIn("else (company or 'Applications')", code)
        self.assertIn(".ph-brand img{width:60px;height:60px;object-fit:contain}", page)
        self.assertIn('id="ph-home" title="Home" aria-label="Home"><img src="{{ entity_logo | e }}"', page)
        self.assertNotIn("Desk</title>", page)
        self.assertNotIn("entity_icon", page + code)

    def test_frappe_website_settings_carry_the_release_version(self):
        build = self.render()
        code = (build / "erpnext_drive_integrations/bootstrap.py").read_text()
        self.assertIn('"/assets/erpnext_drive_integrations/company-favicon-32.png?v=abcdef1"', code)
        self.assertIn('"/assets/erpnext_drive_integrations/company-logo-approved-v6.svg?v=abcdef1"', code)

    def test_drive_sign_in_page_is_white_without_the_upstream_logo(self):
        theme = json.loads((ROOT / "integrations/drive/theme/theme.json").read_text())
        web = theme["clients"]["web"]
        # Root-relative: the web client puts it in a CSS variable used by a stylesheet under
        # /assets/, so a relative URL would resolve to /assets/themes/... (the app's HTML).
        self.assertEqual(web["defaults"]["loginPage"]["backgroundImg"], "/themes/cloud/assets/plain.svg")
        self.assertEqual(web["defaults"]["logo"]["login"], "themes/cloud/assets/blank.svg")
        for variant in web.get("themes", []):
            self.assertNotEqual((variant.get("logo") or {}).get("login"), "themes/owncloud/assets/logo.svg")
        self.assertIn('fill="#ffffff"', (ROOT / "integrations/drive/theme/assets/plain.svg").read_text())
        config = json.loads((ROOT / "integrations/drive/config/web-with-picker.json").read_text())
        self.assertEqual(config["theme"], "https://drive.example.com/themes/cloud/theme.json")
        self.assertIn("integrations/drive/theme", (ROOT / "tools/prepare_runtime.py").read_text())
        # oCIS overrides the config file's theme with WEB_UI_THEME_PATH, so the stack must select it too.
        stack = json.loads((ROOT / "deployment/stacks/drive.compose.json").read_text())
        self.assertEqual(stack["services"]["ocis"]["environment"]["WEB_UI_THEME_PATH"], "/themes/cloud/theme.json")

    def test_webmail_favicon_is_the_compact_icon(self):
        source = (ROOT / "tools/prepare_runtime.py").read_text()
        self.assertIn("company-favicon.svg", source)
        self.assertIn("'FAVICON_URL':favicon", source)
        # A profile may serve the favicon from elsewhere (e.g. the website's /front/ assets).
        self.assertIn("favicon=profile.get('favicon_url') or", source)


if __name__ == "__main__":
    unittest.main()
