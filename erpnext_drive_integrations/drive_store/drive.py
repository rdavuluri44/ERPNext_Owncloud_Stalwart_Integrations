"""Drive (ownCloud Infinite Scale) for the photo store (P74): one dedicated Drive account, its app token, and the
few Drive calls the store needs (project spaces, folders, files, tags, previews).

The token is an oCIS app token (auth-app service), the same kind the document worker uses: valid 30 days,
renewed 5 days before it ends, checked against the account before it is used, then the old one is revoked.
Setup (private, never in Git): site config `drive_store` = {"url": internal Drive URL, "account": the account's
e-mail, "account_id": its Drive user id, "token": the first app token from the CLI enrollment}. Renewed tokens
live in the site's private folder (mode 600) and take precedence. No token value is ever logged or returned.
"""
import base64
import datetime
import json
import xml.etree.ElementTree as ET
import os
import re
import time
import urllib.parse
import uuid

import frappe
import requests

RENEW_BEFORE_S = 5 * 86400
TIMEOUT_S = 60
LABEL = 'ERP photo store'


class DriveError(Exception):
    """Drive refused or could not be reached; the message never contains a credential."""


def settings():
    conf = frappe.conf.get('drive_store') or {}
    if not (conf.get('url') and conf.get('account') and conf.get('account_id')):
        frappe.throw('The photo store is not set up on this site yet.')
    return conf


def _credential_path():
    return frappe.get_site_path('private', 'drive_store', 'credential.json')


