"""P72, P53: the Desk (place_holder) shows the Alerts entry, with the unread count, only to admins, and never breaks
because of it. Tiny fake Frappe; the real portal page and alert module are imported."""
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
STATE = {}


class Dict(dict):
    __getattr__ = dict.get

    def __setattr__(self, key, value):
        self[key] = value


class Redirect(Exception):
    pass


frappe = types.ModuleType('frappe')
frappe.Redirect, frappe.PermissionError, frappe.ValidationError = Redirect, type('PE', (Exception,), {}), Exception
frappe.whitelist = lambda **kw: (lambda f: f)
frappe.session = types.SimpleNamespace(user='admin@example.com')
frappe.local = types.SimpleNamespace(response={})
frappe.get_roles = lambda user=None: STATE['roles'].get(user or frappe.session.user, [])
frappe.get_all = lambda doctype, **kw: STATE['get_all'](doctype, **kw)
frappe.defaults = types.SimpleNamespace(get_user_default=lambda key: 'Example Company')
frappe.db = types.SimpleNamespace(get_single_value=lambda *a: None)
frappe.log_error = lambda *a, **k: STATE['logged'].append(a)
frappe.throw = lambda message, exc=Exception: (_ for _ in ()).throw(exc(message))
frappe.db.get_value = lambda doctype, name, field: None
frappe.db.set_value = lambda doctype, name, field, value, update_modified=True: STATE['seen'].append((name, value, update_modified))
boot = types.ModuleType('frappe.boot')
boot.get_app_data = lambda: [{'app_name': 'erpnext', 'app_title': 'ERPNext', 'on_apps_screen': 1, 'sequence_id': 1}]
utils = types.ModuleType('frappe.utils')
utils.get_fullname = lambda: 'Admin Person'
utils.add_days = utils.escape_html = utils.get_url = utils.now_datetime = lambda *a, **k: None
oauth = types.ModuleType('frappe.utils.oauth')
oauth.get_oauth2_authorize_url = lambda provider, target: f'/oauth/{provider}?to={target}'
limiter = types.ModuleType('frappe.rate_limiter')
limiter.rate_limit = lambda **kw: (lambda f: f)
frappe.utils, utils.oauth = utils, oauth
sys.modules.update({'frappe': frappe, 'frappe.boot': boot, 'frappe.utils': utils, 'frappe.utils.oauth': oauth,
                    'frappe.rate_limiter': limiter})

from erpnext_drive_integrations.www import admin_alerts as page, place_holder  # noqa: E402


def alerts(doctype, filters=None, fields=None, **kw):
    if doctype != 'System Alert':
        return []
    return [Dict(name='a1', _seen=json.dumps(['admin@example.com'])), Dict(name='a2', _seen=None), Dict(name='a3')]


def reset(user='admin@example.com', conf=None, get_all=alerts):
    frappe.session.user = user
    frappe.conf = conf or {}
    STATE.update(roles={'admin@example.com': ['System Manager'], 'staff@example.com': ['Employee']},
                 get_all=get_all, logged=[], seen=[])


def entries():
    return {a['id']: a for a in place_holder.get_context(Dict()).portal_apps}


class DeskEntryTests(unittest.TestCase):
    def test_admin_sees_alerts_with_unread_count(self):
        reset()
        entry = entries()['alerts']
        self.assertEqual(entry, {'id': 'alerts', 'name': 'Alerts (2)', 'url': '/admin-alerts',
                                 'logo': '/assets/erpnext_drive_integrations/app-logos/alerts.svg'})
        self.assertTrue((ROOT / 'erpnext_drive_integrations/public/app-logos/alerts.svg').is_file())

    def test_no_count_when_all_seen(self):
        reset(get_all=lambda doctype, **kw: [])
        self.assertEqual(entries()['alerts']['name'], 'Alerts')

    def test_others_do_not_see_it(self):
        reset(user='staff@example.com')
        self.assertNotIn('alerts', entries())
        reset(conf={'cloud_features': {'admin_alerts': False}})
        self.assertNotIn('alerts', entries())

    def test_configured_role_decides(self):
        reset(conf={'cloud_alerts': {'role': 'Employee'}}, user='staff@example.com')
        self.assertIn('alerts', entries())

    def test_an_error_never_breaks_the_desk(self):
        def broken(doctype, **kw):
            raise RuntimeError('database gone')
        reset(get_all=broken)
        apps = entries()
        self.assertNotIn('alerts', apps)
        self.assertIn('erpnext', apps)
        self.assertEqual(len(STATE['logged']), 1)


class AlertPageTests(unittest.TestCase):
    def test_guest_goes_to_sign_in_and_others_are_refused(self):
        reset(user='Guest')
        with self.assertRaises(Redirect):
            page.get_context(Dict())
        self.assertEqual(frappe.local.response['location'], '/oauth/authentik?to=/admin-alerts')
        reset(user='staff@example.com')
        with self.assertRaises(frappe.PermissionError):
            page.get_context(Dict())

    def test_admin_sees_open_alerts_marked_and_then_seen(self):
        def rows(doctype, filters=None, fields=None, **kw):
            if filters.get('status') == 'Open':
                return [Dict(name='a1', status='Open', link='/desk', _seen=None),
                        Dict(name='a2', status='Open', link='javascript:x', _seen=json.dumps(['admin@example.com']))]
            return []
        reset(get_all=rows, conf={'cloud_alerts': {'links': [{'label': 'Grafana', 'url': 'https://grafana.example.com'},
                                                             {'label': 'Bad', 'url': 'javascript:alert(1)'}]}})
        context = page.get_context(Dict())
        self.assertEqual([(a['name'], a['unread'], a['link']) for a in context.open_alerts],
                         [('a1', True, '/desk'), ('a2', False, '')])
        self.assertEqual([l['label'] for l in context.admin_links], ['Grafana'])
        self.assertIn('tailnet', context.links_note)
        self.assertEqual(STATE['seen'], [('a1', json.dumps(['admin@example.com']), False)])
        self.assertEqual(page.no_cache, 1)


if __name__ == '__main__':
    unittest.main()
