"""Run in the Authentik shell after inventory, backup and integration tests.

This creates only namespaced objects and updates WebAuthn provider restrictions.
It does not change any group membership, delete existing keys, or send mail.
"""
from pathlib import Path
from textwrap import indent
from django.core import serializers
from django.db import transaction
from authentik.core.models import Application, User
from authentik.flows.models import Flow, FlowStageBinding
from authentik.policies.models import PolicyBinding
from authentik.policies.expression.models import ExpressionPolicy
from authentik.stages.authenticator_webauthn.models import AuthenticatorWebAuthnStage, WebAuthnDevice, WebAuthnDeviceType
from authentik.stages.authenticator_validate.models import AuthenticatorValidateStage
from authentik.stages.deny.models import DenyStage
from authentik.stages.email.models import EmailStage
from authentik.stages.invitation.models import InvitationStage
from authentik.stages.user_login.models import UserLoginStage

ROOT = Path("/data/cloud-invitations")
source = (ROOT / "native_recovery.py").read_text()
allowed = ["fbfc3007-154e-4ecc-8c0b-6e020557d7bd", "dd4ec289-e01d-41c9-bb89-70fa845d4bf2", "d548826e-79b4-db40-a3d8-11116f7e8349", "ea9b8d66-4d01-1d21-3ce4-b6b48cb575d4", "adce0002-35bc-c60a-648b-0b25f1f05503"]
types = list(WebAuthnDeviceType.objects.filter(aaguid__in=allowed))
assert {str(t.aaguid) for t in types} == set(allowed), "Required approved-provider metadata is missing"
admin = User.objects.get(username="alex@example.com", is_active=True)
assert admin.is_superuser and WebAuthnDevice.objects.filter(user=admin, confirmed=True, aaguid__in=allowed).exists(), "No allowed administrator key"
baseline = Flow.objects.get(slug="cloud-first-time-enrollment")
assert baseline.authentication == "require_unauthenticated"
backup = ROOT / "native-before.json"
if not backup.exists():
    objects = [*Flow.objects.all(), *FlowStageBinding.objects.all(), *PolicyBinding.objects.all(),
               *ExpressionPolicy.objects.all(), *AuthenticatorWebAuthnStage.objects.all(),
               *AuthenticatorValidateStage.objects.all(), *EmailStage.objects.all()]
    backup.write_text(serializers.serialize("json", objects)); backup.chmod(0o600)


def gate(flow, stage, order, function):
    expression = source + "\ntry:\n    plan = request.context.get('flow_plan')\n    ctx = plan.context if plan else request.context\n    return " + function + "(ctx)\nexcept Exception:\n    return False\n"
    policy, _ = ExpressionPolicy.objects.update_or_create(name="cloud-invite-" + function,
                                                         defaults={"expression": expression, "execution_logging": False})
    binding, _ = FlowStageBinding.objects.update_or_create(target=flow, order=order,
        defaults={"stage": stage, "evaluate_on_plan": False, "re_evaluate_policies": True, "policy_engine_mode": "all"})
    PolicyBinding.objects.update_or_create(target=binding, policy=policy,
        defaults={"order": 0, "enabled": True, "negate": True, "failure_result": True, "timeout": 30})


