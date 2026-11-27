"""Chat rooms (P73) hook fragment: rooms follow the sites; a person's chat name is checked; an hourly run heals."""
after_install = "erpnext_drive_integrations.chat_rooms.sync.install"
after_migrate = "erpnext_drive_integrations.chat_rooms.sync.install"
doc_events = {
    "Field Site": {"on_update": "erpnext_drive_integrations.chat_rooms.sync.site_changed"},
    "User": {"validate": "erpnext_drive_integrations.chat_rooms.sync.validate_user",
             "on_update": "erpnext_drive_integrations.chat_rooms.sync.user_changed"},
}
scheduler_events = {"hourly": ["erpnext_drive_integrations.chat_rooms.sync.sync_all"]}
