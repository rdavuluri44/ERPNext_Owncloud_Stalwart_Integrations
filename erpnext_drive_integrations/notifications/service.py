"""The notification service (P108): the one function through which the system tells a person something.

`notify` writes one record per person and thing and sends the message after the save commits: a decision to the
phone, information to the person's Notices room in chat, mail when neither reaches them. `resolve` closes the
records of something that was decided and tells the phones to remove its alert. The hourly job reminds people of
what still waits (07:00 to 21:00 only) and closes records the events missed; the daily job removes closed
records after 90 days. The decisions themselves are in `rules.py`, without Frappe.
"""
import datetime

import frappe
from frappe import _

from erpnext_drive_integrations.notifications import rules

RECORD = 'Notification Record'
JOB = 'erpnext_drive_integrations.notifications.service.'
FIELDS = ['name', 'user', 'kind', 'reason', 'reference_doctype', 'reference_name', 'state', 'site', 'waiting_since',
          'deadline', 'channel', 'last_reminder', 'reminders', 'open_key']


def _feature(name):
    return (frappe.conf.get('cloud_features') or {}).get(name, True) is not False


def _open(**more):
    return dict({'open_key': ['is', 'set']}, **more)


def _sender():
    from erpnext_drive_integrations.mobile_push import sender
    return sender if _feature('mobile_push') and sender.configured() else None


def _mark(user, doctype, name):
    """This person's mark for this thing (rules.mark), keyed with the site's own encryption key."""
    from frappe.utils.password import get_encryption_key
    return rules.mark(get_encryption_key(), user, doctype, name)


def notify(users, kind, doctype, name, reason=None, state=None, site=None, deadline=None, text=None):
    """Tell these people about one thing, once each.

    kind: `decide` (it waits for the person) or `inform` (they only need to know). reason: why, in one word the
    phone app knows (`approval`, `verify`, `returned`). state: the state the thing is in now; a decision is closed
    when the thing leaves it, and two notices about the same thing are told apart by it. text: for `inform` only,
    what the person reads in chat or mail; a decision never carries a text. The person whose action caused the
    message gets none. Returns the names of the records made."""
    now, made, waits = frappe.utils.now_datetime(), [], kind == rules.DECIDE
    for user in sorted({u for u in users if u and u not in ('Guest', 'Administrator', frappe.session.user)}):
        key = rules.record_key(kind, doctype, name, user)
        again = {'open_key': key} if waits else {'record_key': key, 'state': state or ''}
        if frappe.db.exists(RECORD, again):
            continue
        try:
            made.append(frappe.get_doc(dict(
                doctype=RECORD, user=user, kind=kind, reason=reason, reference_doctype=doctype, reference_name=name,
                state=state or '', site=site, waiting_since=now, deadline=deadline, record_key=key,
                open_key=key if waits else None, resolved_at=None if waits else now)).insert(ignore_permissions=True).name)
        except frappe.UniqueValidationError:
            continue  # the same event arrived twice at the same moment; the other one sends it
    if made:
        frappe.enqueue(JOB + 'deliver', queue='short', enqueue_after_commit=True, records=made, text=text)
    return made


def deliver(records, text=None):
    """Background job: send each new record by the channel the rules give, and write on the record how it went."""
    for name in records:
        record = frappe.db.get_value(RECORD, name, FIELDS, as_dict=True)
        if not record or record.channel or (record.kind == rules.DECIDE and not record.open_key):
            continue  # gone, sent already, or decided before it went out
        channel = _send(record, text)
        if channel:
            frappe.db.set_value(RECORD, name, {'channel': channel, 'sent_at': frappe.utils.now_datetime()},
                                update_modified=False)


def _send(record, text):
    if record.kind == rules.DECIDE:
        sender = _sender()
        if sender and sender.deliver(
                [record.user], record.reason or 'approval', rules.about(record.reference_doctype),
                {record.user: _mark(record.user, record.reference_doctype, record.reference_name)},
                rules.phone_fields(record.kind)):
            return rules.PHONE
        if record.reason == 'approval' and _workflow(record.reference_doctype, 'send_email_alert'):
            return rules.OWN_MAIL  # the workflow mails its approvers itself; a second mail would say the same
        return _mail(record, None)
    return rules.CHAT if text and _chat(record, text) else _mail(record, text)


def _chat(record, text):
    if not _feature('chat_rooms'):
        return False
    from erpnext_drive_integrations.chat_rooms import sync
    try:
        return bool(sync.notify(record.user, record.name, text))
    except Exception:
        frappe.log_error('Notice not posted to chat', f'The chat server refused a notice about {record.reference_doctype}.')
        return False


