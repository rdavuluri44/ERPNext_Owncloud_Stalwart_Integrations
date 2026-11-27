"""What sends an alert (owner, 26 November 2026): something new waits for your approval or check, or your entry
was returned to you. Approved entries and other notifications send nothing."""
import frappe

from erpnext_drive_integrations.mobile_push import rules, sender


def on_notification(doc, method=None):
    """custom_hr writes a Notification Log for each person an attendance entry concerns; the entry's state says
    why (waiting for approval or verification, or returned)."""
    if doc.document_type != rules.ATTENDANCE or not doc.document_name or not doc.for_user:
        return
    entry = frappe.db.get_value(rules.ATTENDANCE, doc.document_name, ['state', 'site'], as_dict=True)
    kind = entry and rules.attendance_kind(entry.state)
    if kind:
        sender.send([doc.for_user], kind, rules.ATTENDANCE, doc.document_name, entry.site,
                    frappe.db.get_value('Field Site', entry.site, 'site_name'))


def on_workflow_action(doc, method=None):
    """A new ERPNext approval (Workflow Action, Open): every person with a phone who holds one of its roles and may
    read the document. ERPNext still decides who may approve when they open it."""
    if doc.get('status') != 'Open' or not doc.get('reference_doctype') or not doc.get('reference_name'):
        return
    if doc.get('user'):
        holders = [doc.user]
    else:
        roles = [row.role for row in doc.get('permitted_roles') or [] if row.role]
        holders = frappe.get_all('Has Role', filters={'role': ['in', roles], 'parenttype': 'User'}, pluck='parent',
                                 distinct=True) if roles else []
    with_phone = frappe.get_all('Mobile Device', filters={'user': ['in', holders], 'enabled': 1}, pluck='user',
                                distinct=True) if holders else []
    allowed = [u for u in with_phone if frappe.db.get_value('User', u, 'enabled')
               and frappe.has_permission(doc.reference_doctype, 'read', doc.reference_name, user=u)]
    sender.send(allowed, 'approval', doc.reference_doctype, doc.reference_name)


def on_user_update(doc, method=None):
    """A disabled person's phones get no more alerts."""
    if not doc.enabled:
        for name in frappe.get_all('Mobile Device', filters={'user': doc.name}, pluck='name'):
            frappe.delete_doc('Mobile Device', name, ignore_permissions=True, force=True)
