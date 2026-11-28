"""Request IDs on the app's saves (P103; owner, 27 November 2026).

The app gives every save one request ID, which is also its tracking number. The calls that make a record already
keep it on the record (`request_id` and `capture_id` on Field Attendance Entry). The calls that only change one
(`submit`, `self_check_out`, `verify`, `review`, `review_many`) had none and were repeat-safe only through the
record's state. `once` gives them the same promise: a call sent twice with the same ID is carried out once, and
the second answer is the first one.

`status` is "what happened to my request ID": for the signed-in person's own IDs only.

A call without an ID works as before, so an older app is not turned away.
"""
import json
import re

import frappe

LOG = 'App Request'
ENTRY = 'Field Attendance Entry'
ID = re.compile(r'[A-Za-z0-9_-]{16,80}')
KEEP_DAYS = 90
USED = 'This request identifier is already used.'


def clean(request_id):
    """The ID as text; None when the caller sent none; refused when it is not an ID."""
    if request_id is None or request_id == '':
        return None
    if not isinstance(request_id, str) or not ID.fullmatch(request_id):
        frappe.throw('The request identifier is not valid.')
    return request_id


def answer(result, request_id, repeated=False):
    """The call's own answer with the ID in it. A list (`review_many`) is wrapped, since a list has no place for it."""
    out = dict(result) if isinstance(result, dict) else {'results': result}
    out['request_id'] = request_id
    if repeated:
        out['repeated'] = True
    return out


def _earlier(method, request_id, user):
    """The answer the first call with this ID got, or None when there was none. An ID belongs to the person and
    the call that used it first: nobody learns from an ID what someone else did."""
    row = frappe.db.get_value(LOG, {'request_id': request_id}, ['user', 'method', 'outcome'], as_dict=True)
    if not row:
        return None
    if row.user != user or row.method != method or not row.outcome:
        frappe.throw(USED)
    return answer(json.loads(row.outcome), request_id, repeated=True)


def once(method, request_id, action, reference=None):
    """Carry `action` out once for this request ID and answer the same on every repeat.

    The ID is written down first, inside the same transaction as the action: a second call that arrives while the
    first still runs waits for it at the unique index and then gets the first answer. If the action is refused,
    nothing is kept, so the same ID can be sent again after the person corrected what was wrong."""
    request_id = clean(request_id)
    if not request_id:
        return action()
    user = frappe.session.user
    earlier = _earlier(method, request_id, user)
    if earlier:
        return earlier
    row = frappe.get_doc(dict(doctype=LOG, request_id=request_id, user=user, method=method))
    row.flags.field_service = True
    try:
        row.insert(ignore_permissions=True)
    except frappe.UniqueValidationError:
        frappe.clear_messages()
        return _earlier(method, request_id, user) or frappe.throw(USED)
    result = action()
    values = {'outcome': json.dumps(result, default=str)}
    if reference:
        values.update(reference_doctype=ENTRY, reference_name=reference)
    frappe.db.set_value(LOG, row.name, values, update_modified=False)
    return answer(result, request_id)


def status(request_id):
    """What happened to one of the signed-in person's own request IDs: the calls made with it and their answers, and
    the attendance entry it made, with its state now and how many notices were written about it. An ID of someone
    else, or one that never arrived, answers an empty list: the two cannot be told apart."""
    user = frappe.session.user
    request_id = clean(request_id)
    if not request_id:
        frappe.throw('Give the request identifier.')
    found = []
    row = frappe.db.get_value(LOG, {'request_id': request_id, 'user': user},
                              ['method', 'creation', 'reference_name', 'outcome'], as_dict=True)
    if row:
        found.append({'what': 'call', 'method': row.method, 'at': str(row.creation), 'entry': row.reference_name,
                      'answer': json.loads(row.outcome) if row.outcome else None,
                      'state_now': row.reference_name and frappe.db.get_value(ENTRY, row.reference_name, 'state')})
    entry = frappe.db.get_value(ENTRY, {'request_id': request_id, 'captured_by': user},
                                ['name', 'state', 'revision', 'creation'], as_dict=True)
    if entry:
        found.append({'what': 'record', 'entry': entry.name, 'at': str(entry.creation), 'state_now': entry.state,
                      'revision': entry.revision,
                      'notices': frappe.db.count('Notification Log', {'document_type': ENTRY,
                                                                      'document_name': entry.name})})
    return {'request_id': request_id, 'found': found}


def purge():
    """Daily: an ID is kept 90 days. After that a repeat would be carried out again, and its record's state decides."""
    frappe.db.delete(LOG, {'creation': ['<', frappe.utils.add_days(frappe.utils.now_datetime(), -KEEP_DAYS)]})
