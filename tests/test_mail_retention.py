"""Offline checks for integrations/mail/retention.py (P69) against a fake Stalwart."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/mail"))
import retention  # noqa: E402


class FakeStalwart:
    """Just enough of the native management and JMAP mail objects for the tool."""

    def __init__(self, stage=None):
        self.roles = [
            {"id": "u", "description": "User", "memberTenantId": None, "disabledPermissions": {}},
            {"id": "g", "description": "Group", "memberTenantId": None, "disabledPermissions": {"x": True}},
            {"id": "a", "description": "Admin", "memberTenantId": None, "disabledPermissions": {}},
        ]
        self.singletons = {"DataRetention": {"expungeTrashAfter": 2592000000},
                           "MtaStageData": {"script": stage or dict(retention.UNRESTRICTED_DATA_STAGE)}}
        self.tracers = [{"id": "t", "@type": "Log", "path": "/var/log/stalwart/", "ansi": True}]
        self.scripts = []
        self.domains = [{"id": "d", "name": "example.com"}]
        self.accounts = [{"id": "alice", "@type": "User", "name": "alice", "emailAddress": "alice@example.com"},
                         {"id": "reader", "@type": "User", "name": "archive-reader",
                          "emailAddress": "archive-reader@example.com"}]
        self.mailboxes = {}
        self.emails = {"alice": [{"id": "old", "receivedAt": "2018-01-01T00:00:00Z"},
                                 {"id": "new", "receivedAt": "2026-11-01T00:00:00Z"}]}
        self.calls = []

    def call(self, method, args, using=None):
        self.calls.append(method)
        name, verb = method.split("/")
        obj = name[2:] if name.startswith("x:") else name
        if obj in self.singletons:
            if verb == "get":
                return {"list": [dict(self.singletons[obj], id="singleton")]}
            self.singletons[obj].update(args["update"]["singleton"])
            return {"updated": {"singleton": None}}
        table = {"Role": self.roles, "Tracer": self.tracers, "SieveSystemScript": self.scripts,
                 "Domain": self.domains, "Account": self.accounts}.get(obj)
        if table is not None:
            if verb == "get":
                return {"list": copy.deepcopy(table)}
            for key, value in args.get("create", {}).items():
                row = dict(value, id=f"{obj.lower()}-{len(table)}")
                if obj == "Account":
                    row["emailAddress"] = value["name"] + "@example.com"
                    self.mailboxes[row["id"]] = [{"id": "inbox", "role": "inbox", "shareWith": {}}]
                    self.emails[row["id"]] = []
                table.append(row)
                return {"created": {key: {"id": row["id"]}}}
            for ident, change in args.get("update", {}).items():
                next(r for r in table if r["id"] == ident).update(change)
            return {"updated": {}}
        if obj == "Mailbox":
            boxes = self.mailboxes[args["accountId"]]
            if verb == "get":
                return {"list": copy.deepcopy(boxes)}
            for ident, change in args["update"].items():
                next(b for b in boxes if b["id"] == ident).update(change)
            return {"updated": {}}
        if obj == "Email":
            rows = self.emails.setdefault(args["accountId"], [])
            if verb == "query":
                ids = [r["id"] for r in rows if r["receivedAt"] < args["filter"]["before"]]
                return {"ids": ids[args.get("position", 0):][:args.get("limit", 100)], "total": len(ids)}
            if verb == "set":
                self.emails[args["accountId"]] = [r for r in rows if r["id"] not in args["destroy"]]
                return {"destroyed": args["destroy"]}
            if verb == "copy":
                source = self.emails[args["fromAccountId"]]
                for spec in args["create"].values():
                    original = next(r for r in source if r["id"] == spec["id"])
                    rows.append(dict(original, id="copy-" + spec["id"]))
                return {"created": {}}
        raise AssertionError("unexpected call " + method)


PROFILE = {"tier": "production", "admin_url": "http://127.0.0.1:1", "recovery_credential": "admin:x",
           "container": "stalwart-x", "archive_address": "archive@example.com",
           "reader_account": "archive-reader", "retention_days": 2557}


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.server = FakeStalwart()
        self.tmp = Path(tempfile.mkdtemp())
        self.receipt = self.tmp / "receipt.json"
        patches = [patch.object(retention, "client_for", return_value=self.server),
                   patch.object(retention.subprocess, "run")]
        for p in patches:
            self.addCleanup(p.stop)
        self.docker = patches[1].start()
        patches[0].start()

    def test_profile_is_validated(self):
        for bad in ({"tier": "staging"}, {"archive_address": "Archive"}, {"retention_days": 30},
                    {"log_path": "/tmp/logs/"}, {"reader_account": "a b"}):
            with self.assertRaises(ValueError):
                retention.check_profile(dict(PROFILE, **bad))

    def test_apply_sets_the_policy_and_records_the_before_state_first(self):
        archive = retention.apply(PROFILE, self.receipt)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual(receipt["expungeTrashAfter"], 2592000000)
        self.assertEqual(receipt["roles"]["g"], {"x": True})
        self.assertEqual(receipt["tracer"], {"id": "t", "path": "/var/log/stalwart/", "ansi": True})
        self.assertIn("journal_started_at", receipt)
        self.assertEqual(retention.check(PROFILE, self.server), [])
        user = next(r for r in self.server.roles if r["id"] == "u")["disabledPermissions"]
        self.assertTrue(all(user[p] for p in retention.DELETION_PERMISSIONS))
        admin = next(r for r in self.server.roles if r["id"] == "a")["disabledPermissions"]
        self.assertEqual(admin, {}, "the administrator role keeps its rights (purge needs them)")
        share = self.server.mailboxes[archive][0]["shareWith"]
        self.assertEqual(share, {"reader": {"mayReadItems": True}})
        commands = [c.args[0] for c in self.docker.call_args_list]
        self.assertEqual(commands, [["docker", "exec", "stalwart-x", "mkdir", "-p", retention.DEFAULT_LOG_PATH],
                                    ["docker", "restart", "stalwart-x"]])

    def test_apply_refuses_a_server_that_already_runs_another_filter(self):
        self.server = FakeStalwart(stage={"else": "'something-else'", "match": {}})
        with patch.object(retention, "client_for", return_value=self.server):
            with self.assertRaises(ValueError):
                retention.apply(PROFILE, self.receipt)
        self.assertFalse(self.receipt.exists())
        self.assertNotIn("x:Role/set", self.server.calls)

    def test_rerun_keeps_the_original_before_state(self):
        retention.apply(PROFILE, self.receipt)
        first = json.loads(self.receipt.read_text())
        retention.apply(PROFILE, self.receipt)
        self.assertEqual(json.loads(self.receipt.read_text()), first)

    def test_rollback_restores_settings_but_keeps_the_archive(self):
        before = copy.deepcopy((self.server.roles, self.server.singletons, self.server.tracers))
        archive = retention.apply(PROFILE, self.receipt)
        retention.rollback(PROFILE, self.receipt)
        self.assertEqual((self.server.roles, self.server.singletons, self.server.tracers), before)
        self.assertFalse(self.server.scripts[0]["isActive"])
        self.assertIn(archive, [r["id"] for r in self.server.accounts])

    def test_backfill_copies_once(self):
        archive = retention.apply(PROFILE, self.receipt)
        state = self.tmp / "state.json"
        self.assertEqual(retention.backfill(PROFILE, self.receipt, state), 2)
        self.assertEqual(retention.backfill(PROFILE, self.receipt, state), 0)
        self.assertEqual(len(self.server.emails[archive]), 2)

    def test_backfill_treats_an_already_archived_message_as_done(self):
        archive = retention.apply(PROFILE, self.receipt)
        original = self.server.call

        def call(method, args, using=None):
            if method == "Email/copy":
                raise retention.NativeError(method, {"notCreated": {"c0": {"type": "alreadyExists"}}})
            return original(method, args, using)

        self.server.call = call
        state = self.tmp / "state.json"
        retention.backfill(PROFILE, self.receipt, state)
        self.assertEqual(len(json.loads(state.read_text())["alice"]), 2)

        def refuse(method, args, using=None):
            if method == "Email/copy":
                raise retention.NativeError(method, {"notCreated": {"c0": {"type": "overQuota"}}})
            return original(method, args, using)

        self.server.call = refuse
        with self.assertRaises(retention.NativeError):
            retention.backfill(PROFILE, self.receipt, self.tmp / "other.json")

    def test_purge_counts_by_default_and_removes_only_old_mail_on_request(self):
        report = retention.purge(PROFILE)
        self.assertEqual((report["messages"], report["removed"]), (1, 0))
        self.assertEqual(len(self.server.emails["alice"]), 2)
        report = retention.purge(PROFILE, apply_changes=True)
        self.assertEqual(report["removed"], 1)
        self.assertEqual([r["id"] for r in self.server.emails["alice"]], ["new"])

    def test_a_wrong_reader_is_refused(self):
        with self.assertRaises(ValueError):
            retention.apply(dict(PROFILE, reader_account="nobody"), self.receipt)
        self.assertFalse(self.receipt.exists())
        self.assertNotIn("x:Role/set", self.server.calls)
        self.assertNotIn("x:Account/set", self.server.calls)


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import prepare_mail  # noqa: E402
import prepare_runtime  # noqa: E402

OVERRIDES = json.loads((Path(__file__).resolve().parents[1] / "integrations/mail/locale-overrides.json").read_text())


class WebmailTextTests(unittest.TestCase):
    def write(self, folder, text):
        path = Path(folder) / "locales/en/common.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(text.encode())
        return path

    def test_only_the_listed_text_changes_and_layout_is_kept(self):
        folder = tempfile.mkdtemp()
        upstream = '{\r\n  "a": {\r\n    "hint": "You can empty it.",\r\n    "list": ["x", "y"]\r\n  }\r\n}\r\n'
        path = self.write(folder, upstream)
        prepare_mail.apply_locale_overrides(Path(folder), {"locales/en/common.json": {
            "a.hint": {"from": "You can empty it.", "to": "Company mail is kept."}}})
        self.assertEqual(path.read_bytes().decode(), upstream.replace("You can empty it.", "Company mail is kept."))

    def test_a_changed_upstream_text_fails_the_build(self):
        folder = tempfile.mkdtemp()
        self.write(folder, '{"a": {"hint": "New upstream wording"}}')
        with self.assertRaises(ValueError):
            prepare_mail.apply_locale_overrides(Path(folder), {"locales/en/common.json": {
                "a.hint": {"from": "You can empty it.", "to": "Company mail is kept."}}})

    def test_override_file_is_complete(self):
        entries = OVERRIDES["locales/en/common.json"]
        self.assertGreaterEqual(len(entries), 10)
        for key, change in entries.items():
            self.assertTrue(change["from"] and change["to"] and change["from"] != change["to"], key)
            self.assertNotIn("forever?", change["to"])

    def test_build_context_is_readable_under_a_private_umask(self):
        import os, stat
        folder = Path(tempfile.mkdtemp())
        old = os.umask(0o077)
        try:
            (folder / "app").mkdir()
            (folder / "app/package.json").write_text("{}")
            (folder / "run.sh").write_text("#!/bin/sh")
            (folder / "run.sh").chmod(0o700)
        finally:
            os.umask(old)
        prepare_mail.make_readable(folder)
        self.assertEqual(stat.S_IMODE((folder / "app/package.json").stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE((folder / "app").stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((folder / "run.sh").stat().st_mode), 0o755)

    def test_webmail_policy_locks_delete_to_trash(self):
        policy = prepare_runtime.MAIL_POLICY
        self.assertEqual(policy["restrictions"]["deleteAction"], {"locked": True, "value": "trash"})
        self.assertTrue(policy["restrictions"]["deletedItemsRecovery"]["hidden"])
        self.assertFalse(policy["features"]["filesEnabled"])


if __name__ == "__main__":
    unittest.main()
