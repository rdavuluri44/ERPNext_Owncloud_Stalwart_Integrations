#!/usr/bin/env python3
"""Native Stalwart v1.1 JMAP configuration from a private operator profile.

Keep the recovery credential and this profile on the deployment host. Test mode
retargets OIDC, removes copied local account credentials and disables protocol
listeners; the workspace egress policy separately blocks external delivery.
"""
import argparse
import base64
import gzip
import json
from pathlib import Path
import urllib.request
import subprocess
import time


class NativeError(RuntimeError):
    def __init__(self,method,result):
        super().__init__('Native Mail operation failed: '+method)
        self.kind=result.get('type')
        self.bootstrap='bootstrap mode' in result.get('description','').lower()
        self.invalid_fields=[field for section in ['notCreated','notUpdated']
            for problem in (result.get(section) or {}).values() for field in problem.get('properties',[])]
        # Error codes only (for example alreadyExists); never descriptions or payloads.
        self.item_types=sorted({problem.get('type') for section in ['notCreated','notUpdated','notDestroyed']
            for problem in (result.get(section) or {}).values()})


class Client:
    def __init__(self,url,credential):
        self.url=url.rstrip('/');self.authorization='Basic '+base64.b64encode(credential.encode()).decode()

    def call(self,method,arguments,using=('urn:ietf:params:jmap:core',)):
        body=json.dumps({'using':list(using),'methodCalls':[[method,arguments,'operation']]}).encode()
        request=urllib.request.Request(self.url+'/jmap',data=body,
            headers={'Authorization':self.authorization,'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=60) as response:data=response.read()
        if data[:2]==b'\x1f\x8b':data=gzip.decompress(data)
        name,result,_=json.loads(data)['methodResponses'][0]
        if name=='error' or result.get('notCreated') or result.get('notUpdated') or result.get('notDestroyed'):
            # Native errors may echo submitted fields. Never print the payload.
            raise NativeError(method,result)
        return result


def configure(profile):
    if profile['tier'] not in {'test','production'}:raise ValueError('Unknown deployment tier')
    client=Client(profile['admin_url'],profile['recovery_credential'])
    directory={'@type':'Oidc','description':profile.get('directory_name','Workspace SSO'),
        'issuerUrl':profile['issuer'],'claimUsername':profile.get('claim_username','office_mailbox'),
        'claimGroups':None,'claimName':None,'acceptedAudiences':{profile['client_id']:True},
        'opaqueTokenValidation':'none','unscopedTokens':'interoperable',
        'skipAudienceValidation':False,'allowIdTokenClaims':False,'allowInvalidCerts':False,
        'trustedProvider':False,'lenientIssuerMatch':False,'usernameDomain':None}
    try:current=client.call('x:Directory/get',{})['list']
    except NativeError as error:
        if error.kind!='forbidden' or not error.bootstrap:raise
        from urllib.parse import urlsplit
        def activate():
            subprocess.run(['docker','restart',profile['container']],check=True,stdout=subprocess.DEVNULL)
            for attempt in range(30):
                try:return client.call('x:Directory/get',{})['list']
                except NativeError as state:
                    if state.kind=='forbidden' and state.bootstrap:return None
                    raise
                except OSError:
                    if attempt==29:raise
                    time.sleep(1)
        # Recover an interrupted previous setup before trying to create its
        # default domain again. Only a server still in bootstrap restarts here.
        current=activate()
        if current is None:
            client.call('x:Bootstrap/set',{'update':{'singleton':{
                'defaultDomain':profile['mail_domain'],
                'defaultHostname':profile.get('mail_hostname') or urlsplit(profile['public_url']).hostname,
                'requestTlsCertificate':False,'generateDkimKeys':profile['tier']=='production'}}})
            current=activate()
            if current is None:raise RuntimeError('Native Mail bootstrap did not activate')
    match=next((row for row in current if row.get('description')==directory['description']),None)
    if not match and profile['tier']=='test':
        oidc=[row for row in current if row.get('@type')=='Oidc']
        if len(oidc)==1:match=oidc[0]
    if match:
        ident=match['id'];client.call('x:Directory/set',{'update':{ident:directory}})
    else:ident=client.call('x:Directory/set',{'create':{'workspace':directory}})['created']['workspace']['id']
    domain_rows=client.call('x:Domain/get',{})['list']
    domain=next((row for row in domain_rows if row['name']==profile['mail_domain']),None)
    if not domain:
        domain_id=client.call('x:Domain/set',{'create':{'workspace':{'name':profile['mail_domain'],'enable':True}}})['created']['workspace']['id']
    else:domain_id=domain['id']
    accounts=client.call('x:Account/get',{})['list']
    by_name={row['name']:row for row in accounts if row.get('domainId')==domain_id}
    for account in profile.get('accounts',[]):
        if account['name'] in by_name:continue
        value={'@type':account['type'],'name':account['name'],'domainId':domain_id,
               'description':account.get('description',account['name']),
               'roles':{'@type':'User' if account['type']=='User' else 'Default'}}
        created=client.call('x:Account/set',{'create':{'account':value}})['created']['account']
        by_name[account['name']]=dict(value,id=created['id'])
    for account in profile.get('accounts',[]):
        if account['type']!='User' or 'groups' not in account:continue
        membership={by_name[group]['id']:True for group in account['groups']}
        client.call('x:Account/set',{'update':{by_name[account['name']]['id']:{'memberGroupIds':membership}}})
    client.call('x:Authentication/set',{'update':{'singleton':{'directoryId':ident}}})
    if profile['tier']=='test':
        from urllib.parse import urlsplit
        hostname = urlsplit(profile['public_url']).hostname
        settings = client.call('x:SystemSettings/get', {'ids':['singleton']})['list'][0]
        services = {key:dict(value, hostname=hostname, cleartext=False)
                    for key,value in settings['services'].items()}
        client.call('x:SystemSettings/set', {'update':{'singleton':{
            'defaultHostname':hostname, 'services':services}}})
        accounts=client.call('x:Account/get',{})['list']
        updates={row['id']:{'credentials':{}} for row in accounts if row.get('@type')=='User'}
        if updates:client.call('x:Account/set',{'update':updates})
        listeners=client.call('x:NetworkListener/get',{})['list']
        destroy=[row['id'] for row in listeners if row.get('protocol') in {'smtp','imap','pop3','managesieve'}]
        if destroy:client.call('x:NetworkListener/set',{'destroy':destroy})
        # Native settings persist immediately but session advertisements are
        # cached by the running server. Activate them before opening webmail.
        subprocess.run(['docker','restart',profile['container']],check=True,stdout=subprocess.DEVNULL)
        request=urllib.request.Request(client.url+'/.well-known/jmap',
            headers={'Authorization':client.authorization})
        for attempt in range(30):
            try:
                with urllib.request.urlopen(request,timeout=30) as response:session=json.load(response)
                break
            except OSError:
                if attempt==29:raise
                time.sleep(1)
        for key in ['apiUrl','downloadUrl','uploadUrl','eventSourceUrl']:
            if urlsplit(session[key]).hostname != hostname:
                raise RuntimeError('Test Mail still advertises a non-test endpoint')
    return {'configured':True,'tier':profile['tier'],'account_names':sorted(by_name)}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile',required=True)
    print(configure(json.loads(Path(parser.parse_args().profile).read_text())))
