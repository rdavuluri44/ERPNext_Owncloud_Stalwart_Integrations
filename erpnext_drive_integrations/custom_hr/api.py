import frappe
from frappe.utils import now_datetime, nowdate, cint
from erpnext_drive_integrations.custom_hr.access import require_user, require_site, require_manager, site_ids, site_access, is_manager, entry_access, self_sites
from erpnext_drive_integrations.custom_hr import service


def data(value):
    return frappe.parse_json(value) if isinstance(value,str) else value


@frappe.whitelist()
def bootstrap():
    user=require_user();sites=[]
    for name in site_ids(user):
        doc=frappe.get_doc('Field Site',name)
        sites.append(dict(name=name,label=doc.site_name,project=doc.project,project_name=frappe.db.get_value('Project',doc.project,'project_name'),company=doc.company,
            supervisor=site_access(name,'Supervisor',user),approver=site_access(name,'Approver',user),
            shifts=[dict(service.shift_details(doc,s),label=label) for s,label in [(doc.day_shift,'Day'),(doc.night_shift,'Night')]],
            supervisors=[dict(user=m.user,label=frappe.db.get_value('User',m.user,'full_name') or m.user)
                for m in doc.members if m.enabled and m.team_role=='Supervisor'],
            assets=[dict(name=r.asset,label=frappe.db.get_value('Asset',r.asset,'asset_name') or r.asset) for r in doc.assets]))
    employee=frappe.db.get_value('Employee',{'user_id':user,'status':'Active'},'name')
    # Sites for the person's own check-in, with the fence so the app can warn before sending (the server decides).
    check_in_sites=[]
    if employee and not frappe.db.exists('Field Worker Assignment',{'employee':employee}):
        for name in self_sites(user):
            doc=frappe.get_doc('Field Site',name)
            check_in_sites.append(dict(name=name,label=doc.site_name,project=doc.project,latitude=doc.latitude,longitude=doc.longitude,
                radius_m=doc.radius_m,maximum_accuracy_m=doc.maximum_accuracy_m,
                shifts=[dict(service.shift_details(doc,s),label=label) for s,label in [(doc.day_shift,'Day'),(doc.night_shift,'Night')]]))
    return dict(user=user,full_name=frappe.db.get_value('User',user,'full_name'),manager=is_manager(user),
        sites=sites,check_in_sites=check_in_sites,server_now=str(now_datetime()),employee=employee,version='0.2.0')


@frappe.whitelist()
def team(site,shift,search='',offset=0):
    user=require_user();location=require_site(site);details=service.shift_details(location,shift)
    can_approve=site_access(site,'Approver',user)
    values={'site':site,'day':details['attendance_date'],'shift':shift,'user':user,'q':'%'+str(search or '')[:100]+'%'}
    join="""FROM `tabField Worker Assignment` a JOIN `tabEmployee` e ON e.name=a.employee
        LEFT JOIN `tabField Shift Allocation` x ON x.employee=a.employee AND x.attendance_date=%(day)s AND x.shift=%(shift)s
        LEFT JOIN `tabField Attendance Entry` f ON f.employee=a.employee AND f.attendance_date=%(day)s AND f.shift=%(shift)s
        WHERE a.site=%(site)s AND e.status='Active' AND (e.employee_name LIKE %(q)s OR a.employee LIKE %(q)s)"""
    if not can_approve:join+=" AND COALESCE(x.supervisor,a.supervisor)=%(user)s"
    counts=frappe.db.sql("SELECT COUNT(*) AS total,SUM(CASE WHEN f.state IS NULL OR f.state IN ('Draft','Returned') THEN 1 ELSE 0 END) AS missing "+join,values,as_dict=True)[0]
    rows=frappe.db.sql("""SELECT a.employee,a.machine_required,e.employee_name,e.designation,
        COALESCE(x.supervisor,a.supervisor) AS supervisor,
        COALESCE(NULLIF(a.locked_by,''),NULLIF(x.locked_by,'')) AS locked_by,
        f.name AS entry,f.state,f.captured_by,f.revision """+join+' ORDER BY e.employee_name LIMIT 500',values,as_dict=True)
    can_capture=site_access(site,'Supervisor',user)
    for row in rows:
        own=row.supervisor==user
        row.locked=bool(row.pop('locked_by',None));row.assignment_source='Approver' if row.locked else 'Supervisor'
        if row.captured_by!=user and not can_approve:row.entry=None
        row.state=row.state or 'Not recorded'
        row.can_capture=own and can_capture
        row.can_edit=bool(row.entry and row.captured_by==user and row.state in ('Draft','Returned'))
        row.can_transfer=can_approve or not row.locked
        row.pop('captured_by',None)
    return dict(workers=rows,total=counts.total,truncated=counts.total>500,attendance_date=details['attendance_date'],missing=cint(counts.missing))


@frappe.whitelist()
def entry(name):
    require_user();doc=frappe.get_doc('Field Attendance Entry',name)
    if not entry_access(doc):frappe.throw('You cannot view this record.',frappe.PermissionError)
    fields=['name','employee','employee_name','site','project','attendance_date','shift','attendance_status','state','work_mode','asset',
            'remarks','review_remarks','photo','latitude','longitude','accuracy_m','check_in_time','auto_checkout_at','check_out_time','checkout_method','captured_at','captured_by','revision','request_id','attendance','machine_required']
    result={f:doc.get(f) for f in fields}
    result['can_review']=site_access(doc.site,'Approver') and doc.captured_by!=frappe.session.user and frappe.db.get_value('Employee',doc.employee,'user_id')!=frappe.session.user
    return result


