"""Socket.IO Origin forwarding in the ERP nginx template.

Frappe 16 rejects a realtime socket when the Origin host differs from the Host.
Browsers omit Origin on same-origin GET (the Socket.IO handshake), and the
pinned official template forces Origin to the internal site name. The template
must fill in the site's own origin only when Origin is absent and pass any
browser-supplied Origin unchanged, so cross-site sockets are still refused.
"""
from pathlib import Path
import re
import unittest

TEMPLATE = (Path(__file__).resolve().parents[1] / 'deployment/erp/frappe.conf.template').read_text()


class RealtimeOriginTests(unittest.TestCase):
    def test_origin_is_filled_in_only_when_absent(self):
        block = re.search(r'map \$http_origin \$socketio_origin \{(.*?)\}', TEMPLATE, re.S)
        self.assertIsNotNone(block)
        rules = dict(line.split(None, 1) for line in
                     (l.strip().rstrip(';') for l in block.group(1).splitlines()) if line)
        self.assertEqual(rules, {'""': '$proxy_x_forwarded_proto://$host', 'default': '$http_origin'})

    def test_socketio_location_uses_it_and_keeps_host(self):
        location = re.search(r'location /socket\.io \{(.*?)\n\t\}', TEMPLATE, re.S).group(1)
        self.assertIn('proxy_set_header Origin $socketio_origin;', location)
        self.assertIn('proxy_set_header Host $host;', location)
        self.assertNotIn('FRAPPE_SITE_NAME_HEADER}://', TEMPLATE.replace('${', '{'))
        self.assertEqual(len(re.findall(r'proxy_set_header Origin', TEMPLATE)), 1)



class ForwardedHeaderTests(unittest.TestCase):
    """P98: the backend sees one protocol indication, X-Forwarded-Proto, set by this template.

    A client's X-Forwarded-SSL or X-Forwarded-Protocol passed through to Gunicorn, which trusts the frontend
    and reads those headers too. Upstream (frappe_docker, after our pin) clears both; so do we.
    """
    def location(self, name):
        found = re.search(r'location ' + re.escape(name) + r' \{(.*?)\n\t\}', TEMPLATE, re.S)
        self.assertIsNotNone(found, name)
        return found.group(1)

    def test_both_proxied_locations_clear_the_other_protocol_headers(self):
        for name in ('/socket.io', '@webserver'):
            block = self.location(name)
            with self.subTest(location=name):
                self.assertIn('proxy_set_header X-Forwarded-Proto $proxy_x_forwarded_proto;', block)
                self.assertIn('proxy_set_header X-Forwarded-SSL "";', block)
                self.assertIn('proxy_set_header X-Forwarded-Protocol "";', block)

    def test_trusted_forwarding_setting_waits_for_the_frappe_docker_bump(self):
        # Our pinned image's nginx entrypoint does not fill in TRUST_UPSTREAM_FORWARDED_PROTO: copying
        # upstream's map now would leave the variable literal and every request would look like plain http.
        # At the next frappe_docker bump: take upstream's map, set the variable to "on" for the frontend, and
        # change this test (register BUILD-2).
        self.assertNotIn('TRUST_UPSTREAM_FORWARDED_PROTO', TEMPLATE)
        self.assertIn('map $http_x_forwarded_proto $proxy_x_forwarded_proto {', TEMPLATE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
