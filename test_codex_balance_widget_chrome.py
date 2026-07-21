"""Unit tests for pure helpers in codex_balance_widget_chrome.py.

Stdlib unittest only. No Tkinter, no Chrome/Playwright launch — only
top-level pure functions and dataclasses are imported and exercised
(module import itself pulls in playwright.async_api at import time,
which is fine and does not start a browser).
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from codex_balance_widget_chrome import (
    Balance,
    CodexBalanceWidget,
    FetchResult,
    build_balance_from_json_fields,
    parse_reset_datetime,
    plan_fetch_outcome,
    tr,
)
from json_usage_provider import JsonFetchResult

CHROME_TEXT_WITH_USAGE = (
    "5-hour usage limit 87% remaining Weekly usage limit 42% remaining Credits remaining 12"
)
CHROME_TEXT_NO_USAGE = "nothing relevant here at all"


class TestParseResetDatetimeIso(unittest.TestCase):
    def test_iso_datetime_parses_full_date(self):
        parsed = parse_reset_datetime("2026-07-27 18:33")
        self.assertEqual(parsed, datetime(2026, 7, 27, 18, 33))

    def test_iso_datetime_parses_start_of_year(self):
        parsed = parse_reset_datetime("2026-01-01 00:05")
        self.assertEqual(parsed, datetime(2026, 1, 1, 0, 5))

    def test_existing_english_absolute_format_still_works(self):
        parsed = parse_reset_datetime("Reset Jun 7, 2026 18:33")
        self.assertEqual(parsed, datetime(2026, 6, 7, 18, 33))

    def test_existing_time_only_format_still_works(self):
        parsed = parse_reset_datetime("Сброс 20:48")
        self.assertIsNotNone(parsed)

    def test_none_input_returns_none(self):
        self.assertIsNone(parse_reset_datetime(None))

    def test_garbage_text_returns_none(self):
        self.assertIsNone(parse_reset_datetime("мусор без даты"))


class TestBuildBalanceFromJsonFields(unittest.TestCase):
    def test_maps_json_fields_onto_balance(self):
        fields = {
            "five_hour_percent": None,
            "weekly_percent": "84",
            "credits": "0",
            "five_hour_reset_text": None,
            "weekly_reset_text": "2026-07-27 18:33",
            "windows": [],
            "missing": ["five_hour"],
        }
        balance = build_balance_from_json_fields(fields)
        self.assertEqual(
            balance,
            Balance(
                five_hour_percent=None,
                weekly_percent="84",
                credits="0",
                five_hour_reset_text=None,
                weekly_reset_text="2026-07-27 18:33",
            ),
        )

    def test_ignores_extra_keys_without_raising(self):
        fields = {
            "five_hour_percent": "10",
            "weekly_percent": "20",
            "credits": "5",
            "five_hour_reset_text": "2026-07-27 18:33",
            "weekly_reset_text": "2026-08-01 00:00",
            "windows": [{"foo": "bar"}],
            "missing": [],
        }
        balance = build_balance_from_json_fields(fields)
        self.assertEqual(balance.five_hour_percent, "10")
        self.assertEqual(balance.weekly_percent, "20")


class TestPlanFetchOutcome(unittest.TestCase):
    LANGUAGE = "en"

    def test_json_ok_weekly_exhausted(self):
        outcome = plan_fetch_outcome(
            json_status="ok",
            json_fields={
                "five_hour_percent": "50",
                "weekly_percent": "0",
                "credits": "10",
                "five_hour_reset_text": None,
                "weekly_reset_text": None,
            },
            json_error=None,
            chrome_attempted=False,
            chrome_status=None,
            chrome_error=None,
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(outcome.source, "json")
        self.assertEqual(outcome.balance.weekly_percent, "0")
        self.assertEqual(
            outcome.status_message,
            tr(self.LANGUAGE, "Codex unavailable: weekly limit exhausted", "Codex недоступен: недельный лимит исчерпан"),
        )
        self.assertIn("source: json", outcome.log_line)

    def test_json_ok_weekly_not_exhausted(self):
        outcome = plan_fetch_outcome(
            json_status="ok",
            json_fields={
                "five_hour_percent": "50",
                "weekly_percent": "50",
                "credits": "10",
                "five_hour_reset_text": None,
                "weekly_reset_text": None,
            },
            json_error=None,
            chrome_attempted=False,
            chrome_status=None,
            chrome_error=None,
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(
            outcome.status_message,
            tr(self.LANGUAGE, "Data is up to date", "Данные актуальны"),
        )
        self.assertIn("source: json", outcome.log_line)

    def test_json_ok_empty_fields_falls_back_not_json_source(self):
        # CR-01 regression: a structurally-valid JSON body with no
        # recognizable usage fields (e.g. `{}`, or a schema change) must not
        # be treated as a successful "json" source update -- it should fall
        # through the same path as a JSON error.
        outcome = plan_fetch_outcome(
            json_status="ok",
            json_fields={},
            json_error=None,
            chrome_attempted=False,
            chrome_status=None,
            chrome_error=None,
            chrome_text=None,
            has_existing_data=True,
            language=self.LANGUAGE,
        )
        self.assertNotEqual(outcome.source, "json")
        self.assertEqual(outcome.source, "none")
        self.assertIsNone(outcome.balance)

    def test_json_error_chrome_not_attempted(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=False,
            chrome_status=None,
            chrome_error=None,
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(outcome.source, "none")
        self.assertIsNone(outcome.balance)
        self.assertEqual(
            outcome.status_message,
            tr(self.LANGUAGE, "Google Chrome not found. Set CHROME_PATH.", "Google Chrome не найден. Укажите CHROME_PATH."),
        )
        self.assertNotIn("source: json", outcome.log_line)
        self.assertNotIn("source: chrome", outcome.log_line)

    def test_json_error_chrome_ok_with_usage(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="ok",
            chrome_error=None,
            chrome_text=CHROME_TEXT_WITH_USAGE,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(outcome.source, "chrome")
        self.assertIsNotNone(outcome.balance)
        self.assertTrue(outcome.status_message.endswith(" · " + tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк")))
        self.assertIn("source: chrome", outcome.log_line)

    def test_json_error_chrome_ok_no_usage_has_existing_data(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="ok",
            chrome_error=None,
            chrome_text=CHROME_TEXT_NO_USAGE,
            has_existing_data=True,
            language=self.LANGUAGE,
        )
        expected = (
            tr(self.LANGUAGE, "Showing last saved data · new data not recognized", "Показаны последние данные · новые не распознаны")
            + " · "
            + tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк")
        )
        self.assertEqual(outcome.status_message, expected)
        self.assertIsNone(outcome.balance)
        self.assertEqual(outcome.source, "none")

    def test_json_error_chrome_browser_error_no_existing_data(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="browser_error",
            chrome_error="boom",
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(
            outcome.status_message,
            tr(self.LANGUAGE, "Chrome failed to start. See widget_launch.log", "Chrome не запустился. Подробности в widget_launch.log"),
        )
        self.assertNotIn(tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк"), outcome.status_message)

    def test_json_error_chrome_login_required(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="login_required",
            chrome_error=None,
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        self.assertEqual(
            outcome.status_message,
            tr(self.LANGUAGE, "Sign in to ChatGPT. Click Refresh to open Chrome.", "Нужен вход в ChatGPT. Нажмите Обновить, чтобы открыть Chrome."),
        )
        self.assertNotIn(tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк"), outcome.status_message)

    def test_json_error_chrome_not_ready_no_existing_data(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="not_ready",
            chrome_error=None,
            chrome_text=None,
            has_existing_data=False,
            language=self.LANGUAGE,
        )
        expected = (
            tr(self.LANGUAGE, "Usage data timed out. Click Refresh.", "Не дождался данных Usage. Нажмите Обновить.")
            + " · "
            + tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк")
        )
        self.assertEqual(outcome.status_message, expected)

    def test_json_error_chrome_fail_has_existing_data(self):
        outcome = plan_fetch_outcome(
            json_status="error",
            json_fields=None,
            json_error="some json error",
            chrome_attempted=True,
            chrome_status="not_ready",
            chrome_error=None,
            chrome_text=None,
            has_existing_data=True,
            language=self.LANGUAGE,
        )
        self.assertTrue(
            outcome.status_message.startswith(
                tr(self.LANGUAGE, "Showing last saved data · refresh failed", "Показаны последние данные · обновить не удалось")
            )
        )
        self.assertTrue(outcome.status_message.endswith(tr(self.LANGUAGE, "Chrome fallback", "Chrome-фолбэк")))


class TestFetchOnceJsonOkNoUsageDataFallback(unittest.TestCase):
    """Integration-level regression test for WR-03 / CR-01.

    `TestPlanFetchOutcome` above only exercises the pure `plan_fetch_outcome()`
    decision function -- it never touches `fetch_once()`'s own glue code,
    which is where the original CR-01 defect actually lived (a hardcoded
    `chrome_attempted=False` on any JSON "ok" status, regardless of whether
    the JSON body had usable fields). These tests instantiate
    `CodexBalanceWidget` via `__new__` (skipping `__init__`, so no Tk root,
    event loop thread, or Chrome discovery is needed) and drive `fetch_once()`
    directly with a mocked `json_provider` and `browser`, so a future
    regression to the `json_ok_with_data` check in `fetch_once()` itself
    (e.g. reverting it back to a bare `json_result.status == "ok"` check)
    would fail these tests even though `plan_fetch_outcome()` remains
    correct and `TestPlanFetchOutcome` keeps passing.
    """

    LANGUAGE = "en"

    def _make_widget(self, *, json_result: JsonFetchResult, browser_fetch_result: FetchResult | None):
        widget = CodexBalanceWidget.__new__(CodexBalanceWidget)
        widget.refresh_in_progress = False
        widget.language = self.LANGUAGE
        widget.current_balance = Balance()
        widget.last_successful_update = None
        widget.last_fetch_status = None
        widget.last_fetch_error = None
        widget.last_usage_text_length = None
        widget.json_provider = MagicMock()
        widget.json_provider.fetch = AsyncMock(return_value=json_result)
        if browser_fetch_result is not None:
            widget.browser = MagicMock()
            widget.browser.fetch = AsyncMock(return_value=browser_fetch_result)
        else:
            widget.browser = None
        widget.set_status = MagicMock()
        widget.update_balance_ui = MagicMock()
        return widget

    @patch("codex_balance_widget_chrome.write_log")
    def test_json_ok_empty_fields_with_browser_attempts_chrome_fallback(self, mock_write_log):
        # CR-01 regression: JSON reports "ok" but with no recognizable usage
        # fields, and a browser fallback IS configured -- fetch_once() must
        # actually await self.browser.fetch() instead of short-circuiting on
        # the JSON "ok" status alone.
        json_result = JsonFetchResult("ok", fields={})
        browser_result = FetchResult("not_ready")
        widget = self._make_widget(json_result=json_result, browser_fetch_result=browser_result)

        asyncio.run(widget.fetch_once())

        widget.browser.fetch.assert_awaited_once()
        self.assertNotEqual(widget.last_fetch_status, "chrome_not_found")
        mock_write_log.assert_called_once()

    @patch("codex_balance_widget_chrome.write_log")
    def test_json_ok_empty_fields_without_browser_reports_chrome_not_found(self, mock_write_log):
        # Same JSON-ok-but-empty input, but no browser configured at all --
        # fetch_once() should fall into the "Chrome not found" leg (which
        # only makes sense once the JSON "ok" result has already been
        # correctly treated as not-a-real-success).
        json_result = JsonFetchResult("ok", fields={})
        widget = self._make_widget(json_result=json_result, browser_fetch_result=None)

        asyncio.run(widget.fetch_once())

        self.assertEqual(widget.last_fetch_status, "chrome_not_found")
        self.assertEqual(
            widget.last_fetch_error,
            tr(self.LANGUAGE, "Google Chrome not found", "Google Chrome не найден"),
        )
        mock_write_log.assert_called_once()

    @patch("codex_balance_widget_chrome.write_log")
    def test_json_ok_with_usage_data_skips_chrome_fallback(self, mock_write_log):
        # Sanity check on the other side of the branch: a genuinely usable
        # JSON payload must NOT trigger the Chrome fallback, even when a
        # browser is configured.
        json_result = JsonFetchResult(
            "ok",
            fields={
                "five_hour_percent": "50",
                "weekly_percent": "50",
                "credits": "10",
                "five_hour_reset_text": None,
                "weekly_reset_text": None,
            },
        )
        browser_result = FetchResult("not_ready")
        widget = self._make_widget(json_result=json_result, browser_fetch_result=browser_result)

        asyncio.run(widget.fetch_once())

        widget.browser.fetch.assert_not_awaited()
        self.assertEqual(widget.last_fetch_status, "ok")


if __name__ == "__main__":
    unittest.main()
