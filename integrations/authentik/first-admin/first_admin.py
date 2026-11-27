"""Create or refresh the first administrator and print a one-time passkey link (P77).

Run through `ak shell` by first-admin.sh, which passes the settings as environment
variables. It is safe to rerun: each run invalidates the previous link and issues a
new one, for example when the administrator lost the passkey.

- The administrator has no password and signs in with a passkey from an approved
  provider only (passkey-providers.json).
- The link opens a dedicated flow that registers that passkey and signs in. It
  expires after 24 hours and works once.
- The built-in `akadmin` is switched off, not deleted: inactive, a random password
  nobody knows, no groups, roles or tokens. Upstream's first-time setup page opens
  whenever `akadmin` is missing or has no usable password, so it must stay present.
"""

import json
import os
import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from authentik.core.models import Group, Token, User
from authentik.flows.models import Flow, FlowStageBinding
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.models import PolicyBinding
from authentik.stages.authenticator_webauthn.models import AuthenticatorWebAuthnStage, WebAuthnDeviceType
from authentik.stages.invitation.models import Invitation, InvitationStage
from authentik.stages.user_login.models import UserLoginStage

FLOW = "first-admin-passkey-setup"
LINK_HOURS = 24

LOAD_IDENTITY = """
from django.utils import timezone
from authentik.core.models import User
plan = request.context.get("flow_plan")
if not plan or not plan.context.get("invitation_in_effect"):
    return False
invite = plan.context.get("invitation")
if (not invite or not invite.single_use or not invite.expiring or invite.expires <= timezone.now()
        or not invite.flow_id or invite.flow.slug != "first-admin-passkey-setup"):
    return False
data = invite.fixed_data or {}
user = User.objects.filter(pk=data.get("user_pk"), email=data.get("email"), path=data.get("path"),
                           is_active=True).first()
if not user or not user.is_superuser or user.has_usable_password():
    return False
plan.context["pending_user"] = user
plan.context.setdefault("first_admin_started", timezone.now().isoformat())
return True
"""

PASSKEY_READY = """
from datetime import datetime
from authentik.stages.authenticator_webauthn.models import WebAuthnDevice
ALLOWED = __ALLOWED__
plan = request.context.get("flow_plan")
ctx = plan.context if plan else request.context
user = ctx.get("pending_user")
started = ctx.get("first_admin_started")
if not user or not user.pk or not started:
    return False
since = datetime.fromisoformat(started)
for device in WebAuthnDevice.objects.filter(user=user, confirmed=True, created_on__gte=since):
    if str(device.aaguid).lower() in ALLOWED:
        return True
return False
"""


def setting(name, default=None):
    value = os.environ.get(name, default)
    if value is None or not str(value).strip():
        raise SystemExit(f"FIRST_ADMIN_ERROR missing {name}")
    return str(value).strip()


def bind(flow, stage, order, policy=None):
    binding, _ = FlowStageBinding.objects.update_or_create(target=flow, order=order, defaults={
        "stage": stage, "re_evaluate_policies": True, "evaluate_on_plan": False,
    })
    if policy:
        PolicyBinding.objects.update_or_create(target=binding, order=0, defaults={
            "policy": policy, "enabled": True, "negate": False, "failure_result": False,
        })


def switch_off_akadmin(admin=None):
    akadmin = User.objects.filter(username="akadmin").first()
    if akadmin and admin is not None and akadmin.pk == admin.pk:
        raise SystemExit("FIRST_ADMIN_ERROR the administrator cannot be akadmin")
    if not akadmin:
        # Present but unusable keeps upstream's first-time setup page closed.
        akadmin = User(username="akadmin", name="authentik Default Admin (switched off)", path="users")
    akadmin.is_active = False
    akadmin.set_password(secrets.token_urlsafe(48))
    akadmin.save()
    akadmin.groups.clear()
    if hasattr(akadmin, "roles"):
        akadmin.roles.clear()
    Token.objects.filter(user=akadmin).delete()
    akadmin.refresh_from_db()
    if akadmin.is_active or akadmin.is_superuser or not akadmin.has_usable_password():
        raise SystemExit("FIRST_ADMIN_ERROR akadmin could not be switched off")


@transaction.atomic
def akadmin_only():
    """Existing instances whose administrator is managed elsewhere (for example a
    Google-linked account): only make sure akadmin exists and is switched off."""
    admins = [u for u in User.objects.filter(is_active=True).exclude(username="akadmin") if u.is_superuser]
    keyed = [u for u in admins if u.webauthndevice_set.filter(confirmed=True).exists()]
    if not keyed:
        raise SystemExit("FIRST_ADMIN_ERROR no other active administrator with a passkey; nothing changed")
    existed = User.objects.filter(username="akadmin").exists()
    switch_off_akadmin()
    print(f"FIRST_ADMIN_OK akadmin={'switched-off' if existed else 'recreated-switched-off'} administrators_with_passkey={len(keyed)}")


