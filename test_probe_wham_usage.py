"""Unit tests for probe_wham_usage.py core functions.

Stdlib unittest only. No network access, no reading of the real
~/.codex/auth.json — all cases use inline dict fixtures and
tempfile.TemporaryDirectory.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import tempfile
import unittest
import urllib.error
from datetime import datetime
from email.message import Message
from pathlib import Path
from unittest.mock import patch

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

    def test_collect_windows_non_dict_rate_limit(self):
        # rate_limit is truthy but not a dict — must be treated as absent
        # instead of raising AttributeError on rate_limit.get(slot) (CR-02).
        payload = {"rate_limit": "not-a-dict"}
        self.assertEqual(probe_wham_usage.collect_windows(payload), [])

    def test_collect_windows_non_dict_additional_rate_limit_entry(self):
        # A malformed additional_rate_limits[] entry (truthy, non-dict) must
        # be skipped instead of raising AttributeError on
        # (extra or {}).get("rate_limit") (CR-02); the valid entry alongside
        # it must still be collected.
        payload = {
            "additional_rate_limits": [
                "not-a-dict",
                {
                    "limit_name": "gpt-5-pro",
                    "rate_limit": {
                        "primary_window": {
                            "limit_window_seconds": 18000,
                            "used_percent": 1,
                            "reset_at": 3,
                        }
                    },
                },
            ]
        }
        windows = probe_wham_usage.collect_windows(payload)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["limit_name"], "gpt-5-pro")


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


def _http_error(code: int, content_type: str | None = None, body: bytes = b"") -> urllib.error.HTTPError:
    hdrs = Message()
    if content_type is not None:
        hdrs.add_header("Content-Type", content_type)
    fp = io.BytesIO(body)
    return urllib.error.HTTPError(
        "https://chatgpt.com/backend-api/wham/usage", code, "msg", hdrs, fp
    )


class _FakeResponse:
    def __init__(self, status: int, content_type: str, body: bytes) -> None:
        self.status = status
        self.headers = Message()
        self.headers.add_header("Content-Type", content_type)
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info) -> bool:
        return False


class TestProbeErrorRetryable(unittest.TestCase):
    def test_default_not_retryable(self):
        exc = probe_wham_usage.ProbeError("msg")
        self.assertFalse(exc.retryable)

    def test_explicit_retryable(self):
        exc = probe_wham_usage.ProbeError("msg", retryable=True)
        self.assertTrue(exc.retryable)
        self.assertEqual(str(exc), "msg")


class TestFetchUsageErrorClassification(unittest.TestCase):
    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_401_not_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(401)
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertFalse(ctx.exception.retryable)
        self.assertIn("401", str(ctx.exception))

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_403_html_not_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(403, "text/html", b"cloudflare body")
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertFalse(ctx.exception.retryable)
        self.assertIn("Cloudflare", str(ctx.exception))

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_403_json_not_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(403, "application/json", b"{}")
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertFalse(ctx.exception.retryable)
        self.assertIn("403", str(ctx.exception))

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_429_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(429)
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertTrue(ctx.exception.retryable)
        self.assertIn("429", str(ctx.exception))

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_500_not_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = _http_error(500)
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertFalse(ctx.exception.retryable)

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_url_error_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("no route")
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertTrue(ctx.exception.retryable)
        self.assertIn("chatgpt.com", str(ctx.exception))

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_timeout_retryable(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()
        with self.assertRaises(probe_wham_usage.ProbeError) as ctx:
            probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertTrue(ctx.exception.retryable)

    @patch("probe_wham_usage.urllib.request.urlopen")
    def test_success_returns_status_and_payload(self, mock_urlopen):
        body = json.dumps({"ok": True}).encode("utf-8")
        mock_urlopen.return_value = _FakeResponse(200, "application/json", body)
        status, payload = probe_wham_usage.fetch_usage("tok", None, 5)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True})


class TestMainErrorHandling(unittest.TestCase):
    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    def test_main_stdout_redaction_post_check_blocks_leak(
        self, mock_load_tokens, mock_fetch_usage
    ):
        # "weird_field" is outside the redact() denylist and doesn't
        # contain "token", so the eyJ-looking value survives redact() —
        # main()'s stdout print path must apply the same redaction_clean()
        # post-check write_fixture() already has and refuse to print (CR-01).
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.return_value = (
            200,
            {"weird_field": "eyJhbGciOiJIUzI1NiJ9"},
        )
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = probe_wham_usage.main(["--no-fixture"])
        self.assertEqual(result, 1)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", buf.getvalue())

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    def test_main_catches_non_probeerror_exception(
        self, mock_load_tokens, mock_fetch_usage
    ):
        # Any non-ProbeError exception raised inside main()'s try block
        # (e.g. a KeyError from fetch_usage) must still be converted to the
        # single clean-diagnostic contract — no raw traceback on stdout
        # unless --debug (WR-01).
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.side_effect = KeyError("boom")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = probe_wham_usage.main(["--no-fixture"])
        self.assertEqual(result, 1)
        self.assertNotIn("Traceback", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
