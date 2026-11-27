"""A saved sheet view with an empty column filter must not crash the editor (a shared workbook, 20-21 Nov 2026).

ONLYOFFICE 10.0.0 (build 169): CT_NsvFilter.IU() calls `.filter.IU()` on every column filter, but a
column filter may have no filter (saved as <columnFilter ...></columnFilter>), which throws
"Cannot read properties of null (reading 'IU')" and leaves the grid blank for everyone who opens the
file. Two defences: the editor start page replaces IU() with a null-safe copy, and the repair tool
removes such entries from a saved file. The guard test runs the editor's own original method (copied
from the pinned build) and the guard block from the start page in headless Chrome; skipped when
Chrome is not installed.
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "integrations/onlyoffice"))
import sheetview_sanitize as tool  # noqa: E402

EJS = (ROOT / "integrations/onlyoffice/editor-wopi.ejs").read_text()
CHROME = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                           "C:/Program Files/Google/Chrome/Application/chrome.exe",
                           shutil.which("google-chrome") or "", shutil.which("chromium") or "") if p and Path(p).exists()), None)

# Exact source of CT_NsvFilter.prototype.IU in sdkjs/cell/sdk-all.js of 10.0.0-25b1e290...
ORIGINAL_IU = "function(){var q=null;if(this.wB&&this.wB.length)for(var r=0;r<this.wB.length;r++)if((this.wB[r]&&this.wB[r].filter).IU()){q=!0;break}return q}"

VIEW_XML = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<namedSheetViews xmlns="http://schemas.microsoft.com/office/spreadsheetml/2019/namedsheetviews">'
            '<namedSheetView name="Temporary View 1" id="{A}"></namedSheetView>'
            '<namedSheetView name="Private - Asha" id="{B}"><nsvFilter filterId="{C}" tableId="3">'
            '<columnFilter colId="5" id="{D}"></columnFilter>'
            '<columnFilter colId="2" id="{E}"><filter colId="2"><x:filters xmlns:x="u"><x:filter val="v"/></x:filters></filter></columnFilter>'
            '</nsvFilter></namedSheetView></namedSheetViews>')


def make_workbook(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/worksheets/sheet1.xml", "<worksheet>cells</worksheet>")
        z.writestr("xl/namedSheetViews/namedSheetView1.xml", VIEW_XML)


class SanitiserTests(unittest.TestCase):
    def test_removes_only_the_empty_column_filter_and_keeps_everything_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx"
            make_workbook(src)
            self.assertEqual(tool.inspect(src)["empty_column_filters"], 1)
            changed = tool.sanitize(src, dst)
            self.assertEqual(changed, ["xl/namedSheetViews/namedSheetView1.xml"])
            self.assertEqual(tool.inspect(dst)["empty_column_filters"], 0)
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst) as b:
                self.assertEqual(a.read("xl/worksheets/sheet1.xml"), b.read("xl/worksheets/sheet1.xml"))
                text = b.read("xl/namedSheetViews/namedSheetView1.xml").decode()
            self.assertIn('name="Private - Asha"', text)       # views and their real filters stay
            self.assertIn('<x:filter val="v"/>', text)
            self.assertIn('name="Temporary View 1"', text)        # shells stay unless asked

    def test_temporary_shells_removed_only_on_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx"
            make_workbook(src)
            tool.sanitize(src, dst, temporary=True)
            self.assertNotIn("Temporary View", zipfile.ZipFile(dst).read("xl/namedSheetViews/namedSheetView1.xml").decode())

    def test_a_clean_workbook_is_copied_unchanged_and_the_input_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, mid, dst = Path(tmp) / "a.xlsx", Path(tmp) / "b.xlsx", Path(tmp) / "c.xlsx"
            make_workbook(src)
            before = src.read_bytes()
            tool.sanitize(src, mid)
            self.assertEqual(tool.sanitize(mid, dst), [])
            self.assertEqual(src.read_bytes(), before)


@unittest.skipUnless(CHROME, "Chrome is not installed")
class GuardTests(unittest.TestCase):
    def run_page(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            page = Path(tmp) / "p.html"
            page.write_text("<!doctype html><title>x</title><script>" + body + "</script>")
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=8000",
                                  "--dump-dom", page.as_uri()], capture_output=True, text=True, timeout=90).stdout
        return json.loads(re.search(r"<title>(\{.*?\})</title>", out).group(1).replace("&quot;", '"'))

    def harness(self):
        block = re.search(r"/\* SHEET-VIEW-FILTER-GUARD-BEGIN \*/(.*?)/\* SHEET-VIEW-FILTER-GUARD-END \*/", EJS, re.S).group(1)
        return ("var Ctor=function(){this.wB=[]};var iframe={contentWindow:{Asc:{CT_NsvFilter:Ctor}}};"
                "document.querySelector=function(){return iframe};"
                "var real=function(){return {filter:{IU:function(){return true}}}};"
                "var P=Ctor.prototype;P.IU=" + ORIGINAL_IU + ";"
                # a file with one empty and one real column filter, read by either reader
                "P.Eh=function(){this.wB.push({filter:null});this.wB.push(real())};"
                "P.zq=function(){this.wB.push({filter:null});this.wB.push(real())};"
                "P.clone=function(){var c=new Ctor();c.wB=this.wB.slice();return c};"
                "P.xh=function(){return this.wB.length};P.vD=function(){return this.wB.length};"
                + block + "cloudInstallViewFilterGuard();"
                "setTimeout(function(){var out={};"
                "function nulls(v){return v.wB.filter(function(e){return !e.filter}).length}"
                "var a=new Ctor();a.Eh();out.eh_len=a.wB.length;out.eh_nulls=nulls(a);"
                "var b=new Ctor();b.zq();out.zq_len=b.wB.length;out.zq_nulls=nulls(b);"
                "var c=new Ctor();c.wB=[{filter:null},real()];out.xh_written=c.xh();out.vD_written=c.vD();"
                "var d=new Ctor();d.wB=[{filter:null},real()];var list=d.wB;var e=d.clone();out.clone_nulls=nulls(e);"
                "out.same_list=d.wB===list&&list.length===1;"
                "var f=new Ctor();f.wB=[{filter:null}];try{out.iu_empty=String(f.IU())}catch(x){out.iu_empty='THROWS '+x.message}"
                "var g=new Ctor();g.wB=[real()];out.iu_real=String(g.IU());"
                "out.guarded=P.IU.cloudSafe===true;document.title=JSON.stringify(out)},1500);")

    def test_the_guard_drops_empty_entries_when_a_view_is_read_written_or_copied(self):
        result = self.run_page(self.harness())
        self.assertTrue(result["guarded"])
        self.assertEqual((result["eh_len"], result["eh_nulls"]), (1, 0))      # read: only the real filter remains
        self.assertEqual((result["zq_len"], result["zq_nulls"]), (1, 0))
        self.assertEqual((result["xh_written"], result["vD_written"]), (1, 1))  # write: nothing empty is saved or sent
        self.assertEqual(result["clone_nulls"], 0)                              # copy
        self.assertTrue(result["same_list"], "cleaned in place: the editor may hold the list while it works")
        self.assertEqual(result["iu_empty"], "null")                            # IU() itself never throws
        self.assertEqual(result["iu_real"], "true")                             # a real filter is still reported

    def test_the_unguarded_original_really_throws_the_reported_error(self):
        body = ("var P={};P.IU=" + ORIGINAL_IU + ";var v={wB:[{filter:null}],IU:P.IU};var m='';"
                "try{v.IU()}catch(e){m=e.message}document.title=JSON.stringify({m:m});")
        self.assertEqual(self.run_page(body)["m"], "Cannot read properties of null (reading 'IU')")

    def test_the_guard_leaves_a_fixed_build_alone(self):
        body = self.harness().replace("P.IU=" + ORIGINAL_IU + ";", "P.IU=function(){return 'fixed upstream'};")
        out = self.run_page(body)
        self.assertFalse(out["guarded"])
        self.assertEqual(out["iu_empty"], "fixed upstream")
        self.assertEqual(out["eh_nulls"], 1)   # untouched: nothing was wrapped

    def test_guard_is_installed_as_soon_as_the_editor_frame_exists_and_again_when_the_app_is_ready(self):
        self.assertRegex(EJS, r'innerAlert\("App ready"\);\s*cloudInstallViewFilterGuard\(\);')
        self.assertRegex(EJS, r'new DocsAPI\.DocEditor\("iframeEditor", config\);\s*cloudInstallViewFilterGuard\(\);')


if __name__ == "__main__":
    unittest.main()
