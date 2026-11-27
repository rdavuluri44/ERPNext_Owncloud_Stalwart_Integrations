"""Face capture queue for field team attendance (P95).

A supervisor (or assigned engineer) sends a team photograph **without choosing the worker**: typically a capture
taken offline and uploaded later, or one the supervisor could not settle on the spot. The server validates the place
and time once, keeps the photograph privately, and tries to recognise the worker among those the supervisor may
record on that shift:

* a confident match is recorded and submitted at once in the supervisor's name, through the same rules as a capture
  with a chosen worker (`service.capture`, `service.submit_entry`), and goes to the site's approvers as usual;
* anything else (uncertain, nobody recognised, no clear face, the face engine off, a rule that needs a person such as
  a machine allocation) waits as **Needs review** for the site's approvers (the project manager), who pick the worker
  or reject the capture with a reason.

The queue's own copy of the photograph is removed as soon as the capture is recorded (the attendance entry keeps
its copy); rejected captures keep theirs for RETENTION_DAYS days and then lose it.
"""
import json
import re

import frappe
from frappe.utils import add_days, cint, now_datetime

from erpnext_drive_integrations.custom_hr import domain, face, face_queue_rules as rules, face_service, service
from erpnext_drive_integrations.custom_hr.access import require_site, require_user, site_access, supervised_users

QUEUE = 'Field Face Capture'
RETENTION_DAYS = rules.RETENTION_DAYS
EVIDENCE = ('latitude', 'longitude', 'accuracy_m', 'gps_captured_at', 'captured_at', 'captured_offline',
            'device_captured_at', 'clock_offset_s')


def _save(doc):
    doc.flags.field_service = True
    return doc.insert(ignore_permissions=True) if doc.is_new() else doc.save(ignore_permissions=True)


def _lock(name):
    if not frappe.db.sql('SELECT name FROM `tabField Face Capture` WHERE name=%s FOR UPDATE', (name,)):
        frappe.throw('This capture was not found.')
    return frappe.get_doc(QUEUE, name)


def _photo_names(doc):
    """Every File record of this capture. Frappe adds a second record for the photo field when the capture is saved
    (found in the first live run on the test site), so there are usually two."""
    return frappe.get_all('File', filters={'attached_to_doctype': QUEUE, 'attached_to_name': doc.name},
                          pluck='name', order_by='creation asc')


def _photo_file(doc):
    names = _photo_names(doc)
    return frappe.get_doc('File', names[0]) if names else None


def _drop_photo(doc):
    """Remove every record of the queue's own copy of the photograph (the attendance entry, when there is one, keeps
    its own records; Frappe deletes the stored file only when no other record still points to it)."""
    for name in _photo_names(doc):
        file = frappe.get_doc('File', name)
        file.flags.field_service = True
        file.delete(ignore_permissions=True)
    doc.photo = None


def _summary(doc):
    return {'name': doc.name, 'state': doc.state, 'decision': doc.decision, 'employee': doc.employee,
            'entry': doc.entry, 'note': doc.note}


def _recognise(doc, photo, user):
    """(decision, employee, candidates, note). Never raises: a capture that cannot be recognised waits for a person."""
    from erpnext_drive_integrations.custom_hr import face_service
    from erpnext_drive_integrations.custom_hr.face_engine import EngineMissing, load
    try:
        engine = load(face_service.config())
    except EngineMissing:
        return 'none', None, [], 'Face recognition is switched off on this site.'
    try:
        probe = engine.embed(photo)
    except ValueError as error:
        return 'none', None, [], f'No single clear face in the photograph ({error}).'
    employees = face_service.roster_for(doc.site, doc.shift, user)
    roster, stale = face_service.templates_of(employees, str(engine.model_id)) if employees else ({}, [])
    try:
        result = face.identify(probe, roster, face_service.rules())
    except domain.RuleError as error:
        return 'none', None, [], str(error)
    names = dict(frappe.get_all('Employee', filters={'name': ['in', [e for e, _ in result['candidates']] or ['']]},
                                fields=['name', 'employee_name'], as_list=True))
    candidates = [{'employee': e, 'employee_name': names.get(e, e), 'score': s} for e, s in result['candidates']]
    missing = len(set(employees) - set(roster) - set(stale))
    note = rules.roster_note(len(employees), missing, len(stale))
    return result['decision'], result['employee'], candidates, note


def _record(doc, employee, work_mode='Not applicable', asset=None, remarks=''):
    """Record and submit the capture for `employee` in the capturing supervisor's name. Raises on any rule."""
    file = _photo_file(doc)
    if not file:
        frappe.throw('The photograph of this capture is no longer available.')
    evidence = {field: doc.get(field) for field in EVIDENCE}
    evidence['photo'] = file.get_content()
    data = dict(site=doc.site, shift=doc.shift, employee=employee, request_id=doc.capture_id, capture_id=doc.capture_id,
                attendance_status='Present', work_mode=work_mode or 'Not applicable', asset=asset or None,
                remarks=remarks or '')
    entry = service.capture(data, actor=doc.captured_by, evidence=evidence)
    service.submit_entry(entry['name'], actor=doc.captured_by)
    return entry['name']


