"""Run with `ak shell` on the existing identity host, using a private profile.

Create test providers from existing approved native templates. Existing flows,
users, groups and production providers are never edited. Results contain fresh
test client secrets: write them privately and transfer only to the test host.
"""
import json
from pathlib import Path
import re
import secrets

from django.db import transaction
from authentik.blueprints.v1.common import get_attrs
from authentik.core.models import Application, Group, Provider
from authentik.outposts.models import Outpost
from authentik.policies.models import PolicyBinding
from authentik.providers.oauth2.models import ScopeMapping
from authentik.providers.proxy.models import ProxyProvider


def configure(profile_path, output_path):
    profile=json.loads(Path(profile_path).read_text())
    prefix=profile.get('prefix','test-')
    if not re.fullmatch(r'test-[a-z0-9-]*',prefix):
        raise ValueError('Only a test-prefixed application namespace is allowed')
    group=Group.objects.get(name=profile['approved_group'])
    results={}
    approval_name=prefix+'approved-user'
    # P49: the claim name the ERP requires (portal/sso.py APPROVED_CLAIM, or the site's cloud_approved_claim)
    claim=profile.get('approved_claim','cloud_approved')
    if not re.fullmatch(r'[a-z][a-z0-9_]*',claim):raise ValueError('Invalid approved_claim')
    with transaction.atomic():
        approval,_=ScopeMapping.objects.update_or_create(name=approval_name,defaults={
            'scope_name':'profile','description':'Approved test workspace identity',
            'expression':'return {'+repr(claim)+': bool(request.user.is_active and request.user.ak_groups.filter(pk='+repr(str(group.pk))+').exists())}'})
        for key,settings in profile['applications'].items():
            callbacks = list(settings.get('callbacks', []))
            if key == 'office-mail':
                # Native webmail includes the selected locale in its callback.
                # Register exact routes for explicitly supported locales only.
                locales = settings.get('locales', ['en'])
                for locale in locales:
                    if not re.fullmatch(r'[a-z]{2}(?:-[A-Z]{2})?', locale):
                        raise ValueError('Invalid Mail locale')
                    callback = settings['url'].rstrip('/')+'/'+locale+'/auth/callback'
                    if callback not in callbacks: callbacks.append(callback)
            original=Application.objects.get(slug=settings['template_slug'])
            source=Provider.objects.get_subclass(pk=original.provider_id)
            slug=prefix+key
            app=Application.objects.filter(slug=slug).first()
            attrs=get_attrs(source)
            attrs['name']=prefix+settings['name']
            if 'redirect_uris' in attrs:
                attrs.update({'client_id':prefix+key,'client_secret':'' if attrs.get('client_type')=='public' else secrets.token_urlsafe(48),
                    'redirect_uris':[{'matching_mode':'strict','url':url} for url in callbacks],
                    'access_token_validity':'minutes=5','refresh_token_validity':'days=30',
                    'logout_uri':settings.get('backchannel_url','')})
                if settings.get('backchannel_url'):
                    attrs['logout_method']='backchannel'
            else:
                attrs.update({'external_host':settings['url'],'internal_host':settings['internal_host']})
            if app and app.provider_id==original.provider_id:
                raise RuntimeError('Refusing to edit a production provider through a test application')
            provider=Provider.objects.get_subclass(pk=app.provider_id) if app and app.provider_id else None
            if provider and 'client_secret' in attrs:
                # Re-running deployment must not silently rotate a live test
                # credential out from underneath its application.
                attrs['client_secret']=provider.client_secret
            # Native serializers validate callback formats and flow/key references.
            serializer=source.serializer(instance=provider,data=attrs)
            serializer.is_valid(raise_exception=True)
            provider=serializer.save()
            if key=='erpnext':
                provider.property_mappings.add(approval)
            app,_=Application.objects.update_or_create(slug=slug,defaults={
                'name':settings['name'],'provider':provider,'meta_launch_url':settings['url'],
                'meta_hide':True,'open_in_new_tab':False,'group':'','policy_engine_mode':'all'})
            PolicyBinding.objects.update_or_create(target=app,order=0,defaults={
                'group':group,'policy':None,'user':None,'enabled':True,'negate':False,'failure_result':False})
            if key=='erp-gateway':
                embedded=Outpost.objects.get(managed='goauthentik.io/outposts/embedded')
                conflicts=ProxyProvider.objects.filter(pk__in=embedded.providers.values('pk'),
                    external_host=settings['url']).exclude(pk=provider.pk)
                if conflicts.exists():
                    from urllib.parse import urlsplit
                    host=urlsplit(settings['url']).hostname or ''
                    if not profile.get('replace_retired_test_gateways') or not host.startswith('test.'):
                        raise RuntimeError('An existing gateway already claims the test hostname')
                    for retired in list(conflicts):
                        embedded.providers.remove(retired)
                        Application.objects.filter(provider=retired).update(meta_hide=True)
                embedded.providers.add(provider)
            issuer=profile['sso_url'].rstrip('/')+'/'
            if getattr(provider,'issuer_mode',None)!='global':
                issuer+='application/o/'+slug+'/'
            results[key]={'slug':slug,'client_id':getattr(provider,'client_id',None),
                'client_secret':getattr(provider,'client_secret',None),'issuer':issuer,
                'application_url':settings['url']}
    path=Path(output_path)
    path.write_text(json.dumps(results,indent=2)+'\n')
    path.chmod(0o600)
    return {'configured':list(results),'production_providers_modified':False}
