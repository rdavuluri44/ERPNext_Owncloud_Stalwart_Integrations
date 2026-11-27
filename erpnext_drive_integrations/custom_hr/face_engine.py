"""The slot where the face model plugs in (P95).

No face model ships yet: under the working agreements a new dependency is adopted only after its licence, maintenance
and security checks, recorded in the decision log. Until then face enrolment and identification refuse with a clear
message. An engine is named in site config `custom_hr_face` -> `engine` as a dotted path to an object or factory with
`model_id` (a short text that changes whenever templates become incomparable) and `embed(jpeg_bytes) -> list[float]`
(raises ValueError when the photograph holds no single clear face).
"""
import importlib

NOT_READY = 'Face attendance is not switched on yet: the face model awaits its licence and security check (P95).'


class EngineMissing(RuntimeError):
    pass


def load(config):
    path = str((config or {}).get('engine') or '').strip()
    if not path:
        raise EngineMissing(NOT_READY)
    module, _, name = path.rpartition('.')
    if not module.startswith('erpnext_drive_integrations.'):
        raise EngineMissing('The face engine must be part of this app.')
    try:
        target = getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        raise EngineMissing('The configured face engine could not be loaded.')
    engine = target() if isinstance(target, type) or (callable(target) and not hasattr(target, 'embed')) else target
    if not callable(getattr(engine, 'embed', None)) or not str(getattr(engine, 'model_id', '') or '').strip():
        raise EngineMissing('The configured face engine is incomplete.')
    return engine
