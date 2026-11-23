"""SSO session enforcement; extends Frappe hooks without editing framework code."""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlencode, urlsplit, parse_qsl, urlunsplit

import frappe
import jwt
from frappe.utils.oauth import get_oauth2_authorize_url, get_oauth2_flow, get_oauth_keys, get_oauth2_providers, get_redirect_uri, login_oauth_user, consume_oauth_state, create_oauth_state

BROWSER_COOKIE = "__Secure-cloud_browser"
PENDING_COOKIE = "cloud_logout_pending"
STATE_PATH = "/var/lib/cloud-integration/sessions.sqlite3"
FINISH = "https://erp.example.com/api/method/erpnext_drive_integrations.portal.sso.finish_logout"
SSO = "https://sso.example.com"
# Every logout ends on the company website. Rendered from the private profile
# (landing_url; default https://www.<domain>/). Apps reach it through the ERP's
# /login?logged_out=1 handler, so this is the only place that names it.
LANDING = "https://www.example.com/"
# A sign-in started from the ERP must be recent, but one passkey prompt is enough:
# authentik may reuse a login from the last FRESH_WINDOW seconds.
FRESH_WINDOW = 600
EVENT = "http://schemas.openid.net/event/backchannel-logout"
# P49: the one claim that says "approved for the workspace". The sign-in provider's scope mapping must send
# exactly this name (integrations/authentik/configuration.json, tested). A deployment whose provider sends
# another name sets it in site config as cloud_approved_claim.
APPROVED_CLAIM = "cloud_approved"


def approved_claim():
    name = frappe.conf.get("cloud_approved_claim") or APPROVED_CLAIM
    if not (isinstance(name, str) and name.replace("_", "").isalnum() and name[0].isalpha()):
        raise frappe.AuthenticationError("Invalid approval claim setting")
    return name


def is_approved(claims):
    """Only a literal true counts; a missing, misspelled or string claim refuses the sign-in."""
    return claims.get(approved_claim()) is True


def enabled():
    return bool(frappe.conf.get("cloud_sso_enforced"))


