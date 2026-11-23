import frappe


def execute():
    """The new "Attendance needs approval" box: every existing site keeps needing approval (owner, 22 November 2026).
    Only an administrator unticks it, site by site (for example head office)."""
    frappe.db.sql("UPDATE `tabField Site` SET approval_required=1")
