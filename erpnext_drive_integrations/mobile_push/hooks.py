"""Mobile push hooks (feature switch `mobile_push` in cloud_features)."""
doc_events = {
    "Notification Log": {"after_insert": "erpnext_drive_integrations.mobile_push.events.on_notification"},
    "Workflow Action": {"after_insert": "erpnext_drive_integrations.mobile_push.events.on_workflow_action"},
    "User": {"on_update": "erpnext_drive_integrations.mobile_push.events.on_user_update"},
}
