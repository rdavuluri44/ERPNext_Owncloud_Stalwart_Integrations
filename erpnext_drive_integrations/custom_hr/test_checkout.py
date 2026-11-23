"""Checkout timing and exclusion checks; no attendance fixtures or real worker writes."""
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace
from erpnext_drive_integrations.custom_hr import checkout


class CheckoutTests(TestCase):
    def test_night_shift_crosses_midnight(self):
        self.assertEqual(checkout.due_time('2026-11-06 19:15:00'), datetime(2026,11,7,7,15))

    def run_job(self, state='Submitted', status='Present', hours=12, already_closed=False):
        check_in=datetime(2026,11,6,7,0)
        doc=SimpleNamespace(state=state, attendance_status=status, check_in_time=check_in,
                            check_out_time=check_in+timedelta(hours=12) if already_closed else None)
        with patch.object(checkout,'now_datetime',return_value=check_in+timedelta(hours=hours)), \
             patch.object(checkout.frappe,'get_all',return_value=['test-entry']), \
             patch.object(checkout.frappe,'get_doc',return_value=doc), \
             patch.object(checkout.frappe.db,'sql'), \
             patch.object(checkout.frappe.db,'set_value') as write:
            count=checkout.close_due_entries()
            return count,write.call_args

    def test_checkout_at_exact_boundary(self):
        count,call=self.run_job()
        self.assertEqual(count,1)
        self.assertEqual(call.args[2]['check_out_time'],datetime(2026,11,6,19))
        self.assertNotIn('state',call.args[2])
        self.assertNotIn('attendance',call.args[2])

    def test_late_scheduler_keeps_due_time(self):
        count,call=self.run_job(state='Approved',hours=15)
        self.assertEqual(count,1)
        self.assertEqual(call.args[2]['check_out_time'],datetime(2026,11,6,19))

    def test_never_checkout_early(self):
        self.assertEqual(self.run_job(hours=11)[0],0)

    def test_do_not_overwrite_existing_checkout(self):
        self.assertEqual(self.run_job(already_closed=True)[0],0)

    def test_exclude_absent_and_unsubmitted(self):
        for state,status in [('Draft','Present'),('Returned','Present'),('Submitted','Absent')]:
            self.assertEqual(self.run_job(state=state,status=status)[0],0)
