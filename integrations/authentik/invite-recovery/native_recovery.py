"""Embedded into namespaced native expression policies; no vendor code patch.

Each guard is bound NEGATED to a Deny stage, so an exception/false result denies
the flow. Bind only at execution, never planning, with native flow policy caching
disabled. Installation checks these assumptions on the installed release.
"""
import hashlib
import json
from datetime import datetime
from django.db import transaction
from django.utils.timezone import now
from authentik.core.models import Token, TokenIntents, User
from authentik.stages.authenticator_webauthn.models import WebAuthnDevice
from authentik.stages.invitation.models import Invitation

RECOVERY_SLUG = "cloud-passkey-recovery-invitation"
MAX_ATTEMPTS = 5  # P78: the administrator chooses 1 to 5 attempts per link
ALLOWED_AAGUIDS = {
    "fbfc3007-154e-4ecc-8c0b-6e020557d7bd",
    "dd4ec289-e01d-41c9-bb89-70fa845d4bf2",
    "d548826e-79b4-db40-a3d8-11116f7e8349",
    "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4",
    "adce0002-35bc-c60a-648b-0b25f1f05503",
}


def approved_user(user):
    return bool(user.is_active and user.type in ("internal", "external")
                and user.ak_groups.filter(name="Workspace Users").exists())


def invitation_identity(ctx, expected_slug=RECOVERY_SLUG):
    invite = ctx.get("invitation")
    if not ctx.get("invitation_in_effect") or not invite:
        return None
    if not invite.expiring or not invite.expires or invite.expires <= now():
        return None
    if not invite.single_use and attempts_allowed(invite) is None:
        return None
    if not invite.flow_id or invite.flow.slug != expected_slug:
        return None
    creator = User.objects.filter(pk=invite.created_by_id, is_active=True).first()
    if not creator or not creator.is_superuser:
        return None
    data = invite.fixed_data or {}
    email = data.get("email")
    if not isinstance(email, str) or not email or email.strip() != email or not data.get("user_id"):
        return None
    matches = User.objects.filter(email__iexact=email, is_active=True)
    if matches.count() != 1:
        return None
    user = matches.first()
    if str(user.pk) != str(data["user_id"]) or user.email != email or not approved_user(user):
        return None
    pending = ctx.get("pending_user")
    if pending and pending.pk != user.pk:
        return None
    if not invite.single_use and not count_attempt(ctx, invite, user):
        return None
    return invite, user


def attempts_allowed(invite):
    # P78: a reusable link carries its attempt count; native single use means 1.
    value = (invite.fixed_data or {}).get("attempts")
    return value if type(value) is int and 2 <= value <= MAX_ATTEMPTS else None


def attempts_ledger(invite):
    return "cloud-invite-attempts-" + hashlib.sha256(str(invite.pk).encode()).hexdigest()


def count_attempt(ctx, invite, user):
    """Count each opening of a reusable link once; remove it after the last attempt."""
    allowed = attempts_allowed(invite)
    if allowed is None or not invite.pk:
        return False
    if ctx.get("cloud_invitation_attempt") == str(invite.pk):
        return True
    with transaction.atomic():
        row = Invitation.objects.select_for_update().filter(pk=invite.pk).first()
        if not row:
            return False
        ledger, _ = Token.objects.including_expired().get_or_create(
            identifier=attempts_ledger(invite), defaults={"user": user, "intent": TokenIntents.INTENT_VERIFICATION,
                "description": "0", "expires": invite.expires, "expiring": True})
        used = int(ledger.description or 0) + 1
        if ledger.user_id != user.pk or used > allowed:
            row.delete()
            return False
        ledger.description = str(used)
        ledger.save(update_fields=["description"])
        if used >= allowed:
            row.delete()  # the last attempt: the link stops working, like native single use
    ctx["cloud_invitation_attempt"] = str(invite.pk)
    return True


def end_invitation(invite):
    """After a successful setup a reusable link stops working, whatever attempts remain."""
    if invite is not None and not invite.single_use and invite.pk:
        Invitation.objects.filter(pk=invite.pk).delete()
        Token.objects.including_expired().filter(identifier=attempts_ledger(invite)).delete()


def begin_recovery(ctx):
    identity = invitation_identity(ctx)
    if not identity:
        return False
    _, user = identity
    ctx["pending_user"] = user
    # Lock the destination to the canonical email. No prompt-supplied override.
    ctx["email"] = user.email
    return True


def ledger_name(invite):
    # Native single-use InvitationStage deletes the row and clears its pk.
    # The admin page supplies a fresh UUID in the immutable invitation name.
    digest = hashlib.sha256((str(invite.flow_id) + ":" + invite.name).encode()).hexdigest()
    return "cloud-passkey-recovery-" + digest


