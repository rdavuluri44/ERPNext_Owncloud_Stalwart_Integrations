"""Compose logical UI modules without creating extra installed apps."""
import frappe

def configure():
    if (frappe.conf.get("cloud_features") or {}).get("portal", True):
        frappe.db.set_single_value("Website Settings", "home_page", "place_holder")
        frappe.db.set_single_value("Website Settings", "disable_signup", 1)
        # Tenant branding comes from the private runtime profile (company_logo, company_favicon_dir).
        # Literal paths, so the renderer stamps them with the release version like every other reference.
        frappe.db.set_single_value("Website Settings", "favicon", "/assets/erpnext_drive_integrations/company-favicon-32.png")
        frappe.db.set_single_value("Website Settings", "app_logo", "/assets/erpnext_drive_integrations/company-logo-approved-v6.svg")

def boot_session(bootinfo):
    features = frappe.conf.get("cloud_features") or {}
    # These labels describe logical navigation, not installed app registrations.
    for entry in (bootinfo.get("module_sidebars") or {}).values():
        if entry.get("app") != "erpnext_drive_integrations":
            continue
        module = entry.get("module") or entry.get("name")
        entry["app"] = {"Onboarding": "onboarding", "Custom HR": "hrms",
                        "Cloud Integrations": "frappe"}.get(module, "onboarding")
    from erpnext_drive_integrations.hooks import _feature_enabled
    if _feature_enabled("custom_hr", features):
        from erpnext_drive_integrations.custom_hr.web import boot_session as hr_boot
        hr_boot(bootinfo)
    if features.get("onboarding", True):
        from erpnext_drive_integrations.onboarding.access import boot_session as onboarding_boot
        onboarding_boot(bootinfo)
