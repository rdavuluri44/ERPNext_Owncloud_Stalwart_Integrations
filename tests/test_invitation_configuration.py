"""Invitation packaging regressions; no live identity changes or mail."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('renderer',ROOT/'tools/render_runtime.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Invitations(unittest.TestCase):
 def test_renderer_excludes_generated_python_caches(self):
  import shutil
  with tempfile.TemporaryDirectory() as d:
   source=Path(d)/'source';source.mkdir()
   for name in ['erpnext_drive_integrations','integrations']:
    (source/name/'__pycache__').mkdir(parents=True)
    (source/name/'__pycache__/generated.pyc').write_bytes(b'generated')
    (source/name/'generated.pyo').write_bytes(b'generated')
    (source/name/'retained.py').write_text('retained = True\n')
   for name in ['pyproject.toml','MANIFEST.in','tools/fetch_face_models.py','deployment/face-models.json']:
    (source/name).parent.mkdir(parents=True,exist_ok=True)
    (source/name).write_text('')
   output=Path(d)/'build'
   m.render(source,output,{'domain':'example.net'})
   self.assertEqual(list(output.rglob('__pycache__')),[])
   self.assertEqual(list(output.rglob('*.pyc')),[])
   self.assertEqual(list(output.rglob('*.pyo')),[])
   self.assertTrue((output/'integrations/retained.py').exists())
 def test_group_and_navigation(self):
  r=ROOT/'integrations/authentik/invite-recovery'
  self.assertIn('APPROVAL_GROUP = "Workspace Users"',(r/'public/invitations.mjs').read_text())
  self.assertIn('name="Workspace Users"',(r/'native_recovery.py').read_text())
  graph=json.loads((ROOT/'integrations/authentik/configuration.json').read_text())
  for e in graph['entries']:
   self.assertNotIn('name__in=["ERPNext"]',e.get('attrs',{}).get('expression',''))
   self.assertNotIn('cloud-invitation-navigation',e.get('attrs',{}).get('branding_custom_css',''))
  navigation=(r/'public/admin-navigation.mjs').read_text()
  self.assertIn('Invite users',navigation)
  self.assertIn('#/flow/stages/invitations',navigation)
  self.assertIn('nativeItem.before(item)',navigation)
  self.assertIn('admin-navigation.mjs',(r/'templates/if/admin.html').read_text())
  self.assertIn('Manage invitations',(r/'public/index.html').read_text())
 def test_modules_render_group_and_cache_version(self):
  with tempfile.TemporaryDirectory() as d:
   m.render(ROOT,Path(d)/'build',{'domain':'example.net','asset_version':'abcdef1','public_replacements':{'Workspace Users':'Shared Users'}})
   r=Path(d)/'build/integrations/authentik/invite-recovery'
   self.assertIn('APPROVAL_GROUP = "Shared Users"',(r/'public/invitations.mjs').read_text())
   self.assertIn('invitations.mjs?v=abcdef1',(r/'public/page.mjs').read_text())
   page=(r/'public/index.html').read_text()
   self.assertIn('page.mjs?v=abcdef1',page)
   self.assertIn('style.css?v=abcdef1',page)
   self.assertIn('invite-mode.mjs?v=abcdef1',(r/'public/page.mjs').read_text())
   self.assertIn('admin-navigation.mjs?v=abcdef1',(r/'templates/if/admin.html').read_text())
if __name__=='__main__':unittest.main()
