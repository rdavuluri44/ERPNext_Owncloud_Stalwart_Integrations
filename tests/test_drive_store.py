"""drive-store (P74): the photo store's own rules, with a small fake Frappe and a fake Drive; the project's
modules (drive_store, custom_hr) are imported for real.

Covers: one fixed Drive path per photo (a retry writes the same file, no folder escapes), the tags, the app
token's renewal (same account checked before use, old token revoked, never on mismatch), the access rule
(custom_hr site membership), idempotent uploads, and that nobody deletes a photo record.
"""
import datetime
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class Thrown(Exception):
    pass


class PermissionDenied(Thrown):
    pass


def _throw(message, exc=None):
    raise (PermissionDenied if exc is PermissionDenied else Thrown)(message)


frappe = types.ModuleType('frappe')
frappe.conf = {}
frappe._ = lambda text: text
frappe.throw = _throw
frappe.PermissionError = PermissionDenied
frappe.parse_json = json.loads
frappe.log_error = mock.Mock()
frappe.local = types.SimpleNamespace(response={})
frappe.db = mock.Mock()
frappe.get_doc = mock.Mock()
frappe.get_all = mock.Mock(return_value=[])
frappe.get_roles = mock.Mock(return_value=[])
frappe.whitelist = lambda **kw: (lambda f: f)
frappe.session = types.SimpleNamespace(user='a@example.com')
_tmp = tempfile.mkdtemp()
frappe.get_site_path = lambda *parts: str(Path(_tmp, *parts))
utils = types.ModuleType('frappe.utils')
utils.cint = lambda v: int(v or 0)
utils.get_datetime = lambda v: v if isinstance(v, datetime.datetime) else datetime.datetime.fromisoformat(str(v))
utils.getdate = lambda v=None: datetime.date.today()
utils.now_datetime = lambda: datetime.datetime(2026, 11, 24, 10, 15, 30)
utils.nowdate = lambda: '2026-11-24'
model = types.ModuleType('frappe.model')
document = types.ModuleType('frappe.model.document')


class Document:
    def __init__(self):
        self.flags = types.SimpleNamespace(drive_store=False)


document.Document = Document
frappe.utils = utils
sys.modules.update({'frappe': frappe, 'frappe.utils': utils, 'frappe.model': model, 'frappe.model.document': document})

from erpnext_drive_integrations.drive_store import api, drive  # noqa: E402
from erpnext_drive_integrations.drive_store.guards import StoreRecord  # noqa: E402

TAKEN = datetime.datetime(2026, 11, 24, 10, 15, 30)
CLIENT = 'abcdef0123456789abcd'


class Paths(unittest.TestCase):
    def test_one_fixed_path_per_photo(self):
        self.assertEqual(drive.photo_path('Site 1', TAKEN, 'Progress', CLIENT), 'Site 1/2026-11-24/101530-Progress-abcdef0123456789abcd.jpg')
        self.assertEqual(drive.photo_path('Site 1', TAKEN, 'Progress', CLIENT), drive.photo_path('Site 1', TAKEN, 'Progress', CLIENT))

    def test_no_folder_escape_or_odd_characters(self):
        for bad in ('../../etc', '..', '/abs', 'a/b\\c', '', None):
            part = drive.safe_part(bad)
            self.assertNotIn('/', part)
            self.assertNotIn('\\', part)
            self.assertNotIn(part, ('', '.', '..'))
        self.assertTrue(drive.photo_path('../x', TAKEN, '../../y', CLIENT).startswith('x/2026-11-24/'))

    def test_ids_sharing_a_prefix_never_share_a_path(self):
        # Drive's PUT overwrites: two different ids must never reach the same file (nobody replaces a photo).
        other = CLIENT[:12] + 'ZZZZZZZZ'
        self.assertNotEqual(drive.photo_path('S', TAKEN, 'Progress', CLIENT), drive.photo_path('S', TAKEN, 'Progress', other))


class Tags(unittest.TestCase):
    def test_tags_carry_project_site_time_place_person_and_marks(self):
        tags = drive.photo_tags('Project, One', 'Site 1', 'Hindrance', 'a@example.com', TAKEN,
                                {'latitude': 17.385044, 'longitude': 78.486671, 'accuracy_m': 8.6}, True, True)
        self.assertEqual(tags, ['Project: Project  One', 'Site: Site 1', 'Type: Hindrance', 'Taken by: a@example.com',
                                'Taken: 2026-11-24 10:15', 'GPS: 17.38504 78.48667 ±9 m', 'From gallery', 'Captured offline'])
        self.assertTrue(all(',' not in t for t in tags))

    def test_camera_photo_online_without_gps(self):
        tags = drive.photo_tags('P', 'S', 'Progress', 'u', TAKEN, None, False, False)
        self.assertNotIn('From gallery', tags)
        self.assertFalse(any(t.startswith('GPS') for t in tags))


