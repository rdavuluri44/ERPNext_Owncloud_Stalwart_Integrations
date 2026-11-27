"""Let the mail archive reader sign in with a passkey, to the mail applications only (P69).

Run inside `ak shell` on an existing authentik. Load this file, then call one of:

    plan(profile)                     # what would change; changes nothing
    apply(profile, receipt_path)      # writes the before-state receipt first, then changes
    rollback(receipt_path)            # restores exactly what the receipt recorded
    check(profile)                    # [] when the live state matches the profile

The profile (no secrets) names the objects:

    {"policy": "<namespace>-passkey-approved-account", "staff_group": "<staff group>",
     "reader_group": "Mail Archive Readers", "reader": "archive-reader",
     "leave_groups": ["Testers"], "mail_apps": ["test-office-mail"]}

What it changes:
1. Creates the reader group (not a superuser group, no parents).
2. The passkey sign-in gate (the approved-account policy) accepts the staff group or the reader group. The
   expression must still be the released one; anything else is refused, so a hand edit is never overwritten.
3. The reader joins the reader group and leaves `leave_groups` (so it does not inherit other applications).
4. Each mail application accepts its existing groups or the reader group: the policy engine mode becomes "any"
   and one group binding is added. Applications with a policy or user binding are refused, because "any" would
   change what those bindings mean.

Other applications keep binding only the staff or test group, so the reader is refused there.
"""
import json
from pathlib import Path

from django.db import transaction
from authentik.core.models import Application, Group, User
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.models import PolicyBinding

GATE = ('user = request.context.get("pending_user")\n'
        'return bool(user and user.is_active and (user.is_superuser or '
        'user.groups.filter(name__in={groups}).exists()))')


def gate_expression(*groups):
    return GATE.format(groups=json.dumps(list(groups)))


def _bindings(app):
    rows = []
    for b in PolicyBinding.objects.filter(target=app).order_by("order"):
        rows.append({"pk": str(b.pk), "order": b.order, "group": b.group.name if b.group else None,
                     "policy": b.policy.name if b.policy else None, "user": b.user.username if b.user else None,
                     "negate": b.negate, "enabled": b.enabled})
    return rows


def snapshot(profile):
    policy = ExpressionPolicy.objects.get(name=profile["policy"])
    reader = User.objects.get(username=profile["reader"])
    group = Group.objects.filter(name=profile["reader_group"]).first()
    apps = {}
    for slug in profile["mail_apps"]:
        app = Application.objects.get(slug=slug)
        apps[slug] = {"mode": app.policy_engine_mode, "bindings": _bindings(app)}
    return {"profile": profile, "policy_expression": policy.expression,
            "reader_groups": sorted(g.name for g in reader.ak_groups.all()),
            "reader_group_existed": group is not None, "apps": apps}


def _problems_before(profile, snap):
    problems = []
    released = gate_expression(profile["staff_group"])
    target = gate_expression(profile["staff_group"], profile["reader_group"])
    if snap["policy_expression"] not in (released, target):
        problems.append("the sign-in gate expression is not the released one; refusing to overwrite it")
    for slug, app in snap["apps"].items():
        for b in app["bindings"]:
            if b["group"] is None or b["negate"] or not b["enabled"]:
                problems.append(f"{slug} has a binding that is not a plain group binding; mode 'any' would change it")
        if app["mode"] not in ("all", "any"):
            problems.append(f"{slug} has an unexpected policy engine mode")
    group = Group.objects.filter(name=profile["reader_group"]).first()
    if group and (group.is_superuser or group.parents.exists()):
        problems.append("the reader group exists with superuser rights or parents")
    reader = User.objects.get(username=profile["reader"])
    if reader.is_superuser or reader.ak_groups.filter(name=profile["staff_group"]).exists():
        problems.append("the reader is a superuser or a staff member; it must be a separate account")
    return problems


def plan(profile):
    snap = snapshot(profile)
    changes = []
    if snap["policy_expression"] != gate_expression(profile["staff_group"], profile["reader_group"]):
        changes.append("sign-in gate accepts the reader group")
    if not snap["reader_group_existed"]:
        changes.append("create group " + profile["reader_group"])
    if profile["reader_group"] not in snap["reader_groups"]:
        changes.append("reader joins " + profile["reader_group"])
    for name in profile["leave_groups"]:
        if name in snap["reader_groups"]:
            changes.append("reader leaves " + name)
    for slug, app in snap["apps"].items():
        if app["mode"] != "any":
            changes.append(slug + ": policy engine mode any")
        if profile["reader_group"] not in [b["group"] for b in app["bindings"]]:
            changes.append(slug + ": bind " + profile["reader_group"])
    return {"problems": _problems_before(profile, snap), "changes": changes}


