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
)


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


if __name__ == "__main__":
    unittest.main()