class Credential(unittest.TestCase):
    conf = {'url': 'http://drive.internal', 'account': 'photos@example.com', 'account_id': 'ID-1', 'token': 'first'}

    def answer(self, body=None, status=200):
        return mock.Mock(status_code=status, json=mock.Mock(return_value=body), headers={}, content=b'')

    def test_renewal_window(self):
        now = 1_000_000
        self.assertTrue(drive.needs_renewal(None, now))
        self.assertTrue(drive.needs_renewal(now + 4 * 86400, now))
        self.assertFalse(drive.needs_renewal(now + 6 * 86400, now))

    def test_renewal_checks_the_account_keeps_the_new_token_then_revokes_the_old(self):
        calls = []

        def fake(method, url, headers=None, timeout=None, **kw):
            calls.append((method, url.split('?')[0]))
            if method == 'POST':
                return self.answer({'token': 'second', 'expiration_date': '2026-12-24T10:00:00Z', 'created_date': 'C1'})
            if url.endswith('/me'):
                return self.answer({'id': 'ID-1'})
            if method == 'GET':
                return self.answer([{'label': drive.LABEL, 'created_date': 'C1', 'token': '$2new'}])
            return self.answer()

        with mock.patch.object(drive.requests, 'request', side_effect=fake):
            saved = drive.renew(self.conf, {'token': 'first', 'hash': '$2old'})
        self.assertEqual(saved['token'], 'second')
        self.assertEqual(json.loads(Path(drive._credential_path()).read_text())['token'], 'second')
        self.assertEqual([m for m, _ in calls], ['POST', 'GET', 'GET', 'DELETE'])

    def test_a_token_of_another_account_is_never_used_or_kept(self):
        Path(drive._credential_path()).unlink(missing_ok=True)

        def fake(method, url, headers=None, timeout=None, **kw):
            if method == 'POST':
                return self.answer({'token': 'second', 'expiration_date': '2026-12-24T10:00:00Z', 'created_date': 'C1'})
            return self.answer({'id': 'SOMEONE-ELSE'})

        with mock.patch.object(drive.requests, 'request', side_effect=fake):
            with self.assertRaises(drive.DriveError):
                drive.renew(self.conf, {'token': 'first', 'hash': '$2old'})
        self.assertFalse(Path(drive._credential_path()).exists())

    def test_errors_never_contain_the_token(self):
        with mock.patch.object(drive.requests, 'request', return_value=self.answer(status=401)):
            with self.assertRaises(drive.DriveError) as caught:
                drive._call('GET', 'http://drive.internal/graph/v1.0/me?x=1', drive._basic(self.conf, 'secret-token'))
        self.assertNotIn('secret-token', str(caught.exception))
        self.assertNotIn('x=1', str(caught.exception))


class Access(unittest.TestCase):
    def test_sites_are_custom_hr_membership(self):
        with mock.patch.object(api, 'site_ids', return_value=['S1']), mock.patch.object(api, 'self_sites', return_value=['S2']):
            self.assertEqual(api.allowed_sites('a@example.com'), {'S1', 'S2'})
            with self.assertRaises(PermissionDenied):
                api.require_photo_site('S3', 'a@example.com')

    def test_list_only_shows_permitted_sites(self):
        frappe.get_all.reset_mock()
        with mock.patch.object(api, 'allowed_sites', return_value=set()):
            self.assertEqual(api.photos(), [])
        frappe.get_all.assert_not_called()


