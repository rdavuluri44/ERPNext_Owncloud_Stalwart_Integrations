"""Native-app OAuth binding (our phone apps) to the existing approved passkey browser session.

Traefik's native-client route is forward-authenticated here; a Bearer header alone
never grants access. Frappe still validates token expiry/scopes/user and resource
permissions. Store only token/code digests in the private session registry.

Approved native clients (site config): the list `cloud_native_mobile_clients`; master switch
`cloud_native_mobile_enabled`. Any other OAuth client is ignored here. The switch was called
`cloud_raven_mobile_enabled` while Raven's phone app was the first client (Raven was removed in P108): that
name is still read when the new one is absent, so a site keeps working until its config is renamed.
"""
import hashlib
import time
import frappe
from . import sso

def enabled():
    value=frappe.conf.get('cloud_native_mobile_enabled')
    return bool(frappe.conf.get('cloud_raven_mobile_enabled') if value is None else value)

def clients():
    if not enabled():return frozenset()
    ids=frappe.conf.get('cloud_native_mobile_clients') or []
    if isinstance(ids,str):ids=[ids]
    return frozenset(str(i) for i in ids if i)

def digest(value):return hashlib.sha256(str(value).encode()).hexdigest()

def init_state():
    sso.init_state()
    with sso.registry() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS mobile_codes (
            hash TEXT PRIMARY KEY, site TEXT NOT NULL, client TEXT NOT NULL,
            user TEXT NOT NULL, browser TEXT NOT NULL, oidc_sid TEXT NOT NULL, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS mobile_tokens (
            hash TEXT PRIMARY KEY, refresh_hash TEXT, site TEXT NOT NULL, client TEXT NOT NULL,
            user TEXT NOT NULL, browser TEXT NOT NULL, oidc_sid TEXT NOT NULL, created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS mobile_refresh ON mobile_tokens(refresh_hash);
        ''')

def active(binding):
    if not binding or binding['site']!=frappe.local.site or binding['client'] not in clients():return False
    if not frappe.db.get_value('User',binding['user'],'enabled'):return False
    with sso.registry() as db:
        browser=db.execute('SELECT user,revoked FROM browsers WHERE id=?',(binding['browser'],)).fetchone()
        revoked=db.execute('SELECT 1 FROM revoked_oidc WHERE sid=?',(binding['oidc_sid'],)).fetchone()
    return bool(browser and browser['user']==binding['user'] and not browser['revoked'] and not revoked)

def code_created(doc,method=None):
    if doc.client not in clients():return
    record=sso.current_record()
    if not record or sso.revoked(record) or record['user']!=doc.user:
        raise frappe.AuthenticationError('Authorize the mobile app through a fresh Authentik passkey session')
    if str(doc.code_challenge_method).lower()!='s256' or not doc.code_challenge:
        raise frappe.AuthenticationError('Mobile sign-in requires PKCE S256')
    init_state()
    with sso.registry() as db:
        db.execute('INSERT OR REPLACE INTO mobile_codes VALUES(?,?,?,?,?,?,?)',
            (digest(doc.authorization_code),frappe.local.site,doc.client,doc.user,record['browser'],record['oidc_sid'],int(time.time())))

def token_binding():
    init_state();form=frappe.form_dict
    with sso.registry() as db:
        if form.get('grant_type')=='authorization_code' and form.get('code'):
            row=db.execute('SELECT * FROM mobile_codes WHERE hash=?',(digest(form['code']),)).fetchone()
            if row and time.time()-row['created']>600:return None
            return row
        if form.get('grant_type')=='refresh_token' and form.get('refresh_token'):
            return db.execute('SELECT * FROM mobile_tokens WHERE refresh_hash=? AND site=?',
                (digest(form['refresh_token']),frappe.local.site)).fetchone()
    return None

def token_created(doc,method=None):
    if doc.client not in clients():return
    binding=token_binding()
    # A code or refresh grant issued to one app can never mint tokens for another.
    if not active(binding) or binding['user']!=doc.user or binding['client']!=doc.client:
        raise frappe.AuthenticationError('Mobile authorization has expired or was signed out; start again')
    with sso.registry() as db:
        db.execute('INSERT OR REPLACE INTO mobile_tokens VALUES(?,?,?,?,?,?,?,?)',
            (digest(doc.access_token),digest(doc.refresh_token) if doc.refresh_token else None,frappe.local.site,
             doc.client,doc.user,binding['browser'],binding['oidc_sid'],int(time.time())))

def checked_token():
    if not clients():raise frappe.AuthenticationError('Native mobile access is not enabled')
    header=frappe.get_request_header('Authorization','').split()
    if len(header)!=2 or header[0].lower()!='bearer' or len(header[1])>4096:
        raise frappe.AuthenticationError('A native mobile token is required')
    # Called after native validate_oauth in the auth hook/whitelisted endpoint.
    if frappe.session.user in ('Guest',''):
        raise frappe.AuthenticationError('Invalid native token')
    token=frappe.db.get_value('OAuth Bearer Token',header[1],['user','client','status','expiration_time'],as_dict=True)
    if not token or token.client not in clients() or token.status!='Active' or token.user!=frappe.session.user:
        raise frappe.AuthenticationError('Invalid native mobile token')
    from frappe.utils import get_datetime, now_datetime
    if not token.expiration_time or get_datetime(token.expiration_time)<=now_datetime():
        raise frappe.AuthenticationError('Native mobile token expired')
    init_state()
    with sso.registry() as db:
        binding=db.execute('SELECT * FROM mobile_tokens WHERE hash=? AND site=?',
            (digest(header[1]),frappe.local.site)).fetchone()
    if not active(binding) or binding['user']!=frappe.session.user or binding['client']!=token.client:
        raise frappe.AuthenticationError('The originating SSO session has ended')
    return binding

def validate():
    if not clients():return
    header=frappe.get_request_header('Authorization','').split()
    if len(header)!=2 or header[0].lower()!='bearer':return
    # Do not change other OAuth clients. Only approved native apps get the session-bound checks.
    owner=frappe.db.get_value('OAuth Bearer Token',header[1],'client')
    if owner in clients():
        # The retired Suite role guard was re-applied here; Suite is gone and the
        # remaining before_request hooks are host / browser-navigation checks only.
        checked_token()

@frappe.whitelist(methods=['GET','POST'])
def check_access():
    checked_token()
    return {'authorized':True}

def cleanup():
    """Also revoke native refresh grants for known ended SSO bindings."""
    if not clients():return
    init_state()
    for token in frappe.get_all('OAuth Bearer Token',filters={'client':['in',sorted(clients())],'status':'Active'},pluck='name'):
        with sso.registry() as db:
            binding=db.execute('SELECT * FROM mobile_tokens WHERE hash=? AND site=?',
                (digest(token),frappe.local.site)).fetchone()
        if binding and not active(binding):
            frappe.db.set_value('OAuth Bearer Token',token,'status','Revoked',update_modified=False)