def add(payload):
    face_service.require_enabled()
    user = require_user()
    site = require_site(payload.get('site'))
    if not (site_access(site.name, 'Supervisor', user) or supervised_users(site.name, user)):
        frappe.throw('You cannot record attendance at this site.', frappe.PermissionError)
    capture_id = str(payload.get('capture_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', capture_id):
        frappe.throw('Missing capture identifier. Reopen the capture screen.')
    known = frappe.db.get_value(QUEUE, {'capture_id': capture_id}, ['name', 'captured_by'], as_dict=True)
    if known:  # a retry of the same upload
        if known.captured_by != user:
            frappe.throw('This capture identifier is already used.', frappe.PermissionError)
        return _summary(frappe.get_doc(QUEUE, known.name))
    photo = service.decode_photo(payload.get('photo'))
    lat, lon, accuracy = service.fail_rule(
        domain.validate_location, payload.get('latitude'), payload.get('longitude'), payload.get('accuracy_m'),
        site.latitude, site.longitude, float(site.radius_m or 0), float(site.maximum_accuracy_m or 200))
    captured_at, gps_time = service.moment(payload, with_gps=True)
    details = service.shift_details(site, payload.get('shift'), captured_at)
    doc = frappe.get_doc(dict(doctype=QUEUE, state='Needs review', site=site.name, shift=details['name'],
                              attendance_date=details['attendance_date'], captured_by=user, captured_at=captured_at,
                              capture_id=capture_id, latitude=lat, longitude=lon, accuracy_m=accuracy,
                              gps_captured_at=gps_time))
    service.mark_offline(doc, payload)
    _save(doc)
    from frappe.utils.file_manager import save_file
    doc.photo = save_file(f'face-{doc.name}.jpg', photo, QUEUE, doc.name, is_private=1).file_url

    doc.decision, matched, candidates, doc.note = _recognise(doc, photo, user)
    doc.candidates = json.dumps(candidates)
    _save(doc)
    if matched:
        frappe.db.savepoint('face_queue_record')
        try:
            doc.entry = _record(doc, matched)
            doc.state, doc.employee = 'Matched', matched
            _drop_photo(doc)
        except (frappe.ValidationError, frappe.PermissionError) as error:
            frappe.db.rollback(save_point='face_queue_record')
            frappe.clear_messages()
            doc.note = rules.join_notes(doc.note, f'Recognised as {matched}, but not recorded: {error}')
        _save(doc)
    if doc.state == 'Needs review':
        for approver in set(frappe.get_all('Field Site Member', filters={'parent': doc.site, 'team_role': 'Approver',
                                                                         'enabled': 1}, pluck='user')):
            if approver != user:
                service.notify(approver, 'A face capture needs your review', doc)
    return _summary(doc)


def _rows(filters, limit):
    fields = ['name', 'state', 'site', 'shift', 'attendance_date', 'captured_by', 'captured_at', 'captured_offline',
              'accuracy_m', 'photo', 'decision', 'candidates', 'note', 'employee', 'entry', 'remarks']
    rows = frappe.get_all(QUEUE, filters=filters, fields=fields, order_by='captured_at asc', limit=limit)
    for row in rows:
        row.candidates = json.loads(row.candidates or '[]')
    return rows


def pending(site):
    """Captures waiting for the project manager at this site."""
    face_service.require_enabled()
    require_user()
    require_site(site, 'Approver')
    return _rows({'site': site, 'state': 'Needs review'}, 200)


def mine(site):
    """The signed-in supervisor's own captures of the last three days, so they can see what became of them."""
    face_service.require_enabled()
    user = require_user()
    require_site(site)
    return _rows({'site': site, 'captured_by': user, 'captured_at': ['>=', add_days(now_datetime(), -3)]}, 200)


def _decide(name, user):
    face_service.require_enabled()
    doc = _lock(name)
    require_site(doc.site, 'Approver')
    if doc.state != 'Needs review':
        frappe.throw('This capture has already been decided.')
    if doc.captured_by == user:
        frappe.throw('Another approver must decide your own capture.', frappe.PermissionError)
    return doc


def resolve(name, employee, work_mode='Not applicable', asset=None, remarks=''):
    user = require_user()
    doc = _decide(name, user)
    if frappe.db.get_value('Employee', employee, 'user_id') == user:
        frappe.throw('You cannot record your own attendance.', frappe.PermissionError)
    remarks = str(remarks or '').strip()[:2000]
    doc.entry = _record(doc, employee, work_mode, asset, remarks)
    doc.state, doc.employee, doc.remarks = 'Resolved', employee, remarks
    doc.resolved_by, doc.resolved_at = user, now_datetime()
    _drop_photo(doc)
    _save(doc)
    return _summary(doc)


def reject(name, reason):
    user = require_user()
    doc = _decide(name, user)
    reason = str(reason or '').strip()
    if not reason:
        frappe.throw('Say why this capture is rejected.')
    doc.state, doc.remarks = 'Rejected', reason[:2000]
    doc.resolved_by, doc.resolved_at = user, now_datetime()
    _save(doc)
    service.notify(doc.captured_by, 'A face capture was rejected', doc)
    return _summary(doc)


def purge_rejected():
    """Daily: rejected captures lose their photograph after RETENTION_DAYS days; the record and the reason stay."""
    cutoff = add_days(now_datetime(), -cint(RETENTION_DAYS))
    for name in frappe.get_all(QUEUE, filters={'state': 'Rejected', 'resolved_at': ['<', cutoff],
                                              'photo': ['is', 'set']}, pluck='name', limit=500):
        doc = frappe.get_doc(QUEUE, name)
        _drop_photo(doc)
        _save(doc)
