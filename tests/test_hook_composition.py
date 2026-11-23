"""The consolidation must not drop a security hook when another module owns the same event."""
import sys
import types
import unittest

fake=types.ModuleType('frappe');fake.conf={};sys.modules['frappe']=fake
from erpnext_drive_integrations import hooks

class CompositionTests(unittest.TestCase):
    def test_user_validators_are_both_retained(self):
        values=hooks.doc_events['User']['validate']
        self.assertIn('erpnext_drive_integrations.portal.combined.new_central_user',values)
        self.assertIn('erpnext_drive_integrations.custom_hr.guards.validate_user',values)
    def test_jobs_and_request_guards_are_retained(self):
        self.assertIn('erpnext_drive_integrations.onboarding.respond.gate',hooks.before_request)
        self.assertIn('erpnext_drive_integrations.portal.guard.refuse_rpc_cmd',hooks.before_request)
        self.assertIn('erpnext_drive_integrations.custom_hr.checkout.close_due_entries',hooks.scheduler_events['cron']['* * * * *'])
        self.assertIn('erpnext_drive_integrations.onboarding.monitor.check_mail',hooks.scheduler_events['hourly'])
    def test_installed_identity(self):
        self.assertEqual(hooks.app_name,'erpnext_drive_integrations')
        from erpnext_drive_integrations import __version__
        self.assertEqual(__version__,'0.1.0')

if __name__=='__main__':unittest.main()
