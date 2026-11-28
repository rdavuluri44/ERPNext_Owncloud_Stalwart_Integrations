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


# What never goes into a message, whoever asks: Google would see it.
NEVER = ('doctype', 'docname', 'site', 'site_label')


def message(token, kind, about=None, mark=None, extra=None):
    """One FCM v1 data message, high priority so a sleeping phone wakes. Data only: the phone writes the visible
    text from the kind and from `about` (a short code for the sort of thing: `payment`, `leave`), so no person's
    name, amount, document type, document ID or site name ever leaves the server. `mark` names the thing for this
    one phone without saying what it is: the phone asks the server what it stands for, as the signed-in person.
    A newer alert of the same kind and sort replaces an older one that is still queued. `extra` is for the
    notification service's own short fields (what the message needs, a count); it can never replace the fields
    above or bring in a document or a site."""
    data = {'v': '2', 'kind': kind}
    for field, value in (('about', about), ('mark', mark)):
        if value:
            data[field] = str(value)
    for field, value in (extra or {}).items():
        if str(field) not in NEVER:
            data.setdefault(str(field), str(value))
    return {'message': {'token': token, 'data': data,
                        'android': {'priority': 'HIGH', 'ttl': '3600s', 'collapse_key': f"{kind}:{about or ''}"}}}


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
