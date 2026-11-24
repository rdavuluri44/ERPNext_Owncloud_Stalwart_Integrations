import frappe
from frappe.model.document import Document


class StoreRecord(Document):
    """Photo-store records are written only by the store's own calls and are never deleted (owner: nobody
    deletes a work photo)."""

    def validate(self):
        if not self.flags.drive_store:
            frappe.throw('Photo-store records change only through the app.', frappe.PermissionError)

    def on_trash(self):
        frappe.throw('Work photos and their records are kept; they cannot be deleted.', frappe.PermissionError)
