"""Admin alert inbox (P72, P53) hook fragment: the /admin-alerts page and the daily summary mail."""
website_route_rules = [{"from_route": "/admin-alerts", "to_route": "admin_alerts"}]
scheduler_events = {"daily": ["erpnext_drive_integrations.admin_alerts.api.daily_digest"]}
