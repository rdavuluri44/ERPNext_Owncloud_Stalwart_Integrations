"""Photo store calls for the mobile app (P74). Everything goes through ERPNext (owner, 24 November 2026): the
person signs in once; ERPNext checks their site membership (custom_hr's rule) and the store's own Drive
account reads and writes the project's Drive space. Nobody deletes a work photo (owner).
"""
import re

import frappe
from frappe.utils import cint

from erpnext_drive_integrations.custom_hr.access import require_user, self_sites, site_ids
from erpnext_drive_integrations.custom_hr.service import decode_photo, moment
from erpnext_drive_integrations.drive_store import drive

KINDS = ('Progress', 'Hindrance', 'Incident', 'Other')
PAGE = 30
PREVIEW_PX = 256


def allowed_sites(user):
    """Sites whose photos the person may add and see: the same membership attendance uses."""
    return set(site_ids(user)) | set(self_sites(user))


def require_photo_site(site, user):
    if site not in allowed_sites(user):
        frappe.throw('You do not have access to this site.', frappe.PermissionError)
    return frappe.get_doc('Field Site', site)


def project_space(project):
    """The project's Drive space, created on first use."""
    existing = frappe.db.get_value('Drive Project Space', {'project': project}, 'space_id')
    if existing:
        return existing
    label = frappe.db.get_value('Project', project, 'project_name') or project
    # ponytail: two first uploads of a project at the same moment can create two spaces; the second record is
    # refused (unique project) and its empty space stays unused. Add a lock if projects start in bulk.
    space_id = drive.create_space(label, f'Work photos of project {project} (ERPNext)')
    doc = frappe.get_doc({'doctype': 'Drive Project Space', 'project': project, 'space_id': space_id})
    doc.flags.drive_store = True
    doc.insert(ignore_permissions=True)
    return space_id


