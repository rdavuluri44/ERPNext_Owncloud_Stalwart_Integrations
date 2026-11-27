#!/usr/bin/env python3
"""Initialize one empty ERP site using the pinned native installer.

Never replaces an existing database/site. Secrets travel on stdin, not shell
arguments. Run with the private instance profile and native Coolify receipt.
"""
import argparse
import json
from pathlib import Path
import secrets
import subprocess

INSTALL = r'''
import json,sys,os
from pathlib import Path
import frappe
from frappe.installer import _new_site
p=json.load(sys.stdin)
os.chdir('/home/frappe/frappe-bench/sites')
if Path(p['site']).exists():
    raise SystemExit('Site already exists; fresh initialization refused')
frappe.init(p['site'],new_site=True)
_new_site(db_name=None,site=p['site'],db_root_username='root',
    db_root_password=p['database_root_password'],admin_password=p['administrator_password'],
    install_apps=p['apps'],db_type='mariadb',db_host='db',db_port=3306,
    mariadb_user_host_login_scope='%')
'''


def initialize(runtime, receipt, site):
    runtime=Path(runtime)
    marker=json.loads((runtime/'.cloud-runtime.json').read_text())
    if marker['tier'] not in {'test','production'}:raise ValueError('Unknown deployment tier')
    if not site or Path(site).name!=site:raise ValueError('Invalid site name')
    uid=json.loads(Path(receipt).read_text())['uuid']
    values=json.loads((runtime/'inputs.private.json').read_text())
    credentials=runtime/'initial-administrator.private.json'
    if not credentials.exists():
        credentials.write_text(json.dumps({'password':secrets.token_urlsafe(48)}));credentials.chmod(0o600)
    payload={'site':site,'database_root_password':values['CI_ERP_DB_MYSQL_ROOT_PASSWORD'],
        'administrator_password':json.loads(credentials.read_text())['password'],
        'apps':['erpnext','hrms','india_compliance','insights','erpnext_drive_integrations',
                'payment_integration_utils','razorpayx_integration','india_payroll']}
    compose=Path('/data/coolify/services')/uid/'docker-compose.yml'
    subprocess.run(['docker','compose','-p',uid,'-f',str(compose),'run','--rm','-T','--no-deps',
        '--entrypoint','/home/frappe/frappe-bench/env/bin/python','backend','-c',INSTALL],
        input=json.dumps(payload),text=True,check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for key in ['runtime','receipt','site']:parser.add_argument('--'+key,required=True)
    args=parser.parse_args();initialize(args.runtime,args.receipt,args.site)