with transaction.atomic():
    # Stage re-evaluation receives a COPY of plan.context. Mutations must target
    # flow_plan.context explicitly or the next Email stage has no pending user.
    # Preserve existing checks, and invert legacy deny predicates so exceptions
    # cannot silently skip a Deny stage.
    for name in ("cloud-enrollment-approved-first-time-user", "cloud-enrollment-verified-first-time-user"):
        policy = ExpressionPolicy.objects.get(name=name)
        if "def enrollment_denied():" not in policy.expression:
            original = policy.expression.replace("ctx = request.context", "plan = request.context.get('flow_plan')\nctx = plan.context if plan else request.context")
            assert original != policy.expression
            policy.expression = "def enrollment_denied():\n" + indent(original, "    ") + "\ntry:\n    return not enrollment_denied()\nexcept Exception:\n    return False\n"
            policy.save(update_fields=["expression"])
        PolicyBinding.objects.filter(policy=policy).update(negate=True, failure_result=True)
    recovery, _ = Flow.objects.update_or_create(slug="cloud-passkey-recovery-invitation", defaults={
        "name": "Cloud passkey recovery invitation", "title": "Replace your Cloud passkeys",
        "designation": "enrollment", "authentication": "require_unauthenticated", "denied_action": "message"})
    deny, _ = DenyStage.objects.update_or_create(name="cloud-recovery-deny", defaults={
        "deny_message": "This recovery cannot continue. Your old passkeys have not been replaced. Contact your administrator."})
    invitation, _ = InvitationStage.objects.get_or_create(name="cloud-recovery-invitation", defaults={"continue_flow_without_invitation": False})
    assert not invitation.continue_flow_without_invitation
    email, _ = EmailStage.objects.update_or_create(name="cloud-recovery-email", defaults={
        "use_global_settings": True, "activate_user_on_success": False, "token_expiry": "minutes=15",
        "subject": "Verify your email to replace your Cloud passkeys", "template": "email/account_confirmation.html"})
    setup, _ = AuthenticatorWebAuthnStage.objects.update_or_create(name="cloud-recovery-passkey", defaults={
        "friendly_name": "Create your replacement passkey",
        "user_verification": "required", "resident_key_requirement": "required", "authenticator_attachment": None, "hints": []})
    validate, _ = AuthenticatorValidateStage.objects.update_or_create(name="cloud-recovery-verify-replacement", defaults={
        "device_classes": ["webauthn"], "not_configured_action": "deny", "last_auth_threshold": "seconds=0",
        "webauthn_user_verification": "required"})
    validate.webauthn_allowed_device_types.set(types)
    login, _ = UserLoginStage.objects.get_or_create(name="cloud-recovery-login")
    for order, stage in [(10, invitation), (30, email), (50, setup), (60, validate), (80, login)]:
        FlowStageBinding.objects.update_or_create(target=recovery, order=order, defaults={
            "stage": stage, "evaluate_on_plan": False, "re_evaluate_policies": True})
    for order, function in [(20, "begin_recovery"), (40, "verified_snapshot"), (70, "commit_recovery")]:
        gate(recovery, deny, order, function)
    # Every available WebAuthn registration stage gets the same allowed providers,
    # including profile/self-service stages. No mobile-only attachment restriction.
    for stage in AuthenticatorWebAuthnStage.objects.all():
        stage.device_type_restrictions.set(types)
        stage.user_verification = "required"; stage.resident_key_requirement = "required"
        stage.authenticator_attachment = None; stage.hints = []
        stage.save(update_fields=["user_verification", "resident_key_requirement", "authenticator_attachment", "hints"])
    # Existing passwordless validation rejects known non-allowed providers. The
    # extra execution gate also rejects untyped legacy/unknown credentials.
    login_flow = Flow.objects.get(slug="cloud-passkey-login")
    login_bindings = list(FlowStageBinding.objects.filter(target=login_flow).order_by("order"))
    login_binding = next(b for b in login_bindings if UserLoginStage.objects.filter(pk=b.stage_id).exists())
    gate_order = login_binding.order - 1
    assert not FlowStageBinding.objects.filter(target=login_flow, order=gate_order).exclude(stage=deny).exists()
    for stage in AuthenticatorValidateStage.objects.filter(pk__in=[b.stage_id for b in login_bindings]):
        stage.webauthn_allowed_device_types.set(types)
    gate(login_flow, deny, gate_order, "allowed_signin")
    application, _ = Application.objects.update_or_create(slug="cloud-invite-user", defaults={
        "name": "Invite user", "meta_launch_url": "",
        "meta_description": "Send first-time enrollment or passkey recovery invitations", "policy_engine_mode": "all"})
    admin_policy, _ = ExpressionPolicy.objects.update_or_create(name="cloud-invite-admin-only", defaults={
        "expression": "return False  # Entry moved to the admin Directory navigation."})
    PolicyBinding.objects.update_or_create(target=application, policy=admin_policy, defaults={"order": 0, "enabled": True})
    print("NATIVE_INSTALLED", str(recovery.pk), "PROVIDERS", [t.description for t in types])
    print("KEYS_PRESERVED", WebAuthnDevice.objects.count())

# Preserve the current single-email invitation design on repeat installation.
exec(compile((ROOT / "install_single_email.py").read_text(), "install_single_email.py", "exec"))
