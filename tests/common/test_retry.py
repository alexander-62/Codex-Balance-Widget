from __future__ import annotations

import unittest
from unittest.mock import AsyncMock

from usage_widget_common.errors import FetchError
from usage_widget_common.retry import fetch_with_retry_once


class TestFetchWithRetryOnce(unittest.IsolatedAsyncioTestCase):
    async def test_success_on_first_attempt(self) -> None:
        fetch_once = AsyncMock(side_effect=["value-1"])

        outcome = await fetch_with_retry_once(fetch_once, retry_delay=0)

        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.value, "value-1")
        self.assertFalse(outcome.retried)
        self.assertEqual(fetch_once.await_count, 1)

    async def test_non_retryable_fetch_error_fails_after_one_attempt(self) -> None:
        fetch_once = AsyncMock(side_effect=[FetchError("msg", retryable=False)])

        outcome = await fetch_with_retry_once(fetch_once, retry_delay=0)

        self.assertEqual(outcome.status, "error")
        self.assertFalse(outcome.retried)
        self.assertEqual(fetch_once.await_count, 1)
        self.assertIn("msg", outcome.error or "")

    async def test_plain_exception_is_treated_as_non_retryable(self) -> None:
        fetch_once = AsyncMock(side_effect=[ValueError("boom")])

        outcome = await fetch_with_retry_once(fetch_once, retry_delay=0)

        self.assertEqual(outcome.status, "error")
        self.assertFalse(outcome.retried)
        self.assertEqual(fetch_once.await_count, 1)
        self.assertIn("ValueError", outcome.error or "")
        self.assertIn("boom", outcome.error or "")

    async def test_retryable_error_then_success(self) -> None:
        fetch_once = AsyncMock(
            side_effect=[FetchError("transient", retryable=True), "value-2"]
        )

        outcome = await fetch_with_retry_once(fetch_once, retry_delay=0)

        self.assertEqual(outcome.status, "ok")
        self.assertEqual(outcome.value, "value-2")
        self.assertTrue(outcome.retried)
        self.assertEqual(fetch_once.await_count, 2)

    async def test_retryable_error_twice_chains_both_messages(self) -> None:
        fetch_once = AsyncMock(
            side_effect=[
                FetchError("first failure", retryable=True),
                FetchError("second failure", retryable=True),
            ]
        )

        outcome = await fetch_with_retry_once(fetch_once, retry_delay=0)

        self.assertEqual(outcome.status, "error")
        self.assertTrue(outcome.retried)
        self.assertEqual(fetch_once.await_count, 2)
        self.assertEqual(outcome.error, "first failure; retry: second failure")


if __name__ == "__main__":
    unittest.main()
