"""Owner rule (21 November 2026): production and test have separate asset sets; a change to the test
site's look must never change production. The shared portal page takes every site-specific look from
site settings, and with none of them set (production) it is exactly production's page."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "erpnext_drive_integrations/www/place_holder.html").read_text()
CODE = (ROOT / "erpnext_drive_integrations/www/place_holder.py").read_text()
LOOK = {"entity_name": "cloud_portal_hide_entity_name", "portal_logo_height": "cloud_portal_logo_height",
        "portal_clean_root": "cloud_portal_clean_root_address",
        "portal_logo_position": "cloud_portal_logo_position"}


def production_view(page):
    """The page as a site without look settings renders it: the company name is shown and the
    optional blocks are dropped."""
    page = page.replace("{% if entity_name %}<span>{{ entity_name | e }}</span>{% endif %}",
                        "<span>{{ entity_name | e }}</span>")
    for flag in ("portal_logo_height", "portal_clean_root", "portal_logo_position"):
        page = re.sub(r"\{% if " + flag + r" %\}.*?\{% endif %\}", "", page, flags=re.S)
    return page


class SiteLook(unittest.TestCase):
    def test_every_look_setting_is_read_from_site_config_with_production_defaults(self):
        for setting in LOOK.values():
            self.assertIn("frappe.conf.get('%s')" % setting, CODE)
        self.assertIn("context.entity_name = '' if frappe.conf.get('cloud_portal_hide_entity_name') else (company or 'Applications')", CODE)
        self.assertIn("40 <= height <= 100 else 0", CODE)                       # unset or odd value: no change

    def test_without_settings_the_page_is_productions(self):
        view = production_view(PAGE)
        # P111: the logo sits in the top bar (its height and position settings no longer change anything);
        # the company name is on the Desk's home.
        self.assertIn('<img src="{{ entity_logo | e }}" alt=""></button><nav id="ph-apps"', view)
        self.assertIn('<section id="ph-homeview" aria-label="Home"><span>{{ entity_name | e }}</span></section>', view)
        self.assertIn("#ph-fullscreen img{height:30px;width:auto;max-width:96px;object-fit:contain;display:block}", view)
        self.assertNotIn("portal_logo_height", view)
        self.assertNotIn("history.replaceState(history.state,'','/'", view)

    def test_site_specific_parts_appear_only_inside_their_setting(self):
        outside = re.sub(r"\{% if (portal_logo_height|portal_clean_root|portal_logo_position) %\}.*?\{% endif %\}", "", PAGE, flags=re.S)
        self.assertNotIn("portal_logo_position.top", outside)
        self.assertNotIn("{{ portal_logo_height }}", outside)
        self.assertNotIn("history.replaceState(history.state,'','/'", outside)

    def test_test_only_stylesheet_never_restyles_shared_elements(self):
        css = (ROOT / "erpnext_drive_integrations/public/test-refresh.css").read_text()
        self.assertNotIn(".ph-brand", css)
        self.assertIn('{% if test_refresh_enabled %}<meta name="test-refresh-csrf"', PAGE)

    def test_test_profile_may_set_only_the_look_settings(self):
        tool = (ROOT / "tools/prepare_test_profiles.py").read_text()
        self.assertIn("allowed={'cloud_portal_hide_entity_name','cloud_portal_logo_height','cloud_portal_logo_position','cloud_portal_clean_root_address'}", tool)


if __name__ == "__main__":
    unittest.main()
