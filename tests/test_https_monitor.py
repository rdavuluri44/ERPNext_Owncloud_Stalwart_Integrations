from datetime import datetime, timedelta, timezone
from io import BytesIO
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integrations/monitoring"))
from https_probe import check, NoRedirect
from job_probe import evaluate


class ProbeTests(unittest.TestCase):
    target = {"name": "Document manager", "url": "https://docs.example.com/", "statuses": [302]}

    @patch("https_probe.build_opener")
    def test_only_configured_status_is_healthy(self, opener):
        for status, expected in ((302, True), (500, False)):
            opener.return_value.open.side_effect = HTTPError(self.target["url"], status, "", {}, BytesIO())
            self.assertEqual(check(self.target), ("Document manager", expected, f"HTTP {status}"))
        self.assertIsInstance(opener.call_args.args[0], NoRedirect)

    @patch("https_probe.build_opener")
    def test_connection_failure_suppresses_remote_error_details(self, opener):
        opener.return_value.open.side_effect = URLError("detail from remote connection")
        self.assertEqual(check(self.target), ("Document manager", False, "connection failed"))


    @patch("https_probe.certificate_days", return_value=2)
    @patch("https_probe.build_opener")
    def test_certificate_near_expiry_reports_down_for_healthy_http(self, opener, certificate):
        opener.return_value.open.side_effect = HTTPError(self.target["url"], 302, "", {}, BytesIO())
        target = dict(self.target, minimum_certificate_days=14)
        self.assertEqual(check(target), ("Document manager", False, "certificate expires in 2.0 days"))
        certificate.assert_called_once_with(self.target["url"])

    @patch("https_probe.socket.create_connection")
    def test_unreachable_tcp_target(self, connection):
        connection.side_effect = TimeoutError
        target = {"name": "Storage host", "kind": "tcp", "host": "host.example.com", "port": 443}
        self.assertEqual(check(target), ("Storage host", False, "TCP unreachable"))


class JobTests(unittest.TestCase):
    def test_failure_and_missed_success_are_reported_separately(self):
        now = datetime(2026, 11, 24, tzinfo=timezone.utc)
        outcome = {"result": "succeeded", "finished_at": (now - timedelta(hours=27)).isoformat()}
        self.assertEqual(evaluate({"result": "failed"}, outcome, "succeeded", 26, now),
                         ["latest run failed", "last success older than 26 hours"])
        self.assertEqual(evaluate(outcome, outcome, "succeeded", 192, now), [])


if __name__ == "__main__":
    unittest.main()
