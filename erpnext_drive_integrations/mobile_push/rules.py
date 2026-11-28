"""Mobile push without Frappe: what a message holds, and when a phone's push address is dead. Tested directly.
What is sent, and when, is the notification service's (`notifications/rules.py`)."""
import hashlib
import re

_TOKEN = re.compile(r'[A-Za-z0-9_:\-]{100,4096}')


def valid_token(token):
    """An FCM registration token: long, URL-safe text. Anything else is refused before it is stored."""
    return isinstance(token, str) and bool(_TOKEN.fullmatch(token))


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def message(token, kind, doctype=None, docname=None, site=None, site_label=None, extra=None):
    """One FCM v1 data message, high priority so a sleeping phone wakes. Data only: the phone writes the visible
    text from the kind, the document type and the site, so no person's name, amount or other business data ever
    leaves the server. A newer alert of the same kind and type replaces an older one that is still queued.
    `extra` is for the notification service's own short fields (what the message needs, a count); it can never
    replace the fields above."""
    data = {'v': '1', 'kind': kind}
    for field, value in (('doctype', doctype), ('docname', docname), ('site', site), ('site_label', site_label)):
        if value:
            data[field] = str(value)
    for field, value in (extra or {}).items():
        data.setdefault(str(field), str(value))
    return {'message': {'token': token, 'data': data,
                        'android': {'priority': 'HIGH', 'ttl': '3600s', 'collapse_key': f"{kind}:{doctype or ''}"}}}


def dead_token(status, body):
    """FCM v1 says the app was removed from that phone or the address was replaced: stop sending to it. A 400 is
    not taken as dead, so a mistake in the message can never switch off every phone."""
    if status == 404:
        return True
    error = (body or {}).get('error') or {}
    return any(d.get('errorCode') == 'UNREGISTERED' for d in error.get('details') or [] if isinstance(d, dict))


def recipients(users, actor):
    """Real people only, never the person whose action caused the alert, each once. Pass no actor when the
    message is also for the person who acted (an alert to remove from their own phone)."""
    return sorted({u for u in users if u and u not in ('Guest', 'Administrator', actor)})
