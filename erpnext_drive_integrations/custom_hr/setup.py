import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def roles():
    for name in ('Field Supervisor','Field Attendance Approver','Field Attendance Manager'):
        if not frappe.db.exists('Role',name):frappe.get_doc(dict(doctype='Role',role_name=name,desk_access=1)).insert(ignore_permissions=True)


def install():
    roles()
    create_custom_fields({
        'Employee':[
            dict(fieldname='custom_field_attendance_section',label='Supervisor-managed attendance',fieldtype='Section Break',insert_after='attendance_device_id'),
            dict(fieldname='custom_field_attendance_required',label='Supervisor-managed attendance required',fieldtype='Check',insert_after='custom_field_attendance_section'),
            dict(fieldname='custom_field_initial_site',label='Initial Field Site (for new employee import)',fieldtype='Link',options='Field Site',insert_after='custom_field_attendance_required',depends_on='eval:doc.custom_field_attendance_required'),
            dict(fieldname='custom_field_initial_supervisor',label='Initial Field Supervisor (for new employee import)',fieldtype='Link',options='User',insert_after='custom_field_initial_site',depends_on='eval:doc.custom_field_attendance_required'),
            dict(fieldname='custom_field_machine_required',label='Machine or standby required (operator / driver)',fieldtype='Check',insert_after='custom_field_initial_supervisor')],
        'Attendance':[dict(fieldname='custom_field_project',label='Field Project',fieldtype='Link',options='Project',read_only=1,no_copy=1,insert_after='shift'),dict(fieldname='custom_field_entry',label='Approved field attendance evidence',fieldtype='Link',options='Field Attendance Entry',read_only=1,no_copy=1,insert_after='shift')],
    },update=True)
    integrate_hr_navigation()
    frappe.clear_cache()


def integrate_hr_navigation():
    """Add site intent without overwriting HRMS's standard sidebar definitions."""
    from frappe.desk.doctype.custom_sidebar.custom_sidebar import add_site_sidebar_item
    frappe.reload_doc('custom_hr', 'page', 'field_attendance')
    # Remove our former HR Setup shortcut without touching other custom items.
    for name in frappe.get_all('Custom Sidebar', filters={'module': 'HR Setup', 'user': ''}, pluck='name'):
        sidebar = frappe.get_doc('Custom Sidebar', name)
        retained = [item for item in sidebar.sidebar_items
                    if not (item.link_type == 'Page' and item.link_to == 'field-attendance')]
        if len(retained) != len(sidebar.sidebar_items):
            sidebar.set('sidebar_items', retained)
            sidebar.save(ignore_permissions=True)
    add_site_sidebar_item('Shift and Attendance', {
        'type': 'Link', 'label': 'Field Attendance', 'link_type': 'Page',
        'link_to': 'field-attendance', 'icon': 'users', 'child': 0,
    })
