"""P111: the Desk's always-visible top bar, and what the applications do inside the Desk (P114, P115).

From the left: the brand icon (full screen), the applications in a strip that scrolls inside its own space, on
the test site the refresh button, then search, notifications and the person's button with About, font size, mode
and Sign out. Search and notifications are universal: the Desk asks the business system itself and every other
application through its own page. These tests pin the page, the protocol both sides speak, and the rules each
application applies inside the Desk, so one side cannot change without the other.
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / 'erpnext_drive_integrations/www/place_holder.html').read_text(encoding='utf-8')
CODE = (ROOT / 'erpnext_drive_integrations/www/place_holder.py').read_text(encoding='utf-8')
DESK_API = (ROOT / 'erpnext_drive_integrations/portal/desk.py').read_text(encoding='utf-8')
ERP = (ROOT / 'erpnext_drive_integrations/public/session.js').read_text(encoding='utf-8')
DRIVE = (ROOT / 'integrations/drive/workspace.js').read_text(encoding='utf-8')
DMS = (ROOT / 'integrations/dms/cloud_session/session.js').read_text(encoding='utf-8')
BAR = re.search(r'<header id="ph-top".*?</header>', PAGE, re.S).group(0)
MENU = re.search(r'<div id="ph-user-menu".*?</div><dialog', PAGE, re.S).group(0)
ABOUT = re.search(r'<dialog id="ph-about".*?</dialog>', PAGE, re.S).group(0)
SCRIPT = re.search(r"<script>\{% raw %\}\n\(\(\)=>\{'use strict';(.*?)\}\)\(\);\{% endraw %\}</script>", PAGE, re.S).group(1)
DRIVE_DESK = DRIVE[DRIVE.index('window.__cloudDriveDesk'):]
DMS_DESK = DMS[DMS.index('window.__cloudDmsDesk'):]


class TheBar(unittest.TestCase):
    def test_order_from_left_to_right(self):
        order = [BAR.index('id="%s"' % name) for name in
                 ('ph-fullscreen', 'ph-apps', 'ph-refresh-toggle', 'ph-search', 'ph-bell', 'ph-user')]
        self.assertEqual(order, sorted(order))

    def test_it_is_always_visible_and_the_applications_start_below_it(self):
        self.assertIn('#ph-top{position:fixed;inset:0 0 auto 0;height:var(--ph-bar);', PAGE)
        self.assertIn('#ph-frames{display:none;position:fixed;inset:var(--ph-bar) 0 0 0;', PAGE)
        self.assertNotRegex(PAGE, r'\.ph-active #ph-top\{[^}]*display:none')
        for rule in ('.ph-active #ph-frames{display:block}', '.ph-frame{display:block;border:0;width:100%;height:100%}',
                     '.sr-only{position:absolute;', '[hidden]{display:none!important}'):
            self.assertIn(rule, PAGE, rule)

    def test_the_auto_hiding_menu_is_gone(self):
        for old in ('ph-edge', 'ph-sidebar', 'ph-shade', 'ph-menu-open', 'ph-two-cols', 'id="ph-bar"'):
            self.assertNotIn(old, PAGE, old)

    def test_the_applications_scroll_inside_their_own_space(self):
        rule = re.search(r'#ph-apps\{([^}]*)\}', PAGE).group(1)
        self.assertIn('flex:1 1 auto;min-width:0', rule)
        self.assertIn('overflow-x:auto', rule)
        self.assertIn("strip.addEventListener('wheel'", SCRIPT)
        self.assertIn('id="ph-home" title="Home" aria-label="Home"', BAR)

    def test_the_brand_icon_toggles_full_screen(self):
        self.assertIn('<button id="ph-fullscreen" type="button" aria-label="Enter fullscreen" title="Enter fullscreen">'
                      '<img src="{{ entity_logo | e }}" alt=""></button>', BAR)
        self.assertIn('root.requestFullscreen()', SCRIPT)

    def test_the_refresh_button_exists_on_the_test_site_only(self):
        self.assertRegex(BAR, r'\{% if test_refresh_enabled %\}<button id="ph-refresh-toggle"[^>]*>.*?</button>\{% endif %\}')
        self.assertRegex(PAGE, r'\{% if test_refresh_enabled %\}<section id="ph-test-refresh"')

    def test_the_person_button_is_squarish_and_shows_the_initial(self):
        self.assertIn('>{{ user_short[:1] | e }}</button>', BAR)
        rule = re.search(r'#ph-top #ph-user\{([^}]*)\}', PAGE).group(1)
        self.assertIn('width:32px;height:32px;border-radius:7px', rule)

    def test_its_menu_has_about_font_size_mode_and_sign_out_last(self):
        self.assertEqual(re.findall(r'<button class="ph-row" id="([a-z-]+)"', MENU), ['ph-about-open', 'ph-signout'])
        self.assertEqual(re.findall(r'data-font="([0-9.]+)"', MENU), ['0.9', '1', '1.15'])
        self.assertEqual(re.findall(r'data-theme-choice="([a-z]+)"', MENU), ['light', 'dark', 'auto'])
        self.assertLess(MENU.index('data-theme-choice'), MENU.index('id="ph-signout"'))

    def test_font_size_and_mode_are_kept_in_the_browser_and_told_to_every_application(self):
        self.assertIn("localStorage.setItem('cloud-desk-look',JSON.stringify(look))", SCRIPT)
        self.assertIn("tell(f,'look',{font:look.font,theme:look.theme,dark:dark()})", SCRIPT)
        self.assertIn("frame.addEventListener('load',()=>sendLook(frame))", SCRIPT)
        for app in (ERP, DRIVE_DESK, DMS_DESK):
            self.assertIn("'look'", app)
            self.assertIn('[0.9,1,1.15].includes(' if app is not ERP else '[0.9, 1, 1.15].includes(', app)


class About(unittest.TestCase):
    def test_the_unformat_mark_is_written_in_the_page_not_read_from_the_assets(self):
        self.assertIn('aria-label="Unformat"', ABOUT)
        self.assertIn('<rect width="64" height="64" rx="14" fill="#1F3A5F"/>', ABOUT)
        self.assertNotIn('/assets/', ABOUT)
        self.assertNotIn('<img', ABOUT)
        self.assertNotIn('entity_logo', ABOUT)

    def test_it_names_our_application_as_the_business_system_installs_it(self):
        self.assertIn("OURS = 'erpnext_drive_integrations'", DESK_API)
        package = (ROOT / 'erpnext_drive_integrations/__init__.py').read_text(encoding='utf-8')
        self.assertIn('__repository__ = "https://github.com/rdavuluri44/erpnext_drive_integrations"', package)
        self.assertIn('from erpnext_drive_integrations import __repository__ as REPOSITORY', DESK_API)
        self.assertIn("context.app_name = 'erpnext_drive_integrations'", CODE)
        self.assertIn("context.app_repository = getattr(ours, '__repository__', '')", CODE)
        self.assertIn('<strong id="ph-about-name">{{ app_name | e }}</strong>', ABOUT)
        self.assertIn('href="{{ app_repository | e }}" target="_blank" rel="noopener noreferrer"', ABOUT)
        self.assertIn('Source on GitHub', ABOUT)

    def test_versions_are_read_when_it_opens_and_written_as_text(self):
        self.assertIn("call('erpnext_drive_integrations.portal.desk.about')", SCRIPT)
        self.assertIn('a.textContent=name;b.textContent=version;', SCRIPT)
        self.assertNotIn('innerHTML', SCRIPT)
        self.assertIn("@frappe.whitelist(methods=['GET'])\ndef about():", DESK_API)
        self.assertIn('frappe.get_installed_apps() if app != OURS', DESK_API)

    def test_the_other_applications_come_from_the_versions_we_pin(self):
        spec = importlib.util.spec_from_file_location('about_components', ROOT / 'tools/about_components.py')
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        packaged = json.loads((ROOT / 'erpnext_drive_integrations/portal/components.json').read_text(encoding='utf-8'))
        self.assertEqual(packaged, tool.components(), 'run tools/about_components.py')
        names = [row['name'] for row in packaged['components']]
        for name in ('ownCloud Infinite Scale', 'ONLYOFFICE Docs', 'Stalwart', 'Paperless-ngx', 'authentik', 'Synapse'):
            self.assertIn(name, names)
        self.assertTrue(all(row['version'] for row in packaged['components']))


class UniversalSearchAndNotifications(unittest.TestCase):
    def test_the_desk_asks_the_business_system_itself_and_every_other_application_in_its_page(self):
        self.assertIn("call('frappe.utils.global_search.search',{text,start:0,limit:8})", SCRIPT)
        self.assertIn("tell(f,'search',{text,round})", SCRIPT)
        self.assertIn("for(const a of apps)if(!a.url.startsWith('/'))frameFor(a.id);", SCRIPT)   # not opened yet: loaded, hidden
        self.assertIn("call('erpnext_drive_integrations.portal.desk.notifications')", SCRIPT)
        self.assertIn("tell(f,'notifications?')", SCRIPT)

    def test_answers_are_taken_only_from_our_own_frames_and_only_for_the_current_search(self):
        self.assertIn("if((!trusted.has(e.origin)&&e.origin!==location.origin)||![...frames.values()].some(f=>f.contentWindow===e.source))return;", SCRIPT)
        self.assertIn("if(e.data.round===searchRound){answers.search.set(idOf(e.source),clean(e.data.items));drawResults();}", SCRIPT)
        self.assertIn("f.contentWindow.postMessage(Object.assign({source:'cloud-desk',type},extra||{}),o)", SCRIPT)
        self.assertNotIn(",'*')", SCRIPT)

    def test_an_application_loaded_in_the_background_never_takes_the_person_away(self):
        # 28 November 2026, on the test site: searching loaded Mail hidden, Mail asked to sign in, and the Desk
        # left for the sign-in page. Mail's sign-in is honoured only while Mail is the application shown.
        self.assertIn("e.data.type==='authorize'){if([...frames.values()].find(f=>f.contentWindow===e.source)?.hidden)return;try{", SCRIPT)

    def test_a_result_opens_only_a_path_of_that_application(self):
        self.assertIn(r"/^\/(?!\/)[^\s\\]*$/.test(path)", SCRIPT)
        self.assertIn("return u.origin===new URL(app.url,location.href).origin?u.href:'';", SCRIPT)
        for app in (DRIVE_DESK, DMS_DESK):
            self.assertIn(r"d.type==='open'&&typeof d.path==='string'&&/^\/(?!\/)[^\s\\]*$/.test(d.path)", app)

    def test_drive_and_the_dms_answer_search_with_the_persons_own_session(self):
        self.assertIn("reply('search-results',{round,items})", DRIVE_DESK)
        self.assertIn("fetch('/remote.php/dav/spaces/',{method:'REPORT',headers:{Authorization:'Bearer '+t", DRIVE_DESK)
        self.assertIn("reply('search-results',{round,items})", DMS_DESK)
        self.assertIn("fetch('/api/documents/?page_size=8&query='+encodeURIComponent(text),{credentials:'same-origin'", DMS_DESK)
        for app in (DRIVE_DESK, DMS_DESK):
            self.assertIn("if(e.origin!==DESK||e.source!==window.parent||e.data?.source!=='cloud-desk')return;", app)
            self.assertIn("window.parent.postMessage(Object.assign({source:'cloud-session',type},extra),DESK)", app)

    def test_both_answer_the_notification_question(self):
        self.assertIn("/ocs/v2.php/apps/notifications/api/v1/notifications?format=json", DRIVE_DESK)
        self.assertIn("reply('notifications',{items})", DRIVE_DESK)
        self.assertIn("reply('notifications',{items:[]})", DMS_DESK)

    def test_the_business_systems_notifications_are_the_persons_own_unread_ones(self):
        self.assertIn("filters={'for_user': user, 'read': 0}", DESK_API)
        self.assertIn("if user == 'Guest':", DESK_API)
        self.assertIn('strip_html(row.subject', DESK_API)


class DeepLinks(unittest.TestCase):
    def test_an_address_may_name_an_application_and_a_path_inside_it(self):
        self.assertIn("const fromHash=()=>{const h=location.hash.slice(1),i=h.indexOf(':');", SCRIPT)
        self.assertIn("else if(first.path&&first.path!=='/'){const href=inside(manifest.get(first.id),first.path);if(href)pendingOpen={id:first.id,path:href};}", SCRIPT)
        self.assertIn("if(first.id==='open'){open=first.path;first.id='';}", SCRIPT)



class OnlyInsideTheDesk(unittest.TestCase):
    """P112: a person's page visit to an application's own address is sent to the Desk; programs are not."""
    HOSTS = {'erp': 'erp.example.net', 'drive': 'drive.example.net', 'office': 'office.example.net',
             'mail': 'mail.example.net', 'dms': 'dms.example.net', 'respond': 'respond.example.net',
             'sso': 'sso.example.net'}

    def routes(self, **extra):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest('needs PyYAML, as the ingress renderer does')
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            from prepare_ingress import prepare
        finally:
            sys.path.pop(0)
        return prepare(ROOT, dict({'hosts': self.HOSTS, 'ingress_prefix': 'isolated'}, **extra))['http']

    def test_only_a_browsers_page_visit_is_redirected(self):
        http = self.routes()
        for name in ('drive', 'dms', 'mail', 'erp'):
            router = http['routers']['isolated-desk-only-' + name]
            self.assertIn('Method(`GET`) && Header(`Sec-Fetch-Dest`, `document`)', router['rule'])
            self.assertEqual(router['service'], 'noop@internal')
            self.assertEqual(router['middlewares'][0], 'isolated-desk-only-' + name)

    def test_the_desk_opens_the_same_place(self):
        http = self.routes()
        drive = http['middlewares']['isolated-desk-only-drive']['redirectRegex']
        self.assertEqual(drive['regex'], r'^https://drive\.example\.net(/.*)?$')
        self.assertEqual(drive['replacement'], 'https://erp.example.net/place_holder#drive:${1}')
        self.assertFalse(drive['permanent'])
        self.assertEqual(http['middlewares']['isolated-desk-only-erp']['redirectRegex']['replacement'],
                         'https://erp.example.net/place_holder#open:${1}')

    def test_what_programs_and_outsiders_use_is_never_listed(self):
        http = self.routes()
        rules = {name: http['routers']['isolated-desk-only-' + name]['rule'] for name in ('drive', 'dms', 'mail', 'erp')}
        for kept in ('/s/', '/files/link', 'oidc-callback', '/dav', '/remote.php', '/ocs', '/graph', '/app/'):
            self.assertNotIn(kept, rules['drive'], kept)
        for kept in ('/api', '/accounts', '/share/', '/admin', '/static'):
            self.assertNotIn(kept, rules['dms'], kept)
        for kept in ('/auth', '/api', '/jmap', '/popout', '/login', '/.well-known'):
            self.assertNotIn(kept, rules['mail'], kept)
        self.assertIn('PathRegexp(`^/(desk|insights)(/|$)`)', rules['erp'])
        self.assertNotIn('/api', rules['erp'])

    def test_a_deployment_may_switch_it_off(self):
        http = self.routes(apps_only_inside_desk=False)
        self.assertFalse([name for name in http['routers'] if 'desk-only' in name])


class InsideTheDesk(unittest.TestCase):
    def test_nothing_of_it_runs_when_an_application_is_not_inside_the_desk(self):
        self.assertIn('if(window.self===window.top||window.__cloudDriveDesk)return;', DRIVE)
        self.assertIn('if(window.self===window.top||window.__cloudDmsDesk)return;', DMS)
        self.assertLess(ERP.index('if (window.self !== window.top) {'), ERP.index("bar.id = 'cloud-desk-bar'"))

    def test_drive_blue_band_is_hidden_but_not_in_the_editors(self):   # P115 (i)
        self.assertIn('html.uf-in-desk body:not(.uf-editor) #web-content-header{display:none!important}', DRIVE_DESK)

    def test_drive_preferences_sit_beneath_deleted_files(self):         # P115 (ii)
        self.assertIn("li.id='uf-nav-preferences'", DRIVE_DESK)
        self.assertIn("""li.querySelector('a[href^="/files/trash"]')""", DRIVE_DESK)
        self.assertIn("go('/account')", DRIVE_DESK)
        self.assertIn('last.after(li)', DRIVE_DESK)

    def test_drive_side_bar_button_sits_left_of_the_view_buttons_and_presses_drives_own(self):   # P115 (iii)
        self.assertIn("b.id='uf-toggle-sidebar'", DRIVE_DESK)
        self.assertIn("document.getElementById('files-toggle-sidebar')?.click()", DRIVE_DESK)
        self.assertIn('views.parentElement.insertBefore(b,views.parentElement.firstChild)', DRIVE_DESK)

    def test_drive_opens_straight_into_spaces(self):                    # P115 (iv)
        self.assertIn("'url': 'https://drive.example.com/files/spaces/projects'", CODE)

    def test_a_spaces_top_level_looks_like_a_folder(self):              # P115 (v)
        self.assertIn('html.uf-in-desk .space-header{position:absolute!important;width:0!important;height:0!important;', DRIVE_DESK)
        self.assertIn('html.uf-in-desk .space-header #space-context-btn{visibility:visible!important;position:fixed!important;', DRIVE_DESK)
        self.assertIn("document.querySelector('#files-breadcrumb li:last-child')", DRIVE_DESK)

    def test_dms_green_band_and_logo_are_hidden_and_upload_is_not_replaced(self):   # P114
        self.assertIn('pngx-app-frame>nav.navbar{display:none!important}', DMS_DESK)
        self.assertIn('pngx-app-frame #sidebarMenu{padding-top:0!important}', DMS_DESK)
        self.assertNotIn('upload', DMS_DESK.split('*/', 1)[1].lower())

    def test_dms_help_that_is_only_a_link_to_the_documentation_is_removed(self):
        self.assertIn('#sidebarMenu a[href*="docs.paperless-ngx.com"]', DMS_DESK)

    def test_dms_keeps_a_way_to_its_left_menu_on_a_phone(self):
        self.assertIn("document.querySelector('pngx-app-frame .navbar-toggler')?.click()", DMS_DESK)
        self.assertIn('@media(max-width:767.98px){#uf-dms-menu{display:grid', DMS_DESK)

    def test_the_business_system_hides_its_own_search_notification_and_help_rows(self):
        self.assertIn("'body .body-sidebar .standard-items-band,body .body-sidebar .uf-help,'", ERP)


if __name__ == '__main__':
    unittest.main()
