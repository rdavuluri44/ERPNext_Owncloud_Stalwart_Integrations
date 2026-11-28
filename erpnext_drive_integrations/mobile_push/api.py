"""The app's calls: register this phone for alerts after sign-in, remove it at sign-out. Writes are POST only."""
import frappe
from frappe import _
from frappe.utils import now_datetime

from erpnext_drive_integrations.mobile_push import rules


def _user():
    user = frappe.session.user
    if user == 'Guest':
        frappe.throw(_('Please sign in again.'), frappe.AuthenticationError)
    return user


@frappe.whitelist(methods=['POST'])
def register_device(token, platform='android'):
    """This phone's push address for the signed-in person. One phone per person: registering a new phone removes
    the older one. An address signed in by someone else moves to the new person."""
    user = _user()
    if platform != 'android' or not rules.valid_token(token):
        frappe.throw(_('This phone could not be registered for alerts.'))
    digest = rules.token_hash(token)
    old = set(frappe.get_all('Mobile Device', filters={'user': user}, pluck='name'))
    old |= set(frappe.get_all('Mobile Device', filters={'token_hash': digest}, pluck='name'))
    for name in old:
        frappe.delete_doc('Mobile Device', name, ignore_permissions=True, force=True)
    frappe.get_doc(dict(doctype='Mobile Device', user=user, platform='Android', token=token, token_hash=digest,
                        enabled=1, last_seen=now_datetime())).insert(ignore_permissions=True)
    return {'ok': True}


@frappe.whitelist(methods=['POST'])
def unregister_device(token):
    """Sign-out: this phone gets no more alerts for this person. Only the person's own record is removed."""
    user = _user()
    if rules.valid_token(token):
        for name in frappe.get_all('Mobile Device', filters={'user': user, 'token_hash': rules.token_hash(token)},
                                   pluck='name'):
            frappe.delete_doc('Mobile Device', name, ignore_permissions=True, force=True)
    return {'ok': True}