def _mail(record, text):
    """The fallback. A decision's mail says only that something waits, with the link; a notice carries its text."""
    address = frappe.db.get_value('User', {'name': record.user, 'enabled': 1}, 'email')
    if not address:
        return None
    link = frappe.utils.get_url_to_form(record.reference_doctype, record.reference_name)
    if record.kind == rules.DECIDE:
        subject, body = _('Something waits for your decision'), _('Something waits for your decision.')
    else:
        subject, body = _('A notice for you'), frappe.utils.escape_html(text or _('There is a notice for you.'))
    frappe.sendmail(recipients=[address], subject=subject,
                    message=f'<p>{body}</p><p><a href="{link}">{_("Open it")}</a></p>')
    return rules.MAIL


def _workflow(doctype, field):
    """One field of the document type's active workflow, or None when it has none."""
    return frappe.db.get_value('Workflow', {'document_type': doctype, 'is_active': 1}, field)


def resolve(doctype, name, current_state=None):
    """The thing was decided, changed state or is gone: close its waiting records and remove the alert from the
    phones. Records made for the state it is in now stay (`current_state`); with None, all are closed."""
    rows = frappe.get_all(RECORD, filters=_open(reference_doctype=doctype, reference_name=name), fields=FIELDS)
    return _close([r for r in rows if rules.moved_on(r.state, current_state)], doctype, name)


def _close(rows, doctype, name):
    now = frappe.utils.now_datetime()
    for row in rows:
        frappe.db.set_value(RECORD, row.name, {'resolved_at': now, 'open_key': None}, update_modified=False)
    phones = [row.user for row in rows if row.channel == rules.PHONE]
    sender = phones and _sender()
    if sender:
        # Content-free: each phone gets its own mark and removes that alert. Also for the person who decided it.
        sender.send(phones, rules.REMOVE, marks={user: _mark(user, doctype, name) for user in phones},
                    include_actor=True)
    return len(rows)


def forget(user):
    """A disabled person waits for nothing: close their records, send nothing."""
    now = frappe.utils.now_datetime()
    for name in frappe.get_all(RECORD, filters=_open(user=user), pluck='name'):
        frappe.db.set_value(RECORD, name, {'resolved_at': now, 'open_key': None}, update_modified=False)


def state_now(doctype, name):
    """The state a waiting record is compared with: the attendance entry's state or the document's workflow state;
    None when the document or its workflow is gone."""
    field = 'state' if doctype == rules.ATTENDANCE else _workflow(doctype, 'workflow_state_field')
    if not field or not frappe.db.exists(doctype, name):
        return None
    return frappe.db.get_value(doctype, name, field) or ''


def heal():
    """Close what the events missed (a state changed without a save event, a deleted document). Only records the
    service's own triggers made: another module that asks for a decision closes it itself with `resolve`."""
    things = {}
    for row in frappe.get_all(RECORD, filters=_open(kind=rules.DECIDE), fields=FIELDS):
        if row.reference_doctype == rules.ATTENDANCE or row.reason == 'approval':
            things.setdefault((row.reference_doctype, row.reference_name), []).append(row)
    closed = 0
    for (doctype, name), rows in things.items():
        current = state_now(doctype, name)
        closed += _close([r for r in rows if rules.moved_on(r.state, current)], doctype, name)
    return closed


def remind():
    """Hourly: one reminder per person for the decisions that still wait for them, every 4 hours and only between
    07:00 and 21:00 (the site's time). The phone gets a count and the oldest wait in hours, nothing else."""
    heal()
    sender = _sender()
    if not sender:
        return 0
    now, reminded = frappe.utils.now_datetime(), 0
    rows = frappe.get_all(RECORD, filters=_open(kind=rules.DECIDE, channel=rules.PHONE), fields=FIELDS)
    for user, summary in rules.due_reminders(now, rows).items():
        if not sender.deliver([user], rules.REMINDER, extra=summary):
            continue
        reminded += 1
        for row in rows:
            if row.user == user:
                frappe.db.set_value(RECORD, row.name, {'last_reminder': now, 'reminders': (row.reminders or 0) + 1},
                                    update_modified=False)
    return reminded


def purge():
    """Daily: closed records older than 90 days are removed. What still waits is never removed."""
    cutoff = frappe.utils.now_datetime() - datetime.timedelta(days=rules.KEEP_DAYS)
    frappe.db.delete(RECORD, {'resolved_at': ['<', cutoff]})


def waiting(user):
    rows = frappe.get_all(RECORD, filters=_open(kind=rules.DECIDE, user=user), fields=FIELDS)
    items = rules.waiting_items(rows, lambda row: _mark(user, row['reference_doctype'], row['reference_name']))
    return dict(rules.waiting_summary(frappe.utils.now_datetime(), rows), items=items)
