"""P95 face engine: the pinned model files are fetched only with matching checksums, the ERP add-on image fetches
them, and the engine (YuNet + SFace through OpenCV) runs when OpenCV and the models are present.

The live part runs where opencv-python-headless and the models are installed (the ERP image, or a developer
machine with CUSTOM_HR_FACE_MODELS set); elsewhere it is skipped. No network: downloads are replaced.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
_frappe = sys.modules.setdefault('frappe', types.ModuleType('frappe'))
if not hasattr(_frappe, 'conf'):
    _frappe.conf = {}
import fetch_face_models as ffm  # noqa: E402

PINS = json.loads((ROOT / 'deployment' / 'face-models.json').read_text(encoding='utf-8'))


class Pins(unittest.TestCase):
    def test_exact_commit_and_a_checksum_for_every_file(self):
        self.assertRegex(PINS['commit'], r'^[0-9a-f]{40}$')
        self.assertTrue(PINS['model_id'].startswith('opencv-zoo-' + PINS['commit'][:7]))
        targets = {f['target'] for f in PINS['files']}
        self.assertTrue({'face_recognition_sface_2021dec.onnx', 'face_detection_yunet_2023mar.onnx',
                         'LICENSE.sface', 'LICENSE.yunet'} <= targets, 'models and their licences')
        for f in PINS['files']:
            self.assertRegex(f['sha256'], r'^[0-9a-f]{64}$', f['path'])
        sface = next(f for f in PINS['files'] if f['target'].startswith('face_recognition_sface'))
        self.assertEqual(sface['sha256'], '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
                         'the fp32 file discussed upstream in opencv/opencv_zoo#313')

    def test_urls_are_the_pinned_commit(self):
        for f in PINS['files']:
            url = ffm.url_for(PINS, f)
            self.assertIn('/opencv/opencv_zoo/' + PINS['commit'] + '/', url)
            self.assertTrue(url.startswith('https://media.githubusercontent.com/media/' if f['lfs'] else
                                           'https://raw.githubusercontent.com/'))


class Fetch(unittest.TestCase):
    def pins(self, data):
        return {**PINS, 'files': [dict(f, sha256=hashlib.sha256(data[f['target']]).hexdigest()) for f in PINS['files']]}

    def test_writes_files_model_id_and_source_note(self):
        data = {f['target']: f['target'].encode() for f in PINS['files']}
        pins = self.pins(data)
        by_url = {ffm.url_for(pins, f): data[f['target']] for f in pins['files']}
        with tempfile.TemporaryDirectory() as tmp:
            out = ffm.fetch(tmp, pins, get=by_url.__getitem__)
            self.assertEqual((out / 'model-id').read_text().strip(), PINS['model_id'])
            self.assertIn(PINS['commit'], (out / 'SOURCE').read_text())
            for target, content in data.items():
                self.assertEqual((out / target).read_bytes(), content)

    def test_a_changed_file_stops_the_fetch(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(RuntimeError) as raised:
            ffm.fetch(tmp, PINS, get=lambda url: b'not the pinned file')
        self.assertIn('differs from the pin', str(raised.exception))


class Image(unittest.TestCase):
    def test_the_addon_image_fetches_the_pinned_models_where_the_engine_looks(self):
        dockerfile = (ROOT / 'deployment' / 'erp' / 'Dockerfile.addon').read_text(encoding='utf-8')
        self.assertIn('fetch_face_models.py', dockerfile)
        self.assertIn('--pins /opt/cloud-build/face/face-models.json --output /opt/face-models', dockerfile)
        engine = (ROOT / 'erpnext_drive_integrations' / 'custom_hr' / 'face_sface.py').read_text(encoding='utf-8')
        self.assertIn("'/opt/face-models'", engine)
        for target in ('face_detection_yunet_2023mar.onnx', 'face_recognition_sface_2021dec.onnx'):
            self.assertIn(target, engine)

    def test_the_build_context_holds_everything_the_addon_image_copies(self):
        # The add-on image is built from the rendered folder, not from the checkout (found by the first test build).
        import render_runtime
        dockerfile = (ROOT / 'deployment' / 'erp' / 'Dockerfile.addon').read_text(encoding='utf-8')
        sources = []
        for line in dockerfile.splitlines():
            parts = line.split()
            if parts[:1] == ['COPY']:
                sources += [p for p in parts[1:-1] if not p.startswith('--')]
        self.assertIn('deployment/face-models.json', sources)
        with tempfile.TemporaryDirectory() as tmp:
            logo = Path(tmp) / 'logo.svg'
            logo.write_text('<svg/>')
            build = Path(tmp) / 'build'
            render_runtime.render(ROOT, build, {'domain': 'example.net', 'asset_version': 'abcdef1',
                                                'company_logo': str(logo)})
            pins = json.loads((build / 'deployment' / 'face-models.json').read_text(encoding='utf-8'))
            self.assertEqual(pins, PINS, 'rendering must not alter the model list')
            for source in sources:
                self.assertTrue((build / source).exists(), source + ' is missing from the build context')

    def test_opencv_is_pinned_in_the_image(self):
        constraints = (ROOT / 'deployment' / 'python-constraints.txt').read_text(encoding='utf-8')
        self.assertRegex(constraints, r'(?m)^opencv-python-headless==5\.')

    def test_the_watch_follows_the_model_pin(self):
        watch = json.loads((ROOT / 'deployment' / 'upstream-watch.json').read_text(encoding='utf-8'))
        self.assertEqual(watch['sources']['opencv_zoo']['github'], 'opencv/opencv_zoo')


def _live():
    folder = Path(os.environ.get('CUSTOM_HR_FACE_MODELS', '/opt/face-models'))
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
    except ImportError:
        return None
    return folder if (folder / 'model-id').is_file() else None


@unittest.skipUnless(_live(), 'needs opencv-python-headless and the face models (ERP image or CUSTOM_HR_FACE_MODELS)')
class LiveEngine(unittest.TestCase):
    def test_one_face_gives_128_numbers_and_a_blank_photo_is_refused(self):
        import cv2
        import numpy
        from erpnext_drive_integrations.custom_hr.face_sface import SFaceEngine
        engine = SFaceEngine(_live())
        self.assertTrue(engine.model_id.startswith('opencv-zoo-'))
        blank = cv2.imencode('.jpg', numpy.full((400, 400, 3), 128, numpy.uint8))[1].tobytes()
        with self.assertRaises(ValueError):
            engine.embed(blank)


if __name__ == '__main__':
    unittest.main()
