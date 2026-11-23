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
from erpnext_drive_integrations.custom_hr.access import require_user, require_site, require_manager, eligible_supervisor, site_access, is_manager, site_ids
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


def shift_details(site,shift):
    if shift not in (site.day_shift,site.night_shift):frappe.throw('Choose one of this site’s shifts.')
    d=frappe.get_doc('Shift Type',shift)
    def as_time(value):
        seconds=int(value.total_seconds()) if hasattr(value,'total_seconds') else None
        if seconds is not None:return time(seconds//3600,(seconds//60)%60,seconds%60)
        return get_datetime(f'2000-01-01 {value}').time()
    day=domain.shift_date(now_datetime(),as_time(d.start_time),as_time(d.end_time))
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


def capture(data):
    user=require_user()
    site=require_site(data.get('site'),'Supervisor')
    employee=data.get('employee');worker=lock_employee(employee)
    if worker.user_id==user:frappe.throw('Use My HR to mark your own attendance.')
    details=shift_details(site,data.get('shift'));day=details['attendance_date']
    base,extra,effective=assignment(employee,site.name,day,details['name'],lock=True)
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
        if doc.state in ('Submitted','Approved'):
            if doc.request_id==request_id:return {'name':doc.name,'state':doc.state}
            frappe.throw('Attendance has already been submitted for this worker and shift.')
        # Require revision match so a stale phone cannot overwrite a returned correction.
        if cint(data.get('revision'))!=doc.revision:frappe.throw('This record changed. Refresh before editing.')
    else:
        if effective['supervisor']!=user:frappe.throw('This worker is no longer assigned to you. Refresh your team.',frappe.PermissionError)
        if frappe.db.exists('Field Attendance Entry',{'request_id':request_id}):frappe.throw('This request identifier is already used.')
        doc=frappe.get_doc(dict(doctype='Field Attendance Entry',attendance_key=key(employee,day,details['name']),request_id=request_id,
            employee=employee,employee_name=worker.employee_name,site=site.name,project=site.project,company=worker.company,attendance_date=day,
            shift=details['name'],captured_by=user,responsible_supervisor=user,captured_at=now_datetime(),revision=1,state='Draft'))
    status=data.get('attendance_status') or 'Present';mode=data.get('work_mode') or 'Not applicable';asset=data.get('asset') or None
    fail_rule(domain.validate_work_mode,effective['machine_required'],status,mode,asset,{r.asset for r in site.assets})
    remarks=str(data.get('remarks') or '').strip()
    if len(remarks)>2000:frappe.throw('Keep remarks under 2,000 characters.')
    if status=='Absent' and not remarks:frappe.throw('Add a reason when marking a worker absent.')
    photo=decode_photo(data['photo']) if data.get('photo') else None
    if status=='Present' and not (photo or doc.photo):frappe.throw('Capture the worker’s photograph.')
    if photo or doc.is_new():
        lat,lon,accuracy=fail_rule(domain.validate_location,data.get('latitude'),data.get('longitude'),data.get('accuracy_m'),
            site.latitude,site.longitude,float(site.radius_m or 0),float(site.maximum_accuracy_m or 200))
        if not data.get('gps_captured_at'):frappe.throw('Capture a fresh GPS location.')
        gps_time=get_datetime(data.get('gps_captured_at'))
        if not gps_time or abs((now_datetime()-gps_time).total_seconds())>300:
            frappe.throw('The location is older than five minutes. Fetch it again.')
        doc.latitude=lat;doc.longitude=lon;doc.accuracy_m=accuracy;doc.gps_captured_at=gps_time;doc.captured_at=now_datetime()
    doc.attendance_status=status;doc.work_mode=mode;doc.asset=asset;doc.remarks=remarks
    doc.machine_required=cint(effective['machine_required']);doc.state='Draft';doc.review_remarks=''
    doc.last_capture_id=capture_id;doc.last_capture_digest=digest
    if not doc.is_new():doc.revision+=1
    save(doc)
    if photo:
        from frappe.utils.file_manager import save_file
        attachment=save_file(f'field-{doc.name}-{doc.revision}.jpg',photo,'Field Attendance Entry',doc.name,is_private=1)
        doc.photo=attachment.file_url;save(doc)
    return {'name':doc.name,'state':doc.state,'revision':doc.revision}


def submit_entry(name):
    user=require_user();doc=lock_doc('Field Attendance Entry',name)
    if doc.captured_by!=user or not site_access(doc.site,'Supervisor',user):frappe.throw('This is not your submission.',frappe.PermissionError)
    if doc.state in ('Submitted','Approved'):return {'name':doc.name,'state':doc.state}
    # A transfer does not erase a capture. The original supervisor can submit an existing draft;
    # creation/update still requires current assignment and original evidence is retained.
    if doc.attendance_status=='Present' and not doc.photo:frappe.throw('A photograph is required.')
    if doc.attendance_status == 'Present' and not doc.check_in_time:
        from datetime import timedelta
        doc.check_in_time = doc.captured_at
        doc.auto_checkout_at = get_datetime(doc.check_in_time) + timedelta(hours=12)
    elif doc.attendance_status == 'Absent':
        doc.check_in_time = doc.auto_checkout_at = doc.check_out_time = doc.checkout_method = None
    doc.state='Submitted';doc.submitted_at=now_datetime();save(doc)
    approvers=frappe.get_all('Field Site Member',filters={'parent':doc.site,'team_role':'Approver','enabled':1},pluck='user')
    for approver in set(approvers):
        if approver!=user:notify(approver,'Attendance ready for review',doc)
    return {'name':doc.name,'state':doc.state}


def review_entry(name,decision,remarks=''):
    user=require_user();doc=lock_doc('Field Attendance Entry',name)
    fail_rule(domain.validate_reviewer,user,doc.captured_by,frappe.db.get_value('Employee',doc.employee,'user_id'),site_access(doc.site,'Approver',user))
    if doc.state=='Approved' and decision=='Approve':return {'name':doc.name,'state':'Approved','attendance':doc.attendance}
    if doc.state!='Submitted':frappe.throw('Only submitted records can be reviewed.')
    if decision not in ('Approve','Return'):frappe.throw('Choose Approve or Return.')
    remarks=str(remarks or '').strip()
    if len(remarks)>2000:frappe.throw('Keep review remarks under 2,000 characters.')
    if decision=='Return' and not remarks:frappe.throw('Explain what needs correcting.')
    if decision=='Approve':
        lock_employee(doc.employee)
        # Never reuse or overwrite HR attendance created elsewhere.
        existing=frappe.db.exists('Attendance',{'employee':doc.employee,'attendance_date':doc.attendance_date,'shift':doc.shift,'docstatus':['<',2]})
        if existing:frappe.throw('HR attendance already exists for this worker and shift. Ask HR to resolve the conflict; nothing was overwritten.')
        attendance=frappe.get_doc(dict(doctype='Attendance',employee=doc.employee,company=doc.company,
            attendance_date=doc.attendance_date,shift=doc.shift,status=doc.attendance_status,custom_field_entry=doc.name,custom_field_project=doc.project))
        if attendance.meta.has_field('project'):attendance.project=doc.project
        attendance.flags.field_service=True;attendance.insert(ignore_permissions=True)
        attendance.flags.ignore_permissions=True;attendance.submit()
        doc.attendance=attendance.name;doc.state='Approved'
    else:doc.state='Returned'
    doc.review_remarks=remarks;doc.reviewed_by=user;doc.reviewed_at=now_datetime();doc.revision+=1;save(doc)
    notify(doc.captured_by,f'Attendance {doc.state.lower()}',doc)
    return {'name':doc.name,'state':doc.state,'attendance':doc.attendance}
