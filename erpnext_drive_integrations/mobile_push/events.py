"""What the phone channel does by itself: a disabled person's phones get no more alerts. What sends an alert, and
to whom, is decided by the notification service (`notifications/events.py`), which uses this module to reach phones."""
import frappe


def on_user_update(doc, method=None):
    """A disabled person's phones get no more alerts."""
    if not doc.enabled:
        for name in frappe.get_all('Mobile Device', filters={'user': doc.name}, pluck='name'):
            frappe.delete_doc('Mobile Device', name, ignore_permissions=True, force=True)
