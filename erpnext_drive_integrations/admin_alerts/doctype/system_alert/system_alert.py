from frappe.model.document import Document


class SystemAlert(Document):
    """One alert per source and key, written only by admin_alerts.api.report (no create or write in the UI)."""
    pass
