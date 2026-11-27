#!/usr/bin/env python3
"""Derive root-private test refresh/bootstrap profiles from native receipts.

Operator identity/SSO inputs remain outside Git. No browser process receives
these files. Refresh remains disabled in ERP until its source export is ready.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import yaml

from prepare_ingress import test_identity_origin


def native_site_settings(clients):
    """Native apps under test (`"native": true` with a fixed client_id) become the
    only native clients portal/mobile.py accepts on test; bootstrap otherwise keeps
    native sign-in off on test copies."""
    native=[c for c in clients if c.get('native')]
    if any(not c.get('client_id') for c in native):raise ValueError('A native test OAuth client needs a fixed client_id')
    if not native:return {}
    return {'cloud_native_mobile_enabled':True,'cloud_native_mobile_clients':[str(c['client_id']) for c in native]}


def prepare(source,runtime,receipts,profile,output):
    source,runtime,receipts,output=map(lambda p:Path(p).resolve(),[source,runtime,receipts,output])
    if profile.get('tier')!='test':raise ValueError('Only test profiles are supported')
    output.mkdir(parents=True,exist_ok=True,mode=0o700)
    clients=json.loads(Path(profile['identity_results']).read_text())
    mounts=json.loads((source/'deployment/stacks/mounts.json').read_text())
    def path(target):
        matches={m['path'] for m in mounts if m['target']==target}
        if len(matches)!=1:raise ValueError('Ambiguous shared mount target')
        return str(runtime/'mounts'/matches.pop())
    def write(name,value,uid=0):
        file=output/name;file.write_text(json.dumps(value,indent=2)+'\n');file.chmod(0o600);os.chown(file,uid,uid)
        return str(file)
    native={};projects=[];applications=[]
    for name in ['erp','drive','editor','mail','dms','processing']:
        uid=json.loads((receipts/(name+'.json')).read_text())['uuid'];projects.append(uid)
        spec=yaml.safe_load((Path('/data/coolify/services')/uid/'docker-compose.yml').read_text())
        native[name]={key:row['container_name'] for key,row in spec['services'].items()}
        for key,row in spec['services'].items():
            if key in {'db','redis-cache','redis-queue','database','broker','configurator'}:continue
            name=row['container_name']
            if subprocess.run(['docker','inspect',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
                applications.append(name)
    containers={'erp_backend':native['erp']['backend'],'erp_database':native['erp']['db'],
        'redis_queue':native['erp']['redis-queue'],'redis_cache':native['erp']['redis-cache'],'dms':native['dms']['paperless'],
        'dms_database':native['dms']['database'],'dms_broker':native['dms']['broker'],
        'drive':native['drive']['ocis'],'drive_collaboration':native['drive']['collaboration'],
        'mail':native['mail']['stalwart']}
    worker_container=native['processing']['document-worker']
    if worker_container in applications:containers['document_worker']=worker_container
    hosts=profile['hosts'];values=json.loads((runtime/'inputs.private.json').read_text())
    owner=profile['administrator_email']
    erp={'tier':'test','host_name':'https://'+hosts['erp'],'sso_url':'https://'+hosts['sso'],
        'issuer':clients['erpnext']['issuer'],'client_id':clients['erpnext']['client_id'],
        'client_secret':clients['erpnext']['client_secret'],'administrator_email':owner,
        'administrator_name':profile.get('administrator_name','Administrator'),
        'features':{'portal':True,'custom_hr':True,'onboarding':True},'refresh_ready':profile.get('refresh_ready') is True,
        'refresh_users':profile.get('refresh_users',[owner]),'site_settings':{'hov_respond_host':hosts['respond']}}
    if origin := test_identity_origin(profile):
        if not erp['issuer'].startswith(origin + '/application/o/'):
            raise ValueError('The test ERP issuer does not belong to the isolated identity origin')
        erp['sso_url'] = origin
        erp['site_settings']['cloud_test_identity_origin'] = origin
    if profile.get('test_oauth_clients'):
        # P38: app OAuth clients blocked on production, re-enabled on test.
        erp['test_oauth_clients']=profile['test_oauth_clients']
        erp['site_settings'].update(native_site_settings(profile['test_oauth_clients']))
    # The test site's own look for shared pages (owner rule: separate asset sets); allow list only.
    look=profile.get('erp_site_settings') or {}
    allowed={'cloud_portal_hide_entity_name','cloud_portal_logo_height','cloud_portal_logo_position','cloud_portal_clean_root_address'}
    if set(look)-allowed:raise ValueError('erp_site_settings may only set: '+', '.join(sorted(allowed)))
    erp['site_settings'].update(look)
    form_smtp=profile.get('test_form_smtp')
    if form_smtp:
        # Owner-approved real form emails from the test copy (P38): a dedicated
        # account only; the password comes from a root-only file, never Git.
        missing=[k for k in ('host','user','sender','password_file') if not form_smtp.get(k)]
        if missing:raise ValueError('test_form_smtp lacks '+', '.join(missing))
        erp['site_settings']['cloud_test_form_smtp']={'host':form_smtp['host'],'port':int(form_smtp.get('port',465)),
            'address':form_smtp.get('address') or form_smtp['host'],
            'user':form_smtp['user'],'sender':form_smtp['sender'],
            'password':Path(form_smtp['password_file']).read_text().strip()}
    erp_file=write('erp-bootstrap.private.json',erp,1000)
    mail={'tier':'test','admin_url':'http://127.0.0.1:'+str(values['CI_MAIL_STALWART_HOST_PORT']),
        'container':containers['mail'],'public_url':'https://'+hosts['mail'],
        'recovery_credential':values['CI_MAIL_STALWART_STALWART_RECOVERY_ADMIN'],
        'issuer':clients['office-mail']['issuer'],'client_id':clients['office-mail']['client_id'],
        'mail_domain':profile['mail_domain'],'accounts':profile.get('mail_accounts',[])}
    mail_file=write('mail-bootstrap.private.json',mail)
    enrollment={'tier':'test','source':str(source),'administrator_email':owner,'users':[],
        'drive_container':containers['drive'],'dms_container':containers['dms'],
        'files_url':'https://'+hosts['drive'],'paperless_url':'http://dms-paperless:8000',
        'paperless_public_url':'https://'+hosts['dms'],'office_space_id':'','office_processor':owner,
        'worker_config':path('/run/secrets/document-worker.json'),'worker_state':path('/state'),
        'source_files_origins':profile['source_files_origins'],'source_dms_origins':profile['source_dms_origins']}
    enrollment_file=write('worker-enrollment.private.json',enrollment)
    refresh={'tier':'test','instance':profile['instance'],'source_instance':profile.get('source_instance','production'),
        'source':str(source),'runtime':str(runtime),'runtime_profile':profile['_profile_path'],
        'site':profile.get('site','erp.internal'),'test_erp_url':'https://'+hosts['erp'],
        'containers':containers,'application_containers':applications,'target_projects':projects,
        'erp_project':json.loads((receipts/'erp.json').read_text())['uuid'],
        'document_worker_state':path('/state'),'state_root':str(runtime.parent/'refresh'),
        'request_directory':str(Path(path('/var/lib/cloud-integration'))/'test-refresh'),
        'erp_bootstrap_profile':erp_file,'mail_bootstrap_profile':mail_file,
        'worker_enrollment_profile':enrollment_file,'allowed_users':erp['refresh_users'],
        'export_ssh':profile.get('export_ssh',{}),'max_snapshot_bytes':profile.get('max_snapshot_bytes',20*1024**3)}
    refresh_file=write('test-refresh.private.json',refresh)
    return {'refresh_profile':refresh_file,'public_button_enabled':erp['refresh_ready']}


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['source','runtime','receipts','profile','output']:p.add_argument('--'+key,required=True)
    a=p.parse_args();profile=json.loads(Path(a.profile).read_text());profile['_profile_path']=str(Path(a.profile).resolve())
    print(prepare(a.source,a.runtime,a.receipts,profile,a.output))