class Upload(unittest.TestCase):
    def setUp(self):
        self.user = mock.patch.object(api, 'require_user', return_value='a@example.com')
        self.user.start()
        self.addCleanup(self.user.stop)

    def test_a_retry_returns_the_same_photo_and_writes_nothing(self):
        frappe.db.get_value = mock.Mock(return_value=types.SimpleNamespace(name='DP-1', taken_by='a@example.com', site='S1', path='p.jpg'))
        with mock.patch.object(drive, 'put_file') as put:
            result = api.upload_photo({'client_id': CLIENT, 'site': 'S1', 'photo': 'x'})
        self.assertEqual(result, {'name': 'DP-1', 'path': 'p.jpg'})
        put.assert_not_called()

    def test_someone_elses_photo_id_is_refused(self):
        frappe.db.get_value = mock.Mock(return_value=types.SimpleNamespace(name='DP-1', taken_by='b@example.com', site='S1', path='p.jpg'))
        with self.assertRaises(PermissionDenied):
            api.upload_photo({'client_id': CLIENT, 'site': 'S1', 'photo': 'x'})

    def test_missing_photo_id_is_refused_before_anything_else(self):
        with self.assertRaises(Thrown):
            api.upload_photo({'client_id': 'short', 'site': 'S1', 'photo': 'x'})

    def test_new_photo_goes_to_the_site_and_date_folder_with_tags(self):
        frappe.db.get_value = mock.Mock(side_effect=lambda doctype, *a, **k: None if doctype == 'Drive Photo' else 'Project One')
        site = types.SimpleNamespace(name='S1', site_name='Site 1', project='PROJ-1')
        inserted = {}

        def make(values):
            doc = mock.Mock()
            doc.flags = types.SimpleNamespace()
            doc.name = 'DP-9'
            doc.insert = mock.Mock(side_effect=lambda **kw: inserted.update(values))
            return doc

        frappe.get_doc = mock.Mock(side_effect=make)
        with mock.patch.object(api, 'require_photo_site', return_value=site), \
                mock.patch.object(api, 'decode_photo', return_value=b'jpeg'), \
                mock.patch.object(api, 'moment', return_value=TAKEN), \
                mock.patch.object(api, 'project_space', return_value='SPACE-1'), \
                mock.patch.object(drive, 'ensure_folders') as folders, \
                mock.patch.object(drive, 'put_file', return_value='FILE-1') as put, \
                mock.patch.object(drive, 'set_tags') as tags:
            result = api.upload_photo({'client_id': CLIENT, 'site': 'S1', 'kind': 'Progress', 'photo': 'x', 'from_gallery': 1,
                                       'latitude': 17.385, 'longitude': 78.486, 'accuracy_m': 9})
        path = 'Site 1/2026-11-24/101530-Progress-abcdef0123456789abcd.jpg'
        self.assertEqual(result, {'name': 'DP-9', 'path': path})
        folders.assert_called_once_with('SPACE-1', 'Site 1/2026-11-24')
        put.assert_called_once_with('SPACE-1', path, b'jpeg')
        self.assertIn('From gallery', tags.call_args[0][1])
        self.assertEqual((inserted['project'], inserted['site'], inserted['taken_by'], inserted['tagged']), ('PROJ-1', 'S1', 'a@example.com', 1))

    def test_unknown_type_becomes_other(self):
        frappe.db.get_value = mock.Mock(side_effect=lambda doctype, *a, **k: None if doctype == 'Drive Photo' else 'P')
        frappe.get_doc = mock.Mock(return_value=mock.Mock(flags=types.SimpleNamespace(), name='DP'))
        with mock.patch.object(api, 'require_photo_site', return_value=types.SimpleNamespace(name='S1', site_name='S', project='P')), \
                mock.patch.object(api, 'decode_photo', return_value=b'j'), mock.patch.object(api, 'moment', return_value=TAKEN), \
                mock.patch.object(api, 'project_space', return_value='SP'), mock.patch.object(drive, 'ensure_folders'), \
                mock.patch.object(drive, 'put_file', return_value='') as put, mock.patch.object(drive, 'set_tags') as tags:
            api.upload_photo({'client_id': CLIENT, 'site': 'S1', 'kind': 'Selfie', 'photo': 'x'})
        self.assertIn('-Other-', put.call_args[0][1])
        tags.assert_not_called()  # no Drive file id: no tag call


class NoDeletes(unittest.TestCase):
    def test_records_change_only_through_the_store_and_are_never_deleted(self):
        record = StoreRecord()
        with self.assertRaises(PermissionDenied):
            record.validate()
        record.flags.drive_store = True
        record.validate()
        with self.assertRaises(PermissionDenied):
            record.on_trash()
        for name in ('drive_photo', 'drive_project_space'):
            meta = json.loads((ROOT / f'erpnext_drive_integrations/drive_store/doctype/{name}/{name}.json').read_text())
            self.assertEqual(meta['module'], 'Drive Store')
            self.assertTrue(all(not p.get('delete') and not p.get('write') and not p.get('create') for p in meta['permissions']))



