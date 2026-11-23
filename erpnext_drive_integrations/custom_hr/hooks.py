app_name = "custom_hr"
app_title = "Field Attendance"
app_publisher = "Cloud"
app_description = "Supervisor attendance, assignments and approval"
app_email = "postmaster@example.com"
app_license = "MIT"
required_apps = ["erpnext", "hrms"]
before_install = "erpnext_drive_integrations.custom_hr.setup.roles"
after_install = "erpnext_drive_integrations.custom_hr.setup.install"
after_migrate = "erpnext_drive_integrations.custom_hr.setup.install"
after_request = ["erpnext_drive_integrations.custom_hr.web.after_request"]
app_include_js = ["/assets/erpnext_drive_integrations/custom_hr/launcher.js?v=013"]
web_include_js = ["/assets/erpnext_drive_integrations/custom_hr/launcher.js?v=013"]
boot_session = "erpnext_drive_integrations.custom_hr.web.boot_session"
doc_events = {
    "Employee": {"validate": "erpnext_drive_integrations.custom_hr.guards.validate_employee", "after_insert": "erpnext_drive_integrations.custom_hr.guards.after_employee_insert", "on_update": "erpnext_drive_integrations.custom_hr.guards.on_employee_update"},
    "User": {"validate": "erpnext_drive_integrations.custom_hr.guards.validate_user", "on_trash": "erpnext_drive_integrations.custom_hr.guards.validate_user"},
    "File": {"validate": "erpnext_drive_integrations.custom_hr.guards.protect_file", "on_trash": "erpnext_drive_integrations.custom_hr.guards.protect_file"},
    "Attendance": {"before_cancel": "erpnext_drive_integrations.custom_hr.guards.before_cancel_attendance", "validate": "erpnext_drive_integrations.custom_hr.guards.validate_attendance"},
}
permission_query_conditions = {
    "Field Attendance Entry": "erpnext_drive_integrations.custom_hr.permissions.entry_query",
    "Field Worker Assignment": "erpnext_drive_integrations.custom_hr.permissions.assignment_query",
    "Field Shift Allocation": "erpnext_drive_integrations.custom_hr.permissions.allocation_query",
    "Field Assignment Event": "erpnext_drive_integrations.custom_hr.permissions.event_query",
    "Field Site": "erpnext_drive_integrations.custom_hr.permissions.site_query",
}
has_permission = {doctype: "erpnext_drive_integrations.custom_hr.permissions.has_permission" for doctype in [
    "Field Attendance Entry", "Field Worker Assignment", "Field Shift Allocation", "Field Assignment Event", "Field Site"
]}
website_route_rules = [{"from_route": "/field-team", "to_route": "field_team"}]

# Run on the server; no open browser or phone connection is required.
scheduler_events = {"cron": {"* * * * *": ["erpnext_drive_integrations.custom_hr.checkout.close_due_entries"]}}
