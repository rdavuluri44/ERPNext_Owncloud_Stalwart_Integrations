"""The notification service's rules (P108): kinds, channels, one record per person and thing, and reminders.

Offline; the rules have no Frappe in them. Owner, 27 November 2026: approvals alert round the clock; a waiting
decision is reminded every 4 hours, but only between 07:00 and 21:00; alerts carry no content.
"""
import datetime
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from erpnext_drive_integrations.notifications import rules  # noqa: E402


def at(day, hour, minute=0):
    return datetime.datetime(2026, 11, day, hour, minute)


class Channels(unittest.TestCase):
    def test_a_decision_goes_to_the_phone_and_information_to_chat(self):
        self.assertEqual(rules.channels(rules.DECIDE, has_phone=True, in_chat=True), ['phone'])
        self.assertEqual(rules.channels(rules.INFORM, has_phone=True, in_chat=True), ['chat'])

    def test_mail_is_the_fallback(self):
        self.assertEqual(rules.channels(rules.DECIDE, has_phone=False, in_chat=True), ['mail'],
                         'a decision is never put into chat')
        self.assertEqual(rules.channels(rules.INFORM, has_phone=True, in_chat=False), ['mail'],
                         'information never rings the phone')

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(rules.RuleError):
            rules.channels('urgent', True, True)

    def test_one_record_per_kind_thing_and_person(self):
        key = rules.record_key(rules.DECIDE, 'Leave Application', 'HR-LAP-0001', 'a@example.net')
        self.assertEqual(key, rules.record_key(rules.DECIDE, 'Leave Application', 'HR-LAP-0001', 'a@example.net'))
        self.assertNotEqual(key, rules.record_key(rules.DECIDE, 'Leave Application', 'HR-LAP-0001', 'b@example.net'))
        self.assertNotEqual(key, rules.record_key(rules.INFORM, 'Leave Application', 'HR-LAP-0001', 'a@example.net'))
        for bad in (('decide', '', 'x', 'u'), ('decide', 'd', '', 'u'), ('decide', 'd', 'x', ''), ('other', 'd', 'x', 'u')):
            with self.assertRaises(rules.RuleError):
                rules.record_key(*bad)


class Reminders(unittest.TestCase):
    def test_four_hours_after_it_started_waiting_inside_the_day(self):
        self.assertEqual(rules.next_reminder(at(27, 9)), at(27, 13))
        self.assertEqual(rules.next_reminder(at(27, 16, 59)), at(27, 20, 59))

    def test_what_starts_at_night_is_first_reminded_at_seven(self):
        self.assertEqual(rules.next_reminder(at(27, 22)), at(28, 7), '22:00 + 4 h is 02:00: wait for 07:00')
        self.assertEqual(rules.next_reminder(at(27, 23, 30)), at(28, 7))
        self.assertEqual(rules.next_reminder(at(28, 1)), at(28, 7))

    def test_four_hours_later_wins_when_that_is_after_seven(self):
        self.assertEqual(rules.next_reminder(at(28, 5)), at(28, 9), 'whichever is later: 07:00 or four hours on')
        self.assertEqual(rules.next_reminder(at(28, 3)), at(28, 7))

    def test_nothing_is_sent_from_nine_in_the_evening(self):
        self.assertEqual(rules.next_reminder(at(27, 17)), at(28, 7), '17:00 + 4 h is 21:00, which is already night')
        self.assertEqual(rules.next_reminder(at(27, 18)), at(28, 7))

    def test_after_a_reminder_the_next_one_is_four_hours_on(self):
        self.assertEqual(rules.next_reminder(at(27, 22), last_reminder=at(28, 7)), at(28, 11))
        self.assertEqual(rules.next_reminder(at(27, 22), last_reminder=at(28, 19)), at(29, 7))

    def test_due_only_inside_the_day_and_only_when_the_time_has_come(self):
        started = at(27, 9)
        self.assertFalse(rules.reminder_due(at(27, 12, 59), started))
        self.assertTrue(rules.reminder_due(at(27, 13), started))
        self.assertTrue(rules.reminder_due(at(27, 20, 59), started), 'late, but still before 21:00')
        self.assertFalse(rules.reminder_due(at(27, 21), started), 'never at or after 21:00')
        self.assertFalse(rules.reminder_due(at(28, 6, 59), started), 'never before 07:00')
        self.assertTrue(rules.reminder_due(at(28, 7), started))
        self.assertFalse(rules.reminder_due(at(27, 14), started, last_reminder=at(27, 13)), 'already reminded')

    def test_a_reminder_says_how_many_wait_and_for_how_long_and_nothing_else(self):
        summary = rules.reminder_summary(at(28, 15, 30), [at(28, 9), at(28, 7, 15), at(27, 22)])
        self.assertEqual(summary, {'count': 3, 'oldest_hours': 17})
        self.assertEqual(set(summary), {'count', 'oldest_hours'}, 'no reference to any single thing')
        self.assertIsNone(rules.reminder_summary(at(28, 15), []))

    def test_decided_things_are_kept_ninety_days_and_waiting_ones_always(self):
        now = at(28, 12)
        self.assertFalse(rules.expired(now, None), 'what still waits is never removed')
        self.assertFalse(rules.expired(now, now - datetime.timedelta(days=90)))
        self.assertTrue(rules.expired(now, now - datetime.timedelta(days=90, minutes=1)))


if __name__ == '__main__':
    unittest.main()
