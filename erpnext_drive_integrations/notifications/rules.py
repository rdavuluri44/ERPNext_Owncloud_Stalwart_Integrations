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


# What follows is used by the service (service.py), still without Frappe.
PHONE, CHAT, MAIL, OWN_MAIL = 'phone', 'chat', 'mail', 'workflow mail'
REMOVE, REMINDER = 'remove', 'reminder'
ATTENDANCE = 'Field Attendance Entry'
# Why an attendance entry waits for someone, by its state (owner, 26 November 2026): to approve, to verify, or it
# was returned to the person who made it. Approved and draft entries wait for nobody.
ATTENDANCE_REASONS = {'Submitted': 'approval', 'Verified': 'approval', 'Pending Verification': 'verify',
                      'Returned': 'returned'}


def attendance_reason(state):
    return ATTENDANCE_REASONS.get(state)


def moved_on(record_state, current_state):
    """Whether the thing a record waits on has been decided: it is gone (no current state), or it is no longer in
    the state it was in when the record was made."""
    return current_state is None or (record_state or '') != (current_state or '')


def phone_fields(kind):
    """What a phone alert says beyond its reason: whether it needs a decision or only informs."""
    if kind not in KINDS:
        raise RuleError('A message is either "decide" or "inform".')
    return {'needs': kind}


def due_reminders(now, rows):
    """Who is reminded now, and with what. `rows` are the waiting decisions (user, waiting_since, last_reminder).
    One reminder per person for everything that waits for them, never more often than every 4 hours: counted from
    the person's last reminder, or from their oldest waiting decision when they were never reminded."""
    people = {}
    for row in rows:
        people.setdefault(row['user'], []).append(row)
    due = {}
    for user, own in people.items():
        last = max((r['last_reminder'] for r in own if r.get('last_reminder')), default=None)
        if reminder_due(now, min(r['waiting_since'] for r in own), last):
            due[user] = reminder_summary(now, [r['waiting_since'] for r in own])
    return due


def _stamp(moment):
    return moment.isoformat(sep=' ', timespec='seconds')


def _block(now, items):
    oldest = min(r['waiting_since'] for r in items)
    deadlines = [r['deadline'] for r in items if r.get('deadline')]
    return {'count': len(items), 'waiting_since': _stamp(oldest),
            'longest_wait_hours': max(0, int((now - oldest).total_seconds() // 3600)),
            'nearest_deadline': _stamp(min(deadlines)) if deadlines else None}


def waiting_summary(now, rows):
    """The numbers behind "what waits for me", for one person's waiting decisions. In total, per kind of thing
    (why it waits and what it is) and per site: how many, since when the oldest waits, and the nearest deadline
    when one is known. No names of documents or people."""
    empty = {'count': 0, 'waiting_since': None, 'longest_wait_hours': 0, 'nearest_deadline': None}
    if not rows:
        return dict(empty, kinds=[], sites=[])
    kinds, sites = {}, {}
    for row in rows:
        kinds.setdefault((row.get('reason') or '', row['reference_doctype']), []).append(row)
        if row.get('site'):
            sites.setdefault(row['site'], []).append(row)
    return dict(_block(now, rows),
                kinds=[dict(_block(now, items), reason=reason, doctype=doctype)
                       for (reason, doctype), items in sorted(kinds.items())],
                sites=[dict(_block(now, items), site=site) for site, items in sorted(sites.items())])
