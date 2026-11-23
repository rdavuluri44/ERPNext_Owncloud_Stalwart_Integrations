"""Server-side checkout clock. Never approves attendance or changes payroll status."""
from datetime import timedelta
import frappe
from frappe.utils import get_datetime, now_datetime


def due_time(check_in):
    return get_datetime(check_in) + timedelta(hours=12)


def close_due_entries():
    now = now_datetime()
    rows = frappe.get_all('Field Attendance Entry', filters={
        'state': ['in', ['Submitted', 'Approved']], 'attendance_status': 'Present',
        'auto_checkout_at': ['<=', now], 'check_out_time': ['is', 'not set'],
    }, pluck='name', order_by='auto_checkout_at', limit=500)
    closed = 0
    for name in rows:
        frappe.db.sql('SELECT name FROM `tabField Attendance Entry` WHERE name=%s FOR UPDATE', name)
        doc = frappe.get_doc('Field Attendance Entry', name)
        if (doc.state not in ('Submitted', 'Approved') or doc.attendance_status != 'Present'
                or not doc.check_in_time or doc.check_out_time):
            continue
        due = due_time(doc.check_in_time)
        if due > now:
            continue
        # Store the scheduled time, not the later scheduler execution time.
        frappe.db.set_value('Field Attendance Entry', name, {
            'auto_checkout_at': due, 'check_out_time': due, 'checkout_method': 'Automatic (12 hours)',
        })
        closed += 1
    return closed
