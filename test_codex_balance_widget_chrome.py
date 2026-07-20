"""Unit tests for pure helpers in codex_balance_widget_chrome.py.

Stdlib unittest only. No Tkinter, no Chrome/Playwright launch — only
top-level pure functions and dataclasses are imported and exercised
(module import itself pulls in playwright.async_api at import time,
which is fine and does not start a browser).
"""

from __future__ import annotations

import unittest
from datetime import datetime

from codex_balance_widget_chrome import (
    Balance,
    build_balance_from_json_fields,
    parse_reset_datetime,
    plan_fetch_outcome,
    tr,
)

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


if __name__ == "__main__":
    unittest.main()