def host_only_cookie():
    """Keep a test or separately hosted portal's cookie on its own hostname."""
    return bool(frappe.conf.get("cloud_cookie_host_only"))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def registry():
    db = sqlite3.connect(STATE_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_state():
    with registry() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS browsers (id TEXT PRIMARY KEY, user TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (site TEXT NOT NULL, hash TEXT NOT NULL, browser TEXT NOT NULL, oidc_sid TEXT NOT NULL, user TEXT NOT NULL, created INTEGER NOT NULL, PRIMARY KEY(site, hash));
        CREATE INDEX IF NOT EXISTS session_oidc ON sessions(oidc_sid);
        CREATE TABLE IF NOT EXISTS revoked_oidc (sid TEXT PRIMARY KEY, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS logout_events (jti TEXT PRIMARY KEY, created INTEGER NOT NULL);
        ''')


def cookie(name, value, *, httponly=True, max_age=None):
    pending = frappe.flags.get("cloud_cookies") or []
    pending.append((name, value, httponly, max_age))
    frappe.flags.cloud_cookies = pending


def browser_id():
    raw = frappe.request.cookies.get(BROWSER_COOKIE, "")
    return digest(raw) if len(raw) == 64 else None


def issuer():
    value = frappe.conf.get("cloud_oidc_issuer")
    if not value or not value.startswith(SSO + "/application/o/"):
        raise frappe.AuthenticationError("SSO issuer configuration is missing")
    return value


def decode_token(token, *, logout=False):
    expected_issuer = issuer()
    client_id = get_oauth_keys("authentik")["client_id"]
    # The trusted issuer and key endpoint are configured, never taken from a token.
    key = jwt.PyJWKClient(expected_issuer + "jwks/", timeout=10).get_signing_key_from_jwt(token).key
    options = {"require": ["iss", "aud", "iat"] + (["jti", "events"] if logout else ["exp", "sub", "sid"])}
    claims = jwt.decode(token, key, algorithms=["RS256", "ES256"], audience=client_id, issuer=expected_issuer, options=options, leeway=15)
    if logout:
        if EVENT not in claims.get("events", {}) or "nonce" in claims or not claims.get("sid"):
            raise frappe.AuthenticationError("Invalid logout event")
        if abs(time.time() - claims["iat"]) > 300:
            raise frappe.AuthenticationError("Expired logout event")
    return claims


@frappe.whitelist(allow_guest=True, methods=["GET"])
def callback(code, state):
    if not enabled():
        from frappe.integrations.oauth2_logins import custom
        return custom(code, state)
    if not frappe.request.path.endswith("/frappe.integrations.oauth2_logins.custom/authentik"):
        raise frappe.AuthenticationError("Only Authentik sign-in is permitted")
    redirect_to = consume_oauth_state(state)
    if redirect_to is None:
        raise frappe.AuthenticationError("Your sign-in attempt is invalid or expired")
    flow = get_oauth2_flow("authentik")
    session = flow.get_auth_session(data={"code": code, "redirect_uri": get_redirect_uri("authentik"), "grant_type": "authorization_code"}, decoder=lambda b: json.loads(b.decode()))
    token_data = json.loads(session.access_token_response.text)
    claims = decode_token(token_data["id_token"])
    fresh_key = "cloud:fresh-login:" + digest(state)
    requested_at = frappe.cache.get_value(fresh_key)
    if requested_at is not None:
        frappe.cache.delete_value(fresh_key)
        if int(claims.get("auth_time") or 0) < int(requested_at) - FRESH_WINDOW:
            raise frappe.AuthenticationError("Fresh passkey authentication is required. Start sign-in again.")
    provider = get_oauth2_providers()["authentik"]
    response = session.get(provider["api_endpoint"], params=provider.get("api_endpoint_args"), timeout=10)
    response.raise_for_status()
    info = response.json()
    email = str(info.get("email", "")).lower()
    if not is_approved(claims) or not email or info.get("sub") != claims["sub"]:
        raise frappe.AuthenticationError("This identity is not approved")
    bid = browser_id()
    if bid:
        with registry() as db:
            old = db.execute("SELECT user,revoked FROM browsers WHERE id=?", (bid,)).fetchone()
            if old and old["revoked"] and host_only_cookie():
                # The ERP logout endpoint cannot clear a cookie on a different
                # hostname. Only a freshly verified OIDC callback may replace it.
                frappe.flags.cloud_reset_local_browser = True
            elif old and (old["revoked"] or old["user"] != email):
                redirect(FINISH)
    ensure_app_user(email, info, claims)
    frappe.flags.cloud_oidc_claims = claims
    login_oauth_user(info, provider="authentik", state=create_oauth_state(redirect_to))


def ensure_app_user(email, info, claims):
    """Provision basic Suite access only after a verified, approved OIDC callback."""
    if frappe.conf.get("cloud_combined_site"):
        from .combined import ensure_user
        ensure_user(email, info, claims)
        return
    if frappe.db.exists("User", email):
        if not frappe.db.get_value("User", email, "enabled"):
            raise frappe.AuthenticationError("This account is disabled on this app")
        return
    if (frappe.local.site != "suite.internal"
            or not frappe.conf.get("cloud_sso_auto_provision")
            or not is_approved(claims)
            or info.get("sub") != claims.get("sub")
            or info.get("email_verified") is not True
            or str(info.get("email", "")).lower() != email):
        raise frappe.AuthenticationError("This account is not enabled on this app")
    user = frappe.get_doc({
        "doctype": "User", "email": email,
        "first_name": info.get("given_name") or info.get("name") or email.split("@")[0],
        "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
        "roles": [{"role": "Desk User"}],
    })
    user.insert(ignore_permissions=True)
    # App hooks must not grant extra roles during first-time provisioning.
    frappe.db.delete("Has Role", {"parent": email, "parenttype": "User", "role": ["!=", "Desk User"]})


def on_login(login_manager):
    if enabled() and frappe.request and login_manager.user != "Guest" and not frappe.flags.get("cloud_oidc_claims"):
        raise frappe.AuthenticationError("Sign in through Authentik with your personal passkey")


def on_session_creation(login_manager):
    claims = frappe.flags.get("cloud_oidc_claims")
    if not enabled() or not claims or login_manager.user == "Guest":
        return
    raw = "" if frappe.flags.get("cloud_reset_local_browser") else frappe.request.cookies.get(BROWSER_COOKIE, "")
    if len(raw) != 64:
        raw = secrets.token_hex(32)
    bid = digest(raw)
    with registry() as db:
        db.execute("INSERT OR IGNORE INTO browsers(id,user,created) VALUES(?,?,?)", (bid, login_manager.user, int(time.time())))
        old = db.execute("SELECT user,revoked FROM browsers WHERE id=?", (bid,)).fetchone()
        if old["revoked"] or old["user"] != login_manager.user:
            raise frappe.AuthenticationError("Start a new SSO session")
        db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?,?)", (frappe.local.site, digest(frappe.session.sid), bid, claims["sid"], login_manager.user, int(time.time()),))
    cookie(BROWSER_COOKIE, raw)
    cookie(PENDING_COOKIE, "", httponly=False, max_age=0)


def current_record():
    if frappe.session.user == "Guest":
        return None
    with registry() as db:
        return db.execute("SELECT s.*, b.revoked FROM sessions s JOIN browsers b ON b.id=s.browser WHERE s.site=? AND s.hash=?", (frappe.local.site, digest(frappe.session.sid))).fetchone()


def revoked(record):
    if not record or record["revoked"]:
        return True
    with registry() as db:
        return db.execute("SELECT 1 FROM revoked_oidc WHERE sid=?", (record["oidc_sid"],)).fetchone() is not None


def active_browser_session():
    bid = browser_id()
    if not bid:
        return False
    with registry() as db:
        return db.execute("""SELECT 1 FROM browsers b JOIN sessions s ON s.browser=b.id
            LEFT JOIN revoked_oidc r ON r.sid=s.oidc_sid
            WHERE b.id=? AND b.revoked=0 AND r.sid IS NULL LIMIT 1""", (bid,)).fetchone() is not None


def before_request():
    if not enabled():
        return
    path = frappe.request.path
    # Signed-out landing is public and must never silently resume a session.
    # The landing page cannot be framed (frame-ancestors none). A portal frame that
    # discovers the sign-out must show the ERP's own, frameable sign-out page; its
    # Sign in button leaves the frame. Top-level navigations go to the landing page.
    framed = frappe.request.headers.get("Sec-Fetch-Dest") in ("iframe", "frame")
    if path == "/signed-out":
        if frappe.session.user != "Guest":
            redirect(FINISH)
        if not framed:
            redirect(LANDING)
    if path == "/login" and frappe.form_dict.get("logged_out"):
        redirect("/signed-out" if framed else LANDING)
    # Only top-level bare Desk navigations go to the portal Home.
    # Native iframe navigation and deep ERP links keep their existing behavior.
    if (frappe.conf.get("cloud_combined_site") and frappe.request.method == "GET"
            and path.rstrip("/") == "/desk"
            and frappe.request.headers.get("Sec-Fetch-Dest") == "document"):
        redirect("https://erp.example.com/")
    # A deep ERP page opened on its own (new tab, pasted link, bookmark) lacks
    # the portal's left-edge app menu. Open it inside the portal at the same
    # page. Pages already inside the portal frame have Sec-Fetch-Dest iframe.
    if (frappe.conf.get("cloud_combined_site") and frappe.request.method == "GET"
            and portal_app_path(path) and path != "/desk/cloud-apps"
            and frappe.request.headers.get("Sec-Fetch-Dest") == "document"
            and frappe.session.user != "Guest"):
        redirect("/?" + urlencode({"open": portal_open_target(path, frappe.request.query_string)}))
    if frappe.conf.get("cloud_combined_site") and path == "/desk/cloud-apps":
        redirect("/desk")
    # An old application cookie must not prevent a verified fresh OAuth login.
    # Clear it locally; the callback still requires a signed approved ID token.
    if path == "/login" or path.endswith("/frappe.integrations.oauth2_logins.custom/authentik"):
        if frappe.session.user != "Guest" and revoked(current_record()):
            frappe.flags.cloud_local_clear = True
            frappe.local.login_manager.logout()
            frappe.db.commit()
        if path.endswith("/frappe.integrations.oauth2_logins.custom/authentik"):
            return
    if frappe.conf.get("cloud_dashboard_host") and path in ("/", "/suite", "/apps"):
        redirect("https://erp.example.com/desk")
    if path == "/login" and frappe.request.method == "GET":
        if host_only_cookie():
            bid = browser_id()
            with registry() as db:
                old = db.execute("SELECT revoked FROM browsers WHERE id=?", (bid,)).fetchone() if bid else None
            if frappe.request.cookies.get(PENDING_COOKIE) or (old and old["revoked"]):
                cookie(BROWSER_COOKIE, "", max_age=0)
                cookie(PENDING_COOKIE, "", httponly=False, max_age=0)
                redirect("/login?logged_out=1")
        if frappe.request.cookies.get(PENDING_COOKIE):
            redirect(FINISH)
        # A participating app may reuse an active browser SSO session. A logged-out
        # browser always stays at the login page until a person chooses sign-in.
        if (frappe.conf.get("cloud_combined_site")
                and not frappe.form_dict.get("logged_out") and active_browser_session()):
            target = frappe.form_dict.get("redirect-to") or frappe.conf.get("cloud_default_app") or "/"
            parsed = urlsplit(target)
            expected_host = urlsplit(frappe.conf.get("host_name") or "").netloc
            if parsed.scheme == "https" and parsed.netloc == expected_host:
                target = parsed.path + (("?" + parsed.query) if parsed.query else "")
            elif not target.startswith("/") or target.startswith("//"):
                target = "/"
            redirect(get_oauth2_authorize_url("authentik", target))
    if path.endswith("erpnext_drive_integrations.portal.sso.backchannel"):
        # Native IdP backchannel calls cannot carry a browser CSRF token.
        return
    if path.endswith("erpnext_drive_integrations.portal.sso.finish_logout"):
        return
    if frappe.request.cookies.get(PENDING_COOKIE) and frappe.request.method == "GET" and not path.startswith("/api/"):
        redirect(FINISH)
    if frappe.session.user != "Guest":
        record = current_record()
        if revoked(record):
            frappe.flags.cloud_local_clear = True
            frappe.flags.cloud_logout_cleanup = True
            frappe.local.login_manager.logout()
            frappe.db.commit()
            if not path.startswith("/api/") and frappe.request.method == "GET":
                redirect("/login")
            raise frappe.AuthenticationError("Your SSO session has ended. Sign in again.")


def on_logout(login_manager):
    if not enabled() or frappe.flags.get("cloud_local_clear") or frappe.session.user == "Guest":
        return
    record = current_record()
    if record:
        with registry() as db:
            db.execute("UPDATE browsers SET revoked=1 WHERE id=?", (record["browser"],))
    frappe.flags.cloud_logout_cleanup = True
    cookie(PENDING_COOKIE, "1", httponly=False, max_age=600)
    cookie("cloud_logout_epoch", secrets.token_hex(16), httponly=False, max_age=604800)
    frappe.local.response["cloud_logout_url"] = FINISH


# Same-origin apps shown in portal frames: Desk pages and the Raven and
# Insights single-page apps.
PORTAL_APP_ROOTS = ("/raven", "/insights")


def portal_app_path(path):
    return path.startswith("/desk/") or any(path == root or path.startswith(root + "/") for root in PORTAL_APP_ROOTS)


def portal_open_target(path, query=b""):
    """Same-origin app path (with its query) for the portal's ?open= deep link."""
    if not portal_app_path(path) or path.startswith("//") or "\\" in path:
        raise ValueError("Only portal app paths can be opened in the portal")
    query = query.decode() if isinstance(query, bytes) else (query or "")
    return path + ("?" + query if query else "")


def redirect(url):
    from werkzeug.exceptions import HTTPException
    from werkzeug.utils import redirect as http_redirect
    raise HTTPException(response=http_redirect(url, code=302))


@frappe.whitelist(allow_guest=True, methods=["GET"])
def finish_logout():
    if frappe.session.user != "Guest":
        frappe.local.login_manager.logout()
        frappe.db.commit()
    bid = browser_id()
    if bid:
        with registry() as db:
            db.execute("UPDATE browsers SET revoked=1 WHERE id=?", (bid,))
    cookie(BROWSER_COOKIE, "", max_age=0)
    cookie(PENDING_COOKIE, "", httponly=False, max_age=0)
    cookie("cloud_logout_epoch", secrets.token_hex(16), httponly=False, max_age=604800)
    redirect("https://erp.example.com/outpost.goauthentik.io/sign_out")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def backchannel(logout_token):
    try:
        claims = decode_token(logout_token, logout=True)
    except jwt.PyJWTError:
        from werkzeug.exceptions import BadRequest
        raise BadRequest("Invalid logout token") from None
    with registry() as db:
        if not db.execute("SELECT 1 FROM logout_events WHERE jti=?", (claims["jti"],)).fetchone():
            db.execute("INSERT INTO logout_events VALUES(?,?)", (claims["jti"], int(time.time())))
            db.execute("INSERT OR IGNORE INTO revoked_oidc VALUES(?,?)", (claims["sid"], int(time.time())))
            db.execute("UPDATE browsers SET revoked=1 WHERE id IN (SELECT browser FROM sessions WHERE oidc_sid=?)", (claims["sid"],))
    return {"status": "ok"}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def session_status():
    return {"authenticated": frappe.session.user != "Guest", "logout_pending": bool(frappe.request.cookies.get(PENDING_COOKIE))}


def after_request(response, request):
    for name, value, httponly, max_age in frappe.flags.get("cloud_cookies") or []:
        response.set_cookie(name, value, domain=None if host_only_cookie() else "example.com", secure=True, httponly=httponly, samesite="Lax", max_age=max_age)
    if frappe.flags.get("cloud_logout_cleanup"):
        response.headers["Clear-Site-Data"] = '"cache", "storage"'
    if enabled() and response.content_type and "text/html" in response.content_type and not response.direct_passthrough:
        html = response.get_data(as_text=True)
        script = '<script defer src="/assets/erpnext_drive_integrations/session.js?v=20261119-marker"></script>'
        if "</head>" in html and "/assets/erpnext_drive_integrations/session.js" not in html:
            response.set_data(html.replace("</head>", script + "</head>", 1))
    if enabled() and not request.path.startswith("/assets/"):
        response.headers["Cache-Control"] = "no-store, private"
        response.headers["Pragma"] = "no-cache"


@frappe.whitelist(allow_guest=True, methods=["GET"])
def start_signin():
    """A deliberate sign-in requires a recent IdP authentication (FRESH_WINDOW).

    prompt=login with max_age=0 made authentik ask for the passkey twice (a login
    that took a second was already "too old"); max_age=FRESH_WINDOW asks once.
    """
    url = get_oauth2_authorize_url("authentik", "/place_holder")
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.pop("prompt", None)
    query.update({"max_age": str(FRESH_WINDOW)})
    state = query.get("state")
    if not state:
        raise frappe.AuthenticationError("Unable to start secure sign-in")
    frappe.cache.set_value("cloud:fresh-login:" + digest(state), int(time.time()), expires_in_sec=600)
    redirect(urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)))