@frappe.whitelist(methods=['POST'])
def upload_photo(payload):
    """Add one photo to its project's Drive folder (site / date). A retry with the same `client_id` returns the
    same record; nothing is written twice."""
    user = require_user()
    p = frappe.parse_json(payload) if isinstance(payload, str) else payload
    client_id = str(p.get('client_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', client_id):
        frappe.throw('Missing photo identifier. Take the photo again.')
    done = frappe.db.get_value('Drive Photo', {'client_id': client_id}, ['name', 'taken_by', 'site', 'path'], as_dict=True)
    if done:
        if done.taken_by != user or done.site != p.get('site'):
            frappe.throw('This photo identifier was already used.', frappe.PermissionError)
        return {'name': done.name, 'path': done.path}
    kind = p.get('kind') if p.get('kind') in KINDS else 'Other'
    site = require_photo_site(p.get('site'), user)
    if not site.project:
        frappe.throw('This site has no project, so its photos have no project folder.')
    content = decode_photo(p.get('photo'))  # checked and re-encoded: no hidden content, no EXIF
    taken = moment(p)
    gps = None
    if p.get('latitude') is not None and p.get('longitude') is not None:
        gps = {'latitude': float(p['latitude']), 'longitude': float(p['longitude']), 'accuracy_m': float(p.get('accuracy_m') or 0)}
    space_id = project_space(site.project)
    path = drive.photo_path(site.site_name, taken, kind, client_id)
    drive.ensure_folders(space_id, path.rsplit('/', 1)[0])
    file_id = drive.put_file(space_id, path, content)
    project_label = frappe.db.get_value('Project', site.project, 'project_name') or site.project
    tags = drive.photo_tags(project_label, site.site_name, kind, user, taken, gps, cint(p.get('from_gallery')), cint(p.get('offline')))
    tagged = 0
    if file_id:
        try:
            drive.set_tags(file_id, tags)
            tagged = 1
        except drive.DriveError:
            # ponytail: tags are also on the ERPNext record; a retry job comes if Drive tags turn out flaky.
            frappe.log_error(title='Drive store: photo tags not set')
    doc = frappe.get_doc({
        'doctype': 'Drive Photo', 'client_id': client_id, 'project': site.project, 'site': site.name, 'kind': kind,
        'space_id': space_id, 'path': path, 'file_id': file_id, 'taken_at': taken, 'taken_by': user,
        'latitude': gps and gps['latitude'], 'longitude': gps and gps['longitude'], 'accuracy_m': gps and gps['accuracy_m'],
        'from_gallery': cint(p.get('from_gallery')), 'captured_offline': cint(p.get('offline')), 'tagged': tagged,
        'tags': '\n'.join(tags), 'remarks': str(p.get('remarks') or '')[:500],
    })
    doc.flags.drive_store = True
    doc.insert(ignore_permissions=True)
    return {'name': doc.name, 'path': path}


@frappe.whitelist(methods=['GET'])
def photos(site=None, project=None, kind=None, day=None, start=0):
    """Photos the person may see, newest first, 30 at a time; filters: site, project, type, day."""
    user = require_user()
    sites = allowed_sites(user)
    if site:
        sites &= {site}
    if project:
        sites &= set(frappe.get_all('Field Site', filters={'project': project}, pluck='name'))
    if not sites:
        return []
    filters = {'site': ['in', sorted(sites)]}
    if kind in KINDS:
        filters['kind'] = kind
    if day:
        filters['taken_at'] = ['between', [f'{day} 00:00:00', f'{day} 23:59:59']]
    return frappe.get_all('Drive Photo', filters=filters, order_by='taken_at desc', start=cint(start), page_length=PAGE,
                          fields=['name', 'project', 'site', 'kind', 'taken_at', 'taken_by', 'from_gallery', 'captured_offline',
                                  'latitude', 'longitude', 'accuracy_m', 'remarks'])


def project_folders(project, user):
    """The top folders of a project's space the person may open: one per site of theirs in that project (the
    first part of `drive.photo_path`). Other sites' folders stay closed, as in `photos`."""
    mine = allowed_sites(user)
    rows = frappe.get_all('Field Site', filters={'project': project}, fields=['name', 'site_name']) if project else []
    folders = {drive.safe_part(r.get('site_name')) for r in rows if r.get('name') in mine}
    if not folders:
        frappe.throw('You do not have access to this project.', frappe.PermissionError)
    return folders


def require_folder(path, folders):
    """A path inside one of the person's site folders (the space's top level is listed separately)."""
    if path.split('/', 1)[0] not in folders:
        frappe.throw('You do not have access to this folder.', frappe.PermissionError)


def asked_path(path):
    try:
        return drive.clean_path(path)
    except ValueError:
        frappe.throw('This folder path is not valid.')


@frappe.whitelist(methods=['GET'])
def files(project, path=''):
    """Folders and files in a project's Drive space (everything through ERPNext, owner); empty until the
    project's space exists (its first photo creates it)."""
    folders = project_folders(project, require_user())
    path = asked_path(path)
    if path:
        require_folder(path, folders)
    space_id = frappe.db.get_value('Drive Project Space', {'project': project}, 'space_id')
    if not space_id:
        return []
    entries = drive.list_folder(space_id, path)
    return entries if path else [e for e in entries if e['folder'] and e['name'] in folders]


@frappe.whitelist(methods=['GET'])
def file(project, path, size='full'):
    """An image from a project's Drive space (preview or full). Other file types open on the web for now."""
    folders = project_folders(project, require_user())
    path = asked_path(path)
    require_folder(path, folders)
    if not drive.is_image(path):
        frappe.throw('Only photos and images open in the app for now.')
    space_id = frappe.db.get_value('Drive Project Space', {'project': project}, 'space_id')
    if not space_id:
        frappe.throw('This project has no Drive space yet.')
    content = drive.read_file(space_id, path, PREVIEW_PX if size == 'preview' else None)
    frappe.local.response.update({'type': 'binary', 'filename': path.rsplit('/', 1)[-1], 'filecontent': content,
                                  'display_content_as': 'inline'})


@frappe.whitelist(methods=['GET'])
def photo(name, size='preview'):
    """One photo's image (a 256 px preview, or the full photo), after the same access check."""
    user = require_user()
    doc = frappe.db.get_value('Drive Photo', name, ['site', 'space_id', 'path'], as_dict=True)
    if not doc or doc.site not in allowed_sites(user):
        frappe.throw('You do not have access to this photo.', frappe.PermissionError)
    content = drive.read_file(doc.space_id, doc.path, PREVIEW_PX if size != 'full' else None)
    frappe.local.response.update({'type': 'binary', 'filename': doc.path.rsplit('/', 1)[-1], 'filecontent': content,
                                  'display_content_as': 'inline'})
