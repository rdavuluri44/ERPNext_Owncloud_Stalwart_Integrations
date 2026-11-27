import frappe
from erpnext_drive_integrations.custom_hr.access import is_manager, site_ids, entry_access, supervised_users


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
    verifier = _site_clause('Field Attendance Entry', user, 'Verifier')
    entry = '`tabField Attendance Entry`'
    clauses = [f"({entry}.captured_by={own} AND (({sup}) OR ({verifier})))",
               f"({entry}.state!='Draft' AND ({app}))"]
    for site in site_ids(user, 'Verifier'):
        supervisors = supervised_users(site, user)
        if supervisors:
            scoped = ','.join(frappe.db.escape(supervisor) for supervisor in supervisors)
            clauses.append(f"({entry}.state!='Draft' AND {entry}.site={frappe.db.escape(site)}"
                           f" AND {entry}.responsible_supervisor IN ({scoped}))")
    return '(' + ' OR '.join(clauses) + ')'


def face_capture_query(user=None):
    user=user or frappe.session.user
    if is_manager(user):return ''
    approver=_site_clause('Field Face Capture',user,'Approver')
    return f"(`tabField Face Capture`.captured_by={frappe.db.escape(user)} OR ({approver}))"


def face_capture_access(doc,user):
    return is_manager(user) or doc.captured_by==user or doc.site in site_ids(user,'Approver')


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
    if doc.doctype=='Field Face Capture':return face_capture_access(doc,user)
    site=doc.name if doc.doctype=='Field Site' else doc.site
    return is_manager(user) or site in site_ids(user)
