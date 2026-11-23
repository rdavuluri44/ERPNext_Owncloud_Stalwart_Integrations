import frappe
from erpnext_drive_integrations.custom_hr.access import is_manager, site_ids


def after_request(response,request):
    if response.content_type and 'text/html' in response.content_type and not response.direct_passthrough:
        path=request.path or ''
        if path.startswith('/hrms') or path.startswith('/field-team'):
            html=response.get_data(as_text=True)
            script='<script defer src="/assets/erpnext_drive_integrations/custom_hr/launcher.js?v=013"></script>'
            if '</head>' in html and '/assets/erpnext_drive_integrations/custom_hr/launcher.js' not in html:
                response.set_data(html.replace('</head>',script+'</head>',1))
            response.headers['Cache-Control']='no-store, private'
            response.headers['Pragma']='no-cache'


def boot_session(bootinfo):
    # Field Attendance is a function inside HR, not a separate Desktop app.
    bootinfo.app_data = [a for a in (bootinfo.get('app_data') or [])
                         if a.get('app_name') not in ('cloud_team', 'cloud_field')]
