from __future__ import annotations

import unittest

from usage_widget_common.fetch_decision import decide_fetch_source


class TestDecideFetchSource(unittest.TestCase):
    def test_primary_ok_wins_even_when_fallback_and_existing_data_also_true(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=True, fallback_ok=True, has_existing_data=True
            ).source,
            "primary",
        )

    def test_primary_ok_wins_even_when_fallback_and_existing_data_both_false(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=True, fallback_ok=False, has_existing_data=False
            ).source,
            "primary",
        )

    def test_fallback_wins_when_existing_data_true(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=False, fallback_ok=True, has_existing_data=True
            ).source,
            "fallback",
        )

    def test_fallback_wins_when_existing_data_false(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=False, fallback_ok=True, has_existing_data=False
            ).source,
            "fallback",
        )

    def test_retains_existing_data_when_both_fail_but_data_exists(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=False, fallback_ok=False, has_existing_data=True
            ).source,
            "retain_existing",
        )

    def test_none_when_both_fail_and_no_existing_data(self) -> None:
        self.assertEqual(
            decide_fetch_source(
                primary_ok=False, fallback_ok=False, has_existing_data=False
            ).source,
            "none",
        )


if __name__ == "__main__":
    unittest.main()
