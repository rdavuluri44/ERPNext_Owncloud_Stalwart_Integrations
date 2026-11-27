"""Configure a newly built/restored site using a private operator profile.

Invoke through Bench, never as a public RPC. Provider secrets are saved through
native Frappe Password fields and never returned or printed.
"""
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

import frappe


def configure(profile_path):
    profile = json.loads(Path(profile_path).read_text())
    tier = os.environ.get('CLOUD_DEPLOYMENT_TIER')
    if tier not in {'test', 'production'} or tier != profile['tier']:
        raise RuntimeError('Deployment tier does not match the operator profile')
    host = profile['host_name'].rstrip('/')
    sso = profile['sso_url'].rstrip('/')
    if any(urlsplit(url).scheme != 'https' or not urlsplit(url).hostname for url in [host, sso]):
        raise ValueError('Public application and issuer URLs must use HTTPS')
    config_path = Path(frappe.get_site_path('site_config.json'))
    config = json.loads(config_path.read_text())
    config.update({'host_name':host, 'cloud_combined_site':True,
        'cloud_sso_auto_provision':False, 'cloud_sso_enforced':True,
        'cloud_cookie_host_only':tier=='test', 'cloud_default_app':'/',
        'cloud_oidc_issuer':profile['issuer'], 'cloud_features':profile.get('features',{}),
        'cloud_test_copy':tier=='test', 'cloud_test_refresh_enabled':False,
        'cloud_test_refresh_users':profile.get('refresh_users',[profile.get('administrator_email')]) if tier=='test' else []})
    if tier=='test':
        config.update({'pause_scheduler':True,'disable_scheduler':True,'mute_emails':True,
                       'cloud_push_enabled':False,'cloud_native_mobile_enabled':False})
    config.update(profile.get('site_settings', {}))
    # A private profile cannot turn a production host into a refresh target.
    config['cloud_test_copy'] = tier=='test'
    config['cloud_test_refresh_enabled'] = tier=='test' and profile.get('refresh_ready') is True
    config_path.write_text(json.dumps(config,indent=2)+'\n')
    frappe.conf.update(config)
    doc = frappe.get_doc('Social Login Key','authentik') if frappe.db.exists('Social Login Key','authentik') else frappe.new_doc('Social Login Key')
    doc.update({'name':'authentik','enable_social_login':1,'social_login_provider':'Custom',
        'provider_name':'authentik','client_id':profile['client_id'],'client_secret':profile['client_secret'],
        'base_url':sso,'authorize_url':'/application/o/authorize/',
        'access_token_url':'/application/o/token/',
        'redirect_url':'/api/method/frappe.integrations.oauth2_logins.custom/authentik',
        'api_endpoint':'/application/o/userinfo/','custom_base_url':1,'sign_ups':'Deny',
        'user_id_property':'sub','auth_url_data':json.dumps({'scope':'openid email profile','response_type':'code'})})
    doc.save(ignore_permissions=True)
    owner = profile.get('administrator_email')
    if owner:
        if not frappe.db.exists('User',owner):
            user=frappe.get_doc({'doctype':'User','email':owner,'first_name':profile.get('administrator_name','Administrator'),
                'enabled':1,'send_welcome_email':0,'roles':[{'role':'System Manager'}]})
            user.insert(ignore_permissions=True)
        else:
            user=frappe.get_doc('User',owner)
            if 'System Manager' not in {r.role for r in user.roles}:
                user.add_roles('System Manager')
    if tier=='test':
        restore_test_oauth_clients(profile.get('test_oauth_clients') or [])
    from erpnext_drive_integrations.portal.sso import init_state
    from erpnext_drive_integrations.bootstrap import configure as configure_navigation
    from erpnext_drive_integrations.portal.combined import configure as configure_home
    init_state()
    configure_home()
    configure_navigation()
    frappe.db.commit()
    frappe.clear_cache()
    return {'configured':True,'tier':tier}


def restore_test_oauth_clients(clients):
    """Re-enable app OAuth clients on a TEST copy (P38).

    An app still under test is blocked on production by giving its OAuth
    client unusable redirect URIs; each production-to-test refresh copies that
    blocked client. This restores only the redirect URIs from the private test
    profile, matched by app name, so the app keeps its client ID and simply
    points at the test host. Tokens stay quarantined: users sign in again.

    A spec with a fixed `client_id` is created when the copy has no client of
    that app name yet (an app not registered on production at all): a public
    native client (no client secret at the token endpoint, PKCE enforced by
    portal/mobile.py) with the consent screen shown.
    `"skip_authorization": true` drops that screen for the deployment's own
    first-party app (owner decision per app); it is applied on every bootstrap.
    """
    if os.environ.get('CLOUD_DEPLOYMENT_TIER')!='test' or frappe.conf.get('cloud_test_copy') is not True:
        raise RuntimeError('Test OAuth clients are restored only on a marked test copy')
    restored=[]
    for spec in clients:
        uris=[u for u in str(spec.get('redirect_uris','')).split() if u]
        default=spec.get('default_redirect_uri') or (uris[0] if uris else '')
        if not spec.get('app_name') or not uris or default not in uris:
            raise ValueError('Each test OAuth client needs app_name and redirect URIs including the default')
        names=frappe.get_all('OAuth Client',filters={'app_name':spec['app_name']},pluck='name')
        values={'redirect_uris':' '.join(uris),'default_redirect_uri':default}
        if 'skip_authorization' in spec:values['skip_authorization']=1 if spec['skip_authorization'] is True else 0
        if not names and spec.get('client_id'):
            client_id=str(spec['client_id'])
            if not re.fullmatch(r'[a-z0-9]{8,40}',client_id):raise ValueError('client_id must be 8-40 lowercase letters or digits')
            frappe.get_doc({'doctype':'OAuth Client','app_name':spec['app_name'],'scopes':'all openid',
                'grant_type':'Authorization Code','response_type':'Code','skip_authorization':0,
                'token_endpoint_auth_method':'None',**values}).insert(ignore_permissions=True,set_name=client_id)
            restored.append(spec['app_name'])
            continue
        for name in names:
            frappe.db.set_value('OAuth Client',name,values)
            restored.append(spec['app_name'])
    return restored
