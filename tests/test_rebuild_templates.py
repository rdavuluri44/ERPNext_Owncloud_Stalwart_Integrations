"""Check portable graph, database isolation and native runtime generation."""
import importlib.util
import json
import re
import yaml
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from authentik_blueprint import retained
from prepare_runtime import prepare
from prepare_ingress import prepare as ingress
from prepare_auth_bridge import prepare as auth_bridge


class Reconstruction(unittest.TestCase):
    def test_test_runtime_cannot_publish_mail_protocols(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'Test may not publish'):
                prepare(ROOT,Path(folder)/'runtime',{'instance':'isolated','tier':'test',
                    'production_mail_ports':['0.0.0.0:25:25']})
    def test_mail_private_overrides_are_not_translated_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            profile={'instance':'mail-test','tier':'test','domain':'example.net',
                'hosts':{k:('test.example.net' if k=='erp' else 'test-'+k+'.example.net') for k in
                    ['erp','sso','drive','office','mail','dms','respond']},
                'network':'isolated-workspace','network_subnet':'10.44.0.0/24',
                'erp_image':'example/erp:test','mail_image':'example/mail:test','projects':['mail'],
                'settings':{'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'test-office-mail',
                    'CI_MAIL_WEBMAIL_OAUTH_ISSUER_URL':'https://sso.example.net/application/o/test-office-mail/',
                    'CI_MAIL_WEBMAIL_SESSION_SECRET':'literal-office-mail-example.com-private-value'}}
            output=Path(folder)/'runtime';prepare(ROOT,output,profile)
            env=json.loads((output/'compose/mail.json').read_text())['services']['webmail']['environment']
            self.assertEqual(env['OAUTH_CLIENT_ID'],'test-office-mail')
            self.assertEqual(env['OAUTH_ISSUER_URL'],'https://sso.example.net/application/o/test-office-mail/')
            self.assertEqual(env['SESSION_SECRET'],'literal-office-mail-example.com-private-value')
    def test_onlyoffice_editor_replaces_collabora(self):
        with tempfile.TemporaryDirectory() as folder:
            hosts={k:('test.example.net' if k=='erp' else ('sso.example.net' if k=='sso' else 'test-'+k+'.example.net')) for k in
                   ['erp','sso','drive','office','mail','dms','respond']}
            profile={'instance':'oo-test','tier':'test','domain':'example.net','hosts':hosts,
                'network':'isolated-workspace','network_subnet':'10.44.0.0/24','editor_product':'onlyoffice',
                'erp_image':'example/erp:test','mail_image':'example/mail:test','projects':['drive','editor'],
                'settings':{'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'}}
            output=Path(folder)/'runtime';prepare(ROOT,output,profile)
            editor=json.loads((output/'compose/editor.json').read_text())['services']
            self.assertEqual(list(editor),['onlyoffice'])
            self.assertRegex(editor['onlyoffice']['image'],r'^onlyoffice/documentserver@sha256:[0-9a-f]{64}$')
            env=editor['onlyoffice']['environment']
            self.assertEqual((env['JWT_ENABLED'],env['WOPI_ENABLED']),('true','true'))
            self.assertGreaterEqual(len(env['JWT_SECRET']),32)
            config=json.loads((output/'mounts/editor_onlyoffice_0').read_text())
            self.assertTrue(config['services']['CoAuthoring']['autoAssembly']['enable'], 'periodic save to Drive')
            self.assertFalse(config['services']['CoAuthoring']['request-filtering-agent']['allowMetaIPAddress'])
            self.assertEqual(config['services']['CoAuthoring']['ipfilter']['rules'][0],{'address':'office-collaboration','allowed':True}, 'ONLYOFFICE 10 only calls WOPI hosts named in ipfilter')
            self.assertFalse((output/'mounts/editor_collabora_1').exists(), 'no Collabora files rendered')
            drive=json.loads((output/'compose/drive.json').read_text())['services']['collaboration']['environment']
            self.assertEqual((drive['COLLABORATION_APP_NAME'],drive['COLLABORATION_APP_PRODUCT']),('OnlyOffice','OnlyOffice'))
            self.assertEqual(drive['COLLABORATION_APP_ADDR'],'https://test-office.example.net')
            self.assertTrue(drive['COLLABORATION_APP_ICON'].startswith('https://test-office.example.net/web-apps/'))
            registry=(output/'mounts'/[m['path'] for m in json.loads((ROOT/'deployment/stacks/mounts.json').read_text()) if m['target']=='/etc/ocis'][0]/'app-registry.yaml').read_text()
            self.assertNotIn('CollaboraOnline',registry,'Drive must not default to the removed editor')
            self.assertIn('default_app: OnlyOffice',registry)
            ocis=json.loads((output/'compose/drive.json').read_text())['services']['ocis']['environment']
            self.assertEqual(ocis['FRONTEND_APP_HANDLER_SECURE_VIEW_APP_ADDR'],'com.owncloud.api.collaboration.OnlyOffice')
            routes=ingress(ROOT,profile)['http']['services']
            office=[k for k in routes if k.endswith('office')]
            self.assertEqual([routes[k]['loadBalancer']['servers'][0]['url'] for k in office],['http://editor-onlyoffice:80'])
            with self.assertRaises(ValueError):prepare(ROOT,Path(folder)/'r2',dict(profile,editor_product='wordpad'))
            # Collabora was retired after the P42 production switch.
            with self.assertRaisesRegex(ValueError,'retired'):prepare(ROOT,Path(folder)/'r3',dict(profile,editor_product='collabora'))
            # ONLYOFFICE is the default when a profile names no editor.
            plain={k:v for k,v in profile.items() if k!='editor_product'}
            prepare(ROOT,Path(folder)/'r4',plain)
            self.assertEqual(list(json.loads((Path(folder)/'r4/compose/editor.json').read_text())['services']),['onlyoffice'])
            self.assertFalse((ROOT/'deployment/stacks/editor.compose.json').exists())
            self.assertFalse((ROOT/'integrations/collabora').exists())
    def test_identity_stack_renders_with_restored_secrets(self):
        # P44: the sign-in stack renders, keeps Compose's $${VAR} escapes and
        # uses the secret key supplied from the backup, not a new one.
        with tempfile.TemporaryDirectory() as folder:
            hosts={k:('test.example.net' if k=='erp' else 'test-'+k+'.example.net') for k in
                   ['erp','sso','drive','office','mail','dms','respond']}
            key='restored-production-key-'+'x'*40
            profile={'instance':'identity-test','tier':'test','domain':'example.net','hosts':hosts,
                'network':'isolated-workspace','network_subnet':'10.44.0.0/24',
                'erp_image':'example/erp:test','mail_image':'example/mail:test','projects':['identity'],
                'settings':{'CI_IDENTITY_SERVER_AUTHENTIK_SECRET_KEY':key,'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'}}
            output=Path(folder)/'runtime';prepare(ROOT,output,profile)
            stack=json.loads((output/'compose/identity.json').read_text())
            self.assertEqual(stack['services']['server']['environment']['AUTHENTIK_SECRET_KEY'],key)
            self.assertEqual(stack['services']['worker']['environment']['AUTHENTIK_SECRET_KEY'],key)
            self.assertIn('$${POSTGRES_DB}',json.dumps(stack['services']['postgresql']['healthcheck']))
    def test_existing_mounts_reuse_production_data_folders(self):
        # P45: production Drive keeps its data folder; nothing is created,
        # emptied or re-owned there, and only persistent data mounts qualify.
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)/'srv/files/data'; data.mkdir(parents=True); (data/'keep.txt').write_text('x')
            hosts={k:('test.example.net' if k=='erp' else 'test-'+k+'.example.net') for k in
                   ['erp','sso','drive','office','mail','dms','respond']}
            profile={'instance':'p45-test','tier':'test','domain':'example.net','hosts':hosts,
                'network':'isolated-workspace','network_subnet':'10.44.0.0/24','erp_image':'example/erp:test',
                'mail_image':'example/mail:test','projects':['drive'],
                'settings':{'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'},
                'existing_mounts':{'drive_ocis_1':str(data)}}
            output=Path(folder)/'runtime';prepare(ROOT,output,profile)
            ocis=json.loads((output/'compose/drive.json').read_text())['services']['ocis']['volumes']
            self.assertIn(str(data)+':/var/lib/ocis',ocis)
            self.assertFalse((output/'mounts/drive_ocis_1').exists())
            self.assertEqual((data/'keep.txt').read_text(),'x')
            self.assertTrue(any((data/'web/assets/apps').iterdir()),'Drive add-ons installed into the reused data folder')
            for bad in [{'drive_ocis_0':str(data)},{'drive_ocis_1':'relative/path'},{'drive_ocis_1':str(Path(folder)/'missing')}]:
                with self.assertRaises(ValueError):prepare(ROOT,Path(folder)/'r2',dict(profile,existing_mounts=bad))
    def test_test_site_marker_in_every_app_and_hostname_rule(self):
        # Owner, 19 Nov 2026: rows were entered on the test site by mistake;
        # every app now shows a TEST SITE marker on test hostnames only.
        for path in ['erpnext_drive_integrations/public/session.js', 'erpnext_drive_integrations/www/place_holder.html',
                     'integrations/drive/workspace.js', 'integrations/onlyoffice/editor-wopi.ejs',
                     'integrations/dms/cloud_session/session.js', 'integrations/mail/overlay/components/cloud-test-marker.tsx']:
            text = (ROOT/path).read_text()
            self.assertIn("cloud-test-marker", text, path)
            self.assertIn("/^test[.-]/.test(location.hostname)", text, path)
            self.assertIn("window.top!==window", text, path)
        self.assertIn('<CloudTestMarker />', (ROOT/'integrations/mail/overlay/app/(main)/layout.tsx').read_text())
        with tempfile.TemporaryDirectory() as folder:
            hosts={k:('test.example.net' if k=='erp' else 'test-'+k+'.example.net') for k in
                   ['erp','sso','drive','office','mail','dms','respond']}
            base={'instance':'marker','tier':'test','domain':'example.net','hosts':hosts,'network':'n',
                  'network_subnet':'10.44.0.0/24','erp_image':'e','mail_image':'m','projects':['drive'],
                  'settings':{'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'}}
            prepare(ROOT,Path(folder)/'ok',base)
            with self.assertRaises(ValueError):
                prepare(ROOT,Path(folder)/'bad1',dict(base,hosts=dict(hosts,drive='drive.example.net')))
            with self.assertRaises(ValueError):
                prepare(ROOT,Path(folder)/'bad2',dict(base,tier='production'))
    def test_coolify_registration_drops_empty_ports_and_volumes(self):
        # Coolify writes an empty volumes list back as {} (seen registering
        # production processing, 19 Nov 2026); omit empty sequences instead.
        source=(ROOT/'tools/coolify_native.py').read_text()
        self.assertIn("for field in ('ports','volumes'):", source)
        self.assertIn("if service.get(field)==[]:service.pop(field)", source)
    def test_production_bindings_are_validated_and_production_only(self):
        # P45: legacy tailnet listeners, private admin ports and fixed relay
        # addresses carried into repository stacks, production tier only.
        with tempfile.TemporaryDirectory() as folder:
            hosts={k:k+'.example.net' for k in ['erp','sso','drive','office','mail','dms','respond']}
            base={'instance':'bind','tier':'production','domain':'example.net','hosts':hosts,'network':'n',
                  'network_subnet':'10.44.0.0/24','erp_image':'e','mail_image':'m','projects':['identity'],
                  'settings':{'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'},
                  'production_bindings':{'identity':{'server':{'ports':['100.64.0.1:19000:9000'],
                                                               'extra_hosts':['mx.example.net:10.45.0.1']}}}}
            prepare(ROOT,Path(folder)/'ok',base)
            server=json.loads((Path(folder)/'ok/compose/identity.json').read_text())['services']['server']
            self.assertIn('100.64.0.1:19000:9000',server['ports'])
            self.assertEqual(server['extra_hosts'],['mx.example.net:10.45.0.1'])
            for bad in [{'identity':{'server':{'ports':['not-an-ip:1:2']}}},
                        {'identity':{'server':{'extra_hosts':['bad host:10.0.0.1']}}},
                        {'identity':{'server':{'command':['x']}}}]:
                with self.assertRaises(ValueError):prepare(ROOT,Path(folder)/'bad',dict(base,production_bindings=bad))
            test_hosts={k:('test.example.net' if k=='erp' else ('sso.example.net' if k=='sso' else 'test-'+k+'.example.net')) for k in hosts}
            with self.assertRaises(ValueError):
                prepare(ROOT,Path(folder)/'t',dict(base,tier='test',hosts=test_hosts))
    def test_remote_auth_bridge_has_fixed_host_and_source_ip_restriction(self):
        profile={'tier':'test','hosts':{'erp':'test.example.net','sso':'sso.example.net'},
                 'test_server_ip':'192.0.2.20','identity_service':'identity@file'}
        http=auth_bridge(profile)['http']
        self.assertEqual(http['middlewares']['cloud-test-auth-source']['ipAllowList']['sourceRange'],['192.0.2.20/32'])
        self.assertEqual(http['middlewares']['cloud-test-auth-context']['headers']['customRequestHeaders']['X-Forwarded-Host'],'test.example.net')
        with self.assertRaises(ValueError):auth_bridge(dict(profile,tier='production'))
    def test_auth_bridge_private_entrypoint_has_its_own_allow_list(self):
        profile={'tier':'test','hosts':{'erp':'test.example.net','sso':'sso.example.net'},
                 'test_server_ip':['192.0.2.20','198.51.100.7'],'identity_service':'identity@file',
                 'auth_bridge_private':{'entrypoint':'private','sources':['10.0.1.1']}}
        http=auth_bridge(profile)['http'];r=http['routers'];m=http['middlewares']
        self.assertEqual(r['cloud-test-auth-context']['entryPoints'],['https'])
        self.assertEqual(m['cloud-test-auth-source']['ipAllowList']['sourceRange'],['192.0.2.20/32','198.51.100.7/32'])
        self.assertEqual(r['cloud-test-auth-context-private']['entryPoints'],['private'])
        self.assertEqual(r['cloud-test-auth-context-private']['middlewares'][0],'cloud-test-auth-private-source')
        self.assertEqual(m['cloud-test-auth-private-source']['ipAllowList']['sourceRange'],['10.0.1.1/32'])
        self.assertEqual(r['cloud-test-outpost']['entryPoints'],['https','private'])
        relayed=auth_bridge(dict(profile,relay_target='100.64.0.20'))['http']
        self.assertEqual(relayed['routers']['cloud-test-outpost']['entryPoints'],['private'],'relay owns public HTTPS for test hosts')
        # A relayed test host trusts no public address (a retired host's address
        # could be reassigned); test_server_ip is then not needed.
        self.assertNotIn('cloud-test-auth-context',relayed['routers'])
        self.assertNotIn('cloud-test-auth-source',relayed['middlewares'])
        bare={k:v for k,v in profile.items() if k!='test_server_ip'}
        self.assertIn('cloud-test-auth-context-private',auth_bridge(dict(bare,relay_target='100.64.0.20'))['http']['routers'])
        with self.assertRaises(ValueError):auth_bridge(dict(profile,relay_target='100.64.0.20',auth_bridge_private=None))
        self.assertNotIn('&id',yaml.safe_dump(auth_bridge(profile)),'plain YAML without anchors')
        self.assertNotIn('cloud-test-auth-context-private',auth_bridge(dict(profile,auth_bridge_private=None))['http']['routers'])
        for bad in [dict(profile,test_server_ip=[]),dict(profile,test_server_ip=['0.0.0.0/0']),
                    dict(profile,auth_bridge_private={'entrypoint':'https','sources':['10.0.1.1']}),
                    dict(profile,auth_bridge_private={'entrypoint':'private','sources':[]})]:
            with self.assertRaises(ValueError):auth_bridge(bad)
    def test_egress_allows_pinned_private_sso_address_only_for_sso(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from test_egress import allowed_sso_addresses
        profile={'hosts':{'sso':'sso.example.net'},'proxy_hosts':{'sso.example.net':'100.64.0.10','other.example.net':'100.64.0.11'}}
        self.assertEqual(allowed_sso_addresses(profile,lambda h:{'192.0.2.5'}),{'192.0.2.5','100.64.0.10'})
        self.assertEqual(allowed_sso_addresses({'hosts':{'sso':'sso.example.net'}},lambda h:{'192.0.2.5'}),{'192.0.2.5'})
        with self.assertRaises(ValueError):allowed_sso_addresses(dict(profile,proxy_hosts={'sso.example.net':'::1'}),lambda h:set())
    def test_every_certificate_name_answers_its_http_challenge(self):
        # P11: a name whose route asks for a certificate must have a port-80 challenge route that outranks
        # every other port-80 route for that name; otherwise a host-wide redirect takes the challenge.
        files=[*sorted((ROOT/'deployment/config/proxy').glob('*.y*ml')),*sorted((ROOT/'deployment/production').glob('*.traefik.yaml'))]
        routers=[]
        for f in files:
            routers+=list(((yaml.safe_load(f.read_text()) or {}).get('http') or {}).get('routers',{}).values())
        hosts=lambda r:set(re.findall(r'Host\([`"]([^`"]+)[`"]\)',r['rule']))
        challenge=lambda r:'PathPrefix(`/.well-known/acme-challenge/`)' in r['rule']
        priority=lambda r:r.get('priority',len(r['rule']))
        named=set().union(*(hosts(r) for r in routers if (r.get('tls') or {}).get('certResolver')))
        self.assertTrue({'erp.example.com','sso.example.com','drive.example.com','respond.example.com','www.example.com'}<=named)
        for host in sorted(named):
            port80=[r for r in routers if 'http' in r.get('entryPoints',[]) and host in hosts(r)]
            answers=[priority(r) for r in port80 if challenge(r)]
            others=[priority(r) for r in port80 if not challenge(r)]
            self.assertTrue(answers,host+': no port-80 challenge route')
            self.assertGreater(max(answers),max(others,default=0),host+': another port-80 route outranks the challenge')
    def test_mail_host_challenge_goes_to_the_repository_mail_service(self):
        # Stalwart renews its own SMTP/IMAP certificate for the mail host; the challenge route must name the
        # service the repository's mail routes define (the pre-repository Docker-label service is gone, P45).
        acme=yaml.safe_load((ROOT/'deployment/config/proxy/office-acme.yml').read_text())['http']['routers']
        mail=yaml.safe_load((ROOT/'deployment/production/mail.traefik.yaml').read_text())['http']
        service=acme['office-smtp-acme-validation']['service']
        self.assertTrue(service.endswith('@file'),service)
        self.assertIn(service.split('@')[0],mail['services'])
    def test_test_relay_terminates_and_forwards_only_test_hosts(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from prepare_test_relay import prepare as relay
        hosts={'erp':'test.example.net','drive':'test-drive.example.net','office':'test-office.example.net',
               'mail':'test-mail.example.net','dms':'test-dms.example.net','respond':'test-respond.example.net'}
        out=relay({'tier':'test','hosts':dict(hosts,sso='sso.example.net'),'relay_target':'100.64.0.20'})
        self.assertNotIn('tcp',out,'no SNI pass-through: browsers coalesce connections')
        http=out['http']
        for host in hosts.values():
            key='cloud-test-relay-'+host.split('.')[0]
            self.assertEqual(http['routers'][key]['rule'],'Host(`'+host+'`)')
            self.assertEqual(http['routers'][key]['tls'],{'certResolver':'letsencrypt-tls'},
                             'own certificate per name, proved on port 443 (P11)')
            self.assertEqual(http['serversTransports'][key],{'serverName':host},'verify the test host certificate per name')
            self.assertEqual(http['services'][key]['loadBalancer']['servers'],[{'url':'https://100.64.0.20'}])
        port80=[r for r in http['routers'].values() if 'http' in r['entryPoints']]
        self.assertEqual([r['service'] for r in port80],['cloud-test-relay-http'],
                         'port 80, challenges included, goes to the test host, which renews through the relay')
        self.assertNotIn('sso.example.net',yaml.safe_dump(out))
        with self.assertRaises(ValueError):relay({'tier':'production','hosts':hosts,'relay_target':'100.64.0.20'})
        with self.assertRaises(ValueError):relay({'tier':'test','hosts':dict(hosts,erp='erp.example.net'),'relay_target':'100.64.0.20'})
    def test_tls_resolver_flags_are_added_once_and_keep_the_rest(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from coolify_proxy_hosts import apply
        from coolify_proxy_tls_resolver import running_has
        text="services:\n  traefik:\n    command:\n    - --ping=true\n    - --certificatesresolvers.letsencrypt.acme.httpchallenge=true\n"
        once=apply(text,{},tls_resolver='letsencrypt-tls')
        command=yaml.safe_load(apply(once,{},tls_resolver='letsencrypt-tls'))['services']['traefik']['command']
        self.assertEqual(command,['--ping=true','--certificatesresolvers.letsencrypt.acme.httpchallenge=true',
                                  '--certificatesresolvers.letsencrypt-tls.acme.tlschallenge=true',
                                  '--certificatesresolvers.letsencrypt-tls.acme.storage=/traefik/acme.json'])
        with self.assertRaises(ValueError):apply(text,{},tls_resolver='bad name')
        import types
        run=lambda argv,**kw:types.SimpleNamespace(stdout=json.dumps(command))
        self.assertTrue(running_has(run=run))
        self.assertFalse(running_has(run=lambda argv,**kw:types.SimpleNamespace(stdout=json.dumps(command[:2]))))
    def test_relayed_ingress_clears_remembered_http3(self):
        import inspect
        source=inspect.getsource(ingress)
        self.assertIn("'Alt-Svc':'clear'",source)
        self.assertIn("['alt-svc-clear'] if profile.get('relay_target')",source)
    def test_proxy_restart_reattaches_coolify_networks(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import types,json as _json
        from coolify_proxy_http3 import restart_keeping_networks
        state={'nets':{'coolify':{},'svc-a':{},'svc-b':{}}};calls=[]
        def run(argv,**kw):
            calls.append(argv)
            if argv[:2]==['docker','inspect']:return types.SimpleNamespace(stdout=_json.dumps(state['nets']))
            if argv[:3]==['docker','compose','up']:state['nets']={'coolify':{}}
            if argv[:3]==['docker','network','connect']:state['nets'][argv[3]]={}
            return types.SimpleNamespace(stdout='')
        self.assertEqual(restart_keeping_networks(run),['svc-a','svc-b'])
        self.assertEqual(set(state['nets']),{'coolify','svc-a','svc-b'})
    def test_relayed_host_drops_http3(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from coolify_proxy_hosts import apply
        text="services:\n  traefik:\n    ports:\n    - 80:80\n    - 443:443\n    - 443:443/udp\n    command:\n    - --ping=true\n    - --entrypoints.https.http3\n"
        svc=yaml.safe_load(apply(text,{},http3=False))['services']['traefik']
        self.assertEqual(svc['ports'],['80:80','443:443']); self.assertEqual(svc['command'],['--ping=true'])
        kept=yaml.safe_load(apply(text,{}))['services']['traefik']
        self.assertIn('--entrypoints.https.http3',kept['command'])
    def test_proxy_protocol_trust_is_one_managed_flag(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from coolify_proxy_hosts import apply
        text="services:\n  traefik:\n    command:\n    - --ping=true\n    - --entrypoints.https.proxyprotocol.trustedips=192.0.2.1/32\n"
        cmd=yaml.safe_load(apply(text,{},proxy_trusted=['10.0.1.1']))['services']['traefik']['command']
        self.assertEqual(cmd,['--ping=true','--entrypoints.https.forwardedheaders.trustedips=10.0.1.1/32'])
        cmd=yaml.safe_load(apply(text,{},proxy_trusted=[]))['services']['traefik']['command']
        self.assertEqual(cmd,['--ping=true'])
        with self.assertRaises(ValueError):apply(text,{},proxy_trusted=['nope'])
    def test_egress_allows_only_the_test_form_smtp_address(self):
        import ast
        source=(ROOT/'tools/test_egress.py').read_text()
        self.assertIn("smtp.get('address')",source)
        self.assertIn("'--dport',str(int(smtp.get('port',465)))",source)
        ast.parse(source)
    def test_proxy_host_pins_replace_only_their_own_entries(self):
        import sys;sys.path.insert(0,str(ROOT/'tools'))
        from coolify_proxy_hosts import apply
        text="services:\n  traefik:\n    extra_hosts:\n    - host.docker.internal:host-gateway\n    - sso.example.net:192.0.2.1\n"
        hosts=yaml.safe_load(apply(text,{'sso.example.net':'100.64.0.10'}))['services']['traefik']['extra_hosts']
        self.assertEqual(hosts,['host.docker.internal:host-gateway','sso.example.net:100.64.0.10'])
        with self.assertRaises(ValueError):apply(text,{'sso.example.net':'not-an-ip'})
        with self.assertRaises(ValueError):apply(text,{'bad host':'100.64.0.10'})
        joined=yaml.safe_load(apply("services:\n  traefik:\n    networks:\n    - coolify\n",{},'ws',['test.example.net']))
        self.assertEqual(joined['networks']['ws'],{'external':True})
        self.assertEqual(joined['services']['traefik']['networks'],{'coolify':None,'ws':{'aliases':['test.example.net']}})
        with self.assertRaises(ValueError):apply(text,{},'bad net!',[])
    def test_dms_extension_class_matches_native_settings(self):
        settings=json.loads((ROOT/'deployment/stacks/inputs.json').read_text())
        import ast
        classes={node.name for node in ast.parse((ROOT/'integrations/dms/cloud_session/apps.py').read_text()).body
                 if isinstance(node,ast.ClassDef)}
        extension=next(v['default'] for k,v in settings.items() if k.endswith('PAPERLESS_APPS'))
        self.assertIn(extension.split(',')[-1].split('.')[-1],classes)
    def test_ingress_references_and_narrow_public_response_routes(self):
        hosts={name:('test.example.net' if name=='erp' else 'test-'+name+'.example.net')
               for name in ['erp','sso','drive','office','mail','dms','respond']}
        http=ingress(ROOT,{'hosts':hosts,'ingress_prefix':'isolated'})['http']
        for router in http['routers'].values():
            self.assertTrue('@' in router['service'] or router['service'] in http['services'])
            self.assertTrue(set(router.get('middlewares',[]))<=http['middlewares'].keys())
        response=http['routers']['isolated-onboarding-response']['rule']
        self.assertIn('/api/method/erpnext_drive_integrations.onboarding.respond.answer',response)
        self.assertNotIn('/api/method/onboarding.',response)
        self.assertEqual(http['routers']['isolated-onboarding-response-root']['service'],'noop@internal')
        self.assertEqual(http['middlewares']['isolated-onboarding-response-help']['redirectRegex']['regex'],
                         r'^https://test\-respond\.example\.net/?$')
        self.assertIn('isolated-private-admin',http['routers']['isolated-office-admin']['middlewares'])
        # P92: ONLYOFFICE's own private paths, not the retired Collabora admin paths.
        office_admin=http['routers']['isolated-office-admin']['rule']
        self.assertNotIn('/cool/',office_admin); self.assertNotIn('/browser/dist/admin',office_admin)
        pattern=re.compile(re.search(r'PathRegexp\(`(.+)`\)',office_admin).group(1))
        for path in ['/info/','/info/info.json','/internal/cluster/inactive','/10.0.0-169/info/']:
            self.assertTrue(pattern.match(path),path)
        for path in ['/','/healthcheck','/web-apps/apps/api/documents/api.js','/hosting/discovery','/informed']:
            self.assertFalse(pattern.match(path),path)
    def test_test_ingress_has_production_native_app_routes(self):
        hosts={name:('test.example.net' if name=='erp' else 'test-'+name+'.example.net')
               for name in ['erp','sso','drive','office','mail','dms','respond']}
        http=ingress(ROOT,{'hosts':hosts,'ingress_prefix':'isolated'})['http']
        production=yaml.safe_load((ROOT/'deployment/config/proxy/cloud-native-clients.yaml').read_text())['http']
        for name,prod in production['routers'].items():
            test=http['routers']['isolated-'+name]
            self.assertEqual(test['rule'],prod['rule'].replace('erp.example.com','test.example.net'))
            self.assertEqual(test['service'],'isolated-erp')
            # Above the outpost-protected ERP route, as on production.
            self.assertGreater(test['priority'],http['routers']['isolated-erp']['priority'])
        bearer=http['routers']['isolated-cloud-native-bearer']
        self.assertEqual(bearer['middlewares'],['isolated-cloud-native-clean-headers','isolated-cloud-native-auth'])
        auth=http['middlewares']['isolated-cloud-native-auth']['forwardAuth']
        self.assertTrue(auth['address'].endswith('/api/method/erpnext_drive_integrations.portal.mobile.check_access'))
        self.assertFalse(auth['trustForwardHeader'])
        self.assertEqual(set(http['middlewares']['isolated-cloud-native-clean-headers']['headers']['customRequestHeaders'].values()),{''})
    def test_identity_graph_is_ordered_and_contains_no_user_credentials(self):
        entries=retained(json.loads((ROOT/'integrations/authentik/configuration.json').read_text())['entries'])
        seen=set()
        def refs(value):
            if isinstance(value,dict):
                if '$ref' in value:
                    yield value['$ref']
                else:
                    for child in value.values():yield from refs(child)
            elif isinstance(value,list):
                for child in value:yield from refs(child)
        for entry in entries:
            self.assertNotIn(entry['model'],{'authentik_core.user','authentik_core.token',
                'authentik_crypto.certificatekeypair','authentik_stages_authenticator_webauthn.webauthndevice'})
            self.assertTrue(set(refs(entry))<=seen,entry['id'])
            seen.add(entry['id'])

    def test_databases_are_pinned_and_not_on_shared_application_network(self):
        for project,names in {'erp':['db','redis-cache','redis-queue'],
            'dms':['database','broker'],'identity':['postgresql']}.items():
            stack=json.loads((ROOT/'deployment/stacks'/(project+'.compose.json')).read_text())
            for name in names:
                service=stack['services'][name]
                self.assertIn('@sha256:',service['image'])
                self.assertNotIn('workspace',service['networks'])

    def test_session_registry_and_drive_configuration_are_shared(self):
        mounts=json.loads((ROOT/'deployment/stacks/mounts.json').read_text())
        for target in ['/var/lib/cloud-integration','/etc/ocis']:
            self.assertEqual(len({m['path'] for m in mounts if m['target']==target}),1)

    def test_existing_volumes_are_reused_as_external(self):
        with tempfile.TemporaryDirectory() as temp:
            profile={'instance':'isolated-prod','tier':'production','domain':'example.com',
                'hosts':{k:('erp.example.com' if k=='erp' else k+'.example.com') for k in
                    ['erp','sso','drive','office','mail','dms','respond']},
                'network':'isolated-workspace','network_subnet':'10.45.0.0/24',
                'erp_image':'example/erp:prod','mail_image':'example/mail:prod','projects':['erp'],
                'existing_volumes':{'erp':{'erp-sites':'erp-production-sites','erp-db-data':'erp-production-db-data',
                                           'erp-redis-queue-data':'erp-production-redis-queue-data'}}}
            profile['settings']={'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'}
            output=Path(temp)/'runtime'; prepare(ROOT,output,profile)
            volumes=json.loads((output/'compose/erp.json').read_text())['volumes']
            self.assertEqual(volumes['erp-sites'],{'external':True,'name':'erp-production-sites'})
            self.assertEqual(volumes['erp-db-data'],{'external':True,'name':'erp-production-db-data'})
            bad=dict(profile,existing_volumes={'erp':{'erp-unknown':'x'}})
            with self.assertRaises(ValueError):prepare(ROOT,Path(temp)/'runtime2',bad)
            bad=dict(profile,existing_volumes={'erp':{'erp-sites':'../escape'}})
            with self.assertRaises(ValueError):prepare(ROOT,Path(temp)/'runtime3',bad)
    def test_extra_networks_keep_legacy_names(self):
        with tempfile.TemporaryDirectory() as temp:
            profile={'instance':'isolated-prod','tier':'production','domain':'example.com',
                'hosts':{k:('erp.example.com' if k=='erp' else k+'.example.com') for k in
                    ['erp','sso','drive','office','mail','dms','respond']},
                'network':'isolated-workspace','network_subnet':'10.45.0.0/24',
                'erp_image':'example/erp:prod','mail_image':'example/mail:prod','projects':['erp'],
                'extra_networks':{'erp':{'frontend':{'workspace':['frontend-legacy'],'coolify':['frontend-legacy']},
                                         'backend':{'workspace':['auth-backend']}}}}
            profile['settings']={'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'office-mail'}
            output=Path(temp)/'runtime'; prepare(ROOT,output,profile)
            compose=json.loads((output/'compose/erp.json').read_text())
            front=compose['services']['frontend']['networks']
            self.assertIn('erp-frontend',front['workspace']['aliases'])
            self.assertIn('frontend-legacy',front['workspace']['aliases'])
            self.assertEqual(front['coolify'],{'aliases':['frontend-legacy']})
            self.assertEqual(compose['networks']['coolify'],{'external':True,'name':'coolify'})
            self.assertIn('auth-backend',compose['services']['backend']['networks']['workspace']['aliases'])
            self.assertNotIn('coolify',compose['services']['db']['networks'])
            for bad in [{'erp':{'nosuch':{'workspace':['x']}}},{'erp':{'frontend':{'coolify':['../x']}}}]:
                with self.assertRaises(ValueError):prepare(ROOT,Path(temp)/('bad'+str(id(bad))),dict(profile,extra_networks=bad))
    def test_addon_frontend_build_has_explicit_node_heap(self):
        # The default Node heap depends on the build host's RAM; the Insights
        # frontend build ran out of memory on an 8 GB host without this.
        dockerfile=(ROOT/'deployment/erp/Dockerfile.addon').read_text()
        self.assertRegex(dockerfile,r'NODE_OPTIONS=--max-old-space-size=\d+ yarn build')
    def test_prepare_erp_only_without_other_app_secrets_or_editor_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            profile={'instance':'isolated-test','tier':'test','domain':'example.com',
                'hosts':{k:('test.example.com' if k=='erp' else ('sso.example.com' if k=='sso' else 'test-'+k+'.example.com')) for k in
                    ['erp','sso','drive','office','mail','dms','respond']},
                'network':'isolated-workspace','network_subnet':'10.44.0.0/24',
                'erp_image':'example/erp:test','mail_image':'example/mail:test','projects':['erp']}
            profile['settings']={'CI_MAIL_WEBMAIL_OAUTH_CLIENT_ID':'test-office-mail'}
            output=Path(temp)/'runtime'
            prepare(ROOT,output,profile)
            spec=json.loads((output/'compose/erp.json').read_text())
            for role in ['backend','frontend','websocket','queue-short','queue-long','scheduler']:
                self.assertEqual(spec['services'][role]['image'],'example/erp:test')
                self.assertEqual(spec['services'][role]['environment']['CLOUD_DEPLOYMENT_TIER'],'test')
            self.assertEqual(spec['services']['scheduler']['profiles'],['manual-workers'])
            self.assertEqual(spec['services']['frontend']['environment']['BACKEND'],'erp-backend:8000')
            secrets_before=json.loads((output/'inputs.private.json').read_text())
            prepare(ROOT,output,profile)
            self.assertEqual(secrets_before['CI_ERP_DB_MYSQL_ROOT_PASSWORD'],
                json.loads((output/'inputs.private.json').read_text())['CI_ERP_DB_MYSQL_ROOT_PASSWORD'])
            self.assertTrue((output/'ready.json').exists())
            portal=(output/'rendered/erpnext_drive_integrations/www/place_holder.html').read_text()
            self.assertIn("get('client_id')==='test-office-mail'",portal)


if __name__=='__main__':unittest.main()
