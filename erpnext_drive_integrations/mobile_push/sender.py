"""Send alerts to phones through Google's Firebase Cloud Messaging (FCM HTTP v1), as a background job.

The service-account key is a file on the server, named in site_config as `mobile_push_fcm_key_file`; it is never
in the repository. Without it nothing is sent and nothing fails.
"""
import json
import time

import frappe
import jwt
import requests

from erpnext_drive_integrations.mobile_push import rules

SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
CACHE_KEY = 'mobile_push_fcm_access'


def configured():
    return bool(frappe.conf.get('mobile_push_fcm_key_file'))


def _key():
    with open(frappe.conf.get('mobile_push_fcm_key_file'), encoding='utf-8') as f:
        return json.load(f)


def _access_token(key):
    """A short-lived Google token signed with the key (RS256), kept until a minute before it expires."""
    cached = frappe.cache.get_value(CACHE_KEY)
    if cached and cached[1] > time.time() + 60:
        return cached[0]
    now = int(time.time())
    assertion = jwt.encode({'iss': key['client_email'], 'scope': SCOPE, 'aud': TOKEN_URL, 'iat': now, 'exp': now + 3600},
                           key['private_key'], algorithm='RS256')
    response = requests.post(TOKEN_URL, data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                              'assertion': assertion}, timeout=10)
    response.raise_for_status()
    body = response.json()
    life = int(body.get('expires_in', 3600))
    frappe.cache.set_value(CACHE_KEY, [body['access_token'], now + life], expires_in_sec=life)
    return body['access_token']


def send(users, kind, doctype, docname=None, site=None, site_label=None):
    """Queue one alert for these people; it goes out after the current transaction commits, so a save is never
    slowed down or undone by Google."""
    users = rules.recipients(users, frappe.session.user)
    if users and configured():
        frappe.enqueue('erpnext_drive_integrations.mobile_push.sender.deliver', queue='short', enqueue_after_commit=True,
                       users=users, kind=kind, doctype=doctype, docname=docname, site=site, site_label=site_label)


def deliver(users, kind, doctype, docname=None, site=None, site_label=None):
    """Background job: one data message per phone of these people. A dead address is switched off; other failures
    are logged without the address or the message."""
    devices = frappe.get_all('Mobile Device', filters={'user': ['in', users], 'enabled': 1}, fields=['name', 'token'])
    if not devices or not configured():
        return
    key = _key()
    url = f"https://fcm.googleapis.com/v1/projects/{key['project_id']}/messages:send"
    headers = {'Authorization': f'Bearer {_access_token(key)}'}
    for device in devices:
        response = requests.post(url, json=rules.message(device.token, kind, doctype, docname, site, site_label),
                                 headers=headers, timeout=10)
        if response.ok:
            continue
        try:
            body = response.json()
        except ValueError:
            body = None
        if rules.dead_token(response.status_code, body):
            frappe.db.set_value('Mobile Device', device.name, 'enabled', 0, update_modified=False)
        else:
            # ponytail: no retry; a missed alert still shows in the app's Inbox and bell. Add a retry queue if needed.
            frappe.log_error('Mobile push not delivered', f'FCM answered {response.status_code} for {doctype} ({kind}).')
