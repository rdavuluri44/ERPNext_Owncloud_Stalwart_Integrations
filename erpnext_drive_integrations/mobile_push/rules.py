"""Mobile push without Frappe: what is sent, when, and when a phone's push address is dead. Tested directly."""
import hashlib
import re

ATTENDANCE = 'Field Attendance Entry'
# Owner, 26 November 2026: alert only what waits for the person and what was returned to them, not every approval.
ATTENDANCE_KINDS = {'Submitted': 'approval', 'Verified': 'approval', 'Pending Verification': 'verify', 'Returned': 'returned'}
_TOKEN = re.compile(r'[A-Za-z0-9_:\-]{100,4096}')


def valid_token(token):
    """An FCM registration token: long, URL-safe text. Anything else is refused before it is stored."""
    return isinstance(token, str) and bool(_TOKEN.fullmatch(token))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def attendance_kind(state):
    """Why an attendance notification is worth an alert, or None (approved, draft: nothing waits)."""
    return ATTENDANCE_KINDS.get(state)


def message(token, kind, doctype, docname=None, site=None, site_label=None):
    """One FCM v1 data message, high priority so a sleeping phone wakes. Data only: the phone writes the visible
    text from the kind, the document type and the site, so no person's name, amount or other business data ever
    leaves the server. A newer alert of the same kind and type replaces an older one that is still queued."""
    data = {'v': '1', 'kind': kind, 'doctype': doctype}
    for field, value in (('docname', docname), ('site', site), ('site_label', site_label)):
        if value:
            data[field] = str(value)
    return {'message': {'token': token, 'data': data,
                        'android': {'priority': 'HIGH', 'ttl': '3600s', 'collapse_key': f'{kind}:{doctype}'}}}


def dead_token(status, body):
    """FCM v1 says the app was removed from that phone or the address was replaced: stop sending to it. A 400 is
    not taken as dead, so a mistake in the message can never switch off every phone."""
    if status == 404:
        return True
    error = (body or {}).get('error') or {}
    return any(d.get('errorCode') == 'UNREGISTERED' for d in error.get('details') or [] if isinstance(d, dict))


def recipients(users, actor):
    """Real people only, never the person whose action caused the alert, each once."""
    return sorted({u for u in users if u and u not in ('Guest', 'Administrator', actor)})
