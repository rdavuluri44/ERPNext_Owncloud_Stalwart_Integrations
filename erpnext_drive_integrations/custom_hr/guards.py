import frappe
import math
from frappe.model.document import Document
from frappe.utils import nowdate, add_days
from erpnext_drive_integrations.custom_hr.access import eligible_supervisor


class ControlledDocument(Document):
    def validate(self):
        if not self.flags.field_service:
            frappe.throw('Use Field Attendance to make this change.', frappe.PermissionError)

    def on_trash(self):
        if not self.flags.field_service:
            frappe.throw('Field history cannot be deleted through the form.', frappe.PermissionError)


class FieldSiteBase(Document):
    def validate(self):
        if not self.is_new():
            frappe.db.sql('SELECT name FROM `tabField Site` WHERE name=%s FOR UPDATE',(self.name,))
        if self.project and frappe.db.get_value('Project',self.project,'company') != self.company:
            frappe.throw('The project must belong to this company.')
        if self.day_shift == self.night_shift:
            frappe.throw('Choose different day and night shifts.')
        if not all(math.isfinite(float(x or 0)) for x in (self.radius_m,self.maximum_accuracy_m)) or float(self.radius_m or 0)<0 or float(self.maximum_accuracy_m or 0)<=0:
            frappe.throw('Set a positive GPS accuracy limit and a non-negative site radius.')
        if self.radius_m:
            from erpnext_drive_integrations.custom_hr.domain import coordinates
            coordinates(self.latitude,self.longitude,1)
        seen=set()
        for member in self.members:
            pair=(member.user,member.team_role)
            if pair in seen:frappe.throw('A team member is listed twice.')
            seen.add(pair)
            if member.enabled and member.team_role=='Staff':
                # Self check-in staff need no role, only an active employee record of this site's company.
                if not frappe.db.get_value('User',member.user,'enabled') or not frappe.db.exists('Employee',
                        {'user_id':member.user,'status':'Active','company':self.company}):
                    frappe.throw(f'{member.user} must be enabled and linked to an active employee of {self.company}.')
            elif member.enabled:
                role='Field Supervisor' if member.team_role=='Supervisor' else 'Field Attendance Approver'
                if not frappe.db.get_value('User',member.user,'enabled') or role not in frappe.get_roles(member.user):
                    frappe.throw(f'{member.user} must be enabled and have the {role} role first.')
        if not any(m.enabled and m.team_role=='Approver' for m in self.members):
            frappe.throw('Add at least one attendance approver.')
        assets=set()
        for row in self.assets:
            if row.asset in assets:frappe.throw('A machine is listed twice.')
            assets.add(row.asset)
            if frappe.db.get_value('Asset',row.asset,'company') != self.company:
                frappe.throw('Every machine must belong to the site company.')
        if not self.is_new():
            supervisors={m.user for m in self.members if m.enabled and m.team_role=='Supervisor'} if self.enabled else set()
            for doctype,filters in [('Field Worker Assignment',{'site':self.name}),('Field Shift Allocation',{'site':self.name,'attendance_date':['>=',add_days(nowdate(),-1)]})]:
                for assigned in frappe.get_all(doctype,filters=filters,fields=['supervisor','employee']):
                    if frappe.db.get_value('Employee',assigned.employee,'status')=='Active' and assigned.supervisor not in supervisors:
                        frappe.throw('Reassign every active worker before removing a supervisor or disabling the site.')

    def on_trash(self):
        if frappe.db.exists('Field Worker Assignment',{'site':self.name}) or frappe.db.exists('Field Attendance Entry',{'site':self.name}):
            frappe.throw('This site has worker or attendance history. It cannot be deleted.')


def validate_user(doc, method=None):
    if doc.is_new():return
    frappe.db.sql('SELECT name FROM `tabUser` WHERE name=%s FOR UPDATE',(doc.name,))
    has_supervisor=any(r.role=='Field Supervisor' for r in doc.roles)
    if method=='on_trash' or not doc.enabled or not has_supervisor:
        for doctype,filters in [('Field Worker Assignment',{'supervisor':doc.name}),('Field Shift Allocation',{'supervisor':doc.name,'attendance_date':['>=',add_days(nowdate(),-1)]})]:
            for row in frappe.get_all(doctype,filters=filters,fields=['employee']):
                if frappe.db.get_value('Employee',row.employee,'status')=='Active':
                    frappe.throw('Reassign this user’s workers before disabling the supervisor or removing their supervisor role.')

    if method=='on_trash' or not doc.enabled or not any(r.role=='Field Attendance Approver' for r in doc.roles):
        sites=frappe.get_all('Field Site Member',filters={'user':doc.name,'team_role':'Approver','enabled':1},pluck='parent')
        for site in sites:
            if frappe.db.get_value('Field Site',site,'enabled'):
                others=frappe.get_all('Field Site Member',filters={'parent':site,'team_role':'Approver','enabled':1,'user':['!=',doc.name]},pluck='user')
                if not any(frappe.db.get_value('User',u,'enabled') and 'Field Attendance Approver' in frappe.get_roles(u) for u in others):
                    frappe.throw('Assign another approver before disabling this site’s last approver.')


