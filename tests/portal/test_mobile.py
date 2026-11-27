"""Native mobile login binding tests (ADR-038 change 2a: approved-clients list).

No Frappe or live data needed: a small fake `frappe` module, a temp SQLite registry.
Run:  uv run --no-project --with pyjwt python test_mobile.py
"""
import datetime
import pathlib
import sys
import tempfile
import time
import types
import unittest
from unittest import mock


class Bag(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__


# ---- fake frappe ---------------------------------------------------------------------------
frappe = types.ModuleType('frappe')
frappe.whitelist = lambda **kwargs: (lambda f: f)
frappe.AuthenticationError = type('AuthenticationError', (Exception,), {})
utils = types.ModuleType('frappe.utils')
utils.get_datetime = lambda v: v
utils.now_datetime = datetime.datetime.now
oauth = types.ModuleType('frappe.utils.oauth')
for name in ['get_oauth2_authorize_url', 'get_oauth2_flow', 'get_oauth_keys', 'get_oauth2_providers',
             'get_redirect_uri', 'login_oauth_user', 'consume_oauth_state', 'create_oauth_state']:
    setattr(oauth, name, lambda *a, **k: None)
sys.modules.update({'frappe': frappe, 'frappe.utils': utils, 'frappe.utils.oauth': oauth})


class FakeDB:
    def __init__(self):
        self.users, self.tokens = {}, {}

    def get_value(self, doctype, name, fields, as_dict=False):
        if doctype == 'User':
            return self.users.get(name)
        token = self.tokens.get(name)
        if token is None:
            return None
        return Bag({f: token[f] for f in fields}) if as_dict else token[fields]

    def set_value(self, doctype, name, field, value, update_modified=True):
        self.tokens[name][field] = value


def get_all(doctype, filters, pluck):
    op, allowed = filters['client']
    assert op == 'in'
    return [n for n, t in frappe.db.tokens.items() if t['client'] in allowed and t['status'] == filters['status']]


frappe.get_all = get_all
frappe.get_request_header = lambda name, default='': frappe.local.headers.get(name, default)

APP = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from erpnext_drive_integrations.portal import mobile, sso  # noqa: E402

SECOND, HOV, OTHER = 'second-client', 'onboarding-client', 'other-client'


class TestIdentityOrigin(unittest.TestCase):
    origin = 'https://test-sso.example.com'
    issuer = origin + '/application/o/test-erpnext/'

    def test_only_test_copies_can_use_a_different_identity_origin(self):
        for flag in (False, True):
            frappe.conf = Bag(cloud_test_copy=flag, cloud_test_identity_origin=self.origin,
                              cloud_oidc_issuer=self.issuer)
            if flag:
                self.assertEqual(sso.issuer(), self.issuer)
            else:
                with self.assertRaises(frappe.AuthenticationError):
                    sso.issuer()

    def test_isolated_logout_uses_the_test_issuer(self):
        frappe.conf = Bag(cloud_test_copy=True, cloud_test_identity_origin=self.origin,
                          cloud_oidc_issuer=self.issuer)
        frappe.session = Bag(user='Guest')
        class Redirected(Exception):
            pass
        with mock.patch.object(sso, 'browser_id', return_value=None), mock.patch.object(sso, 'cookie'), \
             mock.patch.object(sso, 'redirect', side_effect=Redirected) as redirect:
            with self.assertRaises(Redirected):
                sso.finish_logout()
            redirect.assert_called_once_with(self.issuer + 'end-session/')

    def test_test_issuer_must_match_the_configured_origin(self):
        frappe.conf = Bag(cloud_test_copy=True, cloud_test_identity_origin=self.origin,
                          cloud_oidc_issuer='https://other.example.com/application/o/test-erpnext/')
        with self.assertRaises(frappe.AuthenticationError):
            sso.issuer()


class MobileBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        sso.STATE_PATH = self.tmp.name + '/state.sqlite3'
        frappe.conf = Bag(cloud_native_mobile_enabled=1, cloud_native_mobile_clients=[HOV, SECOND])
        frappe.local = Bag(site='erp.internal', headers={})
        frappe.session = Bag(user='Guest', sid='Guest')
        frappe.form_dict = Bag()
        frappe.db = FakeDB()
        frappe.db.users['user-a'] = 1
        mobile.init_state()
        self.add_browser()

    def tearDown(self):
        self.tmp.cleanup()

    # ---- helpers ---------------------------------------------------------------------------
    def add_browser(self, bid='browser-a', user='user-a', sid='sid-a'):
        with sso.registry() as db:
            db.execute('INSERT INTO browsers VALUES(?,?,0,?)', (bid, user, int(time.time())))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                       ('erp.internal', sso.digest(sid), bid, 'oidc-' + bid, user, int(time.time())))

    def authorize(self, client, code='code-1', method='S256'):
        """The browser (Authentik passkey session) approves an OAuth code for `client`."""
        frappe.session = Bag(user='user-a', sid='sid-a')
        mobile.code_created(Bag(client=client, user='user-a', authorization_code=code,
                                code_challenge='challenge', code_challenge_method=method))

    def exchange(self, client, code='code-1', access='at-1', refresh='rt-1'):
        """The app swaps the code for tokens; Frappe inserts the OAuth Bearer Token."""
        frappe.form_dict = Bag(grant_type='authorization_code', code=code)
        mobile.token_created(Bag(client=client, user='user-a', access_token=access, refresh_token=refresh))
        self.store_token(access, client)

    def store_token(self, access, client, minutes=60):
        frappe.db.tokens[access] = Bag(user='user-a', client=client, status='Active',
                                       expiration_time=datetime.datetime.now() + datetime.timedelta(minutes=minutes))

    def call_api(self, access='at-1'):
        """A request from the app through the Traefik forward-auth check."""
        frappe.session = Bag(user='user-a', sid='token-session')
        frappe.local.headers = {'Authorization': 'Bearer ' + access}
        return mobile.check_access()

    def sign_in(self, client):
        self.authorize(client)
        self.exchange(client)

    def assertRefused(self, fn, *args):
        with self.assertRaises(frappe.AuthenticationError):
            fn(*args)

    # ---- approved apps work --------------------------------------------------------------------
    def test_old_switch_name_still_works_until_the_site_config_is_renamed(self):
        frappe.conf.pop('cloud_native_mobile_enabled')
        frappe.conf.cloud_raven_mobile_enabled = 1
        self.sign_in(HOV)
        self.assertEqual(self.call_api(), {'authorized': True})

    def test_new_switch_wins_over_the_old_name(self):
        frappe.conf.cloud_raven_mobile_enabled = 1
        frappe.conf.cloud_native_mobile_enabled = 0
        self.assertEqual(mobile.clients(), frozenset())

    def test_the_removed_raven_client_setting_approves_nothing(self):
        frappe.conf.cloud_raven_mobile_client = 'raven-client'
        self.assertEqual(mobile.clients(), frozenset({HOV, SECOND}))

    def test_onboarding_app_signs_in(self):
        self.sign_in(HOV)
        self.assertEqual(self.call_api(), {'authorized': True})

    def test_onboarding_refused_before_it_is_added_to_config(self):
        frappe.conf.pop('cloud_native_mobile_clients')
        self.authorize(HOV)  # ignored: not an approved native app
        with sso.registry() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM mobile_codes').fetchone())
        self.store_token('at-1', HOV)
        self.assertRefused(self.call_api)

    def test_config_given_as_single_string(self):
        frappe.conf.cloud_native_mobile_clients = HOV
        self.sign_in(HOV)
        self.assertEqual(self.call_api(), {'authorized': True})

    # ---- unknown apps and switch ---------------------------------------------------------------
    def test_unknown_client_ignored_by_hooks_and_refused_at_gateway(self):
        self.authorize(OTHER)
        frappe.form_dict = Bag(grant_type='authorization_code', code='code-1')
        mobile.token_created(Bag(client=OTHER, user='user-a', access_token='at-1', refresh_token=None))
        self.store_token('at-1', OTHER)
        self.assertRefused(self.call_api)

    def test_master_switch_off_refuses_every_app(self):
        self.sign_in(HOV)
        frappe.conf.cloud_native_mobile_enabled = 0
        self.assertRefused(self.call_api)

    # ---- sign-in rules -------------------------------------------------------------------------
    def test_pkce_s256_required(self):
        self.assertRefused(self.authorize, HOV, 'code-1', 'plain')

    def test_fresh_passkey_session_required(self):
        frappe.session = Bag(user='user-a', sid='no-such-session')
        self.assertRefused(mobile.code_created, Bag(client=HOV, user='user-a', authorization_code='c',
                                                    code_challenge='x', code_challenge_method='S256'))

    def test_code_for_one_app_cannot_mint_tokens_for_another(self):
        self.authorize(HOV)
        self.assertRefused(self.exchange, SECOND)

    def test_expired_code_refused(self):
        self.authorize(HOV)
        with sso.registry() as db:
            db.execute('UPDATE mobile_codes SET created=created-601')
        self.assertRefused(self.exchange, HOV)

    def test_refresh_grant_stays_with_its_app(self):
        self.sign_in(HOV)
        frappe.form_dict = Bag(grant_type='refresh_token', refresh_token='rt-1')
        self.assertRefused(mobile.token_created,
                           Bag(client=SECOND, user='user-a', access_token='at-2', refresh_token='rt-2'))
        mobile.token_created(Bag(client=HOV, user='user-a', access_token='at-3', refresh_token='rt-3'))
        self.store_token('at-3', HOV)
        self.assertEqual(self.call_api('at-3'), {'authorized': True})

    # ---- token checks at the gateway ------------------------------------------------------------
    def test_token_client_must_match_binding(self):
        self.sign_in(HOV)
        frappe.db.tokens['at-1']['client'] = SECOND  # both approved, but the binding says HOV
        self.assertRefused(self.call_api)

    def test_expired_or_revoked_token_refused(self):
        self.sign_in(HOV)
        frappe.db.tokens['at-1']['expiration_time'] = datetime.datetime.now() - datetime.timedelta(seconds=1)
        self.assertRefused(self.call_api)
        self.store_token('at-1', HOV)
        frappe.db.tokens['at-1']['status'] = 'Revoked'
        self.assertRefused(self.call_api)

    def test_token_of_another_user_refused(self):
        self.sign_in(HOV)
        frappe.db.tokens['at-1']['user'] = 'user-b'
        self.assertRefused(self.call_api)

    def test_missing_or_bad_header_refused(self):
        frappe.session = Bag(user='user-a', sid='x')
        for header in ['', 'Basic abc', 'Bearer', 'Bearer ' + 'a' * 4097]:
            frappe.local.headers = {'Authorization': header}
            self.assertRefused(mobile.check_access)

    def test_disabled_user_refused(self):
        self.sign_in(HOV)
        frappe.db.users['user-a'] = 0
        self.assertRefused(self.call_api)

    # ---- logout on the web ends app access (shared logout) ------------------------------------
    def test_web_logout_revokes_app_and_cleanup_revokes_token(self):
        self.sign_in(HOV)
        self.store_token('at-second', SECOND)  # unbound token: cleanup must leave it alone
        with sso.registry() as db:
            db.execute("UPDATE browsers SET revoked=1 WHERE id='browser-a'")
        self.assertRefused(self.call_api)
        mobile.cleanup()
        self.assertEqual(frappe.db.tokens['at-1']['status'], 'Revoked')
        self.assertEqual(frappe.db.tokens['at-second']['status'], 'Active')

    def test_authentik_logout_revokes_app(self):
        self.sign_in(HOV)
        with sso.registry() as db:
            db.execute("INSERT INTO revoked_oidc VALUES('oidc-browser-a',?)", (int(time.time()),))
        self.assertRefused(self.call_api)

    # ---- auth hook only touches approved apps -------------------------------------------------
    def test_validate_hook_only_checks_approved_apps(self):
        self.store_token('at-other', OTHER)
        frappe.session = Bag(user='user-a', sid='x')
        frappe.local.headers = {'Authorization': 'Bearer at-other'}
        with mock.patch.object(mobile, 'checked_token', wraps=mobile.checked_token) as checked:
            mobile.validate()  # other OAuth clients: untouched, as before
            checked.assert_not_called()
            self.sign_in(HOV)
            frappe.session = Bag(user='user-a', sid='x')
            frappe.local.headers = {'Authorization': 'Bearer at-1'}
            # Real module imports only: a leftover import of a removed function made every
            # native Bearer request fail with ImportError (500) once native sign-in was on.
            mobile.validate()
            checked.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
