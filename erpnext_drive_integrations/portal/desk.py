"""The Desk's top bar (P111): what About shows, and the business system's part of the universal notifications.

Search uses the framework's own ``frappe.utils.global_search.search``; the other applications answer the Desk's
search and notification questions from their own pages, with the person's own session there.
"""
import json
from pathlib import Path

import frappe

from erpnext_drive_integrations import __repository__ as REPOSITORY

OURS = 'erpnext_drive_integrations'
COMPONENTS = Path(__file__).with_name('components.json')


def _version(app):
    try:
        return str(frappe.get_attr(app + '.__version__'))
    except Exception:
        return ''


def _title(app):
    try:
        return str(frappe.get_hooks('app_title', app_name=app)[0])
    except Exception:
        return app


@frappe.whitelist(methods=['GET'])
def about():
    """Our application, the installed Frappe applications and the other applications, each with its version."""
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in first', frappe.PermissionError)
    apps = [{'name': app, 'title': _title(app), 'version': _version(app)}
            for app in frappe.get_installed_apps() if app != OURS]
    try:
        components = json.loads(COMPONENTS.read_text(encoding='utf-8'))['components']
    except (OSError, ValueError, KeyError):
        components = []
    return {'ours': {'name': OURS, 'version': _version(OURS), 'repository': REPOSITORY},
            'frappe_apps': apps, 'components': components}


@frappe.whitelist(methods=['GET'])
def notifications():
    """The person's unread notifications of the business system, newest first."""
    from frappe.utils import strip_html
    user = frappe.session.user
    if user == 'Guest':
        frappe.throw('Sign in first', frappe.PermissionError)
    rows = frappe.get_all('Notification Log', filters={'for_user': user, 'read': 0},
                          fields=['name', 'subject', 'document_type', 'document_name', 'creation'],
                          order_by='creation desc', limit_page_length=20)
    items = []
    for row in rows:
        path = ''
        if row.document_type and row.document_name:
            path = '/desk/%s/%s' % (frappe.scrub(row.document_type).replace('_', '-'), row.document_name)
        items.append({'title': strip_html(row.subject or '')[:200], 'path': path, 'time': str(row.creation)})
    return {'items': items, 'unread': frappe.db.count('Notification Log', {'for_user': user, 'read': 0})}
