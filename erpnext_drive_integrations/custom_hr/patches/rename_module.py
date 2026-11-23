"""Rename the Module Def "Cloud Field" to "Custom HR" before the DocTypes are synced.

The module's code moved from `cloud_field/` and `field/` to `custom_hr/`. Frappe finds a DocType's controller and
JSON through its module, so the Module Def is renamed first (pre_model_sync); Frappe's own rename rewrites every
link to it (DocType, Page and the rest). Tables and records are not touched. Safe to run twice.
"""
import frappe

OLD, NEW = "Cloud Field", "Custom HR"
APP = "erpnext_drive_integrations"


def execute():
    if not frappe.db.exists("Module Def", OLD):
        return
    if frappe.db.exists("Module Def", NEW):
        raise ValueError(f'Both "{OLD}" and "{NEW}" exist; resolve by hand before migrating.')
    # Module Def can be renamed only while marked custom; restore the flag afterwards (as in migration.py).
    was_custom = frappe.db.get_value("Module Def", OLD, "custom")
    frappe.db.set_value("Module Def", OLD, "custom", 1, update_modified=False)
    frappe.rename_doc("Module Def", OLD, NEW, force=True)
    frappe.db.set_value("Module Def", NEW, {"custom": was_custom, "app_name": APP}, update_modified=False)
    frappe.clear_cache()
