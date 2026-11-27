"""Face enrolment, identification and deletion for field team attendance (P95).

* Enrolment: HR, a Field Attendance Manager, an approver of the worker's site, or the worker's own supervisor or
  assigned engineer enrols a field worker from several angles after checking their identity document and recording
  their consent. Only encrypted templates are kept (site
  encryption key); the photographs are not stored. Re-enrolment replaces the templates.
* Identification: a supervisor (or assigned engineer) sends one photograph for a site and shift; it is compared only
  with the workers that person may record on that shift. The result is a match, a short list of candidates, or none.
* Deletion: templates are deleted permanently (not kept in Deleted Documents) when consent is withdrawn, when the
  worker leaves, or when the employee record is deleted; the consent record stays as evidence, marked ended.
"""
import json

import frappe
from frappe.utils import now_datetime
from frappe.utils.password import decrypt, encrypt

from erpnext_drive_integrations.custom_hr import domain, face
from erpnext_drive_integrations.custom_hr.access import is_manager, require_site, require_user, site_access, supervised_users
from erpnext_drive_integrations.custom_hr.face_engine import EngineMissing, load

ENROLMENT = 'Field Face Enrolment'
CONSENT = 'Biometric Consent'
HR_ROLES = {'HR Manager', 'HR User'}
MAXIMUM_PHOTOS = face.MAXIMUM_ANGLES


def config():
    return frappe.conf.get('custom_hr_face') or {}


def enabled():
    """Face attendance runs only where the site config says `custom_hr_face` -> `enabled: true` (owner, 27 November
    2026: off on production until the legal opinion and the owner's decision). Withdrawing consent and deleting face
    data never depend on it."""
    return config().get('enabled') is True


def require_enabled():
    """First line of every face function that takes in or uses a face; nothing is read or stored before it."""
    if not enabled():
        frappe.throw('Face attendance is switched off on this site.', frappe.PermissionError)


def rules():
    try:
        return face.settings(config().get('thresholds'))
    except domain.RuleError as error:
        frappe.throw(str(error))


def engine():
    try:
        return load(config())
    except EngineMissing as error:
        frappe.throw(str(error))


