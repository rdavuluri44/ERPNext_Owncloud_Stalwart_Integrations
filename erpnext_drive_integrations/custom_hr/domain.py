"""Framework-independent rules shared by the service and its regression tests."""
import math
from datetime import datetime, timedelta


class RuleError(ValueError):
    pass


def coordinates(latitude, longitude, accuracy):
    try:
        lat, lon, acc = float(latitude), float(longitude), float(accuracy)
    except (TypeError, ValueError):
        raise RuleError('Capture a fresh device location before continuing.')
    if not all(math.isfinite(x) for x in (lat, lon, acc)) or not -90 <= lat <= 90 or not -180 <= lon <= 180 or acc <= 0:
        raise RuleError('The device location is invalid.')
    return lat, lon, acc


def distance_metres(lat1, lon1, lat2, lon2):
    a, b = math.radians(lat1), math.radians(lat2)
    da, db = b - a, math.radians(lon2 - lon1)
    h = math.sin(da / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(db / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def validate_location(latitude, longitude, accuracy, site_lat, site_lon, radius, maximum_accuracy):
    lat, lon, acc = coordinates(latitude, longitude, accuracy)
    if acc > maximum_accuracy:
        raise RuleError('GPS is not accurate enough. Move outdoors and fetch the location again.')
    if radius > 0 and distance_metres(lat, lon, float(site_lat), float(site_lon)) > radius:
        raise RuleError('You are outside this site’s permitted attendance area.')
    return lat, lon, acc


def validate_work_mode(required, status, mode, asset, allowed_assets):
    if status not in ('Present', 'Absent'):
        raise RuleError('Choose Present or Absent.')
    if status == 'Absent' or not required:
        if mode != 'Not applicable' or asset:
            raise RuleError('Machine allocation is not applicable to this record.')
    elif mode == 'Operating':
        if not asset or asset not in allowed_assets:
            raise RuleError('Select a machine permitted at this site.')
    elif mode == 'Standby':
        if asset:
            raise RuleError('A standby worker cannot have an operating machine.')
    else:
        raise RuleError('Choose Operating with a machine, or Standby.')


def validate_transfer(actor, current_supervisor, destination, approver, base_locked=False, shift_locked=False):
    if not destination or destination == current_supervisor:
        raise RuleError('Choose a different responsible supervisor.')
    if not approver:
        if actor != current_supervisor:
            raise RuleError('Only the responsible supervisor or site approver can transfer this worker.')
        if base_locked or shift_locked:
            raise RuleError('This assignment was made by an approver. Ask the approver to reassign it.')


def validate_reviewer(actor, captured_by, employee_user, eligible):
    if not eligible:
        raise RuleError('You are not an approver for this site.')
    if actor == captured_by or actor == employee_user:
        raise RuleError('You cannot approve your own attendance or your own submission.')


def shift_date(now, start, end):
    """Night attendance belongs to the shift's starting date."""
    return (now - timedelta(days=1)).date() if end < start and now.time() < end else now.date()
