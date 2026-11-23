"""Private sheet views: one view per person and sheet, never a loop of "Temporary View N".

The bug (21 Nov 2026, workbook with several people): creating a view fires the
sheet-changed event again before the rename is visible in the view list; the old code
looked the name up, did not find it and created another view, again and again. The
simulation below runs the real code block in headless Chrome against a fake editor whose
rename only becomes visible after 1.5 s, and also runs the old algorithm to prove the
simulation reproduces the loop. Skipped when Chrome is not installed.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EJS = (ROOT / "integrations/onlyoffice/editor-wopi.ejs").read_text()
CHROME = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           "C:/Program Files/Google/Chrome/Application/chrome.exe",
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()), None)

OLD = """var makeOld = function (api, name, w) { var ensure = function () { try {
  var views = api.asc_getNamedSheetViews() || [];
  var mine = views.filter(function (v) { return v.asc_getName() === name; })[0];
  if (mine) { if (!mine.asc_getIsActive()) api.asc_setActiveNamedSheetView(name); return; }
  api.asc_addNamedSheetView(null, true);
  var created = (api.asc_getNamedSheetViews() || []).filter(function (v) { return v.asc_getIsActive(); })[0];
  if (created) created.asc_setName(name);
} catch (e) {} }; return { run: ensure, schedule: function () { setTimeout(ensure, 300); } }; };"""

HARNESS = """<script>
%s
%s
function fakeEditor(existing) {
  var views = [], n = 0, listeners = [];
  var mk = function (name) { var v = { name: name, active: true, visible: name };
    v.asc_getName = function () { return v.visible; }; v.asc_getIsActive = function () { return v.active; };
    v.asc_setName = function (x) { setTimeout(function () { v.visible = x; }, 1500); }; return v; };
  var api = {
    asc_getNamedSheetViews: function () { return views.slice(); },
    asc_isProtectedSheet: function () { return false; },
    asc_addNamedSheetView: function () { views.forEach(function (v) { v.active = false; }); views.push(mk('Temporary View ' + (++n)));
      setTimeout(function () { listeners.forEach(function (f) { f(); }); }, 0); },
    asc_setActiveNamedSheetView: function (name) { views.forEach(function (v) { v.active = v.visible === name; }); },
    asc_registerCallback: function (e, f) { listeners.push(f); }
  };
  for (var i = 0; i < (existing || 0); i++) { var o = mk('Private - Person ' + i); o.active = false; views.push(o); }
  return { api: api, views: views };
}
function simulate(factory, existing) {
  var ed = fakeEditor(existing), k = factory(ed.api, 'Private - Rajesh', window);
  ed.api.asc_registerCallback('asc_onActiveSheetChanged', k.schedule);
  k.run();
  return ed;
}
var a = simulate(makeOld), b = simulate(makePrivateViewKeeper);
var full = simulate(makePrivateViewKeeper, MAX_VIEWS), below = simulate(makePrivateViewKeeper, MAX_VIEWS - 1);
setTimeout(function () {
  var names = function (ed) { return ed.views.map(function (v) { return v.visible; }); };
  document.title = JSON.stringify({ old: names(a).length, fixed: names(b), cap: MAX_VIEWS,
    full: names(full).length, below: names(below).filter(function (x) { return x.indexOf('Person') < 0; }) });
}, 9000);
</script>"""


# The keeper before 23 Nov 2026: one creation attempt and one rename per sheet and visit, then it gave up.
ONCE = """var makeOnce = function (api, name, w) { var attempted = false, renamed = false;
  var run = function () { var mine = api.asc_getNamedSheetViews().filter(function (v) { return v.asc_getName() === name; })[0];
    if (mine || attempted) return; attempted = true; api.asc_addNamedSheetView(null, true);
    var t = 0, timer = w.setInterval(function () { t++;
      var fresh = api.asc_getNamedSheetViews().filter(function (v) { return v.asc_getIsActive() && /^Temporary View \\d+$/.test(v.asc_getName()); })[0];
      if (fresh && !renamed) { fresh.asc_setName(name); renamed = true; } if (t >= 40) w.clearInterval(timer); }, 250); };
  return { run: run, schedule: function () { w.setTimeout(run, 300); } }; };"""

# ONLYOFFICE refuses to create or rename a view while another person has View manager open
# (LockedEditView); the fake editor refuses for the first `createLock` / `renameLock` milliseconds.
LOCKED = """<script>
%s
%s
function lockingEditor(createLock, renameLock) {
  var views = [], n = 0, listeners = [], canCreate = !createLock, canRename = !renameLock;
  setTimeout(function () { canCreate = true; }, createLock); setTimeout(function () { canRename = true; }, renameLock);
  var mk = function (name) { var v = { visible: name, active: true };
    v.asc_getName = function () { return v.visible; }; v.asc_getIsActive = function () { return v.active; };
    v.asc_setName = function (x) { if (canRename) setTimeout(function () { v.visible = x; }, 300); }; return v; };
  var api = {
    asc_getNamedSheetViews: function () { return views.slice(); },
    asc_isProtectedSheet: function () { return false; },
    asc_addNamedSheetView: function () { if (!canCreate) return; views.forEach(function (v) { v.active = false; });
      views.push(mk('Temporary View ' + (++n))); setTimeout(function () { listeners.forEach(function (f) { f(); }); }, 0); },
    asc_setActiveNamedSheetView: function (name) { views.forEach(function (v) { v.active = v.visible === name; }); },
    asc_registerCallback: function (e, f) { listeners.push(f); }
  };
  return { api: api, views: views };
}
function start(factory, createLock, renameLock) {
  var ed = lockingEditor(createLock, renameLock), k = factory(ed.api, 'Private - Test User', window);
  ed.api.asc_registerCallback('asc_onActiveSheetChanged', k.schedule); k.run(); ed.keeper = k; return ed;
}
var names = function (ed) { return ed.views.map(function (v) { return v.visible + (v.active ? '*' : ''); }); };
var out = {};
var c1 = start(makePrivateViewKeeper, 6000, 0), c0 = start(makeOnce, 6000, 0);       /* creation refused at first */
var r1 = start(makePrivateViewKeeper, 0, 9000), r0 = start(makeOnce, 0, 9000);       /* rename refused at first */
/* while the rename is refused the person is in their own (still unnamed) view: no notice */
var frame = document.createElement('iframe'); document.body.appendChild(frame);
var rn = makeViewNotice(r1.api, r1.keeper, frame.contentDocument); setInterval(rn.check, 1500);
/* the notice, in the real page: person works in their own view, then picks Default */
var nv = start(makePrivateViewKeeper, 0, 0), notice = makeViewNotice(nv.api, nv.keeper, document);
setInterval(notice.check, 1500);
var bar = function () { var b = document.getElementById('cloud-view-notice'); return b && b.style.display !== 'none' ? b.firstChild.textContent : ''; };
setTimeout(function () { out.own_view_bar = bar(); nv.views.forEach(function (v) { v.active = false; }); }, 4000);
setTimeout(function () { out.default_bar = bar(); document.querySelector('#cloud-view-notice button').click(); }, 11000);
setTimeout(function () { out.after_back = names(nv); out.after_back_bar = bar(); }, 13000);
setTimeout(function () { out.r1_early = names(r1); var b = frame.contentDocument.getElementById('cloud-view-notice');
  out.r1_early_bar = b && b.style.display !== 'none' ? b.firstChild.textContent : ''; }, 8000);
