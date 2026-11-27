"""P42: the ONLYOFFICE start-page patch matches the pinned version and keeps
its layout, sharing and private-sheet-view changes."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'integrations/onlyoffice/editor-wopi.original.ejs'
PATCHED = (ROOT / 'integrations/onlyoffice/editor-wopi.ejs').read_text()
RECORD = json.loads((ROOT / 'integrations/onlyoffice/upstream.json').read_text())
PINNED_ORIGINAL_SHA256 = RECORD['original_sha256']


class OnlyofficeStartPageTests(unittest.TestCase):
    def test_patch_is_based_on_the_pinned_start_page(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), PINNED_ORIGINAL_SHA256,
                         'ONLYOFFICE start page changed: review and re-apply the patch')
        self.assertIn('Ascensio System SIA', PATCHED, 'licence notice kept')

    def test_the_stored_original_belongs_to_the_pinned_image(self):
        # P91: an image bump alone must fail here, so the old patched page is never mounted
        # over a new editor. Refresh with tools/refresh_editor_original.py (register OFFICE-1).
        stack = json.loads((ROOT / 'deployment/stacks/editor-onlyoffice.compose.json').read_text())
        image = stack['services']['onlyoffice']['image']
        self.assertEqual(image, RECORD['image'],
                         'ONLYOFFICE image changed: run tools/refresh_editor_original.py, then re-apply the patch')
        watch = json.loads((ROOT / 'deployment/upstream-watch.json').read_text())['images']
        self.assertIn(image, watch)
        self.assertTrue(RECORD['version'].startswith(watch[image]), 'upstream watch and record name the same version')

    def test_space_saving_layout(self):
        self.assertIn('"compactHeader": true', PATCHED)
        self.assertIn('"header": { "user": false, "users": false, "editMode": false }', PATCHED)
        # Community edition ignores layout options: the right strip, avatar and
        # header search are hidden in the editor frame; the left strip stays
        # because the search, comments and chat panels open in it.
        # Owner: all strip buttons stay, merged into one strip on the right
        # (the pivot field list etc. live there); the empty left column collapses.
        self.assertIn("doc.querySelector('#view-left-menu > .tool-menu-btns')", PATCHED)
        self.assertIn("lm.style.width = '0px'", PATCHED)
        # Owner tried auto-hide and preferred a stationary strip in header grey.
        self.assertNotIn('cloud-strip-peek', PATCHED)
        self.assertIn('#view-right-menu>.tool-menu-btns{background-color:#D9D9D9', PATCHED)
        self.assertIn('body.uf-onlyoffice [data-tippy-root]:not(:has(#oc-files-context-menu)){display:none!important}', (ROOT / 'integrations/drive/workspace.js').read_text())
        # Phones: the free edition's touch editor is view-only, so phones use
        # the desktop editor; its strip opens from a handle there.
        # Owner: a status-bar button (bottom right) opens the strip everywhere.
        self.assertIn("box.id = 'cloud-strip-toggle'", PATCHED)
        self.assertIn('zoom.appendChild(box)', PATCHED)
        # Owner: an open panel covered the hamburger (missed clicks); it is pinned
        # above the strip and closes panel and strip in one tap.
        self.assertIn("'#cloud-strip-toggle{position:fixed;right:0;bottom:0;width:40px;", PATCHED)
        self.assertIn("'#status-zoom-box{padding-right:40px!important}'", PATCHED)
        self.assertIn("doc.querySelector('#view-right-menu .tool-menu-btns .btn-category.active')", PATCHED)
        self.assertIn('<line x1="4" y1="14.5" x2="16" y2="14.5"/>', PATCHED)  # 4-line hamburger like the sheet list
        self.assertNotIn('cloud-strip-handle', PATCHED)
        self.assertIn("'@media (max-width:768px){#status-action,#status-sheets-bar-box,#status-tabs-scroll,'", PATCHED)
        self.assertIn("'#status-zoom-box>:not(#cloud-strip-toggle){display:none!important}}'", PATCHED)
        # Tabs first: file name and logo shrink, wider scroll arrows.
        self.assertIn("'section.box-tabs>section.tabs{flex:1 1 auto!important;min-width:0}'", PATCHED)
        self.assertIn('section.tabs>a.scroll{min-width:28px!important', PATCHED)
        self.assertIn("'canvas-dark-cell-title-text-filtered': '#1F5BC6'", PATCHED)

    def test_always_light_theme(self):
        self.assertIn('"uiTheme": "default-light"', PATCHED)
        self.assertNotIn('"default-dark"', PATCHED)

    def test_licence_notices_kept_and_modification_stated(self):
        # Logo stays (unlinked); About keeps ONLYOFFICE's notices and gains the
        # modification notice required by the additional terms 2 and 3.
        self.assertIn('#header-logo{pointer-events:none', PATCHED)
        self.assertNotIn('#header-logo{display:none', PATCHED)
        self.assertNotIn('#left-btn-about{display:none', PATCHED)
        # About stays (licence) but can always be closed (owner: it got stuck).
        self.assertIn("x.id = 'cloud-about-close'", PATCHED)
        # Adding the close button must not un-hide About (it showed on every open).
        block = PATCHED[PATCHED.index("if (!a || doc.getElementById('cloud-about-close')) return;"):PATCHED.index("x.id = 'cloud-about-close'")]
        self.assertNotIn("style.display = ''", block)
        self.assertIn("'#about-menu-panel{position:fixed!important;left:auto!important;top:auto!important;right:48px!important;bottom:40px!important;'", PATCHED)
        self.assertIn("'width:min(340px,calc(100vw - 64px))!important;", PATCHED)
        # A fixed card has no offsetParent; open/closed must not depend on it.
        self.assertIn("var aboutOpen = function () { return shown(doc.getElementById('about-menu-panel')); };", PATCHED)
        self.assertIn("if (e.key === 'Escape') closeAbout();", PATCHED)
        self.assertIn('if (closeAbout()) { stripOpen = false; applyStrip(); return; }', PATCHED)
        self.assertIn('Modified version: this installation changes the ONLYOFFICE Docs', PATCHED)
        self.assertIn('developed ' + "' +\n                            'by Ascensio System SIA", PATCHED)
        self.assertNotIn('#right-menu{display:none', PATCHED)
        self.assertNotIn('#left-btn-chat,#left-btn-about{display:none', PATCHED)
        self.assertIn('.btn-current-user,#slot-btn-search{display:none!important}', PATCHED)
        self.assertNotIn('#left-menu{display:none', PATCHED)
        self.assertNotIn('"goback"', PATCHED)
        self.assertIn('"onRequestSharingSettings": undefined', PATCHED)

    def test_private_sheet_view_per_person(self):
        self.assertIn('"onDocumentReady": cloudEditorReady', PATCHED)
        self.assertNotIn("documentType !== 'cell'", PATCHED, 'documentType is not in scope there')
        self.assertIn("'Private - '", PATCHED)
        self.assertIn('asc_addNamedSheetView(null, true)', PATCHED)
        self.assertIn('asc_isProtectedSheet', PATCHED)
        # Owner: private views must not show ONLYOFFICE's green sheet-view headers.
        self.assertIn("'canvas-cell-title-background': bg", PATCHED)
        self.assertIn("'canvas-cell-title-background-selected': selected", PATCHED)
        self.assertIn("'canvas-sheet-view-cell-background-pressed': selected", PATCHED)
        self.assertNotIn('AscCommon.ir', PATCHED, 'only the official skin tokens')
        self.assertIn("'canvas-sheet-view-cell-background': bg", PATCHED)


class OnlyofficeStackTests(unittest.TestCase):
    def test_stale_supervisor_pid_removed_on_start(self):
        # A restarted container keeps /var/run/supervisord.pid; if its PID is
        # reused, the image's init script skips supervisord and ONLYOFFICE
        # stays down (502), seen on test 2026-11-18.
        import json
        stack = json.loads((ROOT / 'deployment/stacks/editor-onlyoffice.compose.json').read_text())
        entry = stack['services']['onlyoffice']['entrypoint']
        self.assertEqual(entry[:2], ['/bin/sh', '-c'])
        self.assertIn('rm -f /var/run/supervisord.pid; exec /app/ds/run-document-server.sh', entry[2])


class ProductionSwitchTests(unittest.TestCase):
    def test_production_route_targets_the_onlyoffice_alias(self):
        route = (ROOT / 'deployment/production/office-onlyoffice.traefik.yaml').read_text()
        self.assertIn('rule: Host(`office.example.com`)', route)
        self.assertIn('url: http://editor-onlyoffice-production:80', route)
        self.assertIn('certResolver: letsencrypt', route)
        method = (ROOT / 'docs/production-moves.md').read_text()
        self.assertIn('{**env_file, **environment}', method)
        self.assertIn('Rollback point', method)


class ProductionDriveRouteTests(unittest.TestCase):
    def test_drive_route_keeps_portal_framing_and_targets_repository_stack(self):
        route = (ROOT / 'deployment/production/drive.traefik.yaml').read_text()
        self.assertIn('rule: Host(`drive.example.com`)', route)
        self.assertIn('- place-holder-xfo@file', route)
        self.assertIn('- text/event-stream', route)
        self.assertIn('url: http://drive-ocis-production:9200', route)
        dms = (ROOT / 'deployment/production/dms.traefik.yaml').read_text()
        self.assertIn('rule: Host(`dms.example.com`)', dms)
        self.assertIn('- place-holder-dms-frame@file', dms)
        self.assertIn('url: http://dms-paperless-production:8000', dms)
        mail = (ROOT / 'deployment/production/mail.traefik.yaml').read_text()
        # Admin/setup refused publicly, policy readable, ACME for the SMTP host.
        self.assertIn("PathPrefix(`/admin`) || PathPrefix(`/api/admin`) || PathPrefix(`/setup`) || PathPrefix(`/api/setup`)", mail)
        self.assertIn('- 127.0.0.1/32', mail)
        self.assertIn("Path(`/api/admin/policy`) && Method(`GET`)", mail)
        self.assertIn("Host(`mx.example.com`) && PathPrefix(`/.well-known/acme-challenge/`)", mail)
        self.assertIn('url: http://mail-stalwart-production:8080', mail)
        self.assertIn('url: http://mail-webmail-production:3000', mail)


class DriveEditorFrameTests(unittest.TestCase):
    def test_drive_top_bar_folds_into_the_editor_for_onlyoffice(self):
        js = (ROOT / 'integrations/drive/workspace.js').read_text()
        self.assertIn("location.pathname.startsWith('/external-onlyoffice/')", js)
        self.assertIn('body.uf-editor #external-onlyoffice', js)
        self.assertIn('#app-top-bar-close', js)
        self.assertIn('body.uf-onlyoffice{--uf-editor-bg:transparent;--uf-editor-fg:rgb(56,56,56)}', js)
        self.assertIn('#app-top-bar-close svg{fill:var(--uf-editor-fg)!important', js)
        # Owner: editor runs edge to edge (Drive rounds its app container by 15px).
        self.assertIn('body.uf-onlyoffice #web-content #web-content-main .app-container{border-radius:0!important}', js)
        # Owner: native-app look, editor frame fills the window edge to edge.
        self.assertIn('body.uf-onlyoffice iframe[name="app-iframe"],body.uf-onlyoffice #external-onlyoffice iframe{position:fixed!important;top:0!important;left:0!important;', js)
        # An iframe does not stretch between left/right/top/bottom: it needs an
        # explicit size (auto shrank it to 300x150 on test, 18 Nov 2026), and a
        # low z-index so Drive's ✕ and ⋮ stay above it.
        self.assertIn('width:calc(100vw - var(--uf-sidebar-width,0px))!important;height:100vh!important;height:100dvh!important;', js)
        self.assertIn('border-radius:0!important;z-index:1!important}', js)
        self.assertNotIn('height:auto!important;max-width:none', js)
        # Owner: ✕ centred over the right strip and slightly larger than ⋮.
        # Owner: ✕ and ⋮ at the top left (reachable on phones); editor header
        # row starts after them.
        self.assertIn('body.uf-onlyoffice #app-top-bar-close{right:auto!important;left:10px!important;width:32px!important;height:32px!important;top:0!important}', js)
        self.assertIn('body.uf-onlyoffice #oc-openfile-contextmenu-trigger{right:auto!important;left:46px!important}', js)
        self.assertIn("'section.box-tabs{padding-left:84px!important}'", PATCHED)
        self.assertIn("'section.box-tabs>.extra.left{order:3;flex:0 100 auto!important;min-width:34px;overflow:hidden}'", PATCHED)
        self.assertIn('#app-top-bar-close svg{width:24px!important;height:24px!important}', js)
        self.assertIn('#oc-files-context-menu *{font-family:"Segoe UI",Arial', js)
        # Drive closes its file menu when the editor reports a click.
        self.assertIn("e.data.type==='pointerdown')dismissContext()", js)
        self.assertIn("{ source: 'cloud-editor-ui', type: 'pointerdown' }", PATCHED)


if __name__ == '__main__':
    unittest.main(verbosity=2)
