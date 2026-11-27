"""Run in ak shell. Disposable DB changes roll back; mail is mocked, never sent."""
import json
import runpy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.utils.timezone import now
from rest_framework.test import APIClient
from authentik.core.models import User, Group, Token
from authentik.flows.models import Flow, FlowToken, FlowStageBinding
from authentik.flows.planner import PLAN_CONTEXT_IS_RESTORED
from authentik.policies.models import PolicyBinding
from authentik.policies.process import PolicyProcess
from authentik.policies.types import PolicyRequest
from authentik.stages.invitation.models import Invitation
from authentik.stages.authenticator_webauthn.models import WebAuthnDevice, WebAuthnDeviceType

ROOT = Path("/data/cloud-invitations")
before = (User.objects.count(), WebAuthnDevice.objects.count())
passed = []
def check(condition, name):
    assert condition, name
    passed.append(name)


with transaction.atomic():
    exec(compile((ROOT / "install_native.py").read_text(), "install_native.py", "exec"), {})
    module = runpy.run_path(str(ROOT / "native_recovery.py"))
    begin, snapshot, commit = (module[n] for n in ("begin_recovery", "verified_snapshot", "commit_recovery"))
    admin = User.objects.get(username="alex@example.com")
    user = User.objects.create(username="invite-test-" + uuid4().hex, email="enrollment-test@example.invalid", name="Disposable enrollment test", type="internal")
    user.ak_groups.add(Group.objects.get(name="Workspace Users"))
    flow = Flow.objects.get(slug=module["RECOVERY_SLUG"])
    apple = "fbfc3007-154e-4ecc-8c0b-6e020557d7bd"
    bitwarden = "d548826e-79b4-db40-a3d8-11116f7e8349"
    onepassword = "bada5566-a7aa-401f-bd96-45619a55120d"  # not an approved provider
    def device(aaguid, last_used=None):
        return WebAuthnDevice.objects.create(user=user, name="Disposable key", confirmed=True,
            credential_id=uuid4().hex, public_key="dGVzdA", rp_id="sso.example.com", aaguid=aaguid,
            device_type=WebAuthnDeviceType.objects.filter(aaguid=aaguid).first(), last_used=last_used)
    old = device(bitwarden)
    invite = Invitation(name="enroll-test-" + uuid4().hex, flow=flow, created_by=admin,
        single_use=True, expiring=True, expires=now()+timedelta(hours=1), fixed_data={"email": user.email, "user_id": user.pk})
    ctx = {"invitation": invite, "invitation_in_effect": True}
    check(not begin({}), "missing invitation denied")
    check(begin(ctx) and ctx["pending_user"].pk == user.pk and ctx["email"] == user.email, "exact invitation identity loaded")
    check(not snapshot({}), "missing secret invitation cannot snapshot")
    check(snapshot(ctx), "validated emailed invitation snapshots old keys without second email")
    check(WebAuthnDevice.objects.filter(pk=old.pk).exists(), "snapshot does not delete old key")
    check(not commit(ctx), "missing replacement assertion preserves old key")
    ctx["auth_method_args"] = {"mfa_devices": [old]}
    check(not commit(ctx), "old key cannot masquerade as replacement")
    disallowed = device(onepassword, now())
    ctx["auth_method_args"] = {"mfa_devices": [disallowed]}
    check(not commit(ctx), "unapproved provider replacement denied")
    replacement = device(apple, now())
    ctx["auth_method_args"] = {"mfa_devices": [replacement]}
    user.ak_groups.clear()
    check(not commit(ctx), "revoked approval prevents deletion")
    user.ak_groups.add(Group.objects.get(name="Workspace Users"))
    user.is_active = False; user.save(update_fields=["is_active"])
    check(not commit(ctx), "inactive user prevents deletion")
    user.is_active = True; user.save(update_fields=["is_active"])
    check(commit(ctx), "verified allowed replacement completes recovery")
    check(not WebAuthnDevice.objects.filter(pk=old.pk).exists(), "old snapshot removed")
    check(WebAuthnDevice.objects.filter(pk=replacement.pk).exists(), "replacement preserved")
    check(WebAuthnDevice.objects.filter(pk=disallowed.pk).exists(), "concurrent key outside snapshot preserved")
    check(not commit(ctx), "completed context cannot replay")
    ctx.pop("cloud_recovery_completed", None)
    check(not commit(ctx), "database completion prevents replay from stale context")
    signin = module["allowed_signin"]
    check(signin({"pending_user": user, "auth_method_args": {"mfa_devices": [replacement]}}), "Apple sign-in allowed")
    check(not signin({"pending_user": user, "auth_method_args": {"mfa_devices": [disallowed]}}), "Google sign-in denied")
    check(not signin({"pending_user": user}), "missing authenticator proof denied")
    gate_binding = FlowStageBinding.objects.get(target=flow, order=20)
    policy_binding = PolicyBinding.objects.get(target=gate_binding)
    request = PolicyRequest(AnonymousUser())
    result = PolicyProcess(policy_binding, request, None).execute()
    check(result.passing, "native negated guard executes Deny on missing context")
    request.context = {"invitation": invite, "invitation_in_effect": True}
    result = PolicyProcess(policy_binding, request, None).execute()
    check(not result.passing and request.context.get("pending_user").pk == user.pk, "native compiled guard preserves pending user")
    from authentik.stages.email.models import EmailStage
    check(not FlowStageBinding.objects.filter(target__slug__in=["cloud-first-time-enrollment", module["RECOVERY_SLUG"]], stage_id__in=EmailStage.objects.values("pk")).exists(), "both invitation flows contain no second email stage")
    first = User.objects.create(username="first-test-"+uuid4().hex, email="first-test@example.invalid", type="internal")
    first.ak_groups.add(Group.objects.get(name="Workspace Users"))
    first_flow=Flow.objects.get(slug="cloud-first-time-enrollment")
    first_invite=Invitation(name="enroll-test-"+uuid4().hex,flow=first_flow,created_by=admin,single_use=True,expiring=True,expires=now()+timedelta(hours=1),fixed_data={"email":first.email,"user_id":first.pk})
    first_ctx={"invitation":first_invite,"invitation_in_effect":True}
    enroll=module["single_email_enrollment"]
    check(not enroll({}), "enrollment without secret invitation denied")
    check(enroll(first_ctx) and first_ctx["pending_user"].pk==first.pk, "first-time emailed invitation supplies exact identity without second email")
    first_invite.expires=now()-timedelta(seconds=1)
    check(not enroll(first_ctx), "expired enrollment invitation denied")
    first_invite.expires=now()+timedelta(hours=1);first_invite.fixed_data["email"]="different@example.invalid"
    check(not enroll(first_ctx), "changed destination denied")
    api = APIClient(); api.force_authenticate(user=admin)
    response = api.get("/api/v3/core/users/me/")
    check(response.status_code == 200 and response.data["user"]["is_superuser"], "native current-admin API matches companion")
    response = api.get("/api/v3/core/users/?page_size=100&include_groups=true")
    check(response.status_code == 200 and "groups_obj" in response.data["results"][0], "native user list API matches companion")
    response = api.get("/api/v3/authenticators/admin/webauthn/?page_size=100")
    check(response.status_code == 200 and isinstance(response.data["results"][0]["user"], dict), "native passkey owner API matches companion")
    response = api.post("/api/v3/stages/invitation/invitations/", {
        "name": "enroll-test-"+uuid4().hex, "flow": str(flow.pk), "single_use": True,
        "expires": (now()+timedelta(hours=1)).isoformat(), "fixed_data": {"email": user.email, "user_id": user.pk}}, format="json")
    check(response.status_code == 201, "native invitation creation API matches companion")
    invitation_pk = response.data["pk"]
    with patch("authentik.lib.expression.evaluator.BaseEvaluator.expr_send_email", return_value=True) as send:
        response = api.post("/api/v3/stages/invitation/invitations/"+str(invitation_pk)+"/send_email/", {
            "email_addresses": [user.email], "template": "email/cloud-recovery-invitation.html"}, format="json")
        check(response.status_code == 204 and send.call_count == 1, "native send API accepts namespaced template without real mail")
        check(send.call_args.kwargs["address"] == user.email, "native send destination matches approved email")
    api.force_authenticate(user=user)
    check(api.get("/api/v3/core/users/").status_code == 403, "non-admin cannot enumerate user list")
    check(api.get("/api/v3/authenticators/admin/webauthn/").status_code == 403, "non-admin cannot enumerate passkeys")
    transaction.set_rollback(True)
check(before == (User.objects.count(), WebAuthnDevice.objects.count()), "all disposable user/key changes rolled back")
print("NATIVE_TESTS_PASSED", len(passed), "REAL_MAIL_SENT", 0, "REAL_KEYS_UNCHANGED", before[1])
