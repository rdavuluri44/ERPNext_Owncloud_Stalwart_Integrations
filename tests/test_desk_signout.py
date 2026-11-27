"""P53: sign-out lives on the Desk (the portal page), not in each application.

The Desk shows one Sign out control. Before it ends the single sign-on session it asks every open
application for unsaved work and tells each one to end its own session. Each application's own script
hides that application's sign-out item inside the Desk, and turns it into the way back to the Desk when
the application is opened on its own. These tests pin both halves of that agreement, so a change to one
side that the other no longer understands fails here.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK = (ROOT / "erpnext_drive_integrations/www/place_holder.html").read_text(encoding="utf-8")
ERP = (ROOT / "erpnext_drive_integrations/public/session.js").read_text(encoding="utf-8")
DRIVE = (ROOT / "integrations/drive/workspace.js").read_text(encoding="utf-8")
DMS = (ROOT / "integrations/dms/cloud_session/session.js").read_text(encoding="utf-8")
MAIL = (ROOT / "integrations/mail/overlay/components/cloud-session-guard.tsx").read_text(encoding="utf-8")
MAIL_LIB = (ROOT / "integrations/mail/overlay/lib/cloud-session.ts").read_text(encoding="utf-8")
APPS = {"erp": ERP, "drive": DRIVE, "dms": DMS, "mail": MAIL}
FINISH = "/api/method/erpnext_drive_integrations.portal.sso.finish_logout"


class DeskSide(unittest.TestCase):
    def test_the_desk_has_one_sign_out_control_at_the_top_right(self):
        self.assertEqual(DESK.count('id="ph-signout"'), 1)
        self.assertIn('<div id="ph-bar" role="toolbar"', DESK)
        self.assertRegex(DESK, r"#ph-bar\{position:fixed;top:\d+px;right:\d+px")

    def test_the_bar_shows_on_the_desk_home_only_never_over_an_open_application(self):
        # Owner, 27 November 2026: the bar belongs to the Desk; over an application it hid that
        # application's own controls.
        self.assertIn(".ph-active #ph-bar{display:none}", DESK)

    def test_sign_out_is_the_last_item_of_the_bar(self):
        bar = re.search(r'<div id="ph-bar".*?</div>', DESK, re.S).group(0)
        last = re.findall(r'<(?:button|a) id="([a-z-]+)"', bar)[-1]
        self.assertEqual(last, "ph-signout")

    def test_it_asks_for_unsaved_work_before_it_signs_out(self):
        self.assertIn("tell(f,'unsaved?')", DESK)
        self.assertIn("const dirty=await askUnsaved();if(!dirty.length){leave();return;}", DESK)
        self.assertIn('<button value="stay" autofocus>', DESK)
        # Closing the question any other way (Escape) keeps the person signed in.
        self.assertIn("leaveDialog.returnValue='stay';leaveDialog.showModal()", DESK)
        self.assertIn("if(leaveDialog.returnValue==='leave')leave();", DESK)

    def test_it_lets_every_open_application_end_its_session_and_never_waits_forever(self):
        self.assertIn("tell(f,'signout')", DESK)
        self.assertIn("leaving.delete(e.source);if(!leaving.size)finish();", DESK)
        self.assertIn("setTimeout(finish,2500)", DESK)
        self.assertIn("const finish=()=>location.assign('" + FINISH + "')", DESK)

    def test_it_only_talks_to_its_own_application_frames(self):
        self.assertIn("if((!trusted.has(o)&&o!==location.origin)||!f.contentWindow)return false;", DESK)
        self.assertIn("f.contentWindow.postMessage({source:'cloud-desk',type},o)", DESK)
        self.assertNotIn("postMessage({source:'cloud-desk',type},'*')", DESK)

    def test_an_application_that_signs_out_by_itself_still_ends_everything(self):
        # An older application script, or a session that ended inside the frame.
        self.assertIn("if(leaving){leaving.delete(e.source);if(!leaving.size)finish();}else finish();", DESK)


class ApplicationSide(unittest.TestCase):
    def test_every_application_listens_only_to_the_desk_that_frames_it(self):
        for name, text in APPS.items():
            flat = re.sub(r"\s+", "", text)
            self.assertIn("e.source!==window.parent||e.data?.source!=='cloud-desk'", flat, name)
            self.assertRegex(flat, r"e\.origin!==DESK", name)
        for text in (ERP, DRIVE, DMS, MAIL_LIB):
            self.assertRegex(text, r"DESK ?= ?'https://erp\.example\.com'")

    def test_every_application_answers_both_questions(self):
        for name, text in APPS.items():
            flat = re.sub(r"\s+", "", text)
            self.assertIn("e.data.type==='unsaved?'", flat, name)
            self.assertIn("source:'cloud-session',type:'unsaved',value:", flat, name)
            self.assertIn("e.data.type==='signout'", flat, name)

    def test_the_erp_menu_loses_its_logout_row_only_inside_the_desk(self):
        self.assertIn("if (window.self !== window.top) {\n    const DESK", ERP)
        self.assertIn("filter(option => option.name !== 'logout')", ERP)
        self.assertIn("window.cur_frm?.is_dirty?.()", ERP)

    def test_drive_hides_its_row_inside_the_desk_and_offers_the_way_back_outside(self):
        self.assertIn("html.uf-in-desk #oc-topbar-account-logout", DRIVE)
        self.assertIn("if(FRAMED)void logout(true);else location.assign(DESK+'/');", DRIVE)
        self.assertIn("HOME='Back to home'", DRIVE)

    def test_dms_hides_its_row_inside_the_desk_and_offers_the_way_back_outside(self):
        self.assertIn("OWN+'{display:none!important}'", DMS)
        self.assertEqual(DMS.count("if(window.self!==window.top)void leave(true);else location.assign('https://erp.example.com/');"), 2)
        self.assertIn("pngx-document-detail form.ng-dirty", DMS)
        middleware = (ROOT / "integrations/dms/cloud_session/middleware.py").read_text(encoding="utf-8")
        self.assertIn("/cloud-session.js?v=20261127-desk", middleware)

    def test_mail_hides_its_controls_inside_the_desk_and_keeps_the_timeout_button(self):
        self.assertIn("/^(sign out( of .+)?|log ?out)$/i", MAIL)
        self.assertIn("if (framed) { el.style.display = 'none'; continue; }", MAIL)
        self.assertIn("window.location.assign(DESK + '/')", MAIL)
        self.assertIn("useAuthStore.getState().logoutAll()", MAIL)
        # "Sign out now" (the idle-limit dialog) is not an application sign-out item and stays.
        self.assertIsNone(re.match(r"^(sign out( of .+)?|log ?out)$", "sign out now"))

    def test_no_application_ends_the_session_for_an_unknown_sender(self):
        for name, text in APPS.items():
            self.assertNotIn("postMessage({source:'cloud-session',type:'logout'},'*')", re.sub(r"\s+", "", text), name)


if __name__ == "__main__":
    unittest.main()