def _read_saved():
    try:
        with open(_credential_path(), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _persist(value):
    path = _credential_path()
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    tmp = f'{path}.{uuid.uuid4().hex}.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump(value, f)
    os.replace(tmp, path)


def _basic(conf, token):
    return 'Basic ' + base64.b64encode(f"{conf['account']}:{token}".encode()).decode()


def _timestamp(value):
    return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()


def needs_renewal(expires_at, now):
    """True when the token ends within five days (or its end is unknown)."""
    return not expires_at or expires_at - now < RENEW_BEFORE_S


def _call(method, url, auth, **kw):
    try:
        res = requests.request(method, url, headers={'Authorization': auth, **kw.pop('headers', {})}, timeout=TIMEOUT_S, **kw)
    except requests.RequestException as e:
        raise DriveError(f'Drive could not be reached ({type(e).__name__}).') from None
    if res.status_code >= 400:
        raise DriveError(f'Drive answered {res.status_code} for {method} {urllib.parse.urlsplit(url).path}.')
    return res


def token():
    """The current app token, renewed first when it ends within five days."""
    conf = settings()
    saved = _read_saved() or {'token': conf.get('token'), 'expires_at': None, 'hash': None}
    if not saved.get('token'):
        frappe.throw('The photo store has no Drive credential yet.')
    if needs_renewal(saved.get('expires_at'), time.time()):
        # ponytail: two workers renewing at the same moment leave one extra token that expires by itself.
        saved = renew(conf, saved)
    return saved['token']


def renew(conf, old):
    """Create a new 30-day token with the current one, check it is the same account, keep it, revoke the old."""
    base = conf['url'].rstrip('/')
    manager = base + '/auth-app/tokens'
    created = _call('POST', manager + '?' + urllib.parse.urlencode({'expiry': '720h', 'label': LABEL}), _basic(conf, old['token'])).json()
    auth = _basic(conf, created['token'])
    me = _call('GET', base + '/graph/v1.0/me', auth).json()
    if me.get('id') != conf['account_id']:
        raise DriveError('The renewed Drive credential belongs to another account; it is not used.')
    listed = _call('GET', manager, auth).json() or []
    match = next((t for t in listed if t.get('label') == LABEL and t.get('created_date') == created.get('created_date')), None)
    saved = {'token': created['token'], 'expires_at': _timestamp(created['expiration_date']), 'hash': match.get('token') if match else None}
    _persist(saved)  # keep and verify the new one before the old one goes
    if old.get('hash') and old['hash'] != saved['hash']:
        try:
            _call('DELETE', manager + '?' + urllib.parse.urlencode({'token': old['hash']}), auth)
        except DriveError:
            frappe.log_error('Previous photo-store app token could not be revoked; it expires by itself.', 'Drive store')
    return saved


def renew_if_due():
    """Daily: renew the token in time even when nobody uploads (scheduler)."""
    if not (frappe.conf.get('drive_store') or {}).get('url'):
        return
    try:
        token()
    except Exception:
        frappe.log_error(title='Drive store credential renewal failed')


def _auth():
    return _basic(settings(), token())


def _dav(space_id, path):
    quoted = '/'.join(urllib.parse.quote(part) for part in path.split('/'))
    return settings()['url'].rstrip('/') + f'/dav/spaces/{urllib.parse.quote(space_id)}/{quoted}'


def create_space(name, description):
    """A Drive project space (the store's account becomes its manager)."""
    url = settings()['url'].rstrip('/') + '/graph/v1.0/drives'
    body = _call('POST', url, _auth(), json={'name': name[:255], 'description': description[:255], 'driveType': 'project'}).json()
    return body['id']


def ensure_folders(space_id, folder):
    """Create each level of `folder` in the space (an existing folder is fine)."""
    auth, path = _auth(), ''
    for part in folder.split('/'):
        path = f'{path}/{part}' if path else part
        try:
            _call('MKCOL', _dav(space_id, path), auth)
        except DriveError as e:
            if ' 405 ' not in str(e):  # 405: the folder already exists
                raise


def put_file(space_id, path, content, content_type='image/jpeg'):
    """Write a file; returns Drive's file id (header OC-FileId)."""
    res = _call('PUT', _dav(space_id, path), _auth(), data=content, headers={'Content-Type': content_type})
    return res.headers.get('OC-FileId') or ''


def set_tags(file_id, tags):
    url = settings()['url'].rstrip('/') + '/graph/v1.0/extensions/org.libregraph/tags'
    _call('PUT', url, _auth(), json={'resourceId': file_id, 'tags': tags})


def read_file(space_id, path, preview=None):
    """The file's bytes, or a Drive preview `preview` px wide (thumbnail service)."""
    params = {'preview': 1, 'x': preview, 'y': preview, 'a': 1} if preview else None
    return _call('GET', _dav(space_id, path), _auth(), params=params).content


_PROPFIND = (b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/>'
             b'<d:getlastmodified/><d:getcontenttype/></d:prop></d:propfind>')


def list_folder(space_id, path):
    """The folders and files directly inside `path` of the space (Depth 1), folders first, then by name."""
    body = _call('PROPFIND', _dav(space_id, path), _auth(), data=_PROPFIND,
                 headers={'Depth': '1', 'Content-Type': 'application/xml'}).content
    return parse_listing(body, path)


def parse_listing(body, path):
    ns = {'d': 'DAV:'}
    out = []
    for response in ET.fromstring(body).findall('d:response', ns)[1:]:  # the first answer is the folder itself
        href = urllib.parse.unquote(response.findtext('d:href', default='', namespaces=ns)).rstrip('/')
        name = href.rsplit('/', 1)[-1]
        prop = response.find('d:propstat/d:prop', ns)
        if prop is None or not name:
            continue
        folder = prop.find('d:resourcetype/d:collection', ns) is not None
        entry_path = f'{path}/{name}' if path else name
        out.append({'name': name, 'path': entry_path, 'folder': folder,
                    'size': int(prop.findtext('d:getcontentlength', default='0', namespaces=ns) or 0),
                    'modified': prop.findtext('d:getlastmodified', default='', namespaces=ns),
                    'type': prop.findtext('d:getcontenttype', default='', namespaces=ns)})
    return sorted(out, key=lambda e: (not e['folder'], e['name'].lower()))


def clean_path(path):
    """A path inside a space as asked by the app: no '.' or '..' parts, no backslashes, no leading slash."""
    parts = [p for p in str(path or '').replace('\\', '/').split('/') if p]
    if any(p in ('.', '..') for p in parts):
        raise ValueError('path')
    return '/'.join(parts)


IMAGE_TYPES = ('.jpg', '.jpeg', '.png', '.webp', '.gif')


def is_image(path):
    return path.lower().endswith(IMAGE_TYPES)


# ---- pure rules (unit-tested without Frappe or Drive) ----
_SAFE = re.compile(r'[^A-Za-z0-9 _.-]+')


def safe_part(text, fallback='site'):
    """A folder or file name part: letters, digits, space, _ . - only; never empty, never '.' or '..'."""
    cleaned = _SAFE.sub('-', str(text or '')).strip(' .-')[:80]
    return cleaned or fallback


def photo_path(site_label, taken, kind, client_id):
    """`<site>/<YYYY-MM-DD>/<HHMMSS>-<kind>-<id>.jpg`: one fixed path per photo, so a retry writes the same file.
    The whole `client_id` is in the name: the upload refuses an id already used, so no new upload can reach the
    path of an existing photo (Drive's PUT overwrites, and nobody may replace a work photo)."""
    return f"{safe_part(site_label)}/{taken:%Y-%m-%d}/{taken:%H%M%S}-{safe_part(kind, 'photo')}-{client_id}.jpg"


def photo_tags(project_label, site_label, kind, user, taken, gps, from_gallery, offline):
    """The tags written in Drive (commas are not allowed in a tag)."""
    clean = lambda v: str(v).replace(',', ' ').strip()[:100]
    tags = [f'Project: {clean(project_label)}', f'Site: {clean(site_label)}', f'Type: {clean(kind)}',
            f'Taken by: {clean(user)}', f'Taken: {taken:%Y-%m-%d %H:%M}']
    if gps:
        tags.append(f"GPS: {gps['latitude']:.5f} {gps['longitude']:.5f} ±{round(gps['accuracy_m'])} m")
    if from_gallery:
        tags.append('From gallery')
    if offline:
        tags.append('Captured offline')
    return tags
