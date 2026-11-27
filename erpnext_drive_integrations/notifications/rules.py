"""What the notification service decides (P108): pure rules, no Frappe, no network.

Every message the system sends to a person has a **kind** (owner, 27 November 2026):

* ``decide``: something waits for this person's decision. It appears in the app's Inbox and alerts the phone,
  round the clock. While it still waits, the person is reminded every 4 hours, but only between 07:00 and 21:00.
* ``inform``: the person only needs to know. It goes to their read-only Notices room in chat, and by mail when
  they cannot be reached there.

Alerts carry no content: a kind and a reference, never a name, an amount or a text.
"""
import datetime

DECIDE, INFORM = 'decide', 'inform'
KINDS = (DECIDE, INFORM)
REMINDER_EVERY = datetime.timedelta(hours=4)
DAY_START, DAY_END = datetime.time(7, 0), datetime.time(21, 0)
KEEP_DAYS = 90


class RuleError(ValueError):
    pass


def channels(kind, has_phone, in_chat):
    """Where one message goes, in order. Mail is the fallback when the person cannot be reached otherwise."""
    if kind == DECIDE:
        return ['phone'] if has_phone else ['mail']
    if kind == INFORM:
        return ['chat'] if in_chat else ['mail']
    raise RuleError('A message is either "decide" or "inform".')


def record_key(kind, doctype, name, user):
    """One record per person and thing, so a repeated event is sent once."""
    if kind not in KINDS or not (doctype and name and user):
        raise RuleError('A message needs a kind, what it is about and who it is for.')
    return '%s|%s|%s|%s' % (kind, doctype, name, user)


def _in_day(moment):
    return DAY_START <= moment.time() < DAY_END


def _next_day_start(moment):
    start = datetime.datetime.combine(moment.date(), DAY_START)
    return start if moment <= start else start + datetime.timedelta(days=1)


def next_reminder(waiting_since, last_reminder=None):
    """When the next reminder for a waiting decision is due (local time of the site).

    Four hours after it started waiting or after the last reminder; if that falls outside 07:00 to 21:00, at the
    next 07:00. So something that starts waiting at 22:00 is first reminded at 07:00, and something that starts at
    05:00 at 09:00 (four hours later, which is later than 07:00)."""
    due = (last_reminder or waiting_since) + REMINDER_EVERY
    return due if _in_day(due) else _next_day_start(due)


def reminder_due(now, waiting_since, last_reminder=None):
    """Whether to remind now. Never outside 07:00 to 21:00, whatever the clock of the job does."""
    return _in_day(now) and now >= next_reminder(waiting_since, last_reminder)


def reminder_summary(now, waiting_sinces):
    """What a reminder says for one person: how many decisions still wait and the oldest one's whole hours.
    The phone writes the sentence; no reference to any single thing is sent."""
    if not waiting_sinces:
        return None
    oldest = min(waiting_sinces)
    return {'count': len(waiting_sinces), 'oldest_hours': max(0, int((now - oldest).total_seconds() // 3600))}


def expired(now, resolved_at):
    """A record of something already decided is kept 90 days, then removed. What still waits is never removed."""
    return resolved_at is not None and now - resolved_at > datetime.timedelta(days=KEEP_DAYS)