@frappe.whitelist()
def approvals(site,shift=None):
    user=require_user();location=require_site(site,'Approver')
    filters={'site':site,'state':'Submitted'}
    if shift:
        details=service.shift_details(location,shift);filters.update(shift=shift,attendance_date=details['attendance_date'])
    docs=frappe.get_all('Field Attendance Entry',filters=filters,
        fields=['name','employee','employee_name','attendance_date','shift','attendance_status','work_mode','asset','captured_by','submitted_at',
                'entry_type','captured_offline','check_in_time','accuracy_m'],order_by='submitted_at asc',limit=200)
    for d in docs:
        d.can_review=d.captured_by!=user and frappe.db.get_value('Employee',d.employee,'user_id')!=user
    return docs


@frappe.whitelist(methods=['POST'])
def save_capture(payload):return service.capture(data(payload))


@frappe.whitelist(methods=['POST'])
def submit(name):return service.submit_entry(name)


@frappe.whitelist(methods=['POST'])
def review(name,decision,remarks=''):return service.review_entry(name,decision,remarks)


@frappe.whitelist(methods=['POST'])
def review_many(names,decision,remarks=''):return service.review_many(data(names),decision,remarks)


@frappe.whitelist(methods=['POST'])
def self_check_in(payload):return service.self_capture(data(payload))


@frappe.whitelist(methods=['POST'])
def self_check_out(payload):return service.self_checkout(data(payload))


@frappe.whitelist(methods=['GET'])
def my_attendance():
    """The person's own check-ins (newest first), for My HR."""
    user=require_user()
    employee=frappe.db.get_value('Employee',{'user_id':user,'status':'Active'},'name')
    if not employee:return []
    return frappe.get_all('Field Attendance Entry',filters={'employee':employee,'entry_type':'Self'},
        fields=['name','site','shift','attendance_date','state','check_in_time','check_out_time','checkout_method','captured_offline',
                'review_remarks','attendance'],order_by='attendance_date desc, check_in_time desc',limit=100)


@frappe.whitelist(methods=['POST'])
def move(employees,site,destination,scope,shift,remarks=''):
    return service.transfer(data(employees),site,destination,scope,shift,remarks)


@frappe.whitelist()
def setup_options():
    require_manager()
    users=frappe.get_all('User',filters={'enabled':1,'user_type':'System User'},fields=['name','full_name'],limit=500)
    for u in users:
        roles=frappe.get_roles(u.name)
        u.supervisor='Field Supervisor' in roles;u.approver='Field Attendance Approver' in roles
    return dict(companies=frappe.get_all('Company',fields=['name'],limit=200),
        projects=frappe.get_all('Project',fields=['name','project_name','company'],limit=500),
        shifts=frappe.get_all('Shift Type',fields=['name','start_time','end_time'],limit=100),users=users,
        assets=frappe.get_all('Asset',filters={'docstatus':['<',2]},fields=['name','asset_name','company'],limit=1000))


@frappe.whitelist(methods=['POST'])
def create_shifts():
    require_manager()
    for name,start,end in [('Day Shift','07:00:00','19:00:00'),('Night Shift','19:00:00','07:00:00')]:
        if not frappe.db.exists('Shift Type',name):
            frappe.get_doc(dict(doctype='Shift Type',name=name,start_time=start,end_time=end,enable_auto_attendance=0)).insert(ignore_permissions=True)
    return {'created_or_existing':['Day Shift','Night Shift']}


@frappe.whitelist(methods=['POST'])
def save_site(payload):
    require_manager();p=data(payload)
    doc=frappe.get_doc('Field Site',p['name']) if p.get('name') else frappe.new_doc('Field Site')
    for f in ('site_name','company','project','day_shift','night_shift','latitude','longitude','radius_m','maximum_accuracy_m'):
        doc.set(f,p.get(f))
    doc.enabled=1;doc.set('members',[]);doc.set('assets',[])
    for row in p.get('members',[]):doc.append('members',dict(user=row['user'],team_role=row['team_role'],enabled=1))
    for asset in p.get('assets',[]):doc.append('assets',dict(asset=asset))
    doc.save(ignore_permissions=True)
    return {'name':doc.name}


@frappe.whitelist()
def unassigned(search=''):
    require_manager()
    join="""FROM `tabEmployee` e LEFT JOIN `tabField Worker Assignment` a ON a.employee=e.name
        WHERE e.status='Active' AND a.name IS NULL AND (e.user_id IS NULL OR e.user_id='')
        AND (e.employee_name LIKE %s OR e.name LIKE %s)"""
    values=('%'+str(search or '')[:100]+'%','%'+str(search or '')[:100]+'%')
    rows=frappe.db.sql('SELECT e.name,e.employee_name,e.company,e.designation '+join+' ORDER BY e.employee_name LIMIT 500',values,as_dict=True)
    total=frappe.db.sql('SELECT COUNT(*) '+join,values)[0][0]
    return dict(workers=rows,total=total,truncated=total>500)


@frappe.whitelist(methods=['POST'])
def enroll(employees,site,supervisor,machine_required=0,locked=0):
    require_manager();employees=sorted(set(data(employees)))
    if not employees or len(employees)>100:frappe.throw('Select between 1 and 100 workers.')
    return [service.enroll_employee(e,site,supervisor,cint(machine_required),locked=cint(locked)) for e in employees]


@frappe.whitelist()
def my_records():
    user=require_user()
    sites=site_ids(user,'Supervisor')
    if not sites:return []
    return frappe.get_all('Field Attendance Entry',filters={'captured_by':user,'site':['in',sites]},fields=['name','employee','employee_name','site','shift','attendance_date','state','review_remarks'],order_by='modified desc',limit=100)
