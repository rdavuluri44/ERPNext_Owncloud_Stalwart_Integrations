"""Server-authoritative attendance and reassignment transactions. No client-supplied roles."""
import base64
import binascii
import hashlib
import io
import math
import re
import json
from datetime import datetime, time
import frappe
from frappe.utils import get_datetime, getdate, now_datetime, nowdate, cint
from erpnext_drive_integrations.custom_hr.access import require_user, require_site, require_manager, eligible_supervisor, site_access, is_manager, site_ids, self_sites
from erpnext_drive_integrations.custom_hr.access import approval_access, can_verify, supervised_users, verifier_for, has_membership, APPROVER
from erpnext_drive_integrations.custom_hr import domain


def fail_rule(fn,*args,**kwargs):
    try:return fn(*args,**kwargs)
    except domain.RuleError as exc:frappe.throw(str(exc))


def save(doc):
    doc.flags.field_service=True
    return doc.insert(ignore_permissions=True) if doc.is_new() else doc.save(ignore_permissions=True)


def key(employee,day,shift):
    return hashlib.sha256(f'{employee}|{day}|{shift}'.encode()).hexdigest()


def lock_doc(doctype,name):
    # Only fixed internal DocTypes reach this helper.
    frappe.db.sql(f'SELECT name FROM `tab{doctype}` WHERE name=%s FOR UPDATE',(name,))
    return frappe.get_doc(doctype,name)


def lock_employee(employee):
    if not frappe.db.sql('SELECT name FROM `tabEmployee` WHERE name=%s FOR UPDATE',(employee,)):
        frappe.throw('Employee not found.')
    doc=frappe.get_doc('Employee',employee)
    if doc.status!='Active':frappe.throw('This employee is not active.')
    return doc


def shift_details(site,shift,at=None):
    """The shift and its attendance date for a capture taken `at` (default now; offline captures pass their time)."""
    if shift not in (site.day_shift,site.night_shift):frappe.throw('Choose one of this site’s shifts.')
    d=frappe.get_doc('Shift Type',shift)
    def as_time(value):
        seconds=int(value.total_seconds()) if hasattr(value,'total_seconds') else None
        if seconds is not None:return time(seconds//3600,(seconds//60)%60,seconds%60)
        return get_datetime(f'2000-01-01 {value}').time()
    day=domain.shift_date(at or now_datetime(),as_time(d.start_time),as_time(d.end_time))
    return dict(name=d.name,start=as_time(d.start_time).strftime('%H:%M'),end=as_time(d.end_time).strftime('%H:%M'),attendance_date=str(day))


def assignment(employee,site=None,day=None,shift=None,lock=False):
    name=frappe.db.get_value('Field Worker Assignment',{'employee':employee},'name')
    if not name:frappe.throw('This worker has no responsible supervisor. Ask the attendance manager to assign them.')
    base=lock_doc('Field Worker Assignment',name) if lock else frappe.get_doc('Field Worker Assignment',name)
    if site and base.site!=site:frappe.throw('The worker has moved to another site. Refresh your team.')
    extra=None
    if day and shift:
        extra_name=frappe.db.get_value('Field Shift Allocation',{'allocation_key':key(employee,day,shift)},'name')
        if extra_name:extra=lock_doc('Field Shift Allocation',extra_name) if lock else frappe.get_doc('Field Shift Allocation',extra_name)
    effective=extra or base
    return base,extra,dict(supervisor=effective.supervisor,locked_by=base.locked_by or effective.locked_by,machine_required=bool(base.machine_required))


def notify(user,title,entry=None):
    frappe.get_doc(dict(doctype='Notification Log',subject=title,for_user=user,type='Alert',
        document_type=entry.doctype if entry else None,document_name=entry.name if entry else None)).insert(ignore_permissions=True)


def enroll_employee(employee,site,supervisor,machine_required=False,initial=False,locked=False):
    if not initial:require_manager()
    worker=lock_employee(employee)
    location=lock_doc('Field Site',site)
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(supervisor,))
    if not location.enabled or worker.company!=location.company or not eligible_supervisor(site,supervisor):
        frappe.throw('Choose an enabled supervisor at a site in the worker’s company.')
    if frappe.db.exists('Field Worker Assignment',{'employee':employee}):
        frappe.throw('The worker is already assigned. Use Move to supervisor instead.')
    actor=frappe.session.user
    doc=save(frappe.get_doc(dict(doctype='Field Worker Assignment',employee=employee,site=site,supervisor=supervisor,
        machine_required=cint(machine_required),locked_by=actor if locked else None,assigned_by=actor,effective_at=now_datetime())))
    event(employee,site,None,supervisor,'Ongoing',None,None,bool(locked),'Initial worker assignment')
    frappe.db.set_value('Employee',employee,{'custom_field_attendance_required':1,'custom_field_machine_required':cint(machine_required)},update_modified=False)
    notify(supervisor,'A worker was assigned to you',doc)
    return doc.name


