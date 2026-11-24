"""Photo store (P74) hook fragment: only the daily renewal of the store's Drive app token."""
scheduler_events = {"daily": ["erpnext_drive_integrations.drive_store.drive.renew_if_due"]}