def checked(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except domain.RuleError as error:
        frappe.throw(str(error))


def worker_site(employee):
    return frappe.db.get_value('Field Worker Assignment', {'employee': employee}, 'site')


def worker_supervisor(employee):
    return frappe.db.get_value('Field Worker Assignment', {'employee': employee}, 'supervisor')


def may_enrol(user, site, supervisor):
    """The project manager (approver) of the worker's site, or the worker's own team (owner, 27 November 2026): their
    responsible supervisor, or the engineer assigned to that supervisor at that site. Not other teams' supervisors."""
    if not site:
        return False
    if site_access(site, 'Approver', user):
        return True
    if supervisor and supervisor == user and site_access(site, 'Supervisor', user):
        return True
    return bool(supervisor) and supervisor in supervised_users(site, user)


def require_enroller(employee, user):
    """HR, a Field Attendance Manager, or someone `may_enrol` allows for the worker's site and team."""
    if is_manager(user) or HR_ROLES & set(frappe.get_roles(user)):
        return
    if not may_enrol(user, worker_site(employee), worker_supervisor(employee)):
        frappe.throw('Only HR, the project manager of the worker’s site, or the worker’s own supervisor or engineer '
                     'can enrol or remove a face.', frappe.PermissionError)


def embed(model, photo):
    from erpnext_drive_integrations.custom_hr.service import decode_photo
    try:
        return model.embed(decode_photo(photo))
    except ValueError:
        frappe.throw('No single clear face was found in a photograph. Capture it again in good light.')


def save_doc(doc):
    doc.flags.field_service = True
    doc.flags.ignore_permissions = True
    doc.save() if not doc.is_new() else doc.insert()
    return doc


def delete_templates(employee):
    if frappe.db.exists(ENROLMENT, employee):
        frappe.delete_doc(ENROLMENT, employee, ignore_permissions=True, delete_permanently=True,
                          flags=frappe._dict(field_service=True))
        return True
    return False


def end_consent(employee, status, reason):
    for name in frappe.get_all(CONSENT, filters={'employee': employee, 'status': 'Active'}, pluck='name'):
        doc = frappe.get_doc(CONSENT, name)
        doc.status, doc.ended_at, doc.end_reason = status, now_datetime(), reason[:500]
        save_doc(doc)


def enrol(employee, photos, consent):
    require_enabled()
    user = require_user()
    worker = frappe.db.get_value('Employee', employee, ['name', 'employee_name', 'status'], as_dict=True)
    if not worker or worker.status != 'Active':
        frappe.throw('Choose an active employee.')
    require_enroller(worker.name, user)
    agreement = checked(face.validate_consent, consent)
    if not isinstance(photos, list) or not photos or len(photos) > MAXIMUM_PHOTOS:
        frappe.throw(f'Send between 1 and {MAXIMUM_PHOTOS} photographs.')
    model, limits = engine(), rules()
    templates = checked(face.validate_enrolment, [embed(model, p) for p in photos], limits)
    end_consent(worker.name, 'Replaced', 'Enrolled again')
    record = save_doc(frappe.get_doc(dict(doctype=CONSENT, employee=worker.name, employee_name=worker.employee_name,
                                          status='Active', accepted_at=now_datetime(), recorded_by=user,
                                          identity_checked_by=user, **agreement)))
    doc = frappe.get_doc(ENROLMENT, worker.name) if frappe.db.exists(ENROLMENT, worker.name) else frappe.new_doc(ENROLMENT)
    doc.update(dict(employee=worker.name, employee_name=worker.employee_name, site=worker_site(worker.name),
                    model_id=str(model.model_id), angle_count=len(templates), consent=record.name,
                    enrolled_by=user, enrolled_at=now_datetime(), templates=encrypt(json.dumps(templates))))
    save_doc(doc)
    return {'employee': worker.name, 'angles': len(templates), 'consent': record.name}


def roster_for(site, shift, user):
    """Workers this person may record on this site and shift, as the team screen shows them."""
    from erpnext_drive_integrations.custom_hr.api import team
    return [row.employee for row in team(site, shift)['workers'] if row.get('can_capture')]


def templates_of(employees, model_id):
    roster, stale = {}, []
    for row in frappe.get_all(ENROLMENT, filters={'employee': ['in', employees]}, fields=['employee', 'model_id', 'templates']):
        if row.model_id != model_id:
            stale.append(row.employee)
            continue
        roster[row.employee] = json.loads(decrypt(row.templates))
    return roster, stale


def identify(site, shift, photo):
    require_enabled()
    user = require_user()
    require_site(site)
    if not (site_access(site, 'Supervisor', user) or supervised_users(site, user)):
        frappe.throw('You cannot record attendance at this site.', frappe.PermissionError)
    employees = roster_for(site, shift, user)
    model, limits = engine(), rules()
    probe = embed(model, photo)
    roster, stale = templates_of(employees, str(model.model_id)) if employees else ({}, [])
    result = checked(face.identify, probe, roster, limits)
    names = dict(frappe.get_all('Employee', filters={'name': ['in', [e for e, _ in result['candidates']] or ['']]},
                                fields=['name', 'employee_name'], as_list=True))
    return {'decision': result['decision'], 'employee': result['employee'],
            'candidates': [{'employee': e, 'employee_name': names.get(e, e), 'score': s} for e, s in result['candidates']],
            'not_enrolled': len(set(employees) - set(roster) - set(stale)), 'needs_re_enrolment': len(stale)}


def withdraw(employee, reason):
    user = require_user()
    require_enroller(employee, user)
    reason = str(reason or '').strip()
    if not reason:
        frappe.throw('Record why the worker withdrew consent.')
    removed = delete_templates(employee)
    end_consent(employee, 'Withdrawn', reason)
    return {'employee': employee, 'templates_deleted': removed}


def on_employee_update(doc, method=None):
    if doc.status != 'Active' and frappe.db.exists(ENROLMENT, doc.name):
        delete_templates(doc.name)
        end_consent(doc.name, 'Ended', f'Employee status {doc.status}')


def on_employee_trash(doc, method=None):
    delete_templates(doc.name)
    end_consent(doc.name, 'Ended', 'Employee record deleted')
