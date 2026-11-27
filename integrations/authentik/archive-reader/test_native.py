"""Run in `ak shell` on a throwaway authentik of the release we run. Everything is rolled back at the end.

Builds production-shaped objects (staff and test groups, the released sign-in gate, staff and test mail
applications), applies archive_reader_access.py and checks who may sign in and which applications admit
the reader; then the rollback and the refusals.
"""
import json
import tempfile
from pathlib import Path
from uuid import uuid4

from django.db import transaction
from authentik.core.models import Application, Group, User
from authentik.policies.engine import PolicyEngine
from authentik.policies.expression.models import ExpressionPolicy
from authentik.policies.models import PolicyBinding
from authentik.policies.types import PolicyRequest

HERE = Path(globals().get("ARCHIVE_READER_DIR", "/data/archive-reader"))
module = {}
exec(compile((HERE / "archive_reader_access.py").read_text(), "archive_reader_access.py", "exec"), module)
passed = []


def check(condition, name):
    assert condition, name
    passed.append(name)


class Rollback(Exception):
    pass


def gate(policy, user):
    request = PolicyRequest(user)
    request.context["pending_user"] = user
    return policy.passes(request).passing


def admits(slug, user):
    engine = PolicyEngine(Application.objects.get(slug=slug), user)
    engine.use_cache = False
    engine.build()
    return engine.passing


