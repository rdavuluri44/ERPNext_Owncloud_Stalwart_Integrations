import frappe
from frappe import _

MANAGER = 'Field Attendance Manager'
SUPERVISOR = 'Field Supervisor'
APPROVER = 'Field Attendance Approver'


def is_manager(user=None):
    user = user or frappe.session.user
    return user == 'Administrator' or bool({MANAGER, 'System Manager'} & set(frappe.get_roles(user)))


def require_user():
    user = frappe.session.user
    if user == 'Guest' or not frappe.db.get_value('User', user, 'enabled'):
        frappe.throw(_('Please sign in again.'), frappe.AuthenticationError)
    return user


def site_ids(user=None, role=None):
    user = user or require_user()
    if is_manager(user):
        return frappe.get_all('Field Site', filters={'enabled': 1}, pluck='name')
    roles = set(frappe.get_roles(user))
    permitted = []
    if SUPERVISOR in roles and role in (None, 'Supervisor'):
        permitted.append('Supervisor')
    if APPROVER in roles and role in (None, 'Approver'):
        permitted.append('Approver')
    if not permitted:
        return []
    return frappe.db.sql('''SELECT DISTINCT m.parent FROM `tabField Site Member` m
        JOIN `tabField Site` s ON s.name=m.parent
        WHERE m.user=%s AND m.enabled=1 AND m.team_role IN %s AND s.enabled=1''',
        (user, permitted), pluck=True)


def site_access(site, role=None, user=None):
    return site in site_ids(user, role)


def require_site(site, role=None):
    user = require_user()
    if not site_access(site, role, user):
        frappe.throw(_('You do not have access to this site.'), frappe.PermissionError)
    return frappe.get_doc('Field Site', site)


def eligible_supervisor(site, user):
    return bool(user and frappe.db.get_value('User', user, 'enabled') and
                SUPERVISOR in frappe.get_roles(user) and frappe.db.exists('Field Site Member', {
                    'parent': site, 'parenttype': 'Field Site', 'user': user,
                    'team_role': 'Supervisor', 'enabled': 1}))


def require_manager():
    require_user()
    if not is_manager():
        frappe.throw(_('Only a Field Attendance Manager can configure this module.'), frappe.PermissionError)


def entry_access(doc, user=None):
    user = user or frappe.session.user
    if user == 'Guest':
        return False
    if is_manager(user):
        return True
    if doc.captured_by == user and site_access(doc.site, 'Supervisor', user):
        return True
    return doc.state != 'Draft' and site_access(doc.site, 'Approver', user)
