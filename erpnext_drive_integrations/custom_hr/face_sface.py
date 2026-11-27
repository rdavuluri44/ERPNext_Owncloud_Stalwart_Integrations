"""The face engine of P95: OpenCV Zoo's YuNet detector and SFace recogniser, run by OpenCV on the server.

Adopted on 26 November 2026 (owner; adoption check in docs/decisions.md). The models are fetched into the ERP
add-on image at a pinned commit with checksums (deployment/face-models.json, tools/fetch_face_models.py) into
`/opt/face-models` (override with the environment variable CUSTOM_HR_FACE_MODELS). Switched on per site with
site config `custom_hr_face` -> `engine`: `erpnext_drive_integrations.custom_hr.face_sface.SFaceEngine`.

`embed(jpeg_bytes)` returns SFace's 128 numbers for the one clear face in the photograph, or raises ValueError
when there is no face, more than one, or the face is too small or uncertain. The supervisor photographs one worker
at a time, so a second face is a reason to retake the photograph rather than to guess.
"""
import os
import threading
from pathlib import Path

MODELS = Path(os.environ.get('CUSTOM_HR_FACE_MODELS', '/opt/face-models'))
DETECTOR = 'face_detection_yunet_2023mar.onnx'
RECOGNISER = 'face_recognition_sface_2021dec.onnx'
MIN_SCORE = 0.8     # YuNet detection confidence (0.9 refused a smaller copy of a clear face in the engine test)
MIN_FACE = 80       # pixels, the shorter side of the detected face box
MAX_SIZES = 8       # detectors kept for different photo sizes
_LOCK = threading.Lock()
_LOADED = {}


def _models(folder):
    import cv2
    with _LOCK:
        if folder not in _LOADED:
            for name in (DETECTOR, RECOGNISER, 'model-id'):
                if not (folder / name).is_file():
                    raise RuntimeError(f'Face model file missing: {folder / name}')
            recogniser = cv2.FaceRecognizerSF.create(str(folder / RECOGNISER), '')
            _LOADED[folder] = ({}, recogniser, (folder / 'model-id').read_text(encoding='utf-8').strip())
        return _LOADED[folder]


def _detector(folder, size):
    """One detector per photo size: with OpenCV 5's graph engine, setInputSize after creation has no effect
    (found in the P95 engine test, 26 November 2026), so the size is given at creation. A few sizes are kept."""
    import cv2
    detectors = _models(folder)[0]
    with _LOCK:
        if size not in detectors:
            if len(detectors) >= MAX_SIZES:
                detectors.pop(next(iter(detectors)))
            detectors[size] = cv2.FaceDetectorYN.create(str(folder / DETECTOR), '', size, MIN_SCORE, 0.3, 5000)
        return detectors[size]


class SFaceEngine:
    def __init__(self, folder=None):
        self.folder = Path(folder or MODELS)
        self.model_id = _models(self.folder)[2]

    def embed(self, jpeg_bytes):
        import cv2
        import numpy
        image = cv2.imdecode(numpy.frombuffer(jpeg_bytes, dtype=numpy.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError('not an image')
        recogniser = _models(self.folder)[1]
        height, width = image.shape[:2]
        detector = _detector(self.folder, (width, height))
        with _LOCK:
            _, faces = detector.detect(image)
        faces = [] if faces is None else [f for f in faces if f[14] >= MIN_SCORE]
        if len(faces) != 1:
            raise ValueError('no single clear face' if not faces else 'more than one face')
        if min(faces[0][2], faces[0][3]) < MIN_FACE:
            raise ValueError('the face is too small; come closer')
        aligned = recogniser.alignCrop(image, faces[0])
        return [float(x) for x in recogniser.feature(aligned).flatten()]
