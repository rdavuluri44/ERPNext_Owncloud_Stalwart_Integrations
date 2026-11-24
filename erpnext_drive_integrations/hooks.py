"""One installed Frappe app, independent feature hook fragments."""
from importlib import import_module
import frappe

app_name = "erpnext_drive_integrations"
app_title = "ERPNext_drive_integrations"
app_publisher = "Integration Maintainers"
app_description = "Modular portal, SSO, field, onboarding and Drive integrations"
app_email = "maintainers@example.com"
app_license = "AGPL-3.0-or-later; see LICENSES.md"
required_apps = ["erpnext", "hrms"]

_list_hooks = ["before_request", "after_request", "on_login", "on_session_creation",
               "on_logout", "app_include_js", "web_include_js", "auth_hooks",
               "before_install", "after_install", "before_migrate", "after_migrate"]
_dict_hooks = ["override_whitelisted_methods", "permission_query_conditions", "has_permission", "doctype_js"]
for _key in _list_hooks:
    globals()[_key] = []
for _key in _dict_hooks:
    globals()[_key] = {}
doc_events, scheduler_events, website_route_rules, fixtures = {}, {}, [], []
_configured = frappe.conf.get("cloud_features") or {}

def _values(value):
    return list(value) if isinstance(value, (tuple, list)) else [value]

def _feature_enabled(name, configured):
    """cloud_features switch for one feature; `custom_hr` was called `field` before, and that key still counts."""
    return configured.get(name, configured.get("field", True) if name == "custom_hr" else True) is not False

for _feature in ("portal", "custom_hr", "onboarding", "drive_store"):
    if not _feature_enabled(_feature, _configured):
        continue
    _fragment = import_module(f"erpnext_drive_integrations.{_feature}.hooks")
    for _key in _list_hooks:
        if hasattr(_fragment, _key):
            globals()[_key].extend(_values(getattr(_fragment, _key)))
    for _key in _dict_hooks:
        globals()[_key].update(getattr(_fragment, _key, {}))
    for _doctype, _events in getattr(_fragment, "doc_events", {}).items():
        for _event, _handlers in _events.items():
            doc_events.setdefault(_doctype, {}).setdefault(_event, []).extend(_values(_handlers))
    for _frequency, _handlers in getattr(_fragment, "scheduler_events", {}).items():
        if _frequency == "cron":
            for _expression, _methods in _handlers.items():
                scheduler_events.setdefault("cron", {}).setdefault(_expression, []).extend(_methods)
        else:
            scheduler_events.setdefault(_frequency, []).extend(_values(_handlers))
    website_route_rules.extend(getattr(_fragment, "website_route_rules", []))
    fixtures.extend(getattr(_fragment, "fixtures", []))

boot_session = "erpnext_drive_integrations.bootstrap.boot_session"
# Optional one-time compatibility aliases are supplied privately by the operator.
# They preserve old callers without keeping extra apps or old identifiers in source.
override_whitelisted_methods.update(frappe.conf.get("cloud_legacy_rpc_aliases") or {})
if _configured.get("onboarding", True):
    add_to_apps_screen = [{"name": "onboarding", "title": "Onboarding", "sequence_id": 3,
                          "logo": "/assets/erpnext_drive_integrations/app-logos/onboarding.svg",
                          "route": "/desk/onboarding/vendor-onboarding"}]

after_install.append("erpnext_drive_integrations.bootstrap.configure")
after_migrate.append("erpnext_drive_integrations.bootstrap.configure")
