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


OFFLINE_LIMIT = timedelta(days=1)
GPS_FRESHNESS = timedelta(minutes=5)
CLOCK_TOLERANCE = timedelta(minutes=2)
AUTO_CHECKOUT = timedelta(hours=12)


def corrected_time(now, offline=False, device_time=None, clock_offset_s=0):
    """When a capture happened, on the server's clock.

    Online, it happened now and the phone's clock is not used. Offline, the phone sends its own clock reading and
    the difference to the server clock it measured at its last connection (server minus phone, in seconds); the
    corrected time must lie within the last day and not in the future."""
    if not offline:
        return now
    if isinstance(clock_offset_s, bool) or not isinstance(clock_offset_s, (int, float)) or \
            not math.isfinite(clock_offset_s) or abs(clock_offset_s) > OFFLINE_LIMIT.total_seconds():
        raise RuleError('The phone clock difference is invalid. Connect once and try again.')
    if not isinstance(device_time, datetime):
        raise RuleError('An offline capture needs the time it was taken.')
    captured_at = device_time + timedelta(seconds=clock_offset_s)
    if captured_at > now + CLOCK_TOLERANCE:
        raise RuleError('The capture time is in the future. Check the phone clock and try again.')
    if captured_at < now - OFFLINE_LIMIT:
        raise RuleError('Offline captures older than one day are no longer accepted.')
    return captured_at


def capture_time(now, gps_time, offline=False, device_time=None, clock_offset_s=0):
    """(captured_at, gps_time) on the server's clock; the location must have been fetched within five minutes of
    the capture (the phone's GPS time gets the same clock correction as its capture time)."""
    captured_at = corrected_time(now, offline, device_time, clock_offset_s)
    if not isinstance(gps_time, datetime):
        raise RuleError('Capture a fresh GPS location.')
    gps_time = gps_time + (timedelta(seconds=clock_offset_s) if offline else timedelta(0))
    if abs(captured_at - gps_time) > GPS_FRESHNESS:
        raise RuleError('The location is older than five minutes. Fetch it again.')
    return captured_at, gps_time


def checkout_time(check_in, checked_out):
    """A check-out lies after the check-in and before the automatic check-out 12 hours later."""
    if checked_out < check_in:
        raise RuleError('Check-out cannot be before check-in.')
    if checked_out > check_in + AUTO_CHECKOUT:
        raise RuleError('This shift was already closed automatically after 12 hours.')
    return checked_out


def checkin_allowed(blocked, allowed_roles, user_roles, user=None):
    """Frappe HR's own check-in, as the administrator set it in HR Settings: open to everyone when not blocked;
    when blocked, only for the roles they listed (one per line or comma-separated). Background jobs run as
    Administrator and always pass."""
    if not blocked or user == 'Administrator':
        return True
    allowed = {r.strip() for r in str(allowed_roles or '').replace(',', '\n').splitlines() if r.strip()}
    return bool(allowed & set(user_roles or ()))
