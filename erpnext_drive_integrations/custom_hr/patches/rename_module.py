"""Rename the Module Def "Cloud Field" to "Custom HR" before the DocTypes are synced.

The module's code moved from `cloud_field/` and `field/` to `custom_hr/`. Frappe finds a DocType's controller and
JSON through its module, so migrate it before DocType sync. Some Frappe versions
register the app's new module first. Use Frappe's merge in that case to move links
to the app-owned target. Safe to run twice.
"""
import frappe

OLD, NEW = "Cloud Field", "Custom HR"
APP = "erpnext_drive_integrations"


def execute():
    if not frappe.db.exists("Module Def", OLD):
        return
    target = frappe.db.get_value("Module Def", NEW, ["custom", "app_name"], as_dict=True)
    if target and (target.custom or target.app_name != APP):
        raise ValueError(f'"{NEW}" already belongs to a different owner; resolve it before migrating.')
    # Module Def can be renamed only while marked custom; restore the flag afterwards (as in migration.py).
    was_custom = frappe.db.get_value("Module Def", OLD, "custom")
    frappe.db.set_value("Module Def", OLD, "custom", 1, update_modified=False)
    frappe.rename_doc("Module Def", OLD, NEW, force=True, merge=bool(target))
    frappe.db.set_value("Module Def", NEW, {"custom": was_custom, "app_name": APP}, update_modified=False)
    frappe.clear_cache()
