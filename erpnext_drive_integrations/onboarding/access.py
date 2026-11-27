"""MD rule (2026-11-08): show an app, and a menu item inside it, only when one of the user's OWN roles
is connected to it. Grants every desk user gets (All / Guest / Desk User) do not count, so nobody sees
apps and menus they don't work on. Web Desktop (boot_session hook) and the mobile app use the same rule.

This only decides what is SHOWN. It never grants or removes access: ERPNext's permission checks still
decide what anyone can open (a hidden menu is not security).
"""
import frappe

GENERIC_ROLES = {"All", "Guest", "Desk User"}
OPENABLE = {"DocType", "Report", "Page"}
# Desktop apps whose icon follows this rule (Suite / Insights are handled by cloud_integration).
RULED_APPS = {"erpnext", "hrms", "india_compliance", "onboarding"}


def own_roles(user=None):
    return set(frappe.get_roles(user or frappe.session.user)) - GENERIC_ROLES


class RoleReach:
    """What the user's own roles can open (read, permlevel 0), worked out once per request."""

    def __init__(self, roles):
        self.roles = list(roles)
        self._report_doctype = {}
        if not self.roles:
            self.doctypes, self.reports, self.pages, self.ruled_reports = set(), set(), set(), set()
            return
        custom = set(frappe.get_all("Custom DocPerm", pluck="parent", distinct=True))
        standard = frappe.get_all("DocPerm", filters={"role": ["in", self.roles], "read": 1, "permlevel": 0}, pluck="parent")
        customised = frappe.get_all("Custom DocPerm", filters={"role": ["in", self.roles], "read": 1, "permlevel": 0}, pluck="parent")
        # Frappe uses Custom DocPerm instead of DocPerm for any doctype that has custom rows.
        self.doctypes = {d for d in standard if d not in custom} | set(customised)
        has_role = frappe.get_all("Has Role", filters={"parenttype": ["in", ["Report", "Page"]]}, fields=["parent", "parenttype", "role"])
        self.ruled_reports = {r.parent for r in has_role if r.parenttype == "Report"}
        self.reports = {r.parent for r in has_role if r.parenttype == "Report" and r.role in self.roles}
        self.pages = {r.parent for r in has_role if r.parenttype == "Page" and r.role in self.roles}

    def report_ok(self, name):
        if name in self.ruled_reports:
            return name in self.reports
        # Reports without their own role list follow their source doctype.
        if name not in self._report_doctype:
            self._report_doctype[name] = frappe.db.get_value("Report", name, "ref_doctype")
        return self._report_doctype[name] in self.doctypes

    def connected(self, item):
        if item.get("type") != "Link" or item.get("link_type") not in OPENABLE or not item.get("link_to"):
            return False
        kind, name = item["link_type"], item["link_to"]
        if kind == "DocType":
            return name in self.doctypes
        if kind == "Report":
            return self.report_ok(name)
        return name in self.pages


def filter_items(items, reach):
    """Keep links the user's roles connect to; keep headings only above kept links; keep the module's
    Home (Workspace link) only if the module keeps at least one link. Loose URL / Dashboard links have
    no role behind them, so they are dropped."""
    kept, heading, others = [], None, []
    for item in items or []:
        if item.get("type") == "Section Break":
            heading = item
        elif reach.connected(item):
            if heading is not None:
                kept.append(heading)
                heading = None
            kept.append(item)
        elif item.get("type") == "Link" and item.get("link_type") == "Workspace":
            others.append(item)
    return (others + kept) if kept else []


def filtered_sidebars(sidebars, reach):
    """{shell: entry} with items filtered; shells with nothing left keep an empty item list."""
    return {shell: {**entry, "items": filter_items(entry.get("items"), reach)} for shell, entry in sidebars.items()}


def apps_with_menus(sidebars):
    return {e.get("app") for e in sidebars.values() if e.get("items")}


def boot_session(bootinfo):
    """Apply the rule to the web desk: menus, module rail (dock) and Desktop icons."""
    if frappe.session.user in ("Guest", "Administrator"):
        return
    reach = RoleReach(own_roles())
    sidebars = filtered_sidebars(bootinfo.get("module_sidebars") or {}, reach)
    bootinfo.module_sidebars = sidebars
    live_shells = {shell for shell, e in sidebars.items() if e.get("items")}
    visible = apps_with_menus(sidebars)

    docks = bootinfo.get("dock")
    if isinstance(docks, dict):
        for app, entries in docks.items():
            if isinstance(entries, list):
                docks[app] = [d for d in entries if d.get("link_type") != "Sidebar" or d.get("link_to") in live_shells]

    for app in bootinfo.get("app_data") or []:
        name = app.get("app_name")
        if name not in RULED_APPS:
            continue
        if name not in visible:
            app["on_apps_screen"] = False
            continue
        if not app.get("on_apps_screen"):
            _reopen_app(app, name)
        app["dock"] = [d for d in (app.get("dock") or []) if d.get("link_type") != "Sidebar" or d.get("link_to") in live_shells]


def _reopen_app(app, name):
    """The app's own check hid it (e.g. Frappe HR needs Employee read), but the user's role connects to a
    menu inside it (e.g. Field Supervisor -> HR -> Field Attendance). Rebuild the Desktop entry the way
    frappe.boot.get_app_data does for a permitted app."""
    from frappe.desk.doctype.dock.dock import get_app_entry_set

    source_app = "erpnext_drive_integrations" if name == "onboarding" else name
    hooks = frappe.get_hooks("add_to_apps_screen", app_name=source_app)
    info = hooks[0] if hooks else {}
    app["on_apps_screen"] = True
    app["app_route"] = info.get("route") or (frappe.get_hooks("app_home", app_name=source_app) or [""])[0] or ""
    app["desk_route"] = info.get("desk_route") or ""
    app["dock"] = get_app_entry_set(name)
