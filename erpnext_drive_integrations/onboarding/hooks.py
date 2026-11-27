app_name = "onboarding"
app_title = "Onboarding"
app_publisher = "Cloud"
app_description = "Server side of the Onboarding mobile app"
app_email = "noreply@example.com"
app_license = "Proprietary"
# Native sign-in (session-bound mobile tokens) lives in cloud_integration (ADR-038).
required_apps = ["frappe", "erpnext"]

# MD rule: show apps / menus only where the user's own roles connect (web Desktop). See access.py.
boot_session = "erpnext_drive_integrations.onboarding.access.boot_session"
# Desktop icon (MD 2026-11-12). Opens the Onboarding menu; access.py shows it only to people whose roles reach an item.
# The logo lives in cloud_integration (already served; onboarding has no public folder mount).
add_to_apps_screen = [{"name": "onboarding", "logo": "/assets/erpnext_drive_integrations/app-logos/onboarding.svg?v=20261114-o1", "title": "Onboarding",
                       "route": "/desk/onboarding/vendor-onboarding", "sequence_id": 3}]

# Email health alert (MD 2026-11-08): bell + phone notification to System Managers when mail fails.
scheduler_events = {"hourly": ["erpnext_drive_integrations.onboarding.monitor.check_mail"]}

# Construction schedule (MD 2026-11-08): Project Coordinator role, its access, Task baseline fields, Projects menu.
before_install = "erpnext_drive_integrations.onboarding.setup.ensure_roles"
before_migrate = "erpnext_drive_integrations.onboarding.setup.ensure_roles"
after_install = "erpnext_drive_integrations.onboarding.setup.after_migrate"
after_migrate = "erpnext_drive_integrations.onboarding.setup.after_migrate"

# Outside responses + vendor onboarding (ADR-039): guest page for private links (see www/respond.py).
# On production only respond.example.com exposes these paths (narrow Traefik route); erp.example.com stays behind Authentik.
website_route_rules = [{"from_route": f"/{prefix}/<key>", "to_route": "respond"} for prefix in ("o", "r", "v")]
# Second layer behind Traefik: on the public respond host refuse everything except the response pages / guest methods.
before_request = ["erpnext_drive_integrations.onboarding.respond.gate"]
# Audit HOV-01: a "verified" date counts only for the email / mobile it was verified on.
doc_events = {"Contact": {"validate": "erpnext_drive_integrations.onboarding.amendment.unverify_changed_contact"}}
# "Request response" button; read from disk with the form (no asset build).
doctype_js = {"Purchase Order": "onboarding/client/request_response.js", "Job Offer": "onboarding/client/request_response.js"}