class ProjectFiles(unittest.TestCase):
    LISTING = b'''<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">
<d:response><d:href>/dav/spaces/SP/Site%201/</d:href><d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat></d:response>
<d:response><d:href>/dav/spaces/SP/Site%201/plan.pdf</d:href><d:propstat><d:prop><d:resourcetype/><d:getcontentlength>2048</d:getcontentlength><d:getcontenttype>application/pdf</d:getcontenttype></d:prop></d:propstat></d:response>
<d:response><d:href>/dav/spaces/SP/Site%201/2026-11-24/</d:href><d:propstat><d:prop><d:resourcetype><d:collection/></d:resourcetype></d:prop></d:propstat></d:response>
</d:multistatus>'''

    def test_listing_skips_the_folder_itself_folders_first(self):
        entries = drive.parse_listing(self.LISTING, 'Site 1')
        self.assertEqual([(e['name'], e['folder'], e['path']) for e in entries],
                         [('2026-11-24', True, 'Site 1/2026-11-24'), ('plan.pdf', False, 'Site 1/plan.pdf')])
        self.assertEqual(entries[1]['size'], 2048)

    def test_paths_cannot_leave_the_space(self):
        self.assertEqual(drive.clean_path('/Site 1//2026-11-24/'), 'Site 1/2026-11-24')
        self.assertEqual(drive.clean_path('a' + chr(92) + 'b'), 'a/b')  # a backslash
        for bad in ('../x', 'a/../../b', './a', 'a/.'):
            with self.assertRaises(ValueError):
                drive.clean_path(bad)

    SITES = [{'name': 'S1', 'site_name': 'Site 1'}, {'name': 'S2', 'site_name': 'Site 2'}]

    def test_project_access_is_site_membership(self):
        frappe.get_all = mock.Mock(return_value=self.SITES)
        with mock.patch.object(api, 'allowed_sites', return_value={'S2'}):
            self.assertEqual(api.project_folders('PROJ-1', 'a@example.com'), {'Site 2'})
        with mock.patch.object(api, 'allowed_sites', return_value={'S9'}):
            with self.assertRaises(PermissionDenied):
                api.project_folders('PROJ-1', 'a@example.com')

    def test_other_sites_folders_stay_closed(self):
        frappe.get_all = mock.Mock(return_value=self.SITES)
        frappe.db.get_value = mock.Mock(return_value='SP')
        top = [{'name': 'Site 1', 'folder': True}, {'name': 'Site 2', 'folder': True}, {'name': 'note.txt', 'folder': False}]
        with mock.patch.object(api, 'require_user', return_value='a'), mock.patch.object(api, 'allowed_sites', return_value={'S2'}), \
                mock.patch.object(drive, 'list_folder', return_value=top) as listing, mock.patch.object(drive, 'read_file') as read:
            self.assertEqual(api.files('PROJ-1', ''), [{'name': 'Site 2', 'folder': True}])
            for asked in (lambda: api.files('PROJ-1', 'Site 1'), lambda: api.files('PROJ-1', 'Site 1/2026-11-24'),
                          lambda: api.file('PROJ-1', 'Site 1/2026-11-24/101530-Progress-x.jpg'),
                          lambda: api.file('PROJ-1', 'note.jpg')):
                with self.assertRaises(PermissionDenied):
                    asked()
            api.files('PROJ-1', 'Site 2/2026-11-24')
        self.assertEqual(listing.call_args_list[-1][0], ('SP', 'Site 2/2026-11-24'))
        read.assert_not_called()

    def test_no_space_yet_lists_nothing_and_creates_nothing(self):
        frappe.db.get_value = mock.Mock(return_value=None)
        with mock.patch.object(api, 'require_user', return_value='a'), mock.patch.object(api, 'project_folders', return_value={'Site 1'}), \
                mock.patch.object(drive, 'list_folder') as listing, mock.patch.object(drive, 'create_space') as create:
            self.assertEqual(api.files('PROJ-1', ''), [])
        listing.assert_not_called()
        create.assert_not_called()

    def test_only_images_open_in_the_app_and_bad_paths_are_refused(self):
        with mock.patch.object(api, 'require_user', return_value='a'), mock.patch.object(api, 'project_folders', return_value={'Site 1'}):
            with self.assertRaises(Thrown):
                api.file('PROJ-1', 'Site 1/plan.pdf')
            with self.assertRaises(Thrown):
                api.file('PROJ-1', '../other/photo.jpg')


class PreviewSize(unittest.TestCase):
    def test_drive_makes_the_preview_size_the_store_asks_for(self):
        # oCIS serves only listed thumbnail sizes; any other request gets the next larger one (1080 px on test).
        inputs = json.loads((ROOT / 'deployment/stacks/inputs.json').read_text())
        sizes = inputs['CI_DRIVE_OCIS_THUMBNAILS_RESOLUTIONS']['default'].split(',')
        self.assertIn(f'{api.PREVIEW_PX}x{api.PREVIEW_PX}', sizes)
        for upstream in ('16x16', '32x32', '64x64', '128x128', '1080x1920', '1920x1080'):
            self.assertIn(upstream, sizes)
        compose = json.loads((ROOT / 'deployment/stacks/drive.compose.json').read_text())
        self.assertIn('CI_DRIVE_OCIS_THUMBNAILS_RESOLUTIONS', compose['services']['ocis']['environment']['THUMBNAILS_RESOLUTIONS'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