def apply(profile, receipt_path):
    receipt = Path(receipt_path)
    if receipt.exists():
        before = json.loads(receipt.read_text())["before"]  # a rerun keeps the original before-state
        if before["profile"] != profile:
            raise RuntimeError("the receipt was written for a different profile")
    else:
        before = snapshot(profile)
        problems = _problems_before(profile, before)
        if problems:
            raise RuntimeError("; ".join(problems))
        receipt.write_text(json.dumps({"before": before}, indent=2) + "\n")
        receipt.chmod(0o600)
    with transaction.atomic():
        problems = _problems_before(profile, snapshot(profile))
        if problems:
            raise RuntimeError("; ".join(problems))
        group, _ = Group.objects.get_or_create(name=profile["reader_group"], defaults={"is_superuser": False})
        policy = ExpressionPolicy.objects.select_for_update().get(name=profile["policy"])
        policy.expression = gate_expression(profile["staff_group"], profile["reader_group"])
        policy.save(update_fields=["expression"])
        reader = User.objects.get(username=profile["reader"])
        reader.ak_groups.add(group)
        for name in profile["leave_groups"]:
            left = Group.objects.filter(name=name).first()
            if left:
                reader.ak_groups.remove(left)
        for slug in profile["mail_apps"]:
            app = Application.objects.select_for_update().get(slug=slug)
            if not PolicyBinding.objects.filter(target=app, group=group).exists():
                last = PolicyBinding.objects.filter(target=app).order_by("-order").first()
                PolicyBinding.objects.create(target=app, group=group, order=(last.order + 10) if last else 0,
                                             enabled=True, negate=False, failure_result=False)
            if app.policy_engine_mode != "any":
                app.policy_engine_mode = "any"
                app.save(update_fields=["policy_engine_mode"])
    return {"applied": True, "problems": check(profile)}


def rollback(receipt_path):
    before = json.loads(Path(receipt_path).read_text())["before"]
    profile = before["profile"]
    with transaction.atomic():
        group = Group.objects.filter(name=profile["reader_group"]).first()
        policy = ExpressionPolicy.objects.select_for_update().get(name=profile["policy"])
        policy.expression = before["policy_expression"]
        policy.save(update_fields=["expression"])
        for slug, app_before in before["apps"].items():
            app = Application.objects.select_for_update().get(slug=slug)
            kept = {b["pk"] for b in app_before["bindings"]}
            PolicyBinding.objects.filter(target=app).exclude(pk__in=kept).delete()
            app.policy_engine_mode = app_before["mode"]
            app.save(update_fields=["policy_engine_mode"])
        reader = User.objects.get(username=profile["reader"])
        reader.ak_groups.set(Group.objects.filter(name__in=before["reader_groups"]))
        if group and not before["reader_group_existed"] and not group.users.exists():
            group.delete()
    after = snapshot(profile)
    same = {k: after[k] for k in ("policy_expression", "reader_groups")} == \
        {k: before[k] for k in ("policy_expression", "reader_groups")} and \
        {s: {"mode": a["mode"], "bindings": [b["pk"] for b in a["bindings"]]} for s, a in after["apps"].items()} == \
        {s: {"mode": a["mode"], "bindings": [b["pk"] for b in a["bindings"]]} for s, a in before["apps"].items()}
    return {"restored": same}


def check(profile):
    snap = snapshot(profile)
    problems = []
    if snap["policy_expression"] != gate_expression(profile["staff_group"], profile["reader_group"]):
        problems.append("sign-in gate does not accept the reader group")
    if profile["reader_group"] not in snap["reader_groups"]:
        problems.append("reader is not in the reader group")
    for name in profile["leave_groups"]:
        if name in snap["reader_groups"]:
            problems.append("reader is still in " + name)
    for slug, app in snap["apps"].items():
        if app["mode"] != "any" or profile["reader_group"] not in [b["group"] for b in app["bindings"]]:
            problems.append(slug + " does not accept the reader group")
    return problems
