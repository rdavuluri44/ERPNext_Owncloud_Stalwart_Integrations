"""Admin alert inbox (P72, P53): one place in ERP where every check on every server reports.

Each server's checks send through `tools/send_alert.py` to `report`, with a token per source. Only the SHA-256 of
each token is in site_config (`cloud_alerts.sources`), so a copy of the site config opens nothing. One row per
source and key: a repeat updates it, a resolve closes it, a new failure reopens it. Critical alerts are mailed at
once to the admins; a daily summary lists whatever is still open.

The token travels in `X-Alert-Token`, not `Authorization: Bearer`: Frappe treats any two-part Authorization
header as an OAuth or API-key sign-in and refuses the request before a guest method runs.
"""
import hashlib
import json
import re
import secrets

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, escape_html, get_url, now_datetime

DOCTYPE = "System Alert"
HEADER = "X-Alert-Token"
SEVERITIES = ("critical", "warning", "info")
KEY = re.compile(r"[a-z0-9._:-]{1,80}")
SOURCE = re.compile(r"[A-Za-z0-9._-]{1,64}")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
CONTROL_KEEP_LINES = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
LINK = re.compile(r"(https?://[^\s<>\"'\\]+|/(?![/\\])[^\s<>\"'\\]*)")  # no //host or /\host
REFUSED = "Not permitted"
LINKS_NOTE = ("Reachable only from devices on the company tailnet; each tool has its own administrator sign-in "
              "for now.")


def settings():
    conf = frappe.conf.get("cloud_alerts") or {}
    return conf if isinstance(conf, dict) else {}


def enabled():
    """The cloud_features switch, as in hooks.py (on unless set to false)."""
    return (frappe.conf.get("cloud_features") or {}).get("admin_alerts", True) is not False


def role():
    return settings().get("role") or "System Manager"


def links():
    """The admin tools panel; only http(s) addresses are shown."""
    out = []
    for item in settings().get("links") or []:
        if isinstance(item, dict) and str(item.get("url", "")).startswith(("https://", "http://")):
            out.append({"label": str(item.get("label") or item["url"]), "url": item["url"], "note": str(item.get("note") or "")})
    return out


# ---------- the report endpoint (guest, token per source) ----------

def token_hash(token):
    return hashlib.sha256(str(token or "").encode()).hexdigest()


def authorise(source, token):
    """Refuse unless `source` is configured and the token's SHA-256 equals its stored hash."""
    stored = (settings().get("sources") or {}).get(source) if isinstance(source, str) else None
    good = secrets.compare_digest(token_hash(token), str(stored or "0" * 64).lower())
    if not (stored and token and good):
        frappe.throw(REFUSED, frappe.PermissionError)


def _text(body, field, limit, required=False, lines=False):
    value = body.get(field)
    if value is None or value == "":
        if required:
            frappe.throw(f"{field} is required")
        return ""
    if not isinstance(value, str):
        frappe.throw(f"{field} must be text")
    value = (CONTROL_KEEP_LINES if lines else CONTROL).sub("", value).strip()
    if (required and not value) or len(value) > limit:
        frappe.throw(f"{field} must be 1 to {limit} characters")
    return value


def validate(body):
    """The alert from a report body, strictly checked; control characters are removed."""
    if not isinstance(body, dict):
        frappe.throw("The body must be a JSON object")
    key, severity, state = body.get("key"), body.get("severity"), body.get("state") or "open"
    if not isinstance(key, str) or not KEY.fullmatch(key):
        frappe.throw("key must be 1 to 80 of a-z 0-9 . _ : -")
    if severity not in SEVERITIES:
        frappe.throw("severity must be critical, warning or info")
    if state not in ("open", "resolved"):
        frappe.throw("state must be open or resolved")
    link = _text(body, "link", 300)
    if link and not LINK.fullmatch(link):
        frappe.throw("link must be an http(s) address or a path starting with /")
    return {"key": key, "severity": severity, "state": state, "title": _text(body, "title", 140, required=True),
            "detail": _text(body, "detail", 2000, lines=True), "host": _text(body, "host", 64), "link": link}


def _body():
    try:
        return json.loads(frappe.request.get_data(as_text=True) or "{}")
    except ValueError:
        frappe.throw("The body must be JSON")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=240, seconds=60)
def report():
    if not enabled():
        frappe.throw(REFUSED, frappe.PermissionError)
    body = _body()
    source = body.get("source") if isinstance(body, dict) else None
    authorise(source, frappe.get_request_header(HEADER) or "")
    if not SOURCE.fullmatch(source):
        frappe.throw(REFUSED, frappe.PermissionError)
    return upsert(source, validate(body))


