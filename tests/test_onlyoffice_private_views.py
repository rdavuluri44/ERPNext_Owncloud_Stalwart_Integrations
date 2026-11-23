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
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "",
                           "C:/Program Files/Google/Chrome/Application/chrome.exe") if p and Path(p).exists()), None)

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