def event(employee,site,previous,destination,scope,day,shift,locked,remarks):
    return save(frappe.get_doc(dict(doctype='Field Assignment Event',employee=employee,site=site,
        previous_supervisor=previous,new_supervisor=destination,changed_by=frappe.session.user,effective_at=now_datetime(),
        scope=scope,attendance_date=day,shift=shift,approver_locked=cint(locked),remarks=remarks)))


def transfer(employees,site,destination,scope,shift,remarks=''):
    user=require_user();lock_doc('Field Site',site);location=require_site(site)
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(destination,))
    details=shift_details(location,shift);day=details['attendance_date']
    if scope not in ('Ongoing','This shift'):frappe.throw('Choose Ongoing or This shift.')
    if not eligible_supervisor(site,destination):frappe.throw('Choose an enabled supervisor from this site.')
    is_approver=site_access(site,'Approver',user)
    employees=sorted(set(employees))
    if not employees or len(employees)>100:frappe.throw('Select between 1 and 100 workers.')
    moved=[]
    for employee in employees:
        lock_employee(employee)
        base,extra,effective=assignment(employee,site,day,shift,lock=True)
        fail_rule(domain.validate_transfer,user,effective['supervisor'],destination,is_approver,bool(base.locked_by),bool(extra and extra.locked_by))
        # A temporary assignee cannot alter the permanent team of another supervisor.
        if scope=='Ongoing' and not is_approver and base.supervisor!=user:
            frappe.throw('You can move this temporary worker for this shift only.')
        if scope=='Ongoing':
            # An approver's ongoing instruction supersedes remaining current/future exceptions.
            overrides=frappe.get_all('Field Shift Allocation',filters={'employee':employee,'attendance_date':['>=',day]},pluck='name')
            for name in overrides:
                override=lock_doc('Field Shift Allocation',name)
                if not is_approver and override.locked_by:frappe.throw('An approver has reserved this worker for a shift. Ask them to reassign.')
                override.supervisor=destination;override.locked_by=user if is_approver else None
                override.assigned_by=user;override.effective_at=now_datetime();save(override)
            base.supervisor=destination;base.locked_by=user if is_approver else None
            base.lock_reason=remarks if is_approver else '';base.assigned_by=user;base.effective_at=now_datetime();save(base)
        else:
            doc=extra or frappe.get_doc(dict(doctype='Field Shift Allocation',allocation_key=key(employee,day,shift),
                employee=employee,site=site,attendance_date=day,shift=shift))
            doc.supervisor=destination;doc.locked_by=user if is_approver else None;doc.assigned_by=user;doc.effective_at=now_datetime();save(doc)
        e=event(employee,site,effective['supervisor'],destination,scope,day if scope=='This shift' else None,
                shift if scope=='This shift' else None,is_approver,str(remarks or '')[:2000])
        notify(destination,f'Worker transferred to you: {employee}',e)
        moved.append(employee)
    return {'moved':moved,'scope':scope,'locked':is_approver}