try:
    with transaction.atomic():
        tag = uuid4().hex[:8]
        staff_group = Group.objects.create(name="Staff " + tag)
        testers = Group.objects.create(name="Testers " + tag)
        policy = ExpressionPolicy.objects.create(name="ns-passkey-approved-account-" + tag,
                                                 expression=module["gate_expression"](staff_group.name))
        def user(name, *groups, active=True):
            u = User.objects.create(username=name + "-" + tag, name=name, type="internal", is_active=active)
            for g in groups:
                u.ak_groups.add(g)
            return u
        staff = user("staff", staff_group)
        tester = user("tester", testers)
        reader = user("archive-reader", testers)
        outsider = user("outsider")
        def app(slug, group):
            a = Application.objects.create(slug=slug + "-" + tag, name=slug, policy_engine_mode="all")
            PolicyBinding.objects.create(target=a, group=group, order=0)
            return a.slug
        test_mail, test_erp, prod_mail = app("test-office-mail", testers), app("test-erpnext", testers), app("office-mail", staff_group)
        profile = {"policy": policy.name, "staff_group": staff_group.name, "reader_group": "Mail Archive Readers " + tag,
                   "reader": reader.username, "leave_groups": [testers.name], "mail_apps": [test_mail]}

        check(gate(policy, staff) and not gate(policy, reader), "before: staff pass the sign-in gate, the reader does not")
        p = module["plan"](profile)
        check(p["problems"] == [] and len(p["changes"]) == 6, "plan lists six changes and no problems")
        receipt = Path(tempfile.mkdtemp()) / "receipt.json"
        result = module["apply"](profile, receipt)
        check(result["problems"] == [] and receipt.exists(), "apply writes the receipt and checks clean")
        policy.refresh_from_db()
        check(gate(policy, reader), "after: the reader passes the sign-in gate")
        check(gate(policy, staff), "after: staff still pass the sign-in gate")
        check(not gate(policy, tester) and not gate(policy, outsider), "after: test-only and outside accounts still refused")
        reader.is_active = False; reader.save()
        check(not gate(policy, reader), "a deactivated reader is refused")
        reader.is_active = True; reader.save()
        check(admits(test_mail, reader) and admits(test_mail, tester), "test mail admits the reader and testers")
        check(not admits(test_mail, staff) and not admits(test_mail, outsider), "test mail still refuses others")
        check(not admits(test_erp, reader), "the reader no longer reaches other test applications")
        check(admits(test_erp, tester), "testers keep the other test applications")
        check(not admits(prod_mail, reader) and admits(prod_mail, staff), "production mail unchanged: staff yes, reader no")
        count = PolicyBinding.objects.filter(target__in=Application.objects.filter(slug=test_mail)).count()
        module["apply"](profile, receipt)
        check(PolicyBinding.objects.filter(target__in=Application.objects.filter(slug=test_mail)).count() == count,
              "a rerun adds nothing")
        check(module["rollback"](receipt) == {"restored": True}, "rollback restores the recorded state")
        policy.refresh_from_db(); reader.refresh_from_db()
        check(not gate(policy, reader) and admits(test_erp, reader), "after rollback the reader is back as before")
        check(Application.objects.get(slug=test_mail).policy_engine_mode == "all", "after rollback test mail mode is all")
        check(not Group.objects.filter(name=profile["reader_group"]).exists(), "the created group is removed again")
        policy.expression += "\n# hand edit"; policy.save()
        check(module["plan"](profile)["problems"], "a hand-edited gate is reported")
        try:
            module["apply"](profile, receipt.with_name("other.json"))
            check(False, "a hand-edited gate is refused")
        except RuntimeError:
            check(policy.expression.endswith("# hand edit"), "a hand-edited gate is refused and left as it is")
        policy.expression = module["gate_expression"](staff_group.name); policy.save()
        staff_reader = dict(profile, reader=staff.username)
        check(module["plan"](staff_reader)["problems"], "a staff account cannot be made the reader")

        # configure_test_clients.py: `also_groups` admits the reader group, and a rerun without it keeps it.
        from authentik.flows.models import Flow, FlowDesignation
        from authentik.providers.oauth2.models import OAuth2Provider, RedirectURI, RedirectURIMatchingMode
        readers = Group.objects.create(name="Mail Archive Readers " + tag)
        template = OAuth2Provider.objects.create(
            name="Provider for Office Mail " + tag, client_id="office-mail-" + tag, client_type="public",
            authorization_flow=Flow.objects.create(slug="authz-" + tag, name="authz", title="authz",
                                                   designation=FlowDesignation.AUTHORIZATION),
            invalidation_flow=Flow.objects.create(slug="inval-" + tag, name="inval", title="inval",
                                                  designation=FlowDesignation.INVALIDATION),
            grant_types=["authorization_code", "refresh_token"],
            redirect_uris=[RedirectURI(RedirectURIMatchingMode.STRICT, "https://mail.example.test/en/auth/callback")])
        Application.objects.create(slug="office-mail-template-" + tag, name="Mail", provider=template)
        clients = {}
        exec(compile((HERE / "configure_test_clients.py").read_text(), "configure_test_clients.py", "exec"), clients)
        prof = Path(tempfile.mkdtemp()) / "profile.json"
        settings = {"template_slug": "office-mail-template-" + tag, "name": "Mail", "url": "https://test-mail.example.test",
                    "also_groups": [readers.name]}
        prof.write_text(json.dumps({"prefix": "test-" + tag + "-", "approved_group": testers.name, "sso_url": "https://sso.example.test",
                                    "applications": {"office-mail": settings}}))
        clients["configure"](prof, prof.with_name("out.json"))
        made = Application.objects.get(slug="test-" + tag + "-office-mail")
        groups = sorted(b.group.name for b in PolicyBinding.objects.filter(target=made))
        check(made.policy_engine_mode == "any" and groups == sorted([testers.name, readers.name]),
              "test client setup binds testers or the reader group, mode any")
        del settings["also_groups"]
        prof.write_text(json.dumps({"prefix": "test-" + tag + "-", "approved_group": testers.name, "sso_url": "https://sso.example.test",
                                    "applications": {"office-mail": settings}}))
        clients["configure"](prof, prof.with_name("out.json"))
        made.refresh_from_db()
        check(made.policy_engine_mode == "any" and PolicyBinding.objects.filter(target=made).count() == 2,
              "a rerun without also_groups keeps both groups admitted")
        raise Rollback
except Rollback:
    pass
check(not User.objects.filter(username__endswith="-" + tag).exists() and not Group.objects.filter(name__endswith=tag).exists(),
      "all throwaway objects rolled back")
print(json.dumps({"passed": len(passed), "checks": passed}, indent=1))
