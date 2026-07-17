"""Unit tests for probe_wham_usage.py core functions.

Stdlib unittest only. No network access, no reading of the real
~/.codex/auth.json — all cases use inline dict fixtures and
tempfile.TemporaryDirectory.
"""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import probe_wham_usage


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _make_jwt(claims: dict) -> str:
    header = _b64url(json.dumps({"alg": "none"}).encode("utf-8"))
    payload = _b64url(json.dumps(claims).encode("utf-8"))
    return f"{header}.{payload}.sig"


class TestWindows(unittest.TestCase):
    def test_collect_windows_both(self):
        payload = {
            "rate_limit": {
                "primary_window": {
                    "limit_window_seconds": 604800,
                    "used_percent": 10,
                    "reset_at": 1,
                },
                "secondary_window": {
                    "limit_window_seconds": 18000,
                    "used_percent": 5,
                    "reset_at": 2,
                },
            }
        }
        windows = probe_wham_usage.collect_windows(payload)
        self.assertEqual(len(windows), 2)

    def test_collect_windows_null_rate_limit(self):
        payload = {"rate_limit": None}
        self.assertEqual(probe_wham_usage.collect_windows(payload), [])

    def test_collect_windows_missing_key(self):
        payload = {}
        self.assertEqual(probe_wham_usage.collect_windows(payload), [])

    def test_collect_windows_additional_rate_limits(self):
        payload = {
            "additional_rate_limits": [
                {
                    "limit_name": "gpt-5-pro",
                    "rate_limit": {
                        "primary_window": {
                            "limit_window_seconds": 18000,
                            "used_percent": 1,
                            "reset_at": 3,
                        }
                    },
                }
            ]
        }
        windows = probe_wham_usage.collect_windows(payload)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["limit_name"], "gpt-5-pro")

    def test_pick_window_found(self):
        windows = [{"limit_window_seconds": 18000}]
        self.assertIsNotNone(probe_wham_usage.pick_window(windows, 18000))

    def test_pick_window_not_found(self):
        windows = [{"limit_window_seconds": 604800}]
        self.assertIsNone(probe_wham_usage.pick_window(windows, 18000))

    def test_pick_window_tolerance(self):
        windows = [{"limit_window_seconds": 17500}]
        self.assertIsNotNone(probe_wham_usage.pick_window(windows, 18000))


class TestExtract(unittest.TestCase):
    def test_extract_fields_live_fixture(self):
        payload = {
            "user_id": "u1",
            "account_id": "a1",
            "email": "e@example.com",
            "plan_type": "plus",
            "rate_limit": {
                "allowed": True,
                "limit_reached": False,
                "primary_window": {
                    "used_percent": 16,
                    "limit_window_seconds": 604800,
                    "reset_after_seconds": 511006,
                    "reset_at": 1784792381,
                },
                "secondary_window": None,
            },
            "credits": {
                "has_credits": False,
                "unlimited": False,
                "balance": "0",
            },
        }
        fields = probe_wham_usage.extract_fields(payload)
        self.assertEqual(fields["weekly_percent"], "84")
        self.assertIsNone(fields["five_hour_percent"])
        self.assertEqual(fields["credits"], "0")
        self.assertIn("20", fields["weekly_reset_text"])
        self.assertIn("five_hour", fields["missing"])


