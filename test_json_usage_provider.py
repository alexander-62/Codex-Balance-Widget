"""Unit tests for json_usage_provider.py.

Stdlib unittest.IsolatedAsyncioTestCase only. No network access, no reading
of the real ~/.codex/auth.json — probe_wham_usage.load_tokens / fetch_usage
are mocked via unittest.mock.patch. Every test constructs
JsonUsageProvider(retry_delay=0) so no real asyncio.sleep wait occurs.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

import probe_wham_usage
from json_usage_provider import JsonUsageProvider

# Same weekly-only payload shape as
# test_probe_wham_usage.TestExtract.test_extract_fields_live_fixture, so
# fields["weekly_percent"] == "84" is a reusable, checkable assertion.
_PAYLOAD = {
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


class TestJsonUsageProviderFetch(unittest.IsolatedAsyncioTestCase):
    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_load_tokens_error_skips_fetch_usage(self, mock_load_tokens, mock_fetch_usage):
        mock_load_tokens.side_effect = probe_wham_usage.ProbeError("no auth.json")
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "error")
        self.assertEqual(mock_fetch_usage.call_count, 0)

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_non_retryable_error_no_retry(self, mock_load_tokens, mock_fetch_usage):
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.side_effect = probe_wham_usage.ProbeError(
            "401 unauthorized", retryable=False
        )
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "error")
        self.assertFalse(result.retried)
        self.assertEqual(mock_fetch_usage.call_count, 1)

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_unexpected_exception_becomes_error_result(self, mock_load_tokens, mock_fetch_usage):
        # Regression test for the broad `except Exception` fallback in
        # _fetch_with_retry (02-REVIEW WR-02): a non-ProbeError exception
        # (schema/encoding/IO surprise) must be converted to an error
        # JsonFetchResult instead of propagating and crashing the caller,
        # and must not be retried (treated as non-retryable).
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.side_effect = AttributeError("'str' object has no attribute 'get'")
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "error")
        self.assertIn("AttributeError", result.error)
        self.assertFalse(result.retried)
        self.assertEqual(mock_fetch_usage.call_count, 1)

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_retryable_error_then_success(self, mock_load_tokens, mock_fetch_usage):
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.side_effect = [
            probe_wham_usage.ProbeError("429 too many requests", retryable=True),
            (200, _PAYLOAD),
        ]
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "ok")
        self.assertTrue(result.retried)
        self.assertEqual(mock_fetch_usage.call_count, 2)
        self.assertEqual(result.fields, probe_wham_usage.extract_fields(_PAYLOAD))
        self.assertEqual(result.fields["weekly_percent"], "84")

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_retryable_error_twice_gives_up(self, mock_load_tokens, mock_fetch_usage):
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.side_effect = [
            probe_wham_usage.ProbeError("429 too many requests", retryable=True),
            probe_wham_usage.ProbeError("429 too many requests again", retryable=True),
        ]
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "error")
        self.assertTrue(result.retried)
        self.assertEqual(mock_fetch_usage.call_count, 2)

    @patch("probe_wham_usage.fetch_usage")
    @patch("probe_wham_usage.load_tokens")
    async def test_immediate_success_no_retry(self, mock_load_tokens, mock_fetch_usage):
        mock_load_tokens.return_value = ("tok", None)
        mock_fetch_usage.return_value = (200, _PAYLOAD)
        provider = JsonUsageProvider(retry_delay=0)
        result = await provider.fetch()
        self.assertEqual(result.status, "ok")
        self.assertFalse(result.retried)
        self.assertEqual(mock_fetch_usage.call_count, 1)
        self.assertEqual(result.fields["weekly_percent"], "84")


if __name__ == "__main__":
    unittest.main()