def decode_photo(data):
    if not isinstance(data,str) or len(data)>4_000_000:frappe.throw('Capture a photograph smaller than 3 MB.')
    try:
        prefix,encoded=data.split(',',1)
        if prefix not in ('data:image/jpeg;base64','data:image/png;base64','data:image/webp;base64'):
            raise ValueError()
        raw=base64.b64decode(encoded,validate=True)
        from PIL import Image, ImageOps
        image=Image.open(io.BytesIO(raw))
        if image.width*image.height>20_000_000 or min(image.size)<100:raise ValueError()
        image.load();image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1280,1280))
        out=io.BytesIO();image.save(out,format='JPEG',quality=82)
        return out.getvalue()
    except (ValueError,binascii.Error,OSError):frappe.throw('The camera photograph is invalid. Please capture it again.')


def moment(data,with_gps=False):
    """Server-clock capture time (and GPS time) for a payload; offline payloads carry `offline`,
    `device_captured_at` (the phone's clock) and `clock_offset_s` (server minus phone, measured when last online)."""
    offline=bool(data.get('offline'))
    device=get_datetime(data.get('device_captured_at')) if offline and data.get('device_captured_at') else None
    offset=data.get('clock_offset_s',0) if offline else 0
    if not with_gps:return fail_rule(domain.corrected_time,now_datetime(),offline,device,offset)
    gps=get_datetime(data.get('gps_captured_at')) if data.get('gps_captured_at') else None
    return fail_rule(domain.capture_time,now_datetime(),gps,offline,device,offset)


def mark_offline(doc,data):
    offline=bool(data.get('offline'))
    doc.captured_offline=cint(offline)
    doc.device_captured_at=get_datetime(data.get('device_captured_at')) if offline else None
    doc.clock_offset_s=int(data.get('clock_offset_s') or 0) if offline else 0


def notify_approvers(doc,user,title='Attendance ready for review'):
    approvers=frappe.get_all('Field Site Member',filters={'parent':doc.site,'team_role':'Approver','enabled':1},pluck='user')
    for approver in set(approvers):
        if approver!=user:notify(approver,title,doc)