def validate_employee(doc,method=None):
    if doc.status=='Active' and not doc.user_id:
        doc.custom_field_attendance_required=1
    existing=frappe.db.get_value('Field Worker Assignment',{'employee':doc.name},['site','supervisor'],as_dict=True) if not doc.is_new() else None
    if doc.status!='Active' or (not doc.get('custom_field_attendance_required') and not existing):return
    if existing and not doc.get('custom_field_attendance_required'):
        frappe.throw('This worker already has a responsible supervisor. Managed attendance cannot be switched off while assigned.')
    site=existing.site if existing else doc.get('custom_field_initial_site')
    supervisor=existing.supervisor if existing else doc.get('custom_field_initial_supervisor')
    if not site or not eligible_supervisor(site,supervisor):
        frappe.throw('This worker needs a valid initial Field Site and Field Supervisor before activation/import.')
    if frappe.db.get_value('Field Site',site,'company')!=doc.company:
        frappe.throw('The worker’s company must match their field site.')


def after_employee_insert(doc,method=None):
    if doc.get('custom_field_attendance_required') and doc.status=='Active':
        from erpnext_drive_integrations.custom_hr.service import enroll_employee
        enroll_employee(doc.name,doc.custom_field_initial_site,doc.custom_field_initial_supervisor,bool(doc.get('custom_field_machine_required')),initial=True)


HR_LEAVE_STATUSES={'On Leave','Half Day'}


def validate_attendance(doc,method=None):
    # Leave approval (HRMS) creates On Leave / Half Day attendance itself; presence still needs field evidence.
    if doc.is_new() and not doc.get('custom_field_entry') and doc.status in HR_LEAVE_STATUSES and doc.get('leave_type'):return
    if (doc.get('custom_field_entry') or (doc.is_new() and frappe.db.exists('Field Worker Assignment',{'employee':doc.employee}))) and not doc.flags.field_service:
        frappe.throw('Approved field attendance must be changed through the field attendance review process.',frappe.PermissionError)


def before_cancel_attendance(doc,method=None):
    if doc.get('custom_field_entry'):
        frappe.throw('This attendance is linked to approved field evidence. Ask the field approver to review it; direct cancellation is blocked.')


def protect_file(doc,method=None):
    old=doc.get_doc_before_save()
    protected=doc.attached_to_doctype=='Field Attendance Entry' or bool(old and old.attached_to_doctype=='Field Attendance Entry')
    if not protected:return
    if method=='on_trash':frappe.throw('Attendance photographs are retained as approval evidence and cannot be deleted directly.',frappe.PermissionError)
    if not doc.is_private:frappe.throw('Attendance photographs must remain private.',frappe.PermissionError)
    if old and any(doc.get(f)!=old.get(f) for f in ('file_url','is_private','attached_to_doctype','attached_to_name')):
        frappe.throw('Attendance evidence cannot be moved or replaced directly.',frappe.PermissionError)


def on_employee_update(doc,method=None):
    name=frappe.db.get_value('Field Worker Assignment',{'employee':doc.name},'name')
    if not name and doc.status=='Active' and doc.get('custom_field_attendance_required'):
        from erpnext_drive_integrations.custom_hr.service import enroll_employee
        enroll_employee(doc.name,doc.custom_field_initial_site,doc.custom_field_initial_supervisor,bool(doc.get('custom_field_machine_required')),initial=True)
        return
    old=doc.get_doc_before_save()
    if not name or not old or doc.get('custom_field_machine_required')==old.get('custom_field_machine_required'):return
    from erpnext_drive_integrations.custom_hr.access import require_manager
    require_manager()
    from erpnext_drive_integrations.custom_hr.service import lock_doc,save
    assignment=lock_doc('Field Worker Assignment',name)
    assignment.machine_required=doc.get('custom_field_machine_required') or 0
    save(assignment)


def block_frappe_hr_checkin(doc,method=None):
    """One attendance path: while HR Settings blocks Frappe HR check-ins, only the roles listed there may create or
    change Employee Checkin records, from any screen or route (the hidden button alone is not enough)."""
    from erpnext_drive_integrations.custom_hr.domain import checkin_allowed
    settings=frappe.get_cached_doc('HR Settings')
    if not checkin_allowed(settings.get('custom_block_frappe_hr_checkin'),settings.get('custom_checkin_allowed_roles'),
                           frappe.get_roles(),frappe.session.user):
        frappe.throw('Check in with the company app. Frappe HR check-ins are switched off by your administrator.',frappe.PermissionError)