class TestRedact(unittest.TestCase):
    def test_redact_replaces_values_and_no_mutation(self):
        original = {
            "email": "e@example.com",
            "user_id": "u1",
            "account_id": "a1",
            "access_token": "tok",
            "refresh_token": "tok2",
            "id_token": "tok3",
            "spend_control": {"individual_limit": "100"},
            "nested": {"email": "inner@example.com"},
        }
        redacted = probe_wham_usage.redact(original)
        self.assertEqual(redacted["email"], "<redacted>")
        self.assertEqual(redacted["user_id"], "<redacted>")
        self.assertEqual(redacted["account_id"], "<redacted>")
        self.assertEqual(redacted["access_token"], "<redacted>")
        self.assertEqual(redacted["refresh_token"], "<redacted>")
        self.assertEqual(redacted["id_token"], "<redacted>")
        self.assertEqual(redacted["spend_control"]["individual_limit"], "<redacted>")
        self.assertEqual(redacted["nested"]["email"], "<redacted>")
        # original must not be mutated
        self.assertEqual(original["email"], "e@example.com")
        self.assertEqual(original["spend_control"]["individual_limit"], "100")

    def test_redaction_clean_eyj_false(self):
        self.assertFalse(probe_wham_usage.redaction_clean("token eyJhbGci"))

    def test_redaction_clean_at_false(self):
        self.assertFalse(probe_wham_usage.redaction_clean("user@example.com"))

    def test_redaction_clean_true(self):
        self.assertTrue(probe_wham_usage.redaction_clean("clean text, no secrets"))


class TestJwt(unittest.TestCase):
    def test_jwt_exp_valid(self):
        future = int(datetime(2030, 1, 1).timestamp())
        token = _make_jwt({"exp": future})
        result = probe_wham_usage.jwt_exp(token)
        self.assertIsInstance(result, datetime)

    def test_jwt_exp_garbage(self):
        self.assertIsNone(probe_wham_usage.jwt_exp("garbage"))

    def test_jwt_exp_no_exp(self):
        token = _make_jwt({"sub": "user"})
        self.assertIsNone(probe_wham_usage.jwt_exp(token))


class TestLoadTokens(unittest.TestCase):
    def test_load_tokens_missing_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
                probe_wham_usage.load_tokens(path)
            self.assertIn("auth.json", str(ctx.exception))

    def test_load_tokens_apikey_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text(
                json.dumps({"auth_mode": "apikey", "tokens": None}),
                encoding="utf-8",
            )
            with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
                probe_wham_usage.load_tokens(path)
            self.assertIn("codex login", str(ctx.exception))

    def test_load_tokens_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text(
                json.dumps({"tokens": {"access_token": "abc", "account_id": "acc1"}}),
                encoding="utf-8",
            )
            token, account_id = probe_wham_usage.load_tokens(path)
            self.assertEqual(token, "abc")
            self.assertEqual(account_id, "acc1")

    def test_load_tokens_no_account_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "auth.json"
            path.write_text(
                json.dumps({"tokens": {"access_token": "abc"}}),
                encoding="utf-8",
            )
            token, account_id = probe_wham_usage.load_tokens(path)
            self.assertEqual(token, "abc")
            self.assertIsNone(account_id)


class TestFixtureAndHeaders(unittest.TestCase):
    def test_write_fixture_success(self):
        payload = {"email": "e@example.com", "value": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            probe_wham_usage.write_fixture(payload, path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("<redacted>", text)
            self.assertNotIn("@", text)
            self.assertNotIn("eyJ", text)

    def test_write_fixture_redaction_failure_no_file_written(self):
        # "weird_field" is outside the redact() denylist and doesn't
        # contain "token", so the eyJ-looking value survives redact() —
        # the post-check must catch it and refuse to write the file.
        payload = {"weird_field": "eyJhbGciOiJIUzI1NiJ9"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.json"
            with self.assertRaises(probe_wham_usage.ProbeError):
                probe_wham_usage.write_fixture(payload, path)
            self.assertFalse(path.exists())

    def test_build_headers_with_account_id(self):
        headers = probe_wham_usage.build_headers("tok", "acc1")
        self.assertEqual(headers["ChatGPT-Account-Id"], "acc1")
        self.assertTrue(headers["Authorization"].startswith("Bearer "))
        self.assertEqual(headers["Accept"], "application/json")

    def test_build_headers_without_account_id(self):
        headers = probe_wham_usage.build_headers("tok", None)
        self.assertNotIn("ChatGPT-Account-Id", headers)


if __name__ == "__main__":
    unittest.main()
