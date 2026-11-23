import frappe
from erpnext_drive_integrations.custom_hr.access import is_manager, site_ids, entry_access


def _site_clause(doctype, user, role=None):
    if is_manager(user):
        return ''
    sites=site_ids(user, role)
    if not sites:
        return '1=0'
    key='name' if doctype=='Field Site' else 'site'
    return f'`tab{doctype}`.`{key}` IN ({",".join(frappe.db.escape(s) for s in sites)})'


def entry_query(user=None):
    user=user or frappe.session.user
    if is_manager(user):return ''
    own=frappe.db.escape(user)
    sup=_site_clause('Field Attendance Entry',user,'Supervisor') or '1=1'
    app=_site_clause('Field Attendance Entry',user,'Approver') or '1=1'
    return f"((`tabField Attendance Entry`.captured_by={own} AND ({sup})) OR (`tabField Attendance Entry`.state!='Draft' AND ({app})))"


def assignment_query(user=None):return _site_clause('Field Worker Assignment',user or frappe.session.user)
def allocation_query(user=None):return _site_clause('Field Shift Allocation',user or frappe.session.user)
def event_query(user=None):return _site_clause('Field Assignment Event',user or frappe.session.user)
def site_query(user=None):return _site_clause('Field Site',user or frappe.session.user)


def has_permission(doc, user=None, permission_type=None):
    user=user or frappe.session.user
    if user=='Guest':return False
    if permission_type not in (None,'read','select','print','report','export'):
        return is_manager(user) and doc.doctype=='Field Site'
    if doc.doctype=='Field Attendance Entry':return entry_access(doc,user)
    site=doc.name if doc.doctype=='Field Site' else doc.site
    return is_manager(user) or site in site_ids(user)
