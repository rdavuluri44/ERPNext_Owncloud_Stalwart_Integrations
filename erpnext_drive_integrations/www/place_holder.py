import re

import frappe
from frappe.boot import get_app_data
from frappe.utils.oauth import get_oauth2_authorize_url

no_cache = 1


def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.local.response['type'] = 'redirect'
        frappe.local.response['location'] = get_oauth2_authorize_url('authentik', '/place_holder')
        raise frappe.Redirect
    fullname = frappe.utils.get_fullname() or frappe.session.user
    parts = fullname.split()
    company = frappe.defaults.get_user_default('Company') or frappe.db.get_single_value('Global Defaults', 'default_company')
    # Each site's own look (owner rule, 21 November 2026: production and test have separate asset sets).
    # Without these site settings the page is exactly production's.
    context.entity_name = '' if frappe.conf.get('cloud_portal_hide_entity_name') else (company or 'Applications')
    height = frappe.conf.get('cloud_portal_logo_height')
    context.portal_logo_height = int(height) if isinstance(height, int) and 40 <= height <= 100 else 0
    context.portal_clean_root = bool(frappe.conf.get('cloud_portal_clean_root_address'))
    position = frappe.conf.get('cloud_portal_logo_position') or {}
    ok = isinstance(position, dict) and all(isinstance(position.get(k), int) and 0 <= position[k] <= 80 for k in ('top', 'left'))
    context.portal_logo_position = {'top': position['top'], 'left': position['left']} if ok else None
    context.entity_logo = '/assets/erpnext_drive_integrations/company-logo-approved-v6.svg'
    context.user_name = fullname
    context.user_login = frappe.session.user
    from erpnext_drive_integrations.portal import test_refresh
    context.test_refresh_enabled = test_refresh.enabled()
    context.test_refresh_can_request = test_refresh.can_request()
    if context.test_refresh_enabled:
        from frappe.sessions import get_csrf_token
        context.test_refresh_csrf = get_csrf_token()
    context.user_short = ''.join(p[0] for p in (parts[:1] + parts[-1:] if len(parts) > 1 else parts[:1])).upper()
    fallback = {'erpnext': '/desk/setup/home', 'hrms': '/desk/hr-setup', 'frappe': '/desk/build', 'onboarding': '/desk/onboarding/vendor-onboarding'}
    apps = []
    for app in sorted(get_app_data(), key=lambda x: x.get('sequence_id', 500)):
        if not app.get('on_apps_screen'):
            continue
        name = app['app_name']
        route = fallback.get(name) or app.get('app_route') or app.get('desk_route')
        if not route or name in ('cloud_integration', 'place_holder', 'suite'):
            continue
        logo = app.get('app_logo_url') or ''
        if isinstance(logo, list):
            logo = logo[0] if logo else ''
        if route.startswith('/desk/'):
            route += ('&' if '?' in route else '?') + 'uf_entry=1'
        apps.append({'id': name, 'name': app.get('app_title') or name, 'url': route, 'logo': logo})
    apps.extend([
        {'id': 'drive', 'name': 'Drive', 'url': 'https://drive.example.com/', 'logo': '/assets/erpnext_drive_integrations/app-logos/external-office.svg'},
        {'id': 'mail', 'name': 'Mail', 'url': 'https://mail.example.com/mail/folder/inbox', 'logo': '/assets/erpnext_drive_integrations/app-logos/external-mail.svg'},
        {'id': 'dms', 'name': 'DMS', 'url': 'https://dms.example.com/', 'logo': '/assets/erpnext_drive_integrations/app-logos/external-dms.svg'},
    ])
    # The chat screen (P73) signs in through pages that refuse to be shown inside another page, so it opens
    # in its own tab. Listed only where the site names its address.
    chat = frappe.conf.get('cloud_chat_web_url')
    if isinstance(chat, str) and re.fullmatch(r'https://[a-z0-9.-]+/', chat):
        apps.append({'id': 'chat', 'name': 'Chat', 'url': chat, 'external': True,
                     'logo': '/assets/erpnext_drive_integrations/app-logos/external-chat.svg'})
    context.portal_apps = apps
    context.logout_url = '/api/method/erpnext_drive_integrations.portal.sso.finish_logout'
    return context