def capture(data,actor=None,evidence=None):
    """Record one worker's attendance. `actor` and `evidence` are for the face capture queue (face_queue.py) only:
    the capture is recorded in the name of the supervisor who took the photograph, with the photograph, place and
    time that were validated when the capture reached the server."""
    user=actor or require_user()
    site=require_site(data.get('site'))
    supervisor_access = site_access(site.name, 'Supervisor', user)
    verifier_access = site_access(site.name, 'Verifier', user)
    if not (supervisor_access or verifier_access):
        frappe.throw('You cannot record attendance at this site.', frappe.PermissionError)
    employee=data.get('employee');worker=lock_employee(employee)
    if worker.user_id==user:frappe.throw('Use your own check-in to record your attendance.')
    details=shift_details(site,data.get('shift'),evidence['captured_at'] if evidence else moment(data));day=details['attendance_date']
    base,extra,effective=assignment(employee,site.name,day,details['name'],lock=True)
    supervisor = effective['supervisor']
    can_capture_own_team = supervisor_access and supervisor == user
    can_capture_subteam = supervisor in supervised_users(site.name, user)
    request_id=str(data.get('request_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',request_id):frappe.throw('Missing request identifier. Reopen the capture screen.')
    existing=data.get('name') or frappe.db.get_value('Field Attendance Entry',{'attendance_key':key(employee,day,details['name'])},'name')
    capture_id=str(data.get('capture_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',capture_id):frappe.throw('Missing capture identifier. Reopen the capture screen.')
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
    if existing:
        doc=lock_doc('Field Attendance Entry',existing)
        if doc.captured_by!=user:frappe.throw('Another supervisor has already recorded this worker for the shift.')
        if (doc.employee,doc.site,doc.shift)!=(employee,site.name,details['name']):frappe.throw('The capture does not match the original worker, site and shift.')
        if doc.last_capture_id==capture_id:
            if doc.last_capture_digest!=digest:frappe.throw('A retry cannot change the capture. Refresh and try again.')
            return {'name':doc.name,'state':doc.state,'revision':doc.revision}
        effective['machine_required']=bool(doc.machine_required)
        if doc.state in ('Pending Verification','Submitted','Verified','Approved'):
            if doc.request_id==request_id:return {'name':doc.name,'state':doc.state}
            frappe.throw('Attendance has already been submitted for this worker and shift.')
        if doc.captured_by != doc.responsible_supervisor and (
                not can_capture_subteam or supervisor != doc.responsible_supervisor):
            frappe.throw('This worker is no longer on your assigned team.', frappe.PermissionError)
        if doc.captured_by == doc.responsible_supervisor and not supervisor_access:
            frappe.throw('You cannot edit this submission.', frappe.PermissionError)
        # Require revision match so a stale phone cannot overwrite a returned correction.
        if cint(data.get('revision'))!=doc.revision:frappe.throw('This record changed. Refresh before editing.')
    else:
        if not (can_capture_own_team or can_capture_subteam):
            frappe.throw('This worker is no longer assigned to you. Refresh your team.', frappe.PermissionError)
        if frappe.db.exists('Field Attendance Entry',{'request_id':request_id}):frappe.throw('This request identifier is already used.')
        doc=frappe.get_doc(dict(doctype='Field Attendance Entry',attendance_key=key(employee,day,details['name']),request_id=request_id,
            employee=employee,employee_name=worker.employee_name,site=site.name,project=site.project,company=worker.company,attendance_date=day,
            shift=details['name'],captured_by=user,responsible_supervisor=supervisor,captured_at=now_datetime(),revision=1,state='Draft',
            verification_required=bool(can_capture_subteam or verifier_for(site.name, supervisor))))
    status=data.get('attendance_status') or 'Present';mode=data.get('work_mode') or 'Not applicable';asset=data.get('asset') or None
    fail_rule(domain.validate_work_mode,effective['machine_required'],status,mode,asset,{r.asset for r in site.assets})
    remarks=str(data.get('remarks') or '').strip()
    if len(remarks)>2000:frappe.throw('Keep remarks under 2,000 characters.')
    if status=='Absent' and not remarks:frappe.throw('Add a reason when marking a worker absent.')
    photo=evidence['photo'] if evidence else decode_photo(data['photo']) if data.get('photo') else None
    if status=='Present' and not (photo or doc.photo):frappe.throw('Capture the worker’s photograph.')
    if evidence:
        for field in ('latitude','longitude','accuracy_m','gps_captured_at','captured_at','captured_offline','device_captured_at','clock_offset_s'):
            doc.set(field,evidence[field])
    elif photo or not existing:
        lat,lon,accuracy=fail_rule(domain.validate_location,data.get('latitude'),data.get('longitude'),data.get('accuracy_m'),
            site.latitude,site.longitude,float(site.radius_m or 0),float(site.maximum_accuracy_m or 200))
        captured_at,gps_time=moment(data,with_gps=True)
        doc.latitude=lat;doc.longitude=lon;doc.accuracy_m=accuracy;doc.gps_captured_at=gps_time;doc.captured_at=captured_at
        mark_offline(doc,data)
    doc.attendance_status=status;doc.work_mode=mode;doc.asset=asset;doc.remarks=remarks
    doc.machine_required=cint(effective['machine_required']);doc.state='Draft';doc.review_remarks=''
    doc.verified_by = doc.verified_at = doc.verification_method = None
    doc.last_capture_id=capture_id;doc.last_capture_digest=digest
    if existing:doc.revision+=1
    save(doc)
    if photo:
        from frappe.utils.file_manager import save_file
        attachment=save_file(f'field-{doc.name}-{doc.revision}.jpg',photo,'Field Attendance Entry',doc.name,is_private=1)
        doc.photo=attachment.file_url;save(doc)
    return {'name':doc.name,'state':doc.state,'revision':doc.revision}


def lock_entry_for_submission(name):
    # Capture also locks the employee before related attendance records.
    employee = frappe.db.get_value('Field Attendance Entry', name, 'employee')
    if not employee:
        frappe.throw('Attendance entry was not found.')
    frappe.db.sql('SELECT name FROM `tabEmployee` WHERE name=%s FOR UPDATE', (employee,))
    return lock_doc('Field Attendance Entry', name)


def submit_entry(name, actor=None):
    user = actor or require_user()  # `actor`: the face capture queue submits in the capturing supervisor's name
    doc = lock_entry_for_submission(name)
    engineer_capture = doc.captured_by != doc.responsible_supervisor
    role = 'Verifier' if engineer_capture else 'Supervisor'
    if doc.captured_by != user or doc.get('entry_type') == 'Self' or not site_access(doc.site, role, user):
        frappe.throw('This is not your submission.', frappe.PermissionError)
    if doc.state in ('Pending Verification', 'Submitted', 'Verified', 'Approved'):
        return {'name': doc.name, 'state': doc.state}
    if engineer_capture:
        _, _, effective = assignment(doc.employee, doc.site, doc.attendance_date, doc.shift, lock=True)
        if (effective['supervisor'] != doc.responsible_supervisor
                or doc.responsible_supervisor not in supervised_users(doc.site, user)):
            frappe.throw('This worker is no longer on your assigned team.', frappe.PermissionError)
    # A transfer does not erase a capture. The original supervisor can submit an existing draft;
    # creation/update still requires current assignment and original evidence is retained.
    if doc.attendance_status=='Present' and not doc.photo:frappe.throw('A photograph is required.')
    if doc.attendance_status == 'Present' and not doc.check_in_time:
        from datetime import timedelta
        doc.check_in_time = doc.captured_at
        doc.auto_checkout_at = get_datetime(doc.check_in_time) + timedelta(hours=12)
    elif doc.attendance_status == 'Absent':
        doc.check_in_time = doc.auto_checkout_at = doc.check_out_time = doc.checkout_method = None
    verifier = verifier_for(doc.site, doc.responsible_supervisor)
    doc.verification_required = bool(doc.verification_required or verifier or engineer_capture)
    doc.submitted_at = now_datetime()
    doc.verified_by = doc.verified_at = doc.verification_method = None
    if engineer_capture:
        mark_verified(doc, user, 'Engineer capture')
        save(doc)
        notify_approvers(doc, user)
    elif doc.verification_required:
        if doc.responsible_supervisor not in supervised_users(doc.site, verifier):
            frappe.throw('Assign an active engineer to this supervisor before submitting.')
        doc.state = 'Pending Verification'
        save(doc)
        notify(verifier, 'Attendance ready for verification', doc)
    else:
        doc.state = 'Submitted'
        save(doc)
        if not approve_without_review(doc):
            notify_approvers(doc, user)
    return {'name':doc.name,'state':doc.state}


def mark_verified(doc, user, method):
    doc.state = 'Verified'
    doc.verified_by = user
    doc.verified_at = now_datetime()
    doc.verification_method = method


def verify_entry(name, decision, remarks=''):
    user = require_user()
    doc = lock_doc('Field Attendance Entry', name)
    if not can_verify(doc, user):
        frappe.throw('Only the assigned engineer can verify this record.', frappe.PermissionError)
    if doc.state == 'Verified' and doc.verified_by == user and decision == 'Verify':
        return {'name': doc.name, 'state': doc.state}
    if doc.state != 'Pending Verification':
        frappe.throw('This record is not pending verification.')
    if decision not in ('Verify', 'Return'):
        frappe.throw('Choose Verify or Return.')
    remarks = review_remarks(remarks, decision)
    if decision == 'Verify':
        mark_verified(doc, user, 'Manual')
    else:
        doc.state = 'Returned'
    doc.review_remarks = remarks
    doc.reviewed_by = user
    doc.reviewed_at = now_datetime()
    doc.revision += 1
    save(doc)
    if decision == 'Verify':
        notify_approvers(doc, user)
    else:
        notify(doc.captured_by, 'Attendance returned for correction', doc)
    return {'name': doc.name, 'state': doc.state}


def ready_for_approval(doc):
    return doc.state == 'Verified' or (doc.state == 'Submitted' and not doc.verification_required)


def review_remarks(remarks, decision):
    remarks = str(remarks or '').strip()
    if len(remarks) > 2000:
        frappe.throw('Keep review remarks under 2,000 characters.')
    if decision == 'Return' and not remarks:
        frappe.throw('Explain what needs correcting.')
    return remarks


def self_capture(data):
    """An employee's own check-in: selfie, location inside the site's fence, server time (or a corrected offline
    time). It goes straight to the site's approvers; HR attendance is created only when one of them approves, or at
    once at a site that needs no approval (see approve_without_review)."""
    user=require_user()
    employee=frappe.db.get_value('Employee',{'user_id':user,'status':'Active'},'name')
    if not employee:frappe.throw('Your user is not linked to an active employee. Ask HR.')
    if frappe.db.exists('Field Worker Assignment',{'employee':employee}):
        frappe.throw('Your supervisor records your attendance.')
    if data.get('site') not in self_sites(user):frappe.throw('You cannot check in at this site.',frappe.PermissionError)
    site=frappe.get_doc('Field Site',data.get('site'));worker=lock_employee(employee)
    if worker.company!=site.company:frappe.throw('Your company does not match this site.')
    request_id=str(data.get('request_id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',request_id):frappe.throw('Missing request identifier. Reopen the check-in screen.')
    details=shift_details(site,data.get('shift'),moment(data));day=details['attendance_date']
    existing=frappe.db.get_value('Field Attendance Entry',{'attendance_key':key(employee,day,details['name'])},['name','state','request_id'],as_dict=True)
    if existing:
        if existing.request_id==request_id:return {'name':existing.name,'state':existing.state}
        frappe.throw('You have already checked in for this shift.')
    if frappe.db.exists('Field Attendance Entry',{'request_id':request_id}):frappe.throw('This request identifier is already used.')
    if not data.get('photo'):frappe.throw('Take a selfie to check in.')
    photo=decode_photo(data['photo'])
    lat,lon,accuracy=fail_rule(domain.validate_location,data.get('latitude'),data.get('longitude'),data.get('accuracy_m'),
        site.latitude,site.longitude,float(site.radius_m or 0),float(site.maximum_accuracy_m or 200))
    captured_at,gps_time=moment(data,with_gps=True)
    remarks=str(data.get('remarks') or '').strip()
    if len(remarks)>2000:frappe.throw('Keep remarks under 2,000 characters.')
    doc=frappe.get_doc(dict(doctype='Field Attendance Entry',entry_type='Self',attendance_key=key(employee,day,details['name']),
        request_id=request_id,last_capture_id=request_id,employee=employee,employee_name=worker.employee_name,site=site.name,
        project=site.project,company=worker.company,attendance_date=day,shift=details['name'],captured_by=user,
        responsible_supervisor=user,captured_at=captured_at,revision=1,state='Submitted',attendance_status='Present',
        work_mode='Not applicable',remarks=remarks,latitude=lat,longitude=lon,accuracy_m=accuracy,gps_captured_at=gps_time,
        check_in_time=captured_at,auto_checkout_at=captured_at+domain.AUTO_CHECKOUT,submitted_at=now_datetime()))
    mark_offline(doc,data);save(doc)
    from frappe.utils.file_manager import save_file
    doc.photo=save_file(f'field-{doc.name}-1.jpg',photo,'Field Attendance Entry',doc.name,is_private=1).file_url;save(doc)
    own_site_approver=has_membership(site.name,user,'Approver',APPROVER)
    if not approve_without_review(doc,own_site_approver):notify_approvers(doc,user,'Self check-in ready for review')
    return {'name':doc.name,'state':doc.state,'check_in_time':str(doc.check_in_time),'captured_offline':doc.captured_offline}


def self_checkout(data):
    """The employee's own check-out: location inside the site's fence and the server's (or corrected) time; no selfie."""
    user=require_user();doc=lock_doc('Field Attendance Entry',data.get('name'))
    if doc.get('entry_type')!='Self' or doc.captured_by!=user:frappe.throw('This is not your check-in.',frappe.PermissionError)
    if doc.check_out_time:return {'name':doc.name,'check_out_time':str(doc.check_out_time),'checkout_method':doc.checkout_method}
    if doc.attendance_status!='Present' or doc.state not in ('Submitted','Approved'):frappe.throw('There is no open check-in to close.')
    site=frappe.get_doc('Field Site',doc.site)
    fail_rule(domain.validate_location,data.get('latitude'),data.get('longitude'),data.get('accuracy_m'),
        site.latitude,site.longitude,float(site.radius_m or 0),float(site.maximum_accuracy_m or 200))
    out_at,_=moment(data,with_gps=True)
    doc.check_out_time=fail_rule(domain.checkout_time,get_datetime(doc.check_in_time),out_at)
    doc.checkout_method='Self check-out (offline)' if data.get('offline') else 'Self check-out'
    doc.revision+=1;save(doc)
    return {'name':doc.name,'check_out_time':str(doc.check_out_time),'checkout_method':doc.checkout_method}


def review_many(names,decision,remarks=''):
    """Approve or return several entries; each is reviewed on its own (all rules apply), one failure does not stop
    the rest, and the result says per entry what happened."""
    require_user()
    names=list(dict.fromkeys(names if isinstance(names,list) else []))
    if not names or len(names)>200:frappe.throw('Select between 1 and 200 records.')
    results=[]
    for name in names:
        frappe.db.savepoint('review_many')
        try:
            results.append(dict(review_entry(name,decision,remarks),ok=True))
        except (frappe.ValidationError,frappe.PermissionError) as exc:
            frappe.db.rollback(save_point='review_many');frappe.clear_messages()
            results.append(dict(name=name,ok=False,error=str(exc)))
    return results


def existing_attendance(doc):
    # Never reuse or overwrite HR attendance created elsewhere.
    return frappe.db.exists('Attendance',{'employee':doc.employee,'attendance_date':doc.attendance_date,'shift':doc.shift,'docstatus':['<',2]})


def hr_attendance(doc):
    """Create and submit the HR Attendance for an entry and mark the entry approved (the caller saves it)."""
    attendance=frappe.get_doc(dict(doctype='Attendance',employee=doc.employee,company=doc.company,
        attendance_date=doc.attendance_date,shift=doc.shift,status=doc.attendance_status,custom_field_entry=doc.name,custom_field_project=doc.project))
    if attendance.meta.has_field('project'):attendance.project=doc.project
    attendance.flags.field_service=True;attendance.insert(ignore_permissions=True)
    attendance.flags.ignore_permissions=True;attendance.submit()
    doc.attendance=attendance.name;doc.state='Approved'


def approve_without_review(doc, own_site_approver=False):
    """Sites that need no approval (for example head office; owner, 22 November 2026) and a site approver's own
    check-in (project manager; owner, 25 November 2026): a submitted online entry becomes HR attendance at once.
    Offline entries still go to the site's approvers, and so does a clash with HR attendance created elsewhere
    (domain.skips_approval). Returns True when approved here."""
    site_needs_approval=bool(frappe.db.get_value('Field Site',doc.site,'approval_required'))
    if not domain.skips_approval(bool(doc.captured_offline),site_needs_approval,bool(existing_attendance(doc)),own_site_approver):
        return False
    lock_employee(doc.employee);hr_attendance(doc)
    doc.review_remarks=('Own check-in of the site approver: no approval required.' if site_needs_approval
                        else 'No approval required at this site.')
    doc.reviewed_at=now_datetime();doc.revision+=1;save(doc)
    return True


def review_entry(name,decision,remarks=''):
    user = require_user()
    doc = lock_entry_for_submission(name)
    fail_rule(domain.validate_reviewer,user,doc.captured_by,frappe.db.get_value('Employee',doc.employee,'user_id'),approval_access(doc, user))
    if doc.verified_by == user:
        frappe.throw('A different approver must review this verified record.', frappe.PermissionError)
    if doc.state=='Approved' and decision=='Approve':return {'name':doc.name,'state':'Approved','attendance':doc.attendance}
    if not ready_for_approval(doc):
        frappe.throw('This record is not ready for final approval.')
    if decision not in ('Approve','Return'):frappe.throw('Choose Approve or Return.')
    remarks = review_remarks(remarks, decision)
    if decision=='Approve':
        lock_employee(doc.employee)
        if existing_attendance(doc):frappe.throw('HR attendance already exists for this worker and shift. Ask HR to resolve the conflict; nothing was overwritten.')
        hr_attendance(doc)
    else:doc.state='Returned'
    doc.review_remarks=remarks;doc.reviewed_by=user;doc.reviewed_at=now_datetime();doc.revision+=1;save(doc)
    notify(doc.captured_by,f'Attendance {doc.state.lower()}',doc)
    return {'name':doc.name,'state':doc.state,'attendance':doc.attendance}
