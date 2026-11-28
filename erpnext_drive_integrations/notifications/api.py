"""The app's call: "what waits for me". Read only, for the signed-in person only."""
import frappe
from frappe import _

from erpnext_drive_integrations.notifications import service


@frappe.whitelist(methods=['GET'])
def waiting():
    """How many decisions wait for the signed-in person, since when the oldest waits and the nearest deadline: in
    total, per kind of thing and per site; and the things themselves (`items`), each with the mark its phone alert
    carried, so the app can open the right one and set its list right. The app asks ERPNext for each thing's
    content. Chat and mail unread counts are not here: the app asks those servers."""
    user = frappe.session.user
    if user == 'Guest':
        frappe.throw(_('Please sign in again.'), frappe.AuthenticationError)
    return service.waiting(user)
