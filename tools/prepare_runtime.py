#!/usr/bin/env python3
"""Prepare portable native service mounts/configuration from a Git checkout.

Run on the Linux deployment host. Operator profile, secrets, generated vendor
artifacts and persistent data must be outside Git. Existing data is never reset.
"""
import argparse
import ipaddress
import html
import json
import os
from pathlib import Path
import re
import secrets
import shutil
from urllib.parse import urlsplit

from render_runtime import render, FAVICON_FILES, public_mappings


def write_private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    path.chmod(0o600)


# (follower, leader) per stack: the follower joins every network of the leader.
NETWORK_PEERS={'drive':[('collaboration','ocis')]}


def missing_peer_networks(compose,project):
    """Networks a follower service lacks compared with its leader (must be empty)."""
    missing=[]
    for follower,leader in NETWORK_PEERS.get(project,[]):
        services=compose.get('services',{})
        if follower in services and leader in services:
            lacking=set(services[leader].get('networks',{}))-set(services[follower].get('networks',{}))
            missing+=[(follower,leader,network) for network in sorted(lacking)]
    return missing


def prepare(source, output, profile):
    source, output = Path(source).resolve(), Path(output).resolve()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Runtime must be outside the source checkout')
    marker = output / '.cloud-runtime.json'
    identity = {'instance': profile['instance'], 'tier': profile['tier']}
    if identity['tier'] not in {'test', 'production'}:
        raise ValueError('tier must be test or production')
    mail_ports = profile.get('production_mail_ports', [])
    if mail_ports and identity['tier'] != 'production':
        raise ValueError('Test may not publish mail protocol ports')
    for binding in mail_ports:
        parts = binding.split(':')
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            raise ValueError('Use explicit IPv4:host-port:container-port mail bindings')
        ipaddress.IPv4Address(parts[0])
        if int(parts[1]) not in {25,465,587,993} or parts[1] != parts[2]:
            raise ValueError('Only matching standard mail protocol ports are supported')
    # Production-only extra port bindings and host entries per service (P45):
    # legacy addresses such as the tailnet DNS listener, private admin ports
    # and fixed SMTP relay addresses that the pre-repository services used.
    bindings = profile.get('production_bindings') or {}
    if bindings and identity['tier'] != 'production':
        raise ValueError('production_bindings are for production only')
    for project_name, services in bindings.items():
        for service_name, extra in services.items():
            unknown = set(extra) - {'ports', 'extra_hosts'}
            if unknown:
                raise ValueError('Unsupported production binding: ' + ', '.join(sorted(unknown)))
            for binding in extra.get('ports', []):
                address, rest = binding.split(':', 1)
                ipaddress.IPv4Address(address)
                host_port, _, container = rest.partition(':')
                container, _, protocol = container.partition('/')
                if not host_port.isdigit() or not container.isdigit() or protocol not in ('', 'tcp', 'udp'):
                    raise ValueError('Use IPv4:host-port:container-port[/tcp|udp] bindings')
            for entry in extra.get('extra_hosts', []):
                name, _, address = entry.partition(':')
                if not re.fullmatch(r'[a-z0-9.-]+', name):
                    raise ValueError('Invalid extra host name')
                ipaddress.IPv4Address(address)
    if output.exists() and (not marker.exists() or json.loads(marker.read_text()) != identity):
        raise ValueError('Existing directory is not this instance runtime')
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    write_private(marker, json.dumps(identity)+'\n')
    hosts = profile['hosts']
    required = {'erp', 'sso', 'drive', 'office', 'mail', 'dms', 'respond'}
    if not required <= hosts.keys() or any(not re.fullmatch(r'[a-z0-9.-]+', host) for host in hosts.values()):
        raise ValueError('Supply all application DNS hostnames')
    # The test-site marker in every app keys on this convention: test
    # hostnames start with test. or test- (shared sign-in excepted), production
    # hostnames never do.
    for name, host in hosts.items():
        test_like = bool(re.match(r'test[.-]', host))
        if name != 'sso' and test_like != (identity['tier'] == 'test'):
            raise ValueError('Test hostnames must start with test. or test-, production ones must not: ' + name)
    replacements = {'example.com':profile['domain']}
    replacements.update({name+'.example.com': host for name, host in hosts.items()})
    replacements.update(profile.get('public_replacements', {}))
    replacements=public_mappings(replacements)
    settings = json.loads((source/'deployment/stacks/inputs.json').read_text())
    values_file = output/'inputs.private.json'
    saved = json.loads(values_file.read_text()) if values_file.exists() else {}
    values = {}
    for name, spec in settings.items():
        if spec['kind'] == 'secret':
            if name in profile.get('settings', {}):
                value = profile['settings'][name]
            elif name in saved:
                value = saved[name]
            elif spec.get('generate'):
                value = secrets.token_urlsafe(48)
                if name.endswith('STALWART_RECOVERY_ADMIN'):
                    value = 'admin:' + value
            else:
                value = None
        else:
            value = profile.get('settings', {}).get(name, spec['default'])
        values[name] = value
    unknown = profile.get('settings', {}).keys() - settings.keys()
    if unknown:
        raise ValueError('Unknown setting names: ' + ', '.join(sorted(unknown)))
    values.update({'RUNTIME_ROOT': str(output), 'WORKSPACE_NETWORK': profile['network'],
                   'ERP_IMAGE': profile['erp_image'], 'MAIL_IMAGE': profile['mail_image']})
    # A deployment may use a different private bench site name. Cookie and Desk
    # behavior are selected by site flags rather than a particular site's name.
    values['CI_ERP_BACKEND_NETBIRD_AUTH_SITE'] = profile.get('site', 'erp.internal')
    values['CI_ERP_FRONTEND_FRAPPE_SITE_NAME_HEADER'] = profile.get('site', 'erp.internal')
    values['CI_ERP_FRONTEND_BACKEND'] = 'erp-backend:8000'
    values['CI_ERP_FRONTEND_SOCKETIO'] = 'erp-websocket:9000'
    values['CI_ERP_WEBSOCKET_NETBIRD_AUTH_REALTIME_BACKEND_ORIGIN'] = 'http://erp-frontend:8080'
    values['CI_ERP_BACKEND_NETBIRD_AUTH_FRONTEND_NETWORK'] = profile['network_subnet']
    # These public client identifiers also appear in browser-side issuer and
    # postMessage guards, not just container environment variables.
    replacements.update(public_mappings({
        'office-web':str(values['CI_DRIVE_OCIS_WEB_OIDC_CLIENT_ID']),
        'office-mail':str(values['CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID'])}))

    def public(text):
        for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
            text = text.replace(old, new)
        return text

    for name,spec in settings.items():
        if spec['kind']=='setting' and name not in profile.get('settings',{}) and isinstance(values[name],str):
            values[name]=public(values[name])

    def substitute(value):
        if isinstance(value, dict):
            return {k: substitute(v) for k,v in value.items()}
        if isinstance(value, list):
            return [substitute(v) for v in value]
        if not isinstance(value, str):
            return value
        def variable(match):
            key = match.group(1)
            replacement = values.get(key)
            if replacement is None:
                raise ValueError('Required private setting is missing: ' + key)
            return str(replacement)
        # Render template literals first. Private overrides and secrets are
        # inserted verbatim: translating them again can double-prefix a test
        # client identifier or corrupt an operator-supplied JSON secret.
        # `$${NAME}` is Compose's escape for a literal `${NAME}` evaluated inside
        # the container (for example the identity database healthcheck); keep it.
        return re.sub(r'(?<!\$)\$\{([A-Z][A-Z0-9_]*)(?::\?[^}]*)?\}', variable, public(value))

    build = output/'rendered'
    if build.exists():
        # This directory contains rendered source only, never application data.
        if not (build/'pyproject.toml').is_file():
            raise ValueError('Unexpected rendered source directory')
    render(source, build, {'domain':profile['domain'], 'public_replacements':replacements,
                           'company_logo':profile.get('company_logo'),'company_favicon_dir':profile.get('company_favicon_dir'),
                           'asset_version':profile.get('commit')})
    projects = profile.get('projects',['erp','drive','editor','mail','dms','processing'])
    mounts = json.loads((source/'deployment/stacks/mounts.json').read_text())
    copy_files = {
        '/opt/cloud/backend_start.py': 'deployment/erp/backend_start.py',
        '/opt/cloud/netbird_realtime.cjs': 'deployment/erp/netbird_realtime.cjs',
        '/templates/nginx/frappe.conf.template': 'deployment/erp/frappe.conf.template',
        '/app/document-worker.py': 'integrations/document-worker/document-worker.py',
        '/etc/nginx/conf.d/default.conf': 'integrations/website/nginx-default.conf',
    }
    copy_dirs = {'/opt/cloud-extension':'integrations/dms',
                 '/templates':'integrations/authentik/invite-recovery/templates',
                 '/srv/public':'integrations/authentik/invite-recovery/public',
                 '/srv/site':'integrations/website/site'}
    persistent_targets = {'/var/lib/cloud-integration','/var/lib/ocis','/state',
        '/usr/src/paperless/data','/usr/src/paperless/media','/usr/src/paperless/consume','/usr/src/paperless/export'}
    # Office editor: ONLYOFFICE only. Collabora was retired after the P42
    # production switch (19 November 2026).
    editor_product = profile.get('editor_product', 'onlyoffice')
    if editor_product == 'collabora':
        raise ValueError('Collabora was retired (P42); use editor_product onlyoffice')
    if editor_product != 'onlyoffice':
        raise ValueError('Unknown editor_product')
    # Reuse data folders that already hold production data (P45), like
    # existing_volumes does for named volumes: only persistent data mounts,
    # existing absolute directories, never created, chowned or emptied here.
    existing_mounts = profile.get('existing_mounts') or {}
    for name, folder in existing_mounts.items():
        item = next((m for m in mounts if m['path'] == name), None)
        folder = Path(folder)
        if item is None or item['target'] not in persistent_targets | {'/cert'}:
            raise ValueError('existing_mounts may only name persistent data mounts: ' + name)
        if not folder.is_absolute() or len(folder.parts) < 3 or not folder.is_dir() or folder.is_symlink():
            raise ValueError('existing mount must be an existing absolute data directory: ' + name)
    def brand_website(site):
        """Fill the tenant-neutral front page from the private profile: names, the
        Employee Zone link, the logo and the favicon set (neutral placeholders if
        the profile supplies none)."""
        def text(key, default):
            value = profile.get(key) or default
            if not isinstance(value, str) or len(value) > 80 or re.search(r'[\x00-\x1f<>]', value):
                raise ValueError(key + ' must be a short plain text')
            return html.escape(value)
        zone = profile.get('website_zone_url') or 'https://'+hosts['erp']+'/'
        if not isinstance(zone, str) or not (zone.startswith('/') and not zone.startswith('//') or zone.startswith('https://')) or re.search(r'[\s"<>]', zone):
            raise ValueError('website_zone_url must be a path or an https URL')
        page = site/'index.html'
        page.write_text(page.read_text().replace('__SITE_TITLE__', text('website_title', 'Welcome'))
                        .replace('__SITE_NAME__', text('website_name', 'Company')).replace('__EMPLOYEE_ZONE_URL__', zone))
        placeholders = build/'erpnext_drive_integrations/public'
        logo = Path(profile['company_logo']) if profile.get('company_logo') else placeholders/'company-logo-approved-v6.svg'
        (site/'front').mkdir(exist_ok=True)
        shutil.copy2(logo, site/'front'/'logo.svg')
        folder = Path(profile['company_favicon_dir']) if profile.get('company_favicon_dir') else None
        for name in FAVICON_FILES:
            shutil.copy2(folder/name if folder else placeholders/('company-'+name), site/'front'/name)
    def mount_path(name):
        return Path(existing_mounts[name]) if name in existing_mounts else output/'mounts'/name
    for item in mounts:
        if item['stack'] not in projects:
            continue
        if item['stack'] == 'editor' and item['service'] != editor_product:
            continue
        path = mount_path(item['path'])
        target = item['target']
        if item['path'] in existing_mounts:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if target in persistent_targets:
            path.mkdir(exist_ok=True, mode=0o750)
            if os.geteuid() == 0:
                uid=10001 if target=='/state' else 1000
                os.chown(path, uid, uid)
            if target == '/var/lib/cloud-integration':
                refresh = path/'test-refresh'
                refresh.mkdir(exist_ok=True, mode=0o750)
                if os.geteuid() == 0:
                    os.chown(refresh,1000,1000)
        elif target in copy_files:
            relative = copy_files[target]
            origin = build/relative if (build/relative).is_file() else source/relative
            path.write_text(public(origin.read_text()))
            path.chmod(0o644)
        elif target in copy_dirs:
            relative = copy_dirs[target]
            origin = build/relative if (build/relative).is_dir() else source/relative
            shutil.copytree(origin,path,dirs_exist_ok=True)
            if target == '/srv/site':
                brand_website(path)
        elif target == '/etc/ocis':
            path.mkdir(exist_ok=True,mode=0o750)
            for origin in (build/'integrations/drive/config').iterdir():
                shutil.copy2(origin,path/origin.name)
            if os.geteuid() == 0:
                os.chown(path,1000,1000)
        elif target == '/run/secrets/document-worker.json':
            if not path.exists():
                worker = json.loads((build/'integrations/document-worker/config.example.json').read_text())
                worker['users'] = []
                write_private(path,json.dumps(worker,indent=2)+'\n')
                if os.geteuid()==0:os.chown(path,10001,10001)
        elif item['stack'] == 'editor':
            origin = {'/etc/onlyoffice/documentserver/local-production-linux.json': source/'deployment/config/onlyoffice-local-production-linux.json',
                      '/var/www/onlyoffice/documentserver/web-apps/apps/api/wopi/editor-wopi.ejs': source/'integrations/onlyoffice/editor-wopi.ejs'}[target]
            shutil.copy2(origin, path)
            path.chmod(0o644)
        # Optional private DNS and identity gateway mounts are configured by
        # their separate operator-owned modules; selected stacks must not use
        # missing mounts (checked below).

    # Native oCIS serves these public extensions from its persistent web assets.
    drive_data = next(mount_path(m['path']) for m in mounts if m['target']=='/var/lib/ocis')
    config = json.loads((build/'integrations/drive/config/web-with-picker.json').read_text()) if 'drive' in projects else {}
    if config and profile.get('identity_results'):
        # A shared global issuer can serve several clients. Its root discovery
        # route may have production-only CORS; use this application's native
        # discovery endpoint without changing the global token issuer.
        clients = json.loads(Path(profile['identity_results']).read_text())
        slug = clients['office']['slug']
        if not re.fullmatch(r'[a-z0-9-]+', slug):
            raise ValueError('Invalid Drive application slug')
        config['openIdConnect']['metadata_url'] = 'https://'+hosts['sso']+'/application/o/'+slug+'/.well-known/openid-configuration'
    for script in config.get('scripts',[]):
        url = urlsplit(script['src']).path
        if not url.startswith('/assets/apps/') or '..' in Path(url).parts:
            raise ValueError('Unexpected Drive extension asset location')
        origin = 'mail-picker.js' if 'mail-picker' in url else 'workspace.js'
        destination = drive_data/'web'/url.lstrip('/')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(build/'integrations/drive'/origin,destination)
        if os.geteuid() == 0:
            for parent in [destination,destination.parent,destination.parent.parent,drive_data/'web/assets',drive_data/'web']:
                os.chown(parent,1000,1000)
        if profile.get('commit'):
            script['src']=url+'?v='+profile['commit']
    if config:
        drive_config = next(output/'mounts'/m['path'] for m in mounts if m['target']=='/etc/ocis')
        (drive_config/'web-with-picker.json').write_text(json.dumps(config,indent=2)+'\n')

    for project in projects:
        stack_name = 'editor-onlyoffice' if project == 'editor' else project
        template = source/'deployment/stacks'/(stack_name+'.compose.json')
        compose = substitute(json.loads(template.read_text()))
        if project == 'mail':
            compose['services']['stalwart']['ports'].extend(mail_ports)
            policy_file = output/'mail-policy.json'
            write_private(policy_file,json.dumps({'features':{'filesEnabled':False}},indent=2)+'\n')
            policy_file.chmod(0o644)
            webmail=compose['services']['webmail']
            webmail['volumes'].append(str(policy_file)+':/app/data/admin/policy.json:ro')
            ver='?v='+profile['commit'] if profile.get('commit') else ''
            logo='https://'+hosts['erp']+'/assets/erpnext_drive_integrations/company-logo-approved-v6.svg'+ver
            favicon='https://'+hosts['erp']+'/assets/erpnext_drive_integrations/company-favicon.svg'+ver
            webmail['environment'].update({'FAVICON_URL':favicon,'LOGIN_LOGO_LIGHT_URL':logo,
                'LOGIN_LOGO_DARK_URL':logo,'APP_LOGO_LIGHT_URL':'','APP_LOGO_DARK_URL':'','APP_NAME':'Mail'})
        for name, folder in existing_mounts.items():
            rendered = str(output/'mounts'/name) + ':'
            for service in compose['services'].values():
                service['volumes'] = [v.replace(rendered, str(Path(folder)) + ':', 1) if v.startswith(rendered) else v
                                      for v in service.get('volumes', [])]
        for name,service in compose['services'].items():
            service.pop('extra_hosts',None)
            for network in service.get('networks',{}).values():
                if isinstance(network,dict) and 'aliases' in network:
                    network['aliases'] = [a for a in network['aliases'] if not re.search(r'[a-z0-9]{24}',a)]
            if project=='erp':
                service.setdefault('environment',{})['CLOUD_DEPLOYMENT_TIER']=profile['tier']
                if profile['tier']=='test' and name in {'scheduler','queue-short','queue-long'}:
                    service['profiles']=['manual-workers']
            if project=='processing' and name=='document-worker':
                service['profiles']=['enrolled-worker']
            extra = bindings.get(project, {}).get(name, {})
            if extra.get('ports'):
                service['ports'] = list(dict.fromkeys((service.get('ports') or []) + list(extra['ports'])))
            if extra.get('extra_hosts'):
                service['extra_hosts'] = list(extra['extra_hosts'])
            for volume in service.get('volumes',[]):
                host=volume.split(':',1)[0]
                if host.startswith('/') and not Path(host).exists():
                    raise ValueError('Missing prepared mount for '+project+'/'+name+': '+host)
        # Reuse volumes that already hold data (for example production's
        # pre-repository volumes) instead of creating new empty ones. The
        # profile maps this stack's logical volume names to existing names.
        for logical,existing in (profile.get('existing_volumes') or {}).get(project,{}).items():
            if logical not in compose.get('volumes',{}):
                raise ValueError('Unknown volume '+logical+' for '+project)
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',existing):
                raise ValueError('Invalid existing volume name for '+logical)
            compose['volumes'][logical]={'external':True,'name':existing}
        # Keep legacy network names working during a migration (P37): extra
        # aliases on the stack's own networks, or extra existing external
        # networks with aliases, per service.
        for service_name,networks in (profile.get('extra_networks') or {}).get(project,{}).items():
            if service_name not in compose['services']:
                raise ValueError('Unknown service '+service_name+' for '+project)
            service=compose['services'][service_name]
            for network,aliases in networks.items():
                for name in [network,*aliases]:
                    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',name):raise ValueError('Invalid network or alias name')
                attached=service.setdefault('networks',{})
                if network not in compose.get('networks',{}):
                    compose.setdefault('networks',{})[network]={'external':True,'name':network}
                entry=attached.get(network) or {}
                entry['aliases']=list(dict.fromkeys((entry.get('aliases') or [])+list(aliases)))
                attached[network]=entry
        # P57: some services reach each other through a service registry that
        # advertises one of the leader's own addresses, chosen at random at every
        # start. The follower must therefore be on every network the leader is on,
        # whatever the profile adds to either (the editor bridge could not reach
        # oCIS after a reboot because oCIS advertised its proxy-network address).
        for follower,leader in NETWORK_PEERS.get(project,[]):
            if follower in compose['services'] and leader in compose['services']:
                have=compose['services'][follower].setdefault('networks',{})
                for network in compose['services'][leader].get('networks',{}):
                    have.setdefault(network,{})
        write_private(output/'compose'/(project+'.json'),json.dumps(compose,indent=2)+'\n')
    write_private(values_file,json.dumps(values,indent=2)+'\n')
    write_private(output/'ready.json',json.dumps({'instance':identity['instance'],
        'tier':identity['tier'],'projects':projects},indent=2)+'\n')
    return output


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--profile',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(prepare(args.source,args.output,json.loads(Path(args.profile).read_text())))