def upsert(source, alert):
    """One row per source and key. Returns {"ok", "name", "status"}. Mails when a critical alert opens or reopens,
    when an open alert turns critical, and when a critical alert is resolved; never on a plain repeat."""
    alert_key = f"{source}:{alert['key']}"
    now = now_datetime()
    row = frappe.db.get_value(DOCTYPE, {"alert_key": alert_key}, ["name", "status"], as_dict=True, for_update=True)
    fields = {"title": alert["title"], "detail": alert["detail"], "severity": alert["severity"]}
    if alert["host"]:
        fields["host"] = alert["host"]
    if alert["link"]:
        fields["link"] = alert["link"]
    if alert["state"] == "resolved":
        if not row:
            return {"ok": True, "name": None, "status": None}
        if row.status != "Open":
            return {"ok": True, "name": row.name, "status": row.status}
        doc = frappe.get_doc(DOCTYPE, row.name)
        doc.status, doc.resolved_at = "Resolved", now
        doc.save(ignore_permissions=True)
        if doc.severity == "critical":
            notify(doc, resolved=True)
        return {"ok": True, "name": doc.name, "status": doc.status}
    if not row:
        doc = frappe.get_doc({"doctype": DOCTYPE, "alert_key": alert_key, "source": source, "status": "Open",
                              "first_seen": now, "last_seen": now, "repeat_count": 1, **fields})
        doc.insert(ignore_permissions=True)
        opened, escalated = True, False
    else:
        doc = frappe.get_doc(DOCTYPE, row.name)
        opened = doc.status != "Open"
        escalated = not opened and doc.severity != "critical" and alert["severity"] == "critical"
        doc.update(fields)
        doc.status, doc.last_seen, doc.repeat_count = "Open", now, (doc.repeat_count or 0) + 1
        if opened:
            doc.resolved_at = None
        doc.save(ignore_permissions=True)
        if opened:  # shows as unread again for everyone
            frappe.db.set_value(DOCTYPE, doc.name, "_seen", None, update_modified=False)
    if (opened or escalated) and doc.severity == "critical":
        notify(doc)
    return {"ok": True, "name": doc.name, "status": doc.status}


# ---------- mail ----------

def recipients():
    """E-mail addresses of the enabled users holding the configured role (not Administrator or Guest)."""
    users = frappe.get_all("Has Role", filters={"role": role(), "parenttype": "User"}, pluck="parent", distinct=True)
    users = [u for u in users if u not in ("Administrator", "Guest")]
    if not users:
        return []
    rows = frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, fields=["name", "email"])
    return sorted({r.get("email") for r in rows if r.get("email")})


def _when(value):
    return str(value or "")[:16]


def notify(doc, resolved=False):
    if settings().get("mail", True) is False:
        return
    to = recipients()
    if not to:
        return
    e = escape_html
    rows = [("Source", doc.source), ("Host", doc.host), ("Severity", doc.severity),
            ("Resolved" if resolved else "Since", _when(doc.resolved_at if resolved else doc.first_seen))]
    body = "".join(f"<p><b>{label}:</b> {e(str(value or '-'))}</p>" for label, value in rows)
    if doc.detail and not resolved:
        body += f"<pre>{e(doc.detail)}</pre>"
    if doc.link:
        body += f"<p><b>Where to act:</b> {e(doc.link)}</p>"
    body += f'<p><a href="{e(get_url("/admin-alerts"))}">Open the alert inbox</a></p>'
    frappe.sendmail(recipients=to, subject=("[Resolved] " if resolved else "[Alert] ") + doc.title, message=body)


def daily_digest():
    """One summary mail a day while anything is open (any severity); nothing when all is clear."""
    if settings().get("mail", True) is False:
        return
    open_alerts = frappe.get_all(DOCTYPE, filters={"status": "Open"},
                                 fields=["severity", "title", "source", "host", "first_seen"], order_by="last_seen desc")
    to = recipients() if open_alerts else []
    if not to:
        return
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    open_alerts = sorted(open_alerts, key=lambda a: rank.get(a.get("severity"), 9))
    e = escape_html
    items = "".join(f"<li><b>{e(a.get('severity') or '')}</b> {e(a.get('title') or '')} "
                    f"({e(a.get('source') or '')}{', ' + e(a['host']) if a.get('host') else ''}; "
                    f"since {e(_when(a.get('first_seen')))})</li>" for a in open_alerts)
    body = f"<p>{len(open_alerts)} alert(s) still open:</p><ul>{items}</ul>" \
           f'<p><a href="{e(get_url("/admin-alerts"))}">Open the alert inbox</a></p>'
    frappe.sendmail(recipients=to, subject=f"[Alerts] {len(open_alerts)} still open", message=body)


# ---------- the admin page and the Desk entry ----------

def is_admin(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or role() in frappe.get_roles(user)


def _seen_by(value):
    try:
        seen = json.loads(value or "[]")
    except ValueError:
        return []
    return seen if isinstance(seen, list) else []


def unread_count(user):
    rows = frappe.get_all(DOCTYPE, filters={"status": "Open"}, fields=["name", "_seen"])
    return sum(1 for r in rows if user not in _seen_by(r.get("_seen")))


def mark_seen(names, user):
    """Add the user to each alert's `_seen` without changing `modified`."""
    for name in names:
        seen = _seen_by(frappe.db.get_value(DOCTYPE, name, "_seen"))
        if user not in seen:
            frappe.db.set_value(DOCTYPE, name, "_seen", json.dumps(seen + [user]), update_modified=False)


def page_alerts(user):
    """Open alerts (newest first, with `unread`) and those resolved in the last 7 days."""
    fields = ["name", "source", "host", "severity", "status", "title", "detail", "link", "first_seen", "last_seen",
              "resolved_at", "repeat_count", "_seen"]
    open_alerts = frappe.get_all(DOCTYPE, filters={"status": "Open"}, fields=fields, order_by="last_seen desc")
    resolved = frappe.get_all(DOCTYPE, filters={"status": "Resolved", "resolved_at": [">", add_days(now_datetime(), -7)]},
                              fields=fields, order_by="resolved_at desc")
    for alert in open_alerts + resolved:
        alert["unread"] = alert["status"] == "Open" and user not in _seen_by(alert.get("_seen"))
        alert["link"] = alert.get("link") if LINK.fullmatch(alert.get("link") or "") else ""
    return open_alerts, resolved
