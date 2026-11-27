app_name = "cloud_integration"
app_title = 'place-holder'
app_publisher = "Cloud"
app_description = "Approved SSO and shared-browser logout"
app_email = "postmaster@example.com"
app_license = "MIT"
before_request = ["erpnext_drive_integrations.portal.guard.refuse_rpc_cmd", "erpnext_drive_integrations.portal.sso.before_request"]
on_login = "erpnext_drive_integrations.portal.sso.on_login"
on_session_creation = "erpnext_drive_integrations.portal.sso.on_session_creation"
on_logout = ["erpnext_drive_integrations.portal.push.on_logout", "erpnext_drive_integrations.portal.sso.on_logout"]
override_whitelisted_methods = {
    "frappe.integrations.oauth2_logins.custom": "erpnext_drive_integrations.portal.sso.callback",
}
app_include_js = ['/assets/erpnext_drive_integrations/push-client.js?v=20261106-push2', '/assets/erpnext_drive_integrations/session.js?v=20261119-marker']
web_include_js = ['/assets/erpnext_drive_integrations/push-client.js?v=20261106-push2', '/assets/erpnext_drive_integrations/session.js?v=20261119-marker']

after_request = ['erpnext_drive_integrations.portal.sso.after_request']

boot_session = []

doc_events = {"User": {"validate": "erpnext_drive_integrations.portal.combined.new_central_user"}}
after_migrate = "erpnext_drive_integrations.portal.combined.configure"

before_migrate = "erpnext_drive_integrations.portal.combined.prepare"
fixtures = [{"dt": "Role", "filters": [["name", "=", "Mailbox Administrator"]]}]

# Native phone-app OAuth session binding
auth_hooks = ["erpnext_drive_integrations.portal.mobile.validate"]
doc_events.update({"OAuth Authorization Code": {"after_insert": "erpnext_drive_integrations.portal.mobile.code_created"}, "OAuth Bearer Token": {"after_insert": "erpnext_drive_integrations.portal.mobile.token_created"}})
scheduler_events = {"cron": {"* * * * *": ["erpnext_drive_integrations.portal.mobile.cleanup", "erpnext_drive_integrations.portal.push.cleanup"]}}

doc_events.update({"Notification Log":{"after_insert":"erpnext_drive_integrations.portal.push.notification_created"},"Workflow Action":{"after_insert":"erpnext_drive_integrations.portal.push.workflow_created"}})

# Native desktop preview for independently installed app menus.
app_include_js += []

website_route_rules = (globals().get('website_route_rules') or []) + [{'from_route':'/','to_route':'place_holder'}]

app_include_js = (globals().get('app_include_js') or []) + ['/assets/erpnext_drive_integrations/module-header-20261115.js?v=5']

website_route_rules += [{'from_route':'/signed-out','to_route':'signed_out'}]
