"""The admin alert inbox at /admin-alerts (P72, P53): open alerts, those resolved in the last week, admin tools."""
import frappe
from frappe.utils.oauth import get_oauth2_authorize_url

from erpnext_drive_integrations.admin_alerts import api

no_cache = 1


def get_context(context):
    if frappe.session.user == 'Guest':
        frappe.local.response['type'] = 'redirect'
        frappe.local.response['location'] = get_oauth2_authorize_url('authentik', '/admin-alerts')
        raise frappe.Redirect
    if not api.enabled() or not api.is_admin():
        frappe.throw('Only administrators can see the alerts.', frappe.PermissionError)
    context.no_cache = 1
    context.title = 'Alerts'
    context.open_alerts, context.resolved_alerts = api.page_alerts(frappe.session.user)
    context.admin_links = api.links()
    context.links_note = api.LINKS_NOTE
    api.mark_seen([a['name'] for a in context.open_alerts if a['unread']], frappe.session.user)
    return context
