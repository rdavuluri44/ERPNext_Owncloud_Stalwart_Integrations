from erpnext_drive_integrations.custom_hr.guards import ControlledDocument


class BiometricConsent(ControlledDocument):
    """Written and deleted only by custom_hr.face_service (P95)."""