@transaction.atomic
def run():
    email = setting("FIRST_ADMIN_EMAIL")
    name = setting("FIRST_ADMIN_NAME")
    folder = setting("FIRST_ADMIN_PATH", "administrators")
    base = setting("FIRST_ADMIN_BASE_URL", os.environ.get("AUTHENTIK_WEB__BASE_URL")).rstrip("/")
    providers = json.loads(setting("FIRST_ADMIN_PROVIDERS"))["providers"]
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise SystemExit("FIRST_ADMIN_ERROR the email address is not valid")
    if not re.fullmatch(r"[a-z0-9_-]+(/[a-z0-9_-]+)*", folder) or folder == "users":
        raise SystemExit("FIRST_ADMIN_ERROR the administrator folder is not valid")
    if not base.startswith("https://"):
        raise SystemExit("FIRST_ADMIN_ERROR the base URL must be https")
    allowed = sorted({p["aaguid"].lower() for p in providers})
    types = list(WebAuthnDeviceType.objects.filter(aaguid__in=allowed))
    if {str(t.aaguid).lower() for t in types} != set(allowed):
        raise SystemExit("FIRST_ADMIN_ERROR passkey provider metadata is missing in this authentik")

    admins = Group.objects.filter(is_superuser=True).order_by("name")
    group = admins.filter(name="authentik Admins").first() or admins.first()
    if not group:
        raise SystemExit("FIRST_ADMIN_ERROR no administrator group exists")

    matches = list(User.objects.filter(email__iexact=email))
    if len(matches) > 1:
        raise SystemExit("FIRST_ADMIN_ERROR several accounts use this email address")
    admin = matches[0] if matches else User(username=email, email=email)
    if admin.pk and (admin.path != folder or admin.username == "akadmin"):
        raise SystemExit("FIRST_ADMIN_ERROR an account with this email exists outside the administrator folder")
    if admin.pk and admin.usersourceconnection_set.exists():
        raise SystemExit("FIRST_ADMIN_ERROR the account is linked to an external sign-in source")
    admin.name, admin.path, admin.type, admin.is_active = name, folder, "internal", True
    admin.set_unusable_password()
    admin.save()
    admin.groups.add(group)

    flow, _ = Flow.objects.update_or_create(slug=FLOW, defaults={
        "name": "First administrator passkey", "title": "Set up your administrator passkey",
        "designation": "enrollment", "authentication": "require_unauthenticated",
    })
    invite_stage, _ = InvitationStage.objects.update_or_create(name="first-admin-invitation", defaults={
        "continue_flow_without_invitation": False,
    })
    passkey, _ = AuthenticatorWebAuthnStage.objects.update_or_create(name="first-admin-create-passkey", defaults={
        "friendly_name": "Administrator passkey", "user_verification": "required",
        "resident_key_requirement": "required",
    })
    passkey.device_type_restrictions.set(types)
    login, _ = UserLoginStage.objects.get_or_create(name="first-admin-login")
    load, _ = ExpressionPolicy.objects.update_or_create(name="first-admin-load-identity",
                                                       defaults={"expression": LOAD_IDENTITY})
    ready, _ = ExpressionPolicy.objects.update_or_create(name="first-admin-passkey-ready", defaults={
        "expression": PASSKEY_READY.replace("__ALLOWED__", repr(set(allowed))),
    })
    bind(flow, invite_stage, 10)
    bind(flow, passkey, 20, load)
    bind(flow, login, 30, ready)

    for old in Invitation.objects.filter(flow=flow):
        if (old.fixed_data or {}).get("user_pk") == admin.pk:
            old.delete()
    invitation = Invitation.objects.create(
        name=f"first-admin-{admin.pk}-{secrets.token_hex(4)}", flow=flow, created_by=admin,
        single_use=True, expiring=True, expires=timezone.now() + timedelta(hours=LINK_HOURS),
        fixed_data={"user_pk": admin.pk, "email": admin.email, "path": folder},
    )
    switch_off_akadmin(admin)
    print(f"FIRST_ADMIN_OK user={admin.username} folder={folder} passkeys={admin.webauthndevice_set.count()} akadmin=off")
    print(f"FIRST_ADMIN_LINK {base}/if/flow/{FLOW}/?itoken={invitation.pk}")


if os.environ.get("FIRST_ADMIN_MODE") == "akadmin-only":
    akadmin_only()
else:
    run()