setTimeout(function () {
  out.create_new = names(c1); out.create_old = names(c0); out.rename_new = names(r1); out.rename_old = names(r0);
  document.title = JSON.stringify(out);
}, 30000);
</script>"""


@unittest.skipUnless(CHROME, "Chrome is not installed")
class RefusedViewChangeTests(unittest.TestCase):
    """When ONLYOFFICE refuses a create or rename (another person in View manager), the keeper tries again
    instead of leaving the person in the shared Default view; a notice shows when they are not in their own view."""

    @classmethod
    def setUpClass(cls):
        block = re.search(r"/\* PRIVATE-VIEWS-BEGIN \*/(.*?)/\* PRIVATE-VIEWS-END \*/", EJS, re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "locked.html"
            page.write_text("<!doctype html><title>x</title><body></body>" + LOCKED % (ONCE, block), encoding="utf-8")
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=40000",
                                  "--dump-dom", page.as_uri()], capture_output=True, text=True, timeout=120).stdout
        cls.result = json.loads(re.search(r"<title>(\{.*?\})</title>", out, re.S).group(1).replace("&quot;", '"'))

    def test_refused_creation_is_retried_and_the_old_keeper_gave_up(self):
        self.assertEqual(self.result["create_old"], [], "the simulation must reproduce the bug: nobody's own view")
        self.assertEqual(self.result["create_new"], ["Private - Test User*"])

    def test_refused_rename_is_retried_on_the_same_view_never_a_second_one(self):
        self.assertEqual(self.result["rename_old"], ["Temporary View 1*"], "old keeper left an unnamed view")
        self.assertEqual(self.result["rename_new"], ["Private - Test User*"])

    def test_no_notice_in_ones_own_view_even_before_it_is_renamed(self):
        self.assertEqual(self.result["r1_early"], ["Temporary View 1*"])
        self.assertEqual(self.result["r1_early_bar"], "")
        self.assertEqual(self.result["own_view_bar"], "")

    def test_notice_in_the_shared_view_and_its_button_returns_to_ones_own(self):
        self.assertIn("shared Default view", self.result["default_bar"])
        self.assertEqual(self.result["after_back"], ["Private - Test User*"])
        self.assertEqual(self.result["after_back_bar"], "")

    def test_the_page_starts_the_notice(self):
        self.assertIn("var notice = makeViewNotice(api, keeper, doc);", EJS)
        self.assertIn("w.setInterval(notice.check, 1500);", EJS)
        self.assertNotIn("innerHTML", re.search(r"var makeViewNotice = (.*?)return \{ check: check \};", EJS, re.S).group(1))


@unittest.skipUnless(CHROME, "Chrome is not installed")
class PrivateSheetViewTests(unittest.TestCase):
    def run_simulation(self):
        block = re.search(r"/\* PRIVATE-VIEWS-BEGIN \*/(.*?)/\* PRIVATE-VIEWS-END \*/", EJS, re.S).group(1)
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "sim.html"
            page.write_text("<!doctype html><title>x</title>" + HARNESS % (OLD, block))
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=20000",
                                  "--dump-dom", page.as_uri()], capture_output=True, text=True, timeout=120).stdout
        return json.loads(re.search(r"<title>(\{.*?\})</title>", out).group(1).replace("&quot;", '"'))

    def test_old_logic_loops_and_new_logic_creates_exactly_one_named_view(self):
        result = self.run_simulation()
        self.assertGreater(result["old"], 3, "the simulation must reproduce the loop with the old algorithm")
        self.assertEqual(result["fixed"], ["Private - Rajesh"])

    def test_a_sheet_with_many_views_gets_no_new_one(self):
        result = self.run_simulation()
        self.assertEqual(result["cap"], 20)
        self.assertEqual(result["full"], 20, "no view is added to a sheet that already has the cap")
        self.assertEqual(result["below"], ["Private - Rajesh"], "below the cap the person still gets one")

    def test_the_block_is_what_the_editor_page_uses(self):
        self.assertIn("var keeper = makePrivateViewKeeper(api, name, w);", EJS)
        self.assertIn("registerCallback('asc_onActiveSheetChanged', keeper.schedule)", EJS)


if __name__ == "__main__":
    unittest.main()
