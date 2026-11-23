"""Rollback-only integration checks against the installed Frappe/HRMS version.
Creates synthetic users/employees; never uses real photographs or marks real attendance.
"""
import base64,io,uuid,os
from datetime import timedelta
from pathlib import Path
import frappe
from frappe.utils import now_datetime,nowdate,add_days,get_datetime
from erpnext_drive_integrations.custom_hr import service,api
from erpnext_drive_integrations.custom_hr.access import entry_access


def run():
    original=frappe.session.user
    token='ft'+uuid.uuid4().hex[:10]
    files=[];checks=[];test_users=[]
    def check(label,condition):
        assert condition,label
        checks.append(label)
    def denied(label,fn):
        try:fn()
        except (frappe.ValidationError,frappe.PermissionError,frappe.AuthenticationError):checks.append(label);return
        raise AssertionError(label+' was not rejected')
    def user(label,roles):
        name=f'{token}-{label}@example.invalid'
        d=frappe.get_doc(dict(doctype='User',email=name,first_name='FIELD TEST '+label,enabled=1,user_type='System User',send_welcome_email=0,roles=[{'role':r} for r in roles]))
        d.flags.no_welcome_mail=True;d.insert(ignore_permissions=True);test_users.append(name);return name
    def worker(label,**kw):
        values=dict(doctype='Employee',first_name='FIELD TEST '+label,gender=gender,date_of_birth='1990-01-01',date_of_joining=add_days(nowdate(),-10),company=company,status='Active',custom_field_attendance_required=1,custom_field_initial_site=site.name,custom_field_initial_supervisor=a,custom_field_machine_required=1)
        values.update(kw)
        return frappe.get_doc(values).insert(ignore_permissions=True)
    frappe.set_user('Administrator')
    try:
        company=frappe.get_all('Company',pluck='name',limit=1)[0]
        gender=frappe.get_all('Gender',pluck='name',limit=1)[0]
        a=user('a',['Field Supervisor','Field Attendance Approver'])
        b=user('b',['Field Supervisor']);c=user('c',['Field Supervisor'])
        boss=user('boss',['Field Attendance Approver'])
        outsider=user('outside',['Field Attendance Approver'])
        day=frappe.get_doc(dict(doctype='Shift Type',name=token+' Day',start_time='08:00:00',end_time='20:00:00',enable_auto_attendance=0)).insert(ignore_permissions=True)
        night=frappe.get_doc(dict(doctype='Shift Type',name=token+' Night',start_time='20:00:00',end_time='08:00:00',enable_auto_attendance=0)).insert(ignore_permissions=True)
        project=frappe.get_doc(dict(doctype='Project',project_name=token,company=company,status='Open')).insert(ignore_permissions=True)
        site=frappe.get_doc(dict(doctype='Field Site',site_name=token,company=company,project=project.name,day_shift=day.name,night_shift=night.name,enabled=1,maximum_accuracy_m=200,
            members=[{'user':u,'team_role':r,'enabled':1} for u,r in [(a,'Supervisor'),(b,'Supervisor'),(c,'Supervisor'),(boss,'Approver'),(a,'Approver')]])).insert(ignore_permissions=True)
        w=worker('one');w2=worker('two');w3=worker('three')
        details=service.shift_details(site,day.name)
        from PIL import Image
        buf=io.BytesIO();Image.new('RGB',(160,160),(230,235,230)).save(buf,'JPEG')
        photo='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
        def payload(employee):return dict(employee=employee,site=site.name,shift=day.name,request_id=uuid.uuid4().hex,capture_id=uuid.uuid4().hex,
            revision=0,attendance_status='Present',work_mode='Standby',remarks='Synthetic integration check',photo=photo,
            latitude=17,longitude=78,accuracy_m=10,gps_captured_at=str(now_datetime()))
        frappe.set_user(b)
        denied('other supervisor cannot capture',lambda:service.capture(payload(w.name)))
        frappe.set_user(a)
        p=payload(w.name);saved=service.capture(p)
        doc=frappe.get_doc('Field Attendance Entry',saved['name']);files.append(doc.photo)
        check('new evidence stays draft',doc.state=='Draft' and not doc.attendance)
        check('private photo attached',doc.photo.startswith('/private/files/') and frappe.db.get_value('File',{'file_url':doc.photo},'is_private')==1)
        frappe.set_user(b)
        check('peer cannot read private photograph',not frappe.get_doc('File',{'file_url':doc.photo}).has_permission('read'))
        frappe.set_user(a)
        again=service.capture(p)
        check('capture retry is idempotent',again['name']==saved['name'] and again['revision']==saved['revision'])
        service.submit_entry(doc.name)
        check('submission does not create attendance',not frappe.db.exists('Attendance',{'custom_field_entry':doc.name}))
        denied('submitter cannot self approve',lambda:service.review_entry(doc.name,'Approve'))
        frappe.set_user(outsider)
        denied('other site cannot approve',lambda:service.review_entry(doc.name,'Approve'))
        check('other site cannot read evidence',not entry_access(frappe.get_doc('Field Attendance Entry',doc.name),outsider))
        frappe.set_user(boss)
        returned=service.review_entry(doc.name,'Return','Check remarks')
        check('approver returns evidence',returned['state']=='Returned')
        frappe.set_user(a)
        p2=payload(w.name);p2.update(name=doc.name,request_id=doc.request_id,revision=frappe.db.get_value('Field Attendance Entry',doc.name,'revision'),photo=None,remarks='Corrected test remark')
        saved=service.capture(p2);service.submit_entry(doc.name)
        frappe.set_user(boss)
        approved=service.review_entry(doc.name,'Approve')
        check('approval creates submitted HR attendance',frappe.db.get_value('Attendance',approved['attendance'],'docstatus')==1)
        check('approved attendance retains Project dimension',frappe.db.get_value('Attendance',approved['attendance'],'custom_field_project')==project.name)
        check('approval retry does not duplicate',service.review_entry(doc.name,'Approve')['attendance']==approved['attendance'])
        check('one official attendance record',frappe.db.count('Attendance',{'custom_field_entry':doc.name})==1)
        attendance=frappe.get_doc('Attendance',approved['attendance'])
        frappe.set_user('Administrator')
        denied('direct cancellation blocked',attendance.cancel)
        frappe.set_user(b)
        denied('wrong supervisor cannot transfer',lambda:service.transfer([w2.name],site.name,c,'Ongoing',day.name))
        frappe.set_user('Administrator')
        # a also has approver membership, so use b->c to prove the pure peer rule.
        service.transfer([w2.name],site.name,b,'Ongoing',day.name)
        frappe.set_user(boss)
        service.transfer([w2.name],site.name,c,'This shift',night.name)
        frappe.set_user(b)
        denied('locked ongoing assignment cannot be moved by peer',lambda:service.transfer([w2.name],site.name,c,'Ongoing',day.name))
        frappe.set_user('Administrator')
        # Explicit initial enrollment is unlocked; this worker is independently assigned to b.
        w4=worker('four',custom_field_initial_supervisor=b,custom_field_machine_required=0)
        frappe.set_user(b)
        service.transfer([w4.name],site.name,c,'Ongoing',day.name)
        check('peer transfer effective immediately',service.assignment(w4.name)[0].supervisor==c)
        frappe.set_user(c)
        service.transfer([w4.name],site.name,b,'This shift',day.name)
        check('peer receiving supervisor can reassign',service.assignment(w4.name,site.name,details['attendance_date'],day.name)[2]['supervisor']==b)
        check('permanent supervisor preserved for shift transfer',service.assignment(w4.name)[0].supervisor==c)
        frappe.set_user('Administrator')
        ud=frappe.get_doc('User',c);ud.enabled=0
        denied('supervisor cannot be disabled with workers',lambda:ud.save(ignore_permissions=True))
        bad=frappe.get_doc('Field Worker Assignment',{'employee':w4.name});bad.supervisor=a
        denied('direct assignment write blocked',lambda:bad.save(ignore_permissions=True))
        denied('required worker cannot be imported without supervisor',lambda:worker('unassigned',custom_field_attendance_required=0,custom_field_initial_site=None,custom_field_initial_supervisor=None))
        initial=worker('import',custom_field_attendance_required=1,custom_field_initial_site=site.name,custom_field_initial_supervisor=b)
        check('employee import creates assignment atomically',frappe.db.exists('Field Worker Assignment',{'employee':initial.name,'supervisor':b}) is not None)
        frappe.set_user(boss)
        roster=api.team(site.name,day.name)
        check('approver roster returns all assigned active workers',roster['total']==5)
        check('approver pending queue empty after approval',api.approvals(site.name)==[])
        frappe.set_user(b)
        check('supervisor roster excludes peers',all(r.supervisor==b for r in api.team(site.name,day.name)['workers']))
        frappe.set_user('Administrator')
        check('assignment audit preserved',frappe.db.count('Field Assignment Event',{'site':site.name})>=7)
        # Self check-in (owner, 22 November 2026): Staff members check in themselves with a selfie inside the
        # site's fence; the site's approvers approve, one by one or in bulk; offline captures keep a corrected time.
        frappe.set_user('Administrator')
        staff=user('staff',[])
        frappe.get_doc(dict(doctype='Employee',first_name='FIELD TEST staff',gender=gender,date_of_birth='1990-01-01',date_of_joining=add_days(nowdate(),-10),
            company=company,status='Active',user_id=staff,custom_field_attendance_required=0)).insert(ignore_permissions=True)
        site.reload();site.latitude=17;site.longitude=78;site.radius_m=500
        site.append('members',{'user':staff,'team_role':'Staff','enabled':1});site.save(ignore_permissions=True)
        # Use a different image from the supervisor evidence. Frappe deduplicates by content and
        # refuses a staff user permission to attach a supervisor's existing private file.
        selfie_buffer=io.BytesIO();Image.new('RGB',(160,160),(187,209,224)).save(selfie_buffer,'JPEG')
        selfie='data:image/jpeg;base64,'+base64.b64encode(selfie_buffer.getvalue()).decode()
        def self_payload(**kw):
            p=dict(site=site.name,shift=day.name,request_id=uuid.uuid4().hex,photo=selfie,latitude=17,longitude=78,accuracy_m=10,gps_captured_at=str(now_datetime()))
            p.update(kw);return p
        frappe.set_user(staff)
        check('staff see their check-in site',[s['name'] for s in api.bootstrap()['check_in_sites']]==[site.name])
        denied('self check-in needs a selfie',lambda:service.self_capture(self_payload(photo=None)))
        denied('self check-in outside the fence is refused',lambda:service.self_capture(self_payload(latitude=17.1)))
        old=str(now_datetime()-timedelta(days=2))
        denied('offline check-in older than a day is refused',lambda:service.self_capture(self_payload(offline=1,device_captured_at=old,clock_offset_s=0,gps_captured_at=old)))
        sp=self_payload();mine=service.self_capture(sp)
        sdoc=frappe.get_doc('Field Attendance Entry',mine['name']);files.append(sdoc.photo)
        check('self check-in goes straight to approval',sdoc.state=='Submitted' and sdoc.entry_type=='Self' and not sdoc.attendance)
        check('self check-in retry is idempotent',service.self_capture(sp)['name']==sdoc.name)
        denied('second check-in for the same shift is refused',lambda:service.self_capture(self_payload()))
        check('own check-in is visible to its owner',entry_access(sdoc,staff))
        denied('nobody approves their own check-in',lambda:service.review_entry(sdoc.name,'Approve'))
        frappe.set_user(boss)
        results=service.review_many([sdoc.name,'does-not-exist'],'Approve')
        check('bulk approval reports each record',results[0]['ok'] and not results[1]['ok'])
        check('approved self check-in creates HR attendance',frappe.db.get_value('Attendance',results[0]['attendance'],'docstatus')==1)
        frappe.set_user(staff)
        out=service.self_checkout(dict(name=sdoc.name,latitude=17,longitude=78,accuracy_m=10,gps_captured_at=str(now_datetime())))
        check('self check-out recorded',out['checkout_method']=='Self check-out')
        check('my attendance lists the check-in',[r.name for r in api.my_attendance()]==[sdoc.name])
        frappe.set_user(a)
        then=now_datetime()-timedelta(hours=3);q=payload(w3.name)
        q.update(offline=1,device_captured_at=str(then),clock_offset_s=60,gps_captured_at=str(then))
        odoc=frappe.get_doc('Field Attendance Entry',service.capture(q)['name']);files.append(odoc.photo)
        check('offline team capture keeps its corrected time',odoc.captured_offline==1 and odoc.entry_type=='Team'
              and abs((get_datetime(odoc.captured_at)-(then+timedelta(seconds=60))).total_seconds())<1)
        # Head office (owner, 22 November 2026): a site that needs no approval; offline entries still go to approvers.
        frappe.set_user('Administrator');frappe.db.set_value('Field Site',site.name,'approval_required',0);w5=worker('five')
        frappe.set_user(a)
        check('offline entry still needs approval where approval is off',service.submit_entry(odoc.name)['state']=='Submitted')
        fdoc=frappe.get_doc('Field Attendance Entry',service.capture(payload(w5.name))['name']);files.append(fdoc.photo)
        out=service.submit_entry(fdoc.name);fdoc.reload()
        check('online entry where approval is off becomes HR attendance at once',out['state']=='Approved'
              and frappe.db.get_value('Attendance',fdoc.attendance,'docstatus')==1)
        # Frappe HR's own check-in: blocked on the server while HR Settings says so, except for the listed roles.
        from erpnext_drive_integrations.custom_hr import guards
        frappe.set_user('Administrator')
        check('Frappe HR check-in guard is installed','erpnext_drive_integrations.custom_hr.guards.block_frappe_hr_checkin'
              in frappe.get_hooks('doc_events').get('Employee Checkin',{}).get('validate',[]))
        frappe.db.set_single_value('HR Settings',{'custom_block_frappe_hr_checkin':1,'custom_checkin_allowed_roles':'System Manager'})
        frappe.clear_document_cache('HR Settings','HR Settings')
        log=frappe.get_doc(dict(doctype='Employee Checkin',employee=frappe.db.get_value('Employee',{'user_id':staff},'name'),log_type='IN',time=now_datetime()))
        frappe.set_user(staff)
        denied('Frappe HR check-in is refused while blocked',lambda:guards.block_frappe_hr_checkin(log))
        frappe.set_user('Administrator')
        frappe.db.set_single_value('HR Settings','custom_block_frappe_hr_checkin',0);frappe.clear_document_cache('HR Settings','HR Settings')
        frappe.set_user(staff);guards.block_frappe_hr_checkin(log);check('Frappe HR check-in is open once the admin unticks the box',True)
        print('FIELD_INTEGRATION_PASS',len(checks),checks)
    finally:
        frappe.db.rollback()
        frappe.clear_document_cache('HR Settings','HR Settings')  # the cached copy would keep the test's values
        frappe.set_user(original)
        for url in files:
            path=Path(frappe.get_site_path('private','files',url.rsplit('/',1)[-1]))
            if path.exists():path.unlink()
        for u in test_users:frappe.clear_cache(user=u)
        print('FIELD_TEST_DATA_ROLLED_BACK')
