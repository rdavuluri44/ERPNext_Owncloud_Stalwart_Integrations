"""The portal's app menu turns into two vertical columns above five icons (P58)."""
from pathlib import Path
import re
import unittest

PAGE = (Path(__file__).resolve().parents[1] / 'erpnext_drive_integrations/www/place_holder.html').read_text()


class PortalMenuColumnTests(unittest.TestCase):
    def test_script_switches_on_more_than_five_icons(self):
        self.assertIn("nav.querySelectorAll(':scope > a[data-app-id],:scope > a[data-external]').length>5", PAGE)
        self.assertIn("nav.classList.add('ph-two-cols')", PAGE)

    def test_two_column_rule_fills_down_then_across(self):
        rule = re.search(r'#ph-sidebar\.ph-two-cols\{([^}]*)\}', PAGE).group(1)
        self.assertIn('column-count:2', rule)  # balanced, top to bottom, then the next column
        # The default (five or fewer icons) layout is untouched.
        self.assertIn('#ph-sidebar{position:fixed;left:10px;', PAGE)
        self.assertIn('width:84px;display:flex;flex-direction:column', PAGE)


    def test_existing_menu_behaviour_rules_survive(self):
        """The auto-hide, the home button on the landing screen and the app frames
        depend on these rules; an earlier edit of this page lost them silently."""
        for rule in (
            'body:not(.ph-menu-open) #ph-sidebar,body:not(.ph-menu-open) #ph-shade,[hidden]{display:none!important}',
            'body:not(.ph-active) #ph-home{display:none}',
            '#ph-frames{display:none;position:fixed;inset:0;background:#fff}',
            '.ph-active #ph-frames{display:block}',
            '.ph-frame{display:block;border:0;width:100%;height:100%}',
            '.sr-only{position:absolute;',
        ):
            self.assertIn(rule, PAGE, rule)

    def test_home_button_has_the_first_row_alone(self):
        self.assertIn('#ph-sidebar.ph-two-cols #ph-home{column-span:all;', PAGE)

    def test_menu_is_centred_vertically_on_the_landing_screen_and_in_apps(self):
        self.assertIn('#ph-sidebar{position:fixed;left:10px;top:50%;transform:translateY(-50%);', PAGE)
        self.assertIn('body.ph-active #ph-sidebar{top:50%;', PAGE)


if __name__ == '__main__':
    unittest.main()
