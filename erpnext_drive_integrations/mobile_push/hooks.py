"""Mobile push hooks (feature switch `mobile_push` in cloud_features). The triggers are the notification service's."""
doc_events = {
    "User": {"on_update": "erpnext_drive_integrations.mobile_push.events.on_user_update"},
}
