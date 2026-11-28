"""What makes the service speak, and what closes a waiting record.

Owner, 26 November 2026: a person is alerted when something new waits for their approval or check, or when their
entry was returned to them. Approved entries and other notifications send nothing.
"""
import frappe

from erpnext_drive_integrations.notifications import rules, service


def on_notification(doc, method=None):
    """custom_hr writes a Notification Log for each person an attendance entry concerns; the entry's state says
    why (waiting for approval or verification, or returned)."""
    if doc.document_type != rules.ATTENDANCE or not doc.document_name or not doc.for_user:
        return
    entry = frappe.db.get_value(rules.ATTENDANCE, doc.document_name, ['state', 'site'], as_dict=True)
    reason = entry and rules.attendance_reason(entry.state)
    if reason:
        service.notify([doc.for_user], rules.DECIDE, rules.ATTENDANCE, doc.document_name, reason=reason,
                       state=entry.state, site=entry.site)


def on_workflow_action(doc, method=None):
    """A new ERPNext approval (Workflow Action, Open): every enabled person who holds one of its roles and may read
    the document. ERPNext still decides who may approve when they open it."""
    if doc.get('status') != 'Open' or not doc.get('reference_doctype') or not doc.get('reference_name'):
        return
    if doc.get('user'):
        holders = [doc.user]
    else:
        roles = [row.role for row in doc.get('permitted_roles') or [] if row.role]
        holders = frappe.get_all('Has Role', filters={'role': ['in', roles], 'parenttype': 'User'}, pluck='parent',
                                 distinct=True) if roles else []
    allowed = [u for u in holders if frappe.db.get_value('User', u, 'enabled')
               and frappe.has_permission(doc.reference_doctype, 'read', doc.reference_name, user=u)]
    service.notify(allowed, rules.DECIDE, doc.reference_doctype, doc.reference_name, reason='approval',
                   state=doc.get('workflow_state'))


def _quiet():
    flags = frappe.flags
    return flags.in_install or flags.in_migrate or flags.in_patch or flags.in_import


def on_document_update(doc, method=None):
    """Any saved document: when an attendance entry or a document under a workflow has left the state its waiting
    records were made for, they are closed. Other document types return at once."""
    if _quiet() or doc.doctype == service.RECORD:
        return
    if doc.doctype == rules.ATTENDANCE:
        field = 'state'
    else:
        from frappe.model.workflow import get_workflow_name  # cached by Frappe; no query for most saves
        workflow = get_workflow_name(doc.doctype)
        field = workflow and frappe.get_cached_value('Workflow', workflow, 'workflow_state_field')
    if field:
        service.resolve(doc.doctype, doc.name, doc.get(field) or '')


def on_document_trash(doc, method=None):
    """A deleted document waits for nobody."""
    if not _quiet() and doc.doctype != service.RECORD:
        service.resolve(doc.doctype, doc.name)


def on_user_update(doc, method=None):
    if not doc.enabled:
        service.forget(doc.name)
