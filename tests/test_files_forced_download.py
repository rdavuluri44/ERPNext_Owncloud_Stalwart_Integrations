"""Forced download of script-capable uploads in the ERP nginx template (P97).

Public attachments are served straight from disk under /files/. A file the
browser would render (HTML, SVG, XML and relatives) must come back with
"Content-disposition: attachment", or a signed-in user could upload a page that
runs script in another user's session. The rule used to match lower-case
extensions only, so `poc.SVG` slipped past (frappe_docker advisory
GHSA-94mh-qq29-qwrf, fixed upstream in v4.3.0). Our template replaces
upstream's, so their fix reaches us only through this file: it must keep
upstream's rule, whatever the case of the extension.
"""
from pathlib import Path
import re
import unittest

TEMPLATE = (Path(__file__).resolve().parents[1] / 'deployment/erp/frappe.conf.template').read_text()

# The extensions upstream forces to download (frappe_docker v4.3.0).
EXTENSIONS = {'svg', 'svgz', 'html', 'htm', 'xhtml', 'xht', 'shtml', 'shtm',
              'mhtml', 'mht', 'xml', 'xsl', 'xslt', 'swf'}


def files_locations():
    return re.findall(r'location (~\*?) (\^/files/\S+) \{(.*?)\n\t\t\}', TEMPLATE, re.S)


class ForcedDownloadTests(unittest.TestCase):
    def setUp(self):
        locations = files_locations()
        self.assertEqual(len(locations), 1, 'exactly one /files/ forced-download rule')
        self.modifier, self.pattern, self.body = locations[0]
        # nginx uses PCRE; Python spells the end-of-subject anchor \Z.
        flags = re.I if self.modifier == '~*' else 0
        self.regex = re.compile(self.pattern.replace(r'\z', r'\Z'), flags)

    def test_every_extension_in_any_case(self):
        for ext in sorted(EXTENSIONS):
            for name in (ext, ext.upper(), ext.capitalize(), ext[:-1] + ext[-1].upper()):
                with self.subTest(name=name):
                    self.assertIsNotNone(self.regex.search(f'/files/poc.{name}'))

    def test_extension_list_is_upstreams(self):
        listed = re.search(r'\\.\(\?i:([a-z|]+)\)', self.pattern)
        self.assertIsNotNone(listed, 'case-insensitive extension group')
        self.assertEqual(set(listed.group(1).split('|')), EXTENSIONS)

    def test_awkward_names_are_still_caught(self):
        for path in ('/files/sub/dir/poc.SVG', '/files/a.png.HtMl', '/files/line\nbreak.Svg',
                     '/files/space name.XML'):
            with self.subTest(path=path):
                self.assertIsNotNone(self.regex.search(path))

    def test_other_files_are_not_forced(self):
        for path in ('/files/photo.PNG', '/files/report.pdf', '/files/sheet.xlsx', '/files/svg',
                     '/files/notes.html.txt', '/files/poc.svg/x.png', '/private/files/poc.svg',
                     '/files/htmlguide.docx'):
            with self.subTest(path=path):
                self.assertIsNone(self.regex.search(path))

    def test_rule_forces_the_download(self):
        self.assertIn('add_header Content-disposition "attachment";', self.body)
        self.assertIn('include /etc/nginx/snippets/security_headers.conf;', self.body)
        self.assertIn('try_files /${FRAPPE_SITE_NAME_HEADER}/public/$uri @webserver;', self.body)

    def test_rule_survives_envsubst(self):
        # The template goes through envsubst: a "$" in the pattern would be eaten.
        self.assertNotIn('$', self.pattern)


if __name__ == '__main__':
    unittest.main()
