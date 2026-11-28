"""Notification service (P108) hook fragment (feature switch `notifications` in cloud_features)."""
_events = "erpnext_drive_integrations.notifications.events."
_service = "erpnext_drive_integrations.notifications.service."
doc_events = {
    "Notification Log": {"after_insert": _events + "on_notification"},
    "Workflow Action": {"after_insert": _events + "on_workflow_action"},
    "User": {"on_update": _events + "on_user_update"},
    "*": {"on_update": _events + "on_document_update", "on_trash": _events + "on_document_trash"},
}
scheduler_events = {"hourly": [_service + "remind"], "daily": [_service + "purge"]}