def verified_snapshot(ctx):
    identity = invitation_identity(ctx)
    if not identity:
        return False
    invite, user = identity
    # The native InvitationStage validated and consumed the secret single-use
    # link delivered to the registered email. That link is now the email proof;
    # no second EmailStage/FlowToken is needed.
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        if not approved_user(user) or user.email != invite.fixed_data["email"]:
            return False
        old = list(WebAuthnDevice.objects.select_for_update().filter(user=user).values_list("pk", flat=True))
        snapshot = {"user_id": user.pk, "email": user.email, "flow": RECOVERY_SLUG,
                    "old_keys": [str(pk) for pk in old], "checkpoint": now().isoformat(),
                    "expires": invite.expires.isoformat(), "completed": False}
        ledger, created = Token.objects.including_expired().get_or_create(
            identifier=ledger_name(invite), defaults={"user": user, "intent": TokenIntents.INTENT_VERIFICATION,
                "description": json.dumps(snapshot), "expires": invite.expires, "expiring": True})
        if not created:
            saved = json.loads(ledger.description)
            if ledger.is_expired or ledger.user_id != user.pk or saved.get("completed") or saved.get("email") != user.email:
                return False
        ctx["cloud_recovery_ledger"] = ledger.identifier
        ctx["cloud_recovery_email"] = user.email
        ctx.pop("auth_method_args", None)
        ctx.pop("auth_method", None)
    return True


def commit_recovery(ctx):
    identity = invitation_identity(ctx)
    if not identity or ctx.get("cloud_recovery_completed"):
        return False
    invite, user = identity
    name = ctx.get("cloud_recovery_ledger")
    if name != ledger_name(invite) or ctx.get("cloud_recovery_email") != user.email:
        return False
    verified = ctx.get("auth_method_args", {}).get("mfa_devices", [])
    candidates = [d for d in verified if isinstance(d, WebAuthnDevice) and d.user_id == user.pk]
    if len(candidates) != 1:
        return False
    replacement_pk = candidates[0].pk
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user.pk)
        ledger = Token.objects.including_expired().select_for_update().filter(identifier=name, user=user).first()
        if not ledger or ledger.is_expired or not approved_user(user) or user.email != invite.fixed_data["email"]:
            return False
        snapshot = json.loads(ledger.description)
        if snapshot.get("completed") or snapshot.get("email") != user.email or snapshot.get("user_id") != user.pk:
            return False
        if snapshot.get("flow") != RECOVERY_SLUG or datetime.fromisoformat(snapshot["expires"]) <= now():
            return False
        old = snapshot["old_keys"]
        if str(replacement_pk) in old:
            return False
        replacement = WebAuthnDevice.objects.select_for_update().filter(pk=replacement_pk, user=user, confirmed=True).first()
        checkpoint = datetime.fromisoformat(snapshot["checkpoint"])
        if not replacement or str(replacement.aaguid).lower() not in ALLOWED_AAGUIDS:
            return False
        if replacement.created_on < checkpoint or not replacement.last_used or replacement.last_used < checkpoint:
            return False
        # Select and delete only the exact pre-recovery snapshot for this user.
        # A concurrently added key outside this snapshot is never deleted.
        deleted, _ = WebAuthnDevice.objects.filter(user=user, pk__in=old).exclude(pk=replacement_pk).delete()
        snapshot.update(completed=True, replacement=str(replacement.pk), completed_at=now().isoformat(), deleted=deleted)
        ledger.description = json.dumps(snapshot)
        ledger.save(update_fields=["description"])
        user.attributes = {**user.attributes, "cloud_verified_email": user.email}
        user.save(update_fields=["attributes"])
        ctx["pending_user"] = user
        ctx["cloud_recovery_completed"] = True
        end_invitation(invite)
    return True


def allowed_signin(ctx):
    user = ctx.get("pending_user")
    if not user or not user.pk:
        return False
    args = ctx.get("auth_method_args", {})
    devices = list(args.get("mfa_devices", []))
    if isinstance(args.get("device"), WebAuthnDevice):
        devices.append(args["device"])
    for device in devices:
        if isinstance(device, WebAuthnDevice):
            current = WebAuthnDevice.objects.filter(pk=device.pk, user=user, confirmed=True).first()
            if current and str(current.aaguid).lower() in ALLOWED_AAGUIDS:
                return True
    return False


def single_email_enrollment(ctx):
    identity = invitation_identity(ctx, "cloud-first-time-enrollment")
    if not identity:
        return False
    invite, user = identity
    if WebAuthnDevice.objects.filter(user=user).exists():
        end_invitation(invite)
        return False
    ctx["pending_user"] = user
    ctx["email"] = user.email
    user.attributes = {**user.attributes, "cloud_verified_email": user.email}
    user.save(update_fields=["attributes"])
    return True
