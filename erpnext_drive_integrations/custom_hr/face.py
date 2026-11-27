"""Framework-independent face matching rules for field team attendance (P95).

The server holds one encrypted set of face templates per enrolled worker (one template per enrolment angle). A
supervisor's photograph is turned into one template by the face engine (`face_engine.py`) and compared only with the
workers rostered for that site and shift. These rules decide between a confident match, a short list of candidates
for the supervisor (online) or the project manager (offline queue), and no match. No photograph is kept here.

The default thresholds suit the SFace model's cosine similarity (OpenCV documents 0.363 as its same-person threshold)
and are to be tuned in the P95 trial; a site can override them in site config `custom_hr_face` (see the README).
"""
import math

from erpnext_drive_integrations.custom_hr.domain import RuleError

DEFAULTS = {'match': 0.363, 'margin': 0.05, 'floor': 0.25, 'candidates': 3, 'minimum_angles': 3, 'same_person': 0.30}
LIMITS = {'match': (0.2, 0.95), 'margin': (0.0, 0.5), 'floor': (0.0, 0.9), 'candidates': (1, 5),
          'minimum_angles': (1, 10), 'same_person': (0.0, 0.95)}
MAXIMUM_ANGLES = 10


def settings(overrides=None):
    """Thresholds with a site's overrides, refusing values outside safe bounds rather than silently clamping."""
    values = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key not in DEFAULTS:
            raise RuleError(f'Unknown face matching setting: {key}.')
        low, high = LIMITS[key]
        number = int(value) if isinstance(DEFAULTS[key], int) else float(value)
        if not (low <= number <= high) or (isinstance(number, float) and not math.isfinite(number)):
            raise RuleError(f'The face matching setting {key} must lie between {low} and {high}.')
        values[key] = number
    if values['floor'] > values['match']:
        raise RuleError('The candidate floor must not be above the match threshold.')
    return values


def normalise(vector, dimension=None):
    """A unit-length list of floats; refuses empty, non-finite, zero or wrongly sized vectors."""
    try:
        values = [float(x) for x in vector]
    except (TypeError, ValueError):
        raise RuleError('The face template is invalid.')
    if not values or (dimension and len(values) != dimension) or not all(math.isfinite(x) for x in values):
        raise RuleError('The face template is invalid.')
    length = math.sqrt(sum(x * x for x in values))
    if length == 0:
        raise RuleError('The face template is invalid.')
    return [x / length for x in values]


def cosine(a, b):
    if len(a) != len(b):
        raise RuleError('Face templates from different models cannot be compared.')
    return sum(x * y for x, y in zip(a, b))


def validate_enrolment(templates, rules=None):
    """Templates of one worker from several angles: enough of them, one size, and all of the same person."""
    rules = rules or settings()
    if not isinstance(templates, (list, tuple)) or not templates:
        raise RuleError('Capture the worker’s face from every angle asked for.')
    if len(templates) < rules['minimum_angles']:
        raise RuleError(f'Capture at least {rules["minimum_angles"]} angles of the worker’s face.')
    if len(templates) > MAXIMUM_ANGLES:
        raise RuleError(f'Capture at most {MAXIMUM_ANGLES} angles.')
    first = normalise(templates[0])
    unit = [first] + [normalise(t, len(first)) for t in templates[1:]]
    for i in range(len(unit)):
        for j in range(i + 1, len(unit)):
            if cosine(unit[i], unit[j]) < rules['same_person']:
                raise RuleError('The angles do not look like the same person. Start the enrolment again.')
    return unit


def worker_score(probe, templates):
    return max(cosine(probe, t) for t in templates)


def identify(probe, roster, rules=None):
    """Compare one face with the rostered workers' templates.

    `roster` maps employee -> list of unit templates. Returns a dict with `decision` ('match', 'uncertain' or 'none'),
    `employee` (only for a match) and `candidates` (best first, as (employee, score) pairs, at most
    `rules['candidates']`, never below the floor). A match needs the best score at or above the threshold and a clear
    margin over the second best, so two similar-looking workers are never decided automatically.
    """
    rules = rules or settings()
    if not roster:
        return {'decision': 'none', 'employee': None, 'candidates': []}
    first = next(iter(roster.values()))
    if not first:
        raise RuleError('A rostered worker has no face templates.')
    probe = normalise(probe, len(first[0]))
    scored = sorted(((worker_score(probe, templates), employee) for employee, templates in roster.items() if templates),
                    reverse=True)
    candidates = [(employee, round(score, 4)) for score, employee in scored if score >= rules['floor']][:rules['candidates']]
    best = scored[0][0] if scored else -1
    second = scored[1][0] if len(scored) > 1 else -1
    if best >= rules['match'] and best - second >= rules['margin']:
        return {'decision': 'match', 'employee': scored[0][1], 'candidates': candidates}
    return {'decision': 'uncertain' if candidates else 'none', 'employee': None, 'candidates': candidates}


def validate_consent(consent):
    """The signed agreement shown at enrolment (owner, 26 November 2026): a separate, explicit acceptance."""
    if not isinstance(consent, dict):
        raise RuleError('Record the worker’s consent before enrolling their face.')
    if consent.get('accepted') is not True:
        raise RuleError('The worker has not accepted the face attendance agreement.')
    version = str(consent.get('agreement_version') or '').strip()
    language = str(consent.get('language') or '').strip()
    if not version or len(version) > 40:
        raise RuleError('Name the version of the agreement the worker accepted.')
    if not language or len(language) > 40:
        raise RuleError('Name the language the agreement was shown in.')
    if consent.get('identity_checked') is not True:
        raise RuleError('Check the worker’s identity document before enrolling their face.')
    return {'agreement_version': version, 'language': language}
